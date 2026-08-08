"""Weekly citation-velocity re-poll (deep sweep only).

Citation counts default to OpenAlex, which is keyless: the Semantic Scholar
batch endpoint 429s immediately without an S2_API_KEY, so it is used only when
that key is present. OpenAlex needs no key (an optional ``mailto`` joins its
faster "polite pool"). Fully config-gated + fail-soft: disabled => never
called; any request error => that item is skipped, never aborts the sweep.
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
OPENALEX_API = "https://api.openalex.org/works"
OPENALEX_BATCH = 50  # OpenAlex caps an OR-joined filter at 50 values
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


# --- Keyless citation source: OpenAlex -------------------------------------


def _openalex_doi_for(pid: str) -> str | None:
    """The DOI OpenAlex indexes a paper id under. arXiv papers (>=2022) carry
    the DataCite DOI ``10.48550/arXiv.<id>``; a DOI id maps to itself."""
    if pid.startswith("ARXIV:"):
        return f"10.48550/arxiv.{pid[len('ARXIV:'):].lower()}"
    if pid.startswith("DOI:"):
        return pid[len("DOI:"):].lower()
    return None


def _normalize_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def _openalex_get(params: dict, *, mailto: str | None):
    p = dict(params)
    if mailto:
        p["mailto"] = mailto  # polite pool — optional, still keyless
    resp = httpx.get(OPENALEX_API, params=p, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_citation_counts_openalex(items, *, mailto=None) -> dict[str, int]:
    """Keyless citation counts via OpenAlex. ``items`` is ``[(pid, title)]``.

    Two-tier resolver: batch the DOI lookups first (arXiv ids resolve through
    their ``10.48550/arXiv.<id>`` DOI), then a per-paper ``title.search``
    fallback for the misses — accepted only on an exact normalized-title match,
    since OpenAlex has fragmented/duplicate records. Any request error skips
    that item rather than raising.
    """
    out: dict[str, int] = {}
    doi_to_pid: dict[str, str] = {}
    for pid, _title in items:
        d = _openalex_doi_for(pid)
        if d:
            doi_to_pid[d] = pid
    dois = list(doi_to_pid)
    for i in range(0, len(dois), OPENALEX_BATCH):
        chunk = dois[i:i + OPENALEX_BATCH]
        try:
            data = _openalex_get(
                {"filter": "doi:" + "|".join(chunk),
                 "select": "doi,cited_by_count", "per-page": OPENALEX_BATCH},
                mailto=mailto,
            )
        except Exception:
            continue
        for w in data.get("results", []):
            wd = (w.get("doi") or "").lower().rsplit("doi.org/", 1)[-1]
            pid = doi_to_pid.get(wd)
            if pid and w.get("cited_by_count") is not None:
                out[pid] = w["cited_by_count"]
    for pid, title in items:
        if pid in out or not title:
            continue
        try:
            data = _openalex_get(
                {"filter": f"title.search:{title}",
                 "select": "title,cited_by_count", "per-page": 1},
                mailto=mailto,
            )
        except Exception:
            continue
        results = data.get("results", [])
        if not results:
            continue
        top = results[0]
        if _normalize_title(top.get("title")) == _normalize_title(title) \
                and top.get("cited_by_count") is not None:
            out[pid] = top["cited_by_count"]
    return out


def _citation_counts_for(notes, *, api_key, mailto) -> dict[str, int]:
    """Pick the citation source: keyed Semantic Scholar when a key is available
    (richer data), else keyless OpenAlex (the default)."""
    key = api_key or os.getenv("S2_API_KEY")
    if key:
        return fetch_citation_counts([pid for _n, _t, pid, _fm in notes], api_key=key)
    items = [(pid, fm.get("title") or "") for _n, _t, pid, fm in notes]
    return fetch_citation_counts_openalex(items, mailto=mailto)


def _iter_notes(vault_path: Path):
    for sub in ("research", "benchmarks"):
        d = Path(vault_path) / "strategies" / sub
        if d.exists():
            yield from d.glob("*.md")


def run_citation_velocity(
    vault_path,
    *,
    min_delta: int,
    api_key: str | None,
    today: str | None = None,
    mailto: str | None = None,
) -> int:
    today = today or str(datetime.date.today())
    try:
        notes: list[tuple[Path, str, str, dict]] = []
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
        if not notes:
            return 0
        counts = _citation_counts_for(notes, api_key=api_key, mailto=mailto)
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
