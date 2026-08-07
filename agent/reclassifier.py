# agent/reclassifier.py
"""Retroactive re-classification of existing vault notes.

Reads existing vault notes (old pre-type-system schema or new schema alike),
runs them through the three-pass Evaluator, rewrites their frontmatter to the
new schema, and moves each note into the correct type subdirectory. Does NOT
touch the deduplicator index — this is a metadata update, not an ingest.
"""
import datetime
from pathlib import Path

import yaml

# Represent date/datetime objects as plain strings when dumping frontmatter.
def _str_representer(dumper, val):
    return dumper.represent_str(str(val))

class _YamlDumper(yaml.SafeDumper):
    pass

_YamlDumper.add_representer(datetime.date, _str_representer)
_YamlDumper.add_representer(datetime.datetime, _str_representer)

from agent.evaluator import Evaluator
from agent.models import RawItem
from agent.regenerator import extract_first_source_url, split_note
from agent.writer import TYPE_DIRS, Writer

# Frontmatter keys the evaluator owns and we rewrite; everything else is preserved.
_MANAGED_KEYS = {"type", "score", "score_label", "category", "tags", "novelty"}


class Reclassifier:
    def __init__(self, vault_path, api_key: str | None = None,
                 llm_cfg: dict | None = None):
        self._vault = Path(vault_path)
        self._strategies = self._vault / "strategies"
        self._evaluator = Evaluator(api_key=api_key, llm_cfg=llm_cfg)
        self._writer = Writer(vault_path=self._vault)

    def reclassify(self, date: str | None = None, all_notes: bool = False) -> dict:
        report = {"reclassified": 0, "moved": 0, "errored": 0}
        notes = self._collect_notes(date, all_notes)
        items: list[tuple[Path, dict, str, RawItem]] = []
        for path in notes:
            try:
                fm, body = split_note(path.read_text())
                if not fm:
                    continue
                item = self._build_item(fm, body, path)
                items.append((path, fm, body, item))
            except Exception as exc:  # one bad note must not abort the batch
                print(f"[warn] reclassify read failed for {path.name}: {exc}")
                report["errored"] += 1

        if items:
            self._evaluator.score([it for (_, _, _, it) in items])

        for path, fm, body, item in items:
            try:
                moved = self._rewrite_and_move(path, fm, item)
                report["reclassified"] += 1
                if moved:
                    report["moved"] += 1
            except Exception as exc:
                print(f"[warn] reclassify write failed for {path.name}: {exc}")
                report["errored"] += 1

        try:
            self._writer.regenerate_index()
        except Exception as exc:
            print(f"[warn] index regeneration failed: {exc}")
        return report

    def _collect_notes(self, date: str | None, all_notes: bool) -> list[Path]:
        if not self._strategies.exists():
            return []
        notes = sorted(self._strategies.glob("**/*.md"))
        if all_notes:
            return notes
        target = date or str(datetime.date.today() - datetime.timedelta(days=1))
        return [p for p in notes if p.name.startswith(target)]

    def _build_item(self, fm: dict, body: str, path: Path) -> RawItem:
        return RawItem(
            title=str(fm.get("title", path.stem)),
            body=body,
            url=extract_first_source_url(body) or str(fm.get("url", "")),
            source=str(fm.get("source", "")),
            engagement=0,
            timestamp=str(fm.get("date", "")),
            content_type=str(fm.get("type", "research")),
            score=int(fm.get("score", fm.get("novelty", 0)) or 0),
            score_label=str(fm.get("score_label", "novelty")),
            validated=bool(fm.get("validated", False)),
            sources_count=int(fm.get("sources_count", 1)),
            category=str(fm.get("category", "")),
            tags=list(fm.get("tags", []) or []),
        )

    def _rewrite_and_move(self, path: Path, fm: dict, item: RawItem) -> bool:
        new_fm = {k: v for k, v in fm.items() if k not in _MANAGED_KEYS}
        new_fm["type"] = item.content_type
        new_fm["score"] = item.score
        new_fm["score_label"] = item.score_label
        new_fm["tags"] = item.tags
        if item.content_type == "research" and item.category:
            new_fm["category"] = item.category

        # Rebuild the file: rewritten frontmatter + original body verbatim.
        body = path.read_text().split("---", 2)[2].lstrip("\n")
        fm_text = yaml.dump(new_fm, Dumper=_YamlDumper, sort_keys=True, allow_unicode=True).strip()
        content = f"---\n{fm_text}\n---\n\n{body}"

        subdir = TYPE_DIRS.get(item.content_type, item.content_type)
        dest_dir = self._strategies / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        moved = dest.resolve() != path.resolve()
        if moved and dest.exists():
            dest = dest_dir / f"{path.stem}-2{path.suffix}"

        dest.write_text(content)
        if moved and path.exists():
            path.unlink()
        return moved
