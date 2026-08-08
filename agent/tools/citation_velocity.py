"""Weekly citation-velocity re-poll (deep sweep only).

Reuses the change-0012 Semantic Scholar integration patterns (S2_API_KEY,
429 backoff-then-skip, polite pacing) but hits the batch endpoint. Fully
config-gated + fail-soft: disabled => never called; any error => no-op.
"""

import datetime
import os
import re
import time
from pathlib import Path

import httpx
import yaml

S2_BATCH_API = "https://api.semanticscholar.org/graph/v1/paper/batch"
BACKOFF_SECONDS = 2
_ARXIV = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
# Only recognize a DOI from a genuine (dx.)doi.org context so an incidental
# /10.NNNN/ segment inside an ordinary URL is not read as a DOI paper id.
_DOI = re.compile(
    r"(?:^|//|\.)(?:dx\.)?doi\.org/(10\.\d{4,9}/[^\s?#)]+)",
    re.IGNORECASE,
)


def paper_ids_from_note(text: str) -> str | None:
    m = _ARXIV.search(text)
    if m:
        return f"ARXIV:{m.group(1)}"
    m = _DOI.search(text)
    if m:
        return f"DOI:{m.group(1).lower().rstrip('/')}"
    return None


def fetch_citation_counts(ids: list[str], *, api_key: str | None) -> dict[str, int]:
    if not ids:
        return {}
    key = api_key or os.getenv("S2_API_KEY")
    headers = {"x-api-key": key} if key else {}
    for attempt in range(2):
        try:
            resp = httpx.post(
                S2_BATCH_API,
                params={"fields": "citationCount,externalIds"},
                json={"ids": ids},
                headers=headers,
                timeout=15,
            )
        except Exception:
            return {}
        if getattr(resp, "status_code", None) == 429:
            if attempt == 0:
                time.sleep(BACKOFF_SECONDS)
                continue
            return {}
        try:
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return {}
        out: dict[str, int] = {}
        for req_id, paper in zip(ids, data if isinstance(data, list) else []):
            if isinstance(paper, dict) and paper.get("citationCount") is not None:
                out[req_id] = paper["citationCount"]
        return out
    return {}


def _iter_notes(vault_path: Path):
    for sub in ("research", "benchmarks"):
        d = Path(vault_path) / "strategies" / sub
        if d.exists():
            yield from d.glob("*.md")


def run_citation_velocity(vault_path, *, min_delta: int, api_key: str | None, today: str | None = None) -> int:
    today = today or str(datetime.date.today())
    try:
        notes: list[tuple[Path, str, str, dict]] = []
        ids: list[str] = []
        for note in _iter_notes(vault_path):
            try:
                text = note.read_text()
                parts = text.split("---")
                fm = yaml.safe_load(parts[1]) if len(parts) >= 3 else {}
            except Exception:
                continue
            pid = paper_ids_from_note(text)
            if not pid:
                continue
            notes.append((note, text, pid, fm or {}))
            ids.append(pid)
        if not ids:
            return 0
        counts = fetch_citation_counts(ids, api_key=api_key)
        if not counts:
            return 0
        flagged = 0
        for note, text, pid, fm in notes:
            new_count = counts.get(pid)
            if new_count is None:
                continue
            prev = fm.get("citation_count")
            delta = new_count - prev if isinstance(prev, int) else 0
            rising = isinstance(prev, int) and delta >= min_delta
            try:
                _rewrite_frontmatter(note, text, {
                    "citation_count": new_count,
                    "citation_delta": delta,
                    "citation_checked": today,
                    "rising": rising,
                })
            except Exception as exc:
                print(f"[warn] citation_velocity: {note}: {exc}")
                continue
            if rising:
                flagged += 1
        return flagged
    except Exception as exc:  # fail-soft: never abort the sweep
        print(f"[warn] citation_velocity: {exc}")
        return 0


def _rewrite_frontmatter(note: Path, text: str, updates: dict):
    lines = text.splitlines()
    # locate the frontmatter block (first two --- fences)
    fences = [i for i, l in enumerate(lines) if l.strip() == "---"]
    if len(fences) < 2:
        return
    start, end = fences[0], fences[1]
    keys_seen = set()
    for i in range(start + 1, end):
        key = lines[i].split(":", 1)[0].strip()
        if key in updates:
            val = updates[key]
            lines[i] = f"{key}: {str(val).lower() if isinstance(val, bool) else val}"
            keys_seen.add(key)
    inserts = [
        f"{k}: {str(v).lower() if isinstance(v, bool) else v}"
        for k, v in updates.items() if k not in keys_seen
    ]
    lines[end:end] = inserts
    note.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""))
