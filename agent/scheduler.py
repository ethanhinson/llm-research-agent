from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from agent.deduplicator import Deduplicator
from agent.enricher import ContentEnricher
from agent.evaluator import Evaluator
from agent.fetchers.base import build_adapters
from agent.synthesizer import NoteSynthesizer

from agent.fetchers.web_search import (
    BingSearchClient,
    SerpAPISearchClient,
    TavilySearchClient,
)
from agent.models import RawItem

# Fetcher classes are constructed by `build_adapters`, but stay imported into
# this module so the sweep tests can patch them at the `agent.scheduler.*` seam
# (e.g. `mocker.patch("agent.scheduler.HNFetcher.fetch")`). Re-exported, not
# constructed here directly.
from agent.fetchers.arxiv import ArxivFetcher, ArxivSearchAdapter  # noqa: F401  (patch seam)
from agent.fetchers.github_trending import GitHubTrendingAdapter  # noqa: F401  (patch seam)
from agent.fetchers.hackernews import HNFetcher  # noqa: F401  (test patch seam)
from agent.fetchers.hf_papers import HFPapersAdapter  # noqa: F401  (test patch seam)
from agent.fetchers.multi_search import MultiSearchFetcher  # noqa: F401  (patch seam)
from agent.fetchers.web import WebFetcher  # noqa: F401  (test patch seam)
from agent.canonical import canonical_id
from agent.tools.corroborate import corroborate
from agent.tools.search_query_generator import SearchQueryGenerator
from agent.tools.source_discovery import SourceDiscovery, append_suggestions
from agent.topic_filter import is_relevant
from agent.writer import Writer


def _make_deduplicator(index_path: Path, corroboration_cfg: dict | None) -> Deduplicator:
    """Construct the Deduplicator, threading window_hours from config when the
    corroboration section is enabled. Absent/disabled keeps today's construction
    (72h default), so behavior is unchanged when the section is absent."""
    cfg = corroboration_cfg or {}
    if cfg.get("enabled", True) and "window_hours" in cfg:
        return Deduplicator(index_path, window_hours=cfg.get("window_hours", 72))
    return Deduplicator(index_path)


def _write_kept(
    kept: list[RawItem],
    writer: Writer,
    dedup: Deduplicator,
    api_key: str | None,
    synthesis_cfg: dict | None,
    llm_cfg: dict | None = None,
    corroboration_enabled: bool = True,
):
    """Write each kept item, enriching + synthesizing above-threshold items.

    Fully fail-soft: if synthesis config is absent/disabled, or an item is below
    the score gate, or enrichment/synthesis raises, the item is written via the
    legacy template path. A single item's failure never aborts the batch.

    `corroboration_enabled` gates the cross-sweep corroboration-update path: when
    falsy, a within-window re-surface of a known identity falls through to a
    normal write+record instead of updating the prior note in place.
    """
    cfg = synthesis_cfg or {}
    enabled = cfg.get("enabled", False)
    min_score = cfg.get("min_score", 6)
    max_chars = cfg.get("max_chars", 8000)

    enricher = ContentEnricher(max_chars=max_chars) if enabled else None
    synthesizer = (
        NoteSynthesizer(api_key=api_key, llm_cfg=llm_cfg) if enabled else None
    )

    for item in kept:
        upd = dedup.corroboration_update(item) if corroboration_enabled else None
        if upd is not None:
            writer.update_corroboration(
                upd["note_path"],
                upd["sources_count"],
                upd["validated"],
                upd["new_source_line"],
            )
            continue
        sections = None
        if enabled and item.score >= min_score:
            try:
                enricher.enrich(item)
                sections = synthesizer.synthesize(item) or None
            except Exception as exc:  # fail-soft per item
                print(f"[warn] synthesis pipeline failed for {item.url}: {exc}")
                sections = None
        if sections:
            note_path = writer.write_note(item, sections=sections)
        else:
            note_path = writer.write_note(item)
        # record the identity so later sweeps corroborate against it
        try:
            rel = str(note_path.relative_to(writer._vault))
        except Exception:
            rel = str(note_path)
        dedup.record(item, note_path=rel)

    if kept:
        writer.regenerate_index()


