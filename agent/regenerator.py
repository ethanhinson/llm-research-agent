"""In-place backfill of existing vault notes.

Re-fetches each above-threshold note's source, re-synthesizes the three body
sections, and rewrites the note body IN PLACE — frontmatter is preserved
verbatim (with `content_source` added/updated), and the `## Sources` / `##
Related` sections are kept. Below-threshold notes are skipped. Fail-soft: a
fetch failure re-synthesizes from whatever body text already exists.
"""
import re
from pathlib import Path

import yaml

from agent.enricher import ContentEnricher
from agent.models import RawItem
from agent.synthesizer import NoteSynthesizer
from agent.writer import Writer

_SOURCE_URL_RE = re.compile(r"\]\((https?://[^)]+)\)")
# Section headers we rewrite; everything from the first of these up to
# "## Sources" is the synthesized-body region.
_BODY_START_RE = re.compile(r"^## Summary\s*$", re.MULTILINE)
_SOURCES_RE = re.compile(r"^## Sources\s*$", re.MULTILINE)


def split_note(content: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body string after the closing '---')."""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return fm, body


def extract_first_source_url(body: str) -> str | None:
    section = body
    m = _SOURCES_RE.search(body)
    if m:
        section = body[m.end():]
    url_match = _SOURCE_URL_RE.search(section)
    return url_match.group(1) if url_match else None


def _existing_body_text(body: str) -> str:
    """Grab the current '## How It Works' text as fallback synthesis input."""
    m = re.search(r"## How It Works\s*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def _tail_from_sources(body: str) -> str:
    """The '## Sources' section onward, preserved verbatim."""
    m = _SOURCES_RE.search(body)
    return body[m.start():] if m else ""


class Regenerator:
    def __init__(self, vault_path, api_key: str | None = None, min_score: int = 6,
                 max_chars: int = 8000):
        self._vault = Path(vault_path)
        self._strategies = self._vault / "strategies"
        self._min_score = min_score
        self._enricher = ContentEnricher(max_chars=max_chars)
        self._synthesizer = NoteSynthesizer(api_key=api_key)
        self._writer = Writer(vault_path=self._vault)

    def regenerate_all(self) -> dict:
        return self._run(self._all_notes())

    def regenerate(self, date: str | None = None) -> dict:
        notes = self._all_notes()
        if date:
            notes = [p for p in notes if p.name.startswith(date)]
        return self._run(notes)

    def _all_notes(self) -> list[Path]:
        if not self._strategies.exists():
            return []
        return sorted(self._strategies.glob("**/*.md"))

    def _run(self, notes: list[Path]) -> dict:
        report = {"regenerated": 0, "fetch_failed": 0, "skipped": 0,
                  "preserved": 0, "errored": 0}
        source_tally: dict[str, int] = {}
        for path in notes:
            try:
                outcome = self._regenerate_note(path, source_tally)
            except Exception as exc:  # one bad note must not abort the batch
                print(f"[warn] regenerate errored for {path.name}: {exc}")
                outcome = "errored"
            report[outcome] = report.get(outcome, 0) + 1
        try:
            self._writer.regenerate_index()
        except Exception as exc:
            print(f"[warn] index regeneration failed: {exc}")
        report["content_source_by_domain"] = source_tally
        return report

    def _regenerate_note(self, path: Path, source_tally: dict) -> str:
        content = path.read_text()
        fm, body = split_note(content)
        if not fm:
            return "skipped"

        score = fm.get("score", 0)
        if score < self._min_score:
            return "skipped"

        url = extract_first_source_url(body) or ""
        item = RawItem(
            title=str(fm.get("title", path.stem)),
            body=_existing_body_text(body) or str(fm.get("title", "")),
            url=url,
            source="regenerate",
            engagement=0,
            timestamp=str(fm.get("date", "")),
            content_type=str(fm.get("type", "research")),
            score=score,
            score_label=str(fm.get("score_label", "novelty")),
            validated=bool(fm.get("validated", False)),
            sources_count=int(fm.get("sources_count", 1)),
            category=str(fm.get("category", "")),
            tags=list(fm.get("tags", []) or []),
        )

        outcome = "regenerated"
        try:
            if url:
                self._enricher.enrich(item)
        except Exception as exc:  # fail-soft — re-synthesize from existing body
            print(f"[warn] regenerate enrich failed for {path.name}: {exc}")
            outcome = "fetch_failed"

        sections = self._synthesizer.synthesize(item) or {}

        # If synthesis produced nothing AND enrichment did not upgrade the body
        # to full text, we have nothing better than what is already on disk —
        # leave the note untouched rather than clobber it with a title-only body.
        if not sections and item.content_source != "full":
            return "preserved"

        # tally content_source per domain
        domain = _domain(url)
        source_tally[f"{item.content_source}:{domain}"] = (
            source_tally.get(f"{item.content_source}:{domain}", 0) + 1
        )

        new_content = self._rewrite(fm, body, item, sections)
        path.write_text(new_content)
        return outcome

    def _rewrite(self, fm: dict, body: str, item: RawItem, sections: dict) -> str:
        fm = dict(fm)
        fm["content_source"] = item.content_source

        summary = sections.get("summary") or item.body[:200]
        how = sections.get("how_it_works") or item.body[:500]
        why = sections.get("why_it_matters") or (
            f"Cross-source validated: {str(item.validated).lower()}."
        )

        tail = _tail_from_sources(body)
        if not tail:
            tail = "## Sources\n\n## Related\n"

        fm_text = yaml.safe_dump(fm, sort_keys=True, allow_unicode=True).strip()
        return (
            f"---\n{fm_text}\n---\n\n"
            f"# {fm.get('title', item.title)}\n\n"
            f"## Summary\n{summary}\n\n"
            f"## How It Works\n{how}\n\n"
            f"## Why It Matters\n{why}\n\n"
            f"{tail}"
        )


def _domain(url: str) -> str:
    if not url:
        return "(none)"
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1) if m else "(none)"
