import json
import pytest
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