def run_sweep(
    vault_path: Path,
    index_path: Path,
    thresholds: dict,
    api_key: str | None,
    feeds: list[dict],
    deep: bool = False,
    lookback_days: int | None = None,
    synthesis_cfg: dict | None = None,
    date: str | None = None,
    llm_cfg: dict | None = None,
    sources_cfg: dict | None = None,
    citation_velocity_cfg: dict | None = None,
    corroboration_cfg: dict | None = None,
) -> list[RawItem]:
    vault_path = Path(vault_path)
    index_path = Path(index_path)

    def _fetch(adapter):
        try:
            return adapter.fetch()
        except Exception as exc:
            print(f"[warn] fetcher failed, skipping: {exc}")
            return []

    # Each adapter owns its own engagement policy and returns already-filtered
    # items, so there is no sweep-level engagement allowlist (removing the old
    # reddit_threshold NameError with it). The crawl window is threaded only
    # when explicitly widened; build_adapters preserves each fetcher's own
    # LOOKBACK_DAYS default otherwise. `sources_cfg` gates the change-0010
    # sources (HF papers, arXiv keyword search, GitHub trending).
    adapters = build_adapters(
        {"thresholds": thresholds, "sources": sources_cfg or {}},
        kind="sweep",
        feeds=feeds,
        lookback_days=lookback_days,
    )

    raw: list[RawItem] = []
    for adapter in adapters:
        raw.extend(_fetch(adapter))

    for item in raw:
        item.canonical_id = canonical_id(item)

    dedup = _make_deduplicator(index_path, corroboration_cfg)
    after_dedup = [item for item in raw if not dedup.is_duplicate(item)]

    after_topic = [item for item in after_dedup if is_relevant(item)]

    after_cv = corroborate(after_topic)

    evaluator = Evaluator(api_key=api_key, llm_cfg=llm_cfg)
    scored = evaluator.score(after_cv)

    kept = [item for item in scored if item.keep]

    writer = Writer(vault_path=vault_path, date=date)
    _write_kept(
        kept,
        writer,
        dedup,
        api_key,
        synthesis_cfg,
        llm_cfg=llm_cfg,
        corroboration_enabled=(corroboration_cfg or {}).get("enabled", True),
    )

    # Close the SourceDiscovery loop on the weekly deep sweep: propose new
    # sources for human review (append to vault/sources.md), never edit config.
    # Fail-soft — a discovery error must never abort the sweep.
    if deep:
        _run_source_discovery(vault_path, api_key, llm_cfg=llm_cfg, date=date)

    # Weekly citation-velocity re-poll: deep-only, config-gated, fail-soft.
    if deep and (citation_velocity_cfg or {}).get("enabled"):
        try:
            from agent.tools.citation_velocity import run_citation_velocity
            run_citation_velocity(
                vault_path,
                min_delta=citation_velocity_cfg.get("min_delta", 25),
                api_key=None,  # S2_API_KEY read from env inside
                today=date,
            )
        except Exception as exc:
            print(f"[warn] citation-velocity re-poll failed, skipping: {exc}")

    return kept


def _run_source_discovery(
    vault_path: Path,
    api_key: str | None,
    *,
    llm_cfg: dict | None = None,
    date: str | None = None,
) -> int:
    """Suggest new sources via the LLM and append them to vault/sources.md for
    human review. Returns the count appended (0 on any soft failure)."""
    try:
        sources_path = Path(vault_path) / "sources.md"
        recent = _recent_strategy_titles(vault_path)
        sd = SourceDiscovery(sources_path=sources_path, api_key=api_key, llm_cfg=llm_cfg)
        suggestions = sd.suggest(recent)
        return append_suggestions(sources_path, suggestions, date=date)
    except Exception as exc:  # fail-soft: discovery never aborts the sweep
        print(f"[warn] source discovery failed, skipping: {exc}")
        return 0


def _recent_strategy_titles(vault_path: Path, limit: int = 20) -> list[str]:
    try:
        strategies_dir = Path(vault_path) / "strategies"
        paths = sorted(strategies_dir.glob("**/*.md"), reverse=True)[:limit]
        return [p.stem for p in paths]
    except Exception:
        return []


