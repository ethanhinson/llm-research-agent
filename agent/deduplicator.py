import json
from pathlib import Path

from thefuzz import fuzz

from agent.models import RawItem

FUZZY_THRESHOLD = 90


class Deduplicator:
    def __init__(self, index_path: Path):
        self._path = Path(index_path)
        self._index: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text())
        return {"urls": [], "titles": []}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._index, indent=2))

    def is_duplicate(self, item: RawItem) -> bool:
        if item.url in self._index["urls"]:
            return True
        for seen_title in self._index["titles"]:
            if fuzz.ratio(item.title.lower(), seen_title.lower()) >= FUZZY_THRESHOLD:
                return True
        return False

    def mark_seen(self, item: RawItem):
        if item.url not in self._index["urls"]:
            self._index["urls"].append(item.url)
        if item.title not in self._index["titles"]:
            self._index["titles"].append(item.title)
        self._save()
