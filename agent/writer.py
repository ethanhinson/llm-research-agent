import re
import datetime
import yaml
from pathlib import Path

from agent.models import RawItem

CONTENT_TYPES = ["research", "release", "news", "benchmark", "tutorial"]

TYPE_DIRS = {
    "research": "research",
    "release": "releases",
    "news": "news",
    "benchmark": "benchmarks",
    "tutorial": "tutorials",
}


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:60]


NOTE_TEMPLATE = """\
---
title: "{title}"
date: {date}
type: {content_type}
score: {score}
score_label: {score_label}
{category_line}tags: [{tags}]
validated: {validated}
sources_count: {sources_count}
content_source: {content_source}
status: new
---

# {title}

## Summary
{summary}

## How It Works
{how_it_works}

## Why It Matters
{why_it_matters}

## Sources
- [{source_label}]({url}) — {source} · {engagement}

## Related
"""


class Writer:
    def __init__(self, vault_path: Path, date: str | None = None):
        self._vault = Path(vault_path)
        self._date = date or str(datetime.date.today())
        self._strategies_dir = self._vault / "strategies"
        self._strategies_dir.mkdir(parents=True, exist_ok=True)
        for subdir in TYPE_DIRS.values():
            (self._strategies_dir / subdir).mkdir(parents=True, exist_ok=True)

    def write_note(self, item: RawItem, sections: dict | None = None) -> Path:
        slug = _slugify(item.title)
        filename = f"{self._date}-{slug}.md"
        subdir = TYPE_DIRS.get(item.content_type, item.content_type)
        path = self._strategies_dir / subdir / filename

        tags_str = ", ".join(item.tags) if item.tags else item.content_type

        # Legacy template fill-ins (used when no synthesized section is present).
        body = item.body[:500]
        first_sentence_end = body.find(". ")
        legacy_summary = (
            body[:first_sentence_end + 1] if first_sentence_end != -1 else body[:150]
        ) or body
        legacy_why = (
            f"Engagement: {item.engagement} signals. "
            f"Cross-source validated: {str(item.validated).lower()}."
        )

        sections = sections or {}
        summary = sections.get("summary") or legacy_summary
        how_it_works = sections.get("how_it_works") or body
        why_it_matters = sections.get("why_it_matters") or legacy_why

        category_line = (
            f"category: {item.category}\n"
            if item.content_type == "research" and item.category
            else ""
        )

        content = NOTE_TEMPLATE.format(
            title=item.title.replace('"', '\\"'),
            date=self._date,
            content_type=item.content_type,
            score=item.score,
            score_label=item.score_label,
            category_line=category_line,
            tags=tags_str,
            validated=str(item.validated).lower(),
            sources_count=item.sources_count,
            content_source=item.content_source,
            summary=summary,
            how_it_works=how_it_works,
            why_it_matters=why_it_matters,
            engagement=item.engagement,
            source_label=item.title,
            url=item.url,
            source=item.source,
        )
        path.write_text(content)
        return path

    def regenerate_index(self):
        groups: dict[str, list[tuple]] = {t: [] for t in CONTENT_TYPES}

        for content_type, subdir in TYPE_DIRS.items():
            type_dir = self._strategies_dir / subdir
            if not type_dir.exists():
                continue
            for note_path in sorted(type_dir.glob("*.md"), reverse=True):
                content = note_path.read_text()
                parts = content.split("---")
                if len(parts) < 3:
                    continue
                try:
                    fm = yaml.safe_load(parts[1])
                except Exception:
                    continue
                title = fm.get("title", note_path.stem)
                score = fm.get("score", 0)
                validated = fm.get("validated", False)
                category = fm.get("category", "")
                link = f"[[strategies/{subdir}/{note_path.name}|{title}]]"
                groups[content_type].append((score, title, link, validated, category))

        lines = ["# Strategy Index\n"]

        section_meta = [
            ("research",  "Research",   ["Sub-category", "Novelty",       "Validated"]),
            ("release",   "Releases",   ["Significance", "Validated"]),
            ("news",      "News",       ["Timeliness"]),
            ("benchmark", "Benchmarks", ["Authority",    "Validated"]),
            ("tutorial",  "Tutorials",  ["Practicality"]),
        ]

        for content_type, heading, extra_cols in section_meta:
            rows = groups.get(content_type, [])
            if not rows:
                continue
            rows.sort(key=lambda r: -r[0])
            lines.append(f"## {heading}\n")
            col_headers = ["Title"] + extra_cols
            lines.append("| " + " | ".join(col_headers) + " |")
            lines.append("|" + "---|" * len(col_headers))
            for score, title, link, validated, category in rows:
                if content_type == "research":
                    lines.append(f"| {link} | {category} | {score} | {validated} |")
                elif content_type in ("release", "benchmark"):
                    lines.append(f"| {link} | {score} | {validated} |")
                else:
                    lines.append(f"| {link} | {score} |")
            lines.append("")

        (self._vault / "index.md").write_text("\n".join(lines) + "\n")
