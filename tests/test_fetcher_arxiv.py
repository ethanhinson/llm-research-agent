import pytest
from unittest.mock import MagicMock, patch
import datetime

from agent.fetchers.arxiv import ArxivFetcher


def make_result(title, url, summary="Abstract text"):
    r = MagicMock()
    r.title = title
    r.entry_id = url
    r.summary = summary
    r.published = datetime.datetime(2026, 8, 1, tzinfo=datetime.timezone.utc)
    return r


def test_arxiv_fetcher_maps_fields():
    fetcher = ArxivFetcher()
    mock_results = [
        make_result("Attention Is All You Need v2", "https://arxiv.org/abs/2601.00001"),
    ]
    with patch("arxiv.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.results.return_value = iter(mock_results)
        mock_client_cls.return_value = mock_client
        items = fetcher.fetch()

    assert len(items) == 1
    assert items[0].source == "arxiv"
    assert items[0].engagement == 0
    assert items[0].title == "Attention Is All You Need v2"


def test_arxiv_fetcher_no_threshold():
    """arXiv has no engagement threshold — all results pass."""
    fetcher = ArxivFetcher()
    mock_results = [make_result(f"Paper {i}", f"https://arxiv.org/abs/{i}") for i in range(5)]
    with patch("arxiv.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.results.return_value = iter(mock_results)
        mock_client_cls.return_value = mock_client
        items = fetcher.fetch()

    assert len(items) == 5
