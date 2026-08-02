import pytest
from unittest.mock import patch, MagicMock

from agent.fetchers.hackernews import HNFetcher


MOCK_HN_RESPONSE = {
    "hits": [
        {
            "title": "Flash Attention 3 released",
            "url": "https://github.com/Dao-AILab/flash-attention",
            "points": 847,
            "created_at": "2026-08-01T10:00:00.000Z",
            "objectID": "12345",
            "story_text": "Details about flash attention",
        },
        {
            "title": "Low quality post",
            "url": "https://example.com/low",
            "points": 10,
            "created_at": "2026-08-01T09:00:00.000Z",
            "objectID": "12346",
            "story_text": None,
        },
    ]
}


def test_hn_fetcher_maps_fields():
    fetcher = HNFetcher(threshold=50)
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: MOCK_HN_RESPONSE)
        items = fetcher.fetch()

    assert len(items) == 1
    item = items[0]
    assert item.title == "Flash Attention 3 released"
    assert item.url == "https://github.com/Dao-AILab/flash-attention"
    assert item.engagement == 847
    assert item.source == "hackernews"


def test_hn_fetcher_filters_below_threshold():
    fetcher = HNFetcher(threshold=50)
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: MOCK_HN_RESPONSE)
        items = fetcher.fetch()

    urls = [i.url for i in items]
    assert "https://example.com/low" not in urls
