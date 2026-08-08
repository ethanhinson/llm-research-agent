import json
from datetime import datetime, timezone
from pathlib import Path

from thefuzz import fuzz

from agent.models import RawItem

FUZZY_THRESHOLD = 90
DEFAULT_WINDOW_HOURS = 72


class Deduplicator:
    def __init__(self, index_path: Path, window_hours: int = DEFAULT_WINDOW_HOURS):
        self._path = Path(index_path)
        self.window_hours = window_hours
        self._index: dict = self._load()

    def _load(self) -> dict:
        default = {"urls": [], "titles": [], "items": {}}
        if self._path.exists():
            data = json.loads(self._path.read_text())
            merged = {**default, **{k: v for k, v in data.items() if k in default}}
            # a v1 index has no "items" -> stays the default empty map
            if not isinstance(merged.get("items"), dict):
                merged["items"] = {}
            return merged
        return default

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._index, indent=2))

    def _known(self, item: RawItem):
        cid = item.canonical_id or ""
        return self._index["items"].get(cid) if cid else None

    def is_duplicate(self, item: RawItem) -> bool:
        rec = self._known(item)
        if rec is not None:
            # known identity: duplicate unless it is a within-window NEW source
            if self.corroboration_update(item, _peek=True) is not None:
                return False
            return True
        if item.url in self._index["urls"]:
            return True
        for seen_title in self._index["titles"]:
            if fuzz.ratio(item.title.lower(), seen_title.lower()) >= FUZZY_THRESHOLD:
                return True
        return False

    def record(self, item: RawItem, note_path: str):
        cid = item.canonical_id or ""
        if cid:
            self._index["items"][cid] = {
                "sources": sorted(
                    {item.source} | {s for (s, _u, _e) in item.corroboration_sources}
                ),
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "note_path": note_path,
                "title": item.title,
            }
        if item.url not in self._index["urls"]:
            self._index["urls"].append(item.url)
        if item.title not in self._index["titles"]:
            self._index["titles"].append(item.title)
        self._save()

    def corroboration_update(self, item: RawItem, _peek: bool = False):
        rec = self._known(item)
        if rec is None:
            return None
        try:
            first_seen = datetime.fromisoformat(rec["first_seen"])
        except Exception:
            return None
        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - first_seen).total_seconds() / 3600.0
        if age_h > self.window_hours:
            return None
        if item.source in rec["sources"]:
            return None
        if not _peek:
            rec["sources"].append(item.source)
            self._save()
        # When _peek=False the source was just appended, so len already includes
        # it. When _peek=True nothing was appended, so add 1 for the would-be count.
        sources_count = len(rec["sources"]) if _peek is False else len(rec["sources"]) + 1
        new_line = f"- [{item.title}]({item.url}) — {item.source} · {item.engagement}"
        return {
            "note_path": rec["note_path"],
            "sources_count": sources_count,
            "validated": sources_count >= 2,
            "new_source_line": new_line,
        }

    def mark_seen(self, item: RawItem):
        # legacy no-op-safe path retained for callers not yet on record();
        # record() is the canonical writer now.
        if item.url not in self._index["urls"]:
            self._index["urls"].append(item.url)
        if item.title not in self._index["titles"]:
            self._index["titles"].append(item.title)
        self._save()
