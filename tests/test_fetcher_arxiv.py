import pytest
from unittest.mock import MagicMock, patch
import datetime

from agent.fetchers.arxiv import ArxivFetcher, ArxivSearchAdapter


def make_result(title, url, summary="Abstract text"):
    r = MagicMock()
    r.title = title
    r.entry_id = url
    r.summary = summary
    # Recent (within the fetcher's default 7-day lookback) so it survives the
    # date-window filter regardless of when the suite runs. A fixed calendar
    # date turns this into a time-bomb once the window advances past it.
    r.published = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
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


# ---------------------------------------------------------------------------
# ArxivSearchAdapter — keyword-search adapter alongside the category firehose.
# ---------------------------------------------------------------------------


def _recent(days_ago):
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)


def make_search_result(title, url, published, summary="Abstract text"):
    r = MagicMock()
    r.title = title
    r.entry_id = url
    r.summary = summary
    r.published = published
    return r


def test_search_adapter_one_search_per_query_sorted_by_date():
    """One arxiv.Search(query=...) per configured query string, sorted by SubmittedDate."""
    adapter = ArxivSearchAdapter(queries=["agent memory", "chain of thought"])
    results = [make_search_result("P", "https://arxiv.org/abs/1", _recent(1))]
    with patch("arxiv.Search") as mock_search, patch("arxiv.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.results.return_value = iter(results)
        mock_client_cls.return_value = mock_client
        adapter.fetch()

    assert mock_search.call_count == 2
    queries = [kw.kwargs["query"] for kw in mock_search.call_args_list]
    assert queries == ["agent memory", "chain of thought"]
    for call in mock_search.call_args_list:
        assert call.kwargs["sort_by"] == __import__("arxiv").SortCriterion.SubmittedDate


def test_search_adapter_maps_fields_with_search_source():
    """Results map to RawItem: source='arxiv/search', title, summary[:2000], entry_id url, published ts."""
    adapter = ArxivSearchAdapter(queries=["agent memory"])
    published = _recent(1)
    long_summary = "x" * 5000
    results = [
        make_search_result(
            "Agentic Memory", "https://arxiv.org/abs/2601.09999", published, summary=long_summary
        )
    ]
    with patch("arxiv.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.results.return_value = iter(results)
        mock_client_cls.return_value = mock_client
        items = adapter.fetch()

    assert len(items) == 1
    item = items[0]
    assert item.source == "arxiv/search"
    assert item.title == "Agentic Memory"
    assert item.body == long_summary[:2000]
    assert len(item.body) == 2000
    assert item.url == "https://arxiv.org/abs/2601.09999"
    assert item.engagement == 0
    assert item.timestamp == published.isoformat()


def test_search_adapter_family_name_is_arxiv():
    assert ArxivSearchAdapter(queries=[]).name == "arxiv"


def test_search_adapter_lookback_filters_old_results():
    """Results older than lookback_days (default 7) are dropped via Python post-filter."""
    adapter = ArxivSearchAdapter(queries=["agent memory"])
    results = [
        make_search_result("Fresh", "https://arxiv.org/abs/1", _recent(1)),
        make_search_result("Stale", "https://arxiv.org/abs/2", _recent(30)),
    ]
    with patch("arxiv.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.results.return_value = iter(results)
        mock_client_cls.return_value = mock_client
        items = adapter.fetch()

    titles = [i.title for i in items]
    assert titles == ["Fresh"]


def test_search_adapter_caps_max_results_per_query():
    """Each query is capped at max_results_per_query."""
    adapter = ArxivSearchAdapter(queries=["agent memory"], max_results_per_query=3)
    with patch("arxiv.Search") as mock_search, patch("arxiv.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.results.return_value = iter([])
        mock_client_cls.return_value = mock_client
        adapter.fetch()

    assert mock_search.call_args_list[0].kwargs["max_results"] == 3


def test_search_adapter_empty_query_list_no_calls():
    """Empty/absent query list -> no search calls, returns []."""
    adapter = ArxivSearchAdapter(queries=[])
    with patch("arxiv.Search") as mock_search, patch("arxiv.Client") as mock_client_cls:
        items = adapter.fetch()

    assert items == []
    assert mock_search.call_count == 0
    assert mock_client_cls.call_count == 0


def test_search_adapter_fail_soft_on_error():
    """A raising search/client returns [] rather than raising."""
    adapter = ArxivSearchAdapter(queries=["agent memory"])
    with patch("arxiv.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.results.side_effect = RuntimeError("arxiv 500")
        mock_client_cls.return_value = mock_client
        items = adapter.fetch()

    assert items == []
