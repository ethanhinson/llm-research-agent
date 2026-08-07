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
from agent.fetchers.arxiv import ArxivFetcher  # noqa: F401  (test patch seam)
from agent.fetchers.hackernews import HNFetcher  # noqa: F401  (test patch seam)
from agent.fetchers.multi_search import MultiSearchFetcher  # noqa: F401  (patch seam)
from agent.fetchers.web import WebFetcher  # noqa: F401  (test patch seam)
from agent.tools.cross_validate import cross_validate
from agent.tools.search_query_generator import SearchQueryGenerator
from agent.topic_filter import is_relevant
from agent.writer import Writer


def _write_kept(
    kept: list[RawItem],
    writer: Writer,
    dedup: Deduplicator,
    api_key: str | None,
    synthesis_cfg: dict | None,
    llm_cfg: dict | None = None,
):
    """Write each kept item, enriching + synthesizing above-threshold items.

    Fully fail-soft: if synthesis config is absent/disabled, or an item is below
    the score gate, or enrichment/synthesis raises, the item is written via the
    legacy template path. A single item's failure never aborts the batch.
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
        sections = None
        if enabled and item.score >= min_score:
            try:
                enricher.enrich(item)
                sections = synthesizer.synthesize(item) or None
            except Exception as exc:  # fail-soft per item
                print(f"[warn] synthesis pipeline failed for {item.url}: {exc}")
                sections = None
        if sections:
            writer.write_note(item, sections=sections)
        else:
            writer.write_note(item)
        dedup.mark_seen(item)

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
    # LOOKBACK_DAYS default otherwise.
    adapters = build_adapters(
        {"thresholds": thresholds},
        kind="sweep",
        feeds=feeds,
        lookback_days=lookback_days,
    )

    raw: list[RawItem] = []
    for adapter in adapters:
        raw.extend(_fetch(adapter))

    dedup = Deduplicator(index_path)
    after_dedup = [item for item in raw if not dedup.is_duplicate(item)]

    after_topic = [item for item in after_dedup if is_relevant(item)]

    after_cv = cross_validate(after_topic)

    evaluator = Evaluator(api_key=api_key, llm_cfg=llm_cfg)
    scored = evaluator.score(after_cv)

    kept = [item for item in scored if item.keep]

    writer = Writer(vault_path=vault_path, date=date)
    _write_kept(kept, writer, dedup, api_key, synthesis_cfg, llm_cfg=llm_cfg)

    return kept


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

    dedup = Deduplicator(index_path)
    after_dedup = [item for item in raw if not dedup.is_duplicate(item)]

    # The search adapter owns its own engagement policy, so there is no
    # sweep-level engagement allowlist here either.
    after_topic = [item for item in after_dedup if is_relevant(item)]

    after_cv = cross_validate(after_topic)

    evaluator = Evaluator(api_key=api_key, llm_cfg=llm_cfg)
    scored = evaluator.score(after_cv)

    kept = [item for item in scored if item.keep]

    writer = Writer(vault_path=vault_path, date=date)
    _write_kept(kept, writer, dedup, api_key, synthesis_cfg, llm_cfg=llm_cfg)

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
            },
            id="search_sweep",
            name="Multi-backend web search sweep",
        )

    scheduler.start()