def search_sweep(
    vault_path: Path,
    index_path: Path,
    search_cfg: dict,
    api_key: str | None,
    synthesis_cfg: dict | None = None,
    date: str | None = None,
    llm_cfg: dict | None = None,
    corroboration_cfg: dict | None = None,
) -> list[RawItem]:
    vault_path = Path(vault_path)
    index_path = Path(index_path)
    search_cfg = search_cfg or {}

    # Build all three clients; each self-skips when its key is absent.
    clients = [
        TavilySearchClient(),
        BingSearchClient(),
        SerpAPISearchClient(),
    ]

    recent_titles = _recent_strategy_titles(vault_path)
    queries = SearchQueryGenerator(
        cfg={"search": search_cfg}, api_key=api_key, llm_cfg=llm_cfg
    ).queries(recent_titles=recent_titles)

    (fetcher,) = build_adapters(
        search_cfg,
        kind="search",
        clients=clients,
        queries=queries,
        max_results_per_query=search_cfg.get("max_results_per_query", 10),
    )
    raw = fetcher.fetch()

    for item in raw:
        item.canonical_id = canonical_id(item)

    dedup = _make_deduplicator(index_path, corroboration_cfg)
    after_dedup = [item for item in raw if not dedup.is_duplicate(item)]

    # The search adapter owns its own engagement policy, so there is no
    # sweep-level engagement allowlist here either.
    after_topic = [item for item in after_dedup if is_relevant(item)]

    after_cv = corroborate(after_topic)

    evaluator = Evaluator(api_key=api_key, llm_cfg=llm_cfg)
    scored = evaluator.score(after_cv)

    kept = [item for item in scored if item.keep]

    writer = Writer(vault_path=vault_path, date=date)
    _write_kept(
        kept,
        writer,
        dedup,
        api_key,
        synthesis_cfg,
        llm_cfg=llm_cfg,
        corroboration_enabled=(corroboration_cfg or {}).get("enabled", True),
    )

    return kept


def start_scheduler(
    vault_path: Path,
    index_path: Path,
    thresholds: dict,
    api_key: str | None,
    feeds: list[dict],
    daily_time: str = "08:00",
    weekly_day: str = "sunday",
    search_cfg: dict | None = None,
    llm_cfg: dict | None = None,
    sources_cfg: dict | None = None,
    corroboration_cfg: dict | None = None,
    citation_velocity_cfg: dict | None = None,
):
    weekly_day = weekly_day[:3].lower()
    parts = daily_time.split(":")
    if len(parts) < 2:
        raise ValueError(f"daily_time must be HH:MM, got: {daily_time!r}")
    hour, minute = parts[0], parts[1]

    scheduler = BlockingScheduler()

    scheduler.add_job(
        run_sweep,
        trigger="cron",
        hour=int(hour),
        minute=int(minute),
        kwargs={
            "vault_path": vault_path,
            "index_path": index_path,
            "thresholds": thresholds,
            "api_key": api_key,
            "feeds": feeds,
            "deep": False,
            "llm_cfg": llm_cfg,
            "sources_cfg": sources_cfg,
            "corroboration_cfg": corroboration_cfg,
        },
        id="daily_sweep",
        name="Daily LLM research sweep",
    )

    scheduler.add_job(
        run_sweep,
        trigger="cron",
        day_of_week=weekly_day,
        hour=int(hour),
        minute=int(minute),
        kwargs={
            "vault_path": vault_path,
            "index_path": index_path,
            "thresholds": thresholds,
            "api_key": api_key,
            "feeds": feeds,
            "deep": True,
            "llm_cfg": llm_cfg,
            "sources_cfg": sources_cfg,
            "corroboration_cfg": corroboration_cfg,
            "citation_velocity_cfg": citation_velocity_cfg,
        },
        id="weekly_deep_sweep",
        name="Weekly deep LLM research sweep",
    )

    if search_cfg:
        scheduler.add_job(
            search_sweep,
            trigger="interval",
            hours=search_cfg.get("interval_hours", 6),
            kwargs={
                "vault_path": vault_path,
                "index_path": index_path,
                "search_cfg": search_cfg,
                "api_key": api_key,
                "llm_cfg": llm_cfg,
                "corroboration_cfg": corroboration_cfg,
            },
            id="search_sweep",
            name="Multi-backend web search sweep",
        )

    scheduler.start()
