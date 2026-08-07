import pytest

from agent.fetchers.base import SourceAdapter, build_adapters
from agent.fetchers.arxiv import ArxivFetcher
from agent.fetchers.hackernews import HNFetcher
from agent.fetchers.multi_search import MultiSearchFetcher
from agent.fetchers.web import WebFetcher


def test_sweep_kind_returns_hn_and_arxiv_without_feeds():
    adapters = build_adapters({"thresholds": {"hn_points": 50}}, kind="sweep", feeds=[])
    types = [type(a) for a in adapters]
    assert types == [HNFetcher, ArxivFetcher]
    assert all(isinstance(a, SourceAdapter) for a in adapters)


def test_sweep_kind_includes_web_when_feeds_present():
    feeds = [{"name": "blog", "url": "https://example.com/feed"}]
    adapters = build_adapters(
        {"thresholds": {"hn_points": 50}}, kind="sweep", feeds=feeds
    )
    types = [type(a) for a in adapters]
    assert types == [HNFetcher, ArxivFetcher, WebFetcher]
    web = adapters[-1]
    assert web.feeds == feeds


def test_sweep_kind_threads_hn_threshold():
    adapters = build_adapters(
        {"thresholds": {"hn_points": 123}}, kind="sweep", feeds=[]
    )
    hn = adapters[0]
    assert isinstance(hn, HNFetcher)
    assert hn.threshold == 123


def test_sweep_kind_defaults_hn_threshold_when_absent():
    adapters = build_adapters({}, kind="sweep", feeds=[])
    assert adapters[0].threshold == 50


def test_sweep_kind_threads_lookback_days_when_widened():
    adapters = build_adapters(
        {"thresholds": {"hn_points": 50}},
        kind="sweep",
        feeds=[{"name": "b", "url": "u"}],
        lookback_days=30,
    )
    assert adapters[0].lookback_days == 30  # HN
    assert adapters[1].lookback_days == 30  # arXiv
    assert adapters[2].lookback_days == 30  # web


def test_sweep_kind_preserves_default_lookback_when_none():
    # lookback_days omitted => each fetcher keeps its own LOOKBACK_DAYS default (7)
    adapters = build_adapters({"thresholds": {"hn_points": 50}}, kind="sweep", feeds=[])
    assert adapters[0].lookback_days == 7


def test_search_kind_returns_multi_search_adapter():
    adapters = build_adapters(
        {},
        kind="search",
        clients=[],
        queries=["q"],
        max_results_per_query=7,
    )
    assert len(adapters) == 1
    fetcher = adapters[0]
    assert isinstance(fetcher, MultiSearchFetcher)
    assert isinstance(fetcher, SourceAdapter)
    assert fetcher.queries == ["q"]
    assert fetcher.max_results_per_query == 7


def test_unknown_kind_raises():
    with pytest.raises(ValueError, match="unknown adapter kind"):
        build_adapters({}, kind="bogus")
