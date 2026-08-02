from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from agent.deduplicator import Deduplicator
from agent.evaluator import Evaluator
from agent.fetchers.arxiv import ArxivFetcher
from agent.fetchers.hackernews import HNFetcher

from agent.fetchers.web import WebFetcher
from agent.models import RawItem
from agent.tools.cross_validate import cross_validate
from agent.topic_filter import is_relevant
from agent.writer import Writer


def run_sweep(
    vault_path: Path,
    index_path: Path,
    thresholds: dict,
    api_key: str | None,
    feeds: list[dict],
    deep: bool = False,
    novelty_min: int = 6,
) -> list[RawItem]:
    vault_path = Path(vault_path)
    index_path = Path(index_path)

    hn_threshold = thresholds.get("hn_points", 50)
    min_novelty = thresholds.get("novelty_min", novelty_min)

    def _fetch(fetcher_fn):
        try:
            return fetcher_fn()
        except Exception as exc:
            print(f"[warn] fetcher failed, skipping: {exc}")
            return []

    raw: list[RawItem] = []
    raw.extend(_fetch(lambda: HNFetcher(threshold=hn_threshold).fetch()))
    raw.extend(_fetch(lambda: ArxivFetcher().fetch()))
    if feeds:
        raw.extend(_fetch(lambda: WebFetcher(feeds=feeds).fetch()))

    dedup = Deduplicator(index_path)
    after_dedup = [item for item in raw if not dedup.is_duplicate(item)]

    after_engagement = [
        item for item in after_dedup
        if item.source == "arxiv"
        or ("hackernews" in item.source and item.engagement >= hn_threshold)
        or ("reddit" in item.source and item.engagement >= reddit_threshold)
        or ("web/" in item.source)
    ]

    after_topic = [item for item in after_engagement if is_relevant(item)]

    after_cv = cross_validate(after_topic)

    evaluator = Evaluator(api_key=api_key)
    scored = evaluator.score(after_cv)

    above_threshold = [item for item in scored if item.novelty >= min_novelty]

    writer = Writer(vault_path=vault_path)
    for item in above_threshold:
        writer.write_note(item)
        dedup.mark_seen(item)

    if above_threshold:
        writer.regenerate_index()

    return above_threshold


def start_scheduler(
    vault_path: Path,
    index_path: Path,
    thresholds: dict,
    api_key: str | None,
    feeds: list[dict],
    daily_time: str = "08:00",
    weekly_day: str = "sunday",
):
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
        },
        id="weekly_deep_sweep",
        name="Weekly deep LLM research sweep",
    )

    scheduler.start()
