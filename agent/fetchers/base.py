"""Source intake abstraction.

A single ``SourceAdapter`` protocol unifies every article-intake source behind a
``fetch() -> list[RawItem]`` seam (the same protocol-plus-factory idiom as the
``LLMClient`` abstraction, ADR-0001). Each adapter owns its own engagement
policy — the sweeps no longer carry stringly-typed engagement allowlists.
"""

from typing import Protocol, runtime_checkable

from agent.models import RawItem


@runtime_checkable
class SourceAdapter(Protocol):
    """An article-intake source.

    ``name`` is the source *family* id (e.g. ``"hackernews"``, ``"arxiv"``,
    ``"web"``, ``"search"``); individual items may carry a finer per-item
    ``RawItem.source`` (e.g. ``"web/<feed>"``, ``"search/<backend>"``).

    ``fetch`` returns already-engagement-filtered items — an adapter applies its
    own threshold, so the sweep-level pipeline never re-filters by source.
    """

    name: str

    def fetch(self) -> list[RawItem]: ...


def build_adapters(
    cfg: dict,
    *,
    kind: str,
    feeds: list[dict] | None = None,
    lookback_days: int | None = None,
    clients: list | None = None,
    queries: list[str] | None = None,
    max_results_per_query: int = 10,
) -> list["SourceAdapter"]:
    """Construct the adapter set for a sweep ``kind`` from config.

    This is the single construction site for article-intake sources — the
    protocol-plus-factory idiom mirrored from ADR-0001's ``get_client``.

    - ``kind="sweep"``: HN + arXiv, plus a ``WebFetcher`` **only when** ``feeds``
      is non-empty (matching ``run_sweep``'s ``if feeds:`` guard). The HN
      threshold reads ``cfg["thresholds"]["hn_points"]`` (default 50). The crawl
      window is threaded only when ``lookback_days`` is explicitly widened, so
      each fetcher's own ``LOOKBACK_DAYS`` default is preserved otherwise.
    - ``kind="search"``: a single ``MultiSearchFetcher`` over the given
      ``clients`` + ``queries`` (runtime-built by ``search_sweep``), threading
      ``max_results_per_query``.

    An unknown ``kind`` raises ``ValueError`` (fail loud at the call site,
    mirroring ADR-0001's unknown-provider posture).
    """
    # Imported here to avoid an import cycle (the fetcher modules import RawItem
    # from agent.models, and scheduler imports these classes for test patching).
    from agent.fetchers.arxiv import ArxivFetcher, ArxivSearchAdapter
    from agent.fetchers.github_trending import GitHubTrendingAdapter
    from agent.fetchers.hackernews import HNFetcher
    from agent.fetchers.hf_papers import HFPapersAdapter
    from agent.fetchers.multi_search import MultiSearchFetcher
    from agent.fetchers.semantic_scholar import SemanticScholarAdapter
    from agent.fetchers.web import WebFetcher
    from agent.fetchers.bluesky import BlueskyAdapter

    if kind == "sweep":
        lb = {} if lookback_days is None else {"lookback_days": lookback_days}
        hn_threshold = (cfg.get("thresholds") or {}).get("hn_points", 50)
        adapters: list[SourceAdapter] = [
            HNFetcher(threshold=hn_threshold, **lb),
            ArxivFetcher(**lb),
        ]
        if feeds:
            adapters.append(WebFetcher(feeds=feeds, **lb))

        # Change 0010: three config-gated sources under the `sources:` block.
        # Each is fail-soft at fetch time; here only the enabled ones are
        # constructed. `lb` threads a widened crawl window into them too.
        sources = cfg.get("sources") or {}

        hf_cfg = sources.get("hf_papers") or {}
        if hf_cfg.get("enabled"):
            adapters.append(
                HFPapersAdapter(min_upvotes=hf_cfg.get("min_upvotes", 0), **lb)
            )

        arxiv_queries = sources.get("arxiv_queries") or []
        if arxiv_queries:
            adapters.append(ArxivSearchAdapter(queries=list(arxiv_queries), **lb))

        gh_cfg = sources.get("github_trending") or {}
        if gh_cfg.get("enabled"):
            adapters.append(
                GitHubTrendingAdapter(
                    topics=list(gh_cfg.get("topics") or []),
                    min_stars=gh_cfg.get("min_stars", 100),
                    **lb,
                )
            )

        # Change 0012: Semantic Scholar keyword search. `s2_queries` defaults to
        # the arXiv keyword list (`arxiv_queries`) when unset.
        s2_cfg = sources.get("semantic_scholar") or {}
        if s2_cfg.get("enabled"):
            s2_queries = sources.get("s2_queries") or sources.get("arxiv_queries") or []
            adapters.append(
                SemanticScholarAdapter(
                    queries=list(s2_queries),
                    max_per_query=s2_cfg.get("max_per_query", 10),
                    **lb,
                )
            )

        # Change 0013: Bluesky author feeds. `authors` is a config registry of
        # researcher handles; each is polled fail-soft at fetch time.
        bsky_cfg = sources.get("bluesky") or {}
        if bsky_cfg.get("enabled"):
            adapters.append(
                BlueskyAdapter(
                    authors=list(bsky_cfg.get("authors") or []),
                    min_engagement=bsky_cfg.get("min_engagement", 5),
                    **lb,
                )
            )

        return adapters

    if kind == "search":
        return [
            MultiSearchFetcher(
                clients or [],
                queries or [],
                max_results_per_query=max_results_per_query,
            )
        ]

    raise ValueError(f"unknown adapter kind: {kind!r}")
