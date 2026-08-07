import datetime

import pytest
from unittest.mock import MagicMock

from agent.fetchers.hf_papers import HFPapersAdapter


def _iso(dt: datetime.datetime) -> str:
    # HF returns an ISO string with milliseconds and a trailing Z.
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


NOW = datetime.datetime.now(datetime.timezone.utc)
RECENT = _iso(NOW - datetime.timedelta(days=1))
OLD = _iso(NOW - datetime.timedelta(days=30))


def _payload(entries):
    return MagicMock(json=lambda: entries, raise_for_status=lambda: None)


RECENT_ENTRY = {
    "paper": {
        "id": "2401.12345",
        "title": "A Recent Paper",
        "summary": "A summary of the recent paper.",
        "upvotes": 42,
        "publishedAt": RECENT,
    },
    "publishedAt": RECENT,
}


def test_maps_to_rawitem(mocker):
    mock_get = mocker.patch("httpx.get", return_value=_payload([RECENT_ENTRY]))
    items = HFPapersAdapter().fetch()

    mock_get.assert_called_once()
    assert len(items) == 1
    item = items[0]
    assert item.title == "A Recent Paper"
    assert item.body == "A summary of the recent paper."
    assert item.url == "https://huggingface.co/papers/2401.12345"
    assert item.engagement == 42
    assert item.timestamp == RECENT
    assert item.source == "hf-papers"


def test_body_truncated_to_2000_chars(mocker):
    long_entry = {
        "paper": {
            "id": "2401.99999",
            "title": "Long",
            "summary": "x" * 5000,
            "upvotes": 10,
            "publishedAt": RECENT,
        },
    }
    mocker.patch("httpx.get", return_value=_payload([long_entry]))
    items = HFPapersAdapter().fetch()
    assert len(items[0].body) == 2000


def test_lookback_drops_old_entries(mocker):
    old_entry = {
        "paper": {
            "id": "2401.00001",
            "title": "Old Paper",
            "summary": "old",
            "upvotes": 100,
            "publishedAt": OLD,
        },
    }
    mocker.patch("httpx.get", return_value=_payload([RECENT_ENTRY, old_entry]))
    items = HFPapersAdapter().fetch()
    urls = [i.url for i in items]
    assert "https://huggingface.co/papers/2401.12345" in urls
    assert "https://huggingface.co/papers/2401.00001" not in urls


def test_widened_lookback_keeps_old_entries(mocker):
    old_entry = {
        "paper": {
            "id": "2401.00001",
            "title": "Old Paper",
            "summary": "old",
            "upvotes": 100,
            "publishedAt": OLD,
        },
    }
    mocker.patch("httpx.get", return_value=_payload([RECENT_ENTRY, old_entry]))
    items = HFPapersAdapter(lookback_days=60).fetch()
    urls = [i.url for i in items]
    assert "https://huggingface.co/papers/2401.00001" in urls
    assert len(items) == 2


def test_default_min_upvotes_keeps_everything(mocker):
    low_entry = {
        "paper": {
            "id": "2401.00002",
            "title": "Low upvotes",
            "summary": "low",
            "upvotes": 0,
            "publishedAt": RECENT,
        },
    }
    mocker.patch("httpx.get", return_value=_payload([RECENT_ENTRY, low_entry]))
    items = HFPapersAdapter().fetch()
    assert len(items) == 2


def test_higher_min_upvotes_drops_low(mocker):
    low_entry = {
        "paper": {
            "id": "2401.00002",
            "title": "Low upvotes",
            "summary": "low",
            "upvotes": 5,
            "publishedAt": RECENT,
        },
    }
    mocker.patch("httpx.get", return_value=_payload([RECENT_ENTRY, low_entry]))
    items = HFPapersAdapter(min_upvotes=40).fetch()
    urls = [i.url for i in items]
    assert "https://huggingface.co/papers/2401.12345" in urls
    assert "https://huggingface.co/papers/2401.00002" not in urls


def test_fail_soft_on_exception(mocker):
    mocker.patch("httpx.get", side_effect=RuntimeError("network down"))
    assert HFPapersAdapter().fetch() == []


def test_fail_soft_on_malformed_payload(mocker):
    mocker.patch("httpx.get", return_value=_payload(None))
    assert HFPapersAdapter().fetch() == []


def test_empty_payload_returns_empty(mocker):
    mocker.patch("httpx.get", return_value=_payload([]))
    assert HFPapersAdapter().fetch() == []


def test_flat_entry_shape_supported(mocker):
    flat_entry = {
        "id": "2401.55555",
        "title": "Flat Paper",
        "summary": "flat",
        "upvotes": 20,
        "publishedAt": RECENT,
    }
    mocker.patch("httpx.get", return_value=_payload([flat_entry]))
    items = HFPapersAdapter().fetch()
    assert len(items) == 1
    assert items[0].url == "https://huggingface.co/papers/2401.55555"


def test_name_attr():
    assert HFPapersAdapter().name == "hf-papers"
