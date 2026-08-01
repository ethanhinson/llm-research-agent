import re
import datetime
import yaml
from pathlib import Path

from agent.models import RawItem

CATEGORIES = ["prompting", "architecture", "agentic", "tooling", "use-case"]


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
category: {category}
tags: [{tags}]
novelty: {novelty}
validated: {validated}
sources_count: {sources_count}
status: new
---

# {title}

## Summary
{summary}

## How It Works
{body}

## Why It's Gaining Traction
Engagement: {engagement} signals. Cross-source validated: {validated}.

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

    def write_note(self, item: RawItem) -> Path:
        slug = _slugify(item.title)
        filename = f"{self._date}-{slug}.md"
        path = self._strategies_dir / filename

        tags_str = ", ".join(item.tags) if item.tags else "emerging"
        body = item.body[:500]
        # Summary: first sentence or up to 150 chars; How It Works: full body
        first_sentence_end = body.find(". ")
        summary = body[:first_sentence_end + 1] if first_sentence_end != -1 else body[:150]

        content = NOTE_TEMPLATE.format(
            title=item.title.replace('"', '\\"'),
            date=self._date,
            category=item.category or "architecture",
            tags=tags_str,
            novelty=item.novelty,
            validated=str(item.validated).lower(),
            sources_count=item.sources_count,
            summary=summary or body,
            body=body,
            engagement=item.engagement,
            source_label=item.title,
            url=item.url,
            source=item.source,
        )
        path.write_text(content)
        return path

    def regenerate_index(self):
        strategies = sorted(
            self._strategies_dir.glob("*.md"),
            key=lambda p: p.name,
            reverse=True,
        )

        rows = []
        for strategy_path in strategies:
            content = strategy_path.read_text()
            parts = content.split("---")
            if len(parts) < 3:
                continue
            try:
                fm = yaml.safe_load(parts[1])
            except Exception:
                continue
            title = fm.get("title", strategy_path.stem)
            category = fm.get("category", "")
            novelty = fm.get("novelty", 0)
            validated = fm.get("validated", False)
            link = f"[[strategies/{strategy_path.name}|{title}]]"
            rows.append((category, novelty, title, link, validated))

        rows.sort(key=lambda r: (r[0], -r[1]))

        lines = ["# Strategy Index\n", "| Title | Category | Novelty | Validated |",
                 "|-------|----------|---------|-----------|"]
        for cat, novelty, title, link, validated in rows:
            lines.append(f"| {link} | {cat} | {novelty} | {validated} |")

        (self._vault / "index.md").write_text("\n".join(lines) + "\n")
