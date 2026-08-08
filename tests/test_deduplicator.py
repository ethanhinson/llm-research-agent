import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent.models import RawItem
from agent.deduplicator import Deduplicator


@pytest.fixture
def index_path(tmp_path):
    return tmp_path / ".index.json"


def make_item(title, url, source="hn"):
    return RawItem(title=title, body="body", url=url, source=source, engagement=200, timestamp="2026-08-01")


def test_new_item_passes(index_path):
    d = Deduplicator(index_path)
    item = make_item("Speculative Decoding explained", "https://example.com/1")
    assert d.is_duplicate(item) is False


def test_exact_url_dedup(index_path):
    d = Deduplicator(index_path)
    item = make_item("Speculative Decoding explained", "https://example.com/1")
    d.mark_seen(item)
    item2 = make_item("Different title", "https://example.com/1")
    assert d.is_duplicate(item2) is True


def test_fuzzy_title_dedup(index_path):
    d = Deduplicator(index_path)
    item = make_item("Speculative Decoding: A Deep Dive", "https://example.com/1")
    d.mark_seen(item)
    # Very similar title from different URL
    item2 = make_item("Speculative Decoding: A Deep Dive!", "https://example.com/2")
    assert d.is_duplicate(item2) is True


def test_dissimilar_title_passes(index_path):
    d = Deduplicator(index_path)
    item = make_item("Flash Attention 3 released", "https://example.com/1")
    d.mark_seen(item)
    item2 = make_item("Chain-of-Thought prompting survey", "https://example.com/2")
    assert d.is_duplicate(item2) is False


def test_index_persists(index_path):
    d1 = Deduplicator(index_path)
    item = make_item("Persistent item", "https://example.com/persist")
    d1.mark_seen(item)

    d2 = Deduplicator(index_path)
    item2 = make_item("Different title", "https://example.com/persist")
    assert d2.is_duplicate(item2) is True


# --- Task 3: schema v2 + cross-sweep corroboration ---


def _rec_item(cid, source, url="https://arxiv.org/abs/2410.12345", title="Paper"):
    it = RawItem(title=title, body="", url=url, source=source, engagement=10, timestamp="2026-08-01")
    it.canonical_id = cid
    return it


def test_v1_index_migrates_to_empty_items_map(tmp_path):
    p = tmp_path / ".index.json"
    p.write_text(json.dumps({"urls": ["https://x"], "titles": ["Old"]}))
    d = Deduplicator(p)
    # legacy still readable; items map present and empty
    assert d._index.get("items") == {}
    assert "https://x" in d._index["urls"]


def test_record_new_identity_writes_items_entry(tmp_path):
    p = tmp_path / ".index.json"
    d = Deduplicator(p)
    it = _rec_item("arxiv:2410.12345", "hackernews")
    d.record(it, note_path="research/2026-08-08-paper.md")
    d2 = Deduplicator(p)  # reload from disk
    rec = d2._index["items"]["arxiv:2410.12345"]
    assert rec["sources"] == ["hackernews"]
    assert rec["note_path"] == "research/2026-08-08-paper.md"
    assert "first_seen" in rec


def test_within_window_new_source_returns_update(tmp_path):
    p = tmp_path / ".index.json"
    d = Deduplicator(p, window_hours=72)
    it = _rec_item("arxiv:2410.12345", "hackernews")
    d.record(it, note_path="research/n.md")
    resurface = _rec_item("arxiv:2410.12345", "hf-papers")
    upd = d.corroboration_update(resurface)
    assert upd is not None
    assert upd["note_path"] == "research/n.md"
    assert upd["sources_count"] == 2
    assert upd["validated"] is True
    assert "hf-papers" in upd["new_source_line"]


def test_already_counted_source_no_update(tmp_path):
    p = tmp_path / ".index.json"
    d = Deduplicator(p)
    it = _rec_item("arxiv:2410.12345", "hackernews")
    d.record(it, note_path="research/n.md")
    again = _rec_item("arxiv:2410.12345", "hackernews")
    assert d.corroboration_update(again) is None


def test_outside_window_no_update(tmp_path):
    p = tmp_path / ".index.json"
    d = Deduplicator(p, window_hours=72)
    it = _rec_item("arxiv:2410.12345", "hackernews")
    d.record(it, note_path="research/n.md")
    # backdate first_seen beyond the window
    old = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
    d._index["items"]["arxiv:2410.12345"]["first_seen"] = old
    resurface = _rec_item("arxiv:2410.12345", "hf-papers")
    assert d.corroboration_update(resurface) is None
    assert d.is_duplicate(resurface) is True
