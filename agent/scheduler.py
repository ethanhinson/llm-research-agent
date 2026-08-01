from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from agent.deduplicator import Deduplicator
from agent.evaluator import Evaluator
from agent.fetchers.arxiv import ArxivFetcher
from agent.fetchers.hackernews import HNFetcher
from agent.fetchers.reddit import RedditFetcher
from agent.fetchers.web import WebFetcher
from agent.models import RawItem
from agent.tools.cross_validate import cross_validate
from agent.writer import Writer


def run_sweep(
    vault_path: Path,
    index_path: Path,
    thresholds: dict,
    api_key: str | None,
    subreddits: list[str],
    feeds: list[dict],
    deep: bool = False,
) -> list[RawItem]:
    vault_path = Path(vault_path)
    index_path = Path(index_path)

    hn_threshold = thresholds.get("hn_points", 50)
    reddit_threshold = thresholds.get("reddit_upvotes", 100)

    raw: list[RawItem] = []
    raw.extend(HNFetcher(threshold=hn_threshold).fetch())
    if subreddits:
        raw.extend(RedditFetcher(subreddits=subreddits, threshold=reddit_threshold).fetch())
    raw.extend(ArxivFetcher().fetch())
    if feeds:
        raw.extend(WebFetcher(feeds=feeds).fetch())

    dedup = Deduplicator(index_path)
    after_dedup = [item for item in raw if not dedup.is_duplicate(item)]

    after_engagement = [
        item for item in after_dedup
        if item.source == "arxiv"
        or ("hackernews" in item.source and item.engagement >= hn_threshold)
        or ("reddit" in item.source and item.engagement >= reddit_threshold)
        or ("web/" in item.source)
    ]

    after_cv = cross_validate(after_engagement)

    evaluator = Evaluator(api_key=api_key)
    scored = evaluator.score(after_cv)

    writer = Writer(vault_path=vault_path)
    for item in scored:
        writer.write_note(item)
        dedup.mark_seen(item)

    if scored:
        writer.regenerate_index()

    return scored


def start_scheduler(
    vault_path: Path,
    index_path: Path,
    thresholds: dict,
    api_key: str | None,
    subreddits: list[str],
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
            "subreddits": subreddits,
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
            "subreddits": subreddits,
            "feeds": feeds,
            "deep": True,
        },
        id="weekly_deep_sweep",
        name="Weekly deep LLM research sweep",
    )

    scheduler.start()
