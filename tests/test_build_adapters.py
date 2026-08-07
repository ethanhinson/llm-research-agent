import pytest

from agent.fetchers.base import SourceAdapter, build_adapters
from agent.fetchers.arxiv import ArxivFetcher, ArxivSearchAdapter
from agent.fetchers.github_trending import GitHubTrendingAdapter
from agent.fetchers.hackernews import HNFetcher
from agent.fetchers.hf_papers import HFPapersAdapter
from agent.fetchers.multi_search import MultiSearchFetcher
from agent.fetchers.semantic_scholar import SemanticScholarAdapter
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


# --- New sources config block (change 0010) ---------------------------------


def _sweep_types(cfg, **kw):
    return [type(a) for a in build_adapters(cfg, kind="sweep", feeds=[], **kw)]


def test_sweep_omits_new_sources_when_sources_block_absent():
    # A config with no `sources` block behaves exactly as before.
    types = _sweep_types({"thresholds": {"hn_points": 50}})
    assert types == [HNFetcher, ArxivFetcher]


def test_sweep_adds_hf_papers_when_enabled():
    cfg = {"thresholds": {}, "sources": {"hf_papers": {"enabled": True, "min_upvotes": 5}}}
    adapters = build_adapters(cfg, kind="sweep", feeds=[])
    hf = [a for a in adapters if isinstance(a, HFPapersAdapter)]
    assert len(hf) == 1
    assert hf[0].min_upvotes == 5
    assert all(isinstance(a, SourceAdapter) for a in adapters)


def test_sweep_omits_hf_papers_when_disabled():
    cfg = {"sources": {"hf_papers": {"enabled": False}}}
    assert HFPapersAdapter not in _sweep_types(cfg)


def test_sweep_adds_arxiv_search_when_queries_present():
    cfg = {"sources": {"arxiv_queries": ["LLM agents", "prompt optimization"]}}
    adapters = build_adapters(cfg, kind="sweep", feeds=[])
    srch = [a for a in adapters if isinstance(a, ArxivSearchAdapter)]
    assert len(srch) == 1
    assert srch[0].queries == ["LLM agents", "prompt optimization"]


def test_sweep_omits_arxiv_search_when_queries_absent_or_empty():
    assert ArxivSearchAdapter not in _sweep_types({"sources": {"arxiv_queries": []}})
    assert ArxivSearchAdapter not in _sweep_types({"sources": {}})


def test_sweep_adds_github_trending_when_enabled():
    cfg = {
        "sources": {
            "github_trending": {"enabled": True, "topics": ["llm", "rag"], "min_stars": 250}
        }
    }
    adapters = build_adapters(cfg, kind="sweep", feeds=[])
    gh = [a for a in adapters if isinstance(a, GitHubTrendingAdapter)]
    assert len(gh) == 1
    assert gh[0].topics == ["llm", "rag"]
    assert gh[0].min_stars == 250


def test_sweep_omits_github_trending_when_disabled():
    cfg = {"sources": {"github_trending": {"enabled": False, "topics": ["llm"]}}}
    assert GitHubTrendingAdapter not in _sweep_types(cfg)


def test_sweep_threads_lookback_into_new_sources():
    cfg = {
        "sources": {
            "hf_papers": {"enabled": True},
            "arxiv_queries": ["q"],
            "github_trending": {"enabled": True, "topics": ["llm"]},
        }
    }
    adapters = build_adapters(cfg, kind="sweep", feeds=[], lookback_days=30)
    for a in adapters:
        assert a.lookback_days == 30


def test_sweep_all_new_sources_registered_in_order():
    cfg = {
        "thresholds": {"hn_points": 50},
        "sources": {
            "hf_papers": {"enabled": True},
            "arxiv_queries": ["q"],
            "github_trending": {"enabled": True, "topics": ["llm"]},
        },
    }
    feeds = [{"name": "b", "url": "u"}]
    types = [type(a) for a in build_adapters(cfg, kind="sweep", feeds=feeds)]
    assert types == [
        HNFetcher,
        ArxivFetcher,
        WebFetcher,
        HFPapersAdapter,
        ArxivSearchAdapter,
        GitHubTrendingAdapter,
    ]


# --- Semantic Scholar (change 0012) -----------------------------------------


def test_sweep_adds_semantic_scholar_when_enabled():
    cfg = {
        "sources": {
            "semantic_scholar": {"enabled": True, "max_per_query": 15},
            "arxiv_queries": ["LLM agents", "RAG"],
        }
    }
    adapters = build_adapters(cfg, kind="sweep", feeds=[])
    s2 = [a for a in adapters if isinstance(a, SemanticScholarAdapter)]
    assert len(s2) == 1
    # defaults its queries to arxiv_queries when s2_queries is unset
    assert s2[0].queries == ["LLM agents", "RAG"]
    assert s2[0].max_per_query == 15
    assert all(isinstance(a, SourceAdapter) for a in adapters)


def test_sweep_s2_uses_explicit_s2_queries_over_arxiv():
    cfg = {
        "sources": {
            "semantic_scholar": {"enabled": True},
            "arxiv_queries": ["arxiv-only"],
            "s2_queries": ["s2-specific"],
        }
    }
    adapters = build_adapters(cfg, kind="sweep", feeds=[])
    s2 = [a for a in adapters if isinstance(a, SemanticScholarAdapter)][0]
    assert s2.queries == ["s2-specific"]


def test_sweep_omits_semantic_scholar_when_disabled():
    cfg = {"sources": {"semantic_scholar": {"enabled": False}, "arxiv_queries": ["q"]}}
    assert SemanticScholarAdapter not in _sweep_types(cfg)


def test_sweep_omits_semantic_scholar_when_absent():
    assert SemanticScholarAdapter not in _sweep_types({"sources": {"arxiv_queries": ["q"]}})
    assert SemanticScholarAdapter not in _sweep_types({"sources": {}})


def test_sweep_threads_lookback_into_semantic_scholar():
    cfg = {
        "sources": {
            "semantic_scholar": {"enabled": True},
            "arxiv_queries": ["q"],
        }
    }
    adapters = build_adapters(cfg, kind="sweep", feeds=[], lookback_days=30)
    s2 = [a for a in adapters if isinstance(a, SemanticScholarAdapter)][0]
    assert s2.lookback_days == 30
