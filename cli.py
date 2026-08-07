import argparse
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).parent
CONFIG_FILE = REPO_ROOT / "config.yml"
VAULT_PATH = REPO_ROOT / "vault"
INDEX_PATH = VAULT_PATH / ".index.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return yaml.safe_load(CONFIG_FILE.read_text())
    return {}


def cmd_sweep(args, cfg):
    from agent import scheduler
    deep = getattr(args, "deep", False)
    lookback_days = getattr(args, "lookback_days", None)
    date = getattr(args, "date", None)
    thresholds = cfg.get("thresholds", {})
    feeds = cfg.get("sources", {}).get("feeds", [])
    search_cfg = cfg.get("search", {})
    synthesis_cfg = cfg.get("synthesis", {})
    api_key = os.getenv("ANTHROPIC_API_KEY")

    # Feed / HN / arXiv path.
    feed_items = scheduler.run_sweep(
        vault_path=VAULT_PATH,
        index_path=INDEX_PATH,
        thresholds=thresholds,
        api_key=api_key,
        feeds=feeds,
        deep=deep,
        lookback_days=lookback_days,
        synthesis_cfg=synthesis_cfg,
        date=date,
    )

    # Search-backend path (Tavily/Bing/SerpAPI) — each client self-skips
    # without its key, so this is safe even when only one backend is configured.
    search_items = []
    if search_cfg:
        search_items = scheduler.search_sweep(
            vault_path=VAULT_PATH,
            index_path=INDEX_PATH,
            search_cfg=search_cfg,
            api_key=api_key,
            synthesis_cfg=synthesis_cfg,
            date=date,
        )

    total = len(feed_items) + len(search_items)
    print(f"Sweep complete. {total} new strategies documented.")


def _build_sweep_parser(subparsers):
    sweep_p = subparsers.add_parser("sweep", help="Run a one-shot sweep now")
    sweep_p.add_argument("--deep", action="store_true", help="Run a deep sweep")
    sweep_p.add_argument(
        "--lookback-days",
        type=int,
        default=None,
        help="Widen the crawl window to N days into the past",
    )
    sweep_p.add_argument(
        "--date",
        default=None,
        help="Note date stamp (YYYY-MM-DD); defaults to today",
    )
    return sweep_p


def cmd_regenerate(args, cfg):
    from agent.regenerator import Regenerator
    synthesis_cfg = cfg.get("synthesis", {})
    min_score = getattr(args, "min_score", None)
    if min_score is None:
        min_score = synthesis_cfg.get("min_score", 6)
    max_chars = synthesis_cfg.get("max_chars", 8000)
    api_key = os.getenv("ANTHROPIC_API_KEY")

    reg = Regenerator(
        vault_path=VAULT_PATH,
        api_key=api_key,
        min_score=min_score,
        max_chars=max_chars,
    )
    date = getattr(args, "date", None)
    if date:
        report = reg.regenerate(date=date)
    else:
        report = reg.regenerate_all()

    print(
        f"Regenerate complete. "
        f"regenerated={report.get('regenerated', 0)} "
        f"fetch-failed={report.get('fetch_failed', 0)} "
        f"skipped-below-threshold={report.get('skipped', 0)} "
        f"preserved={report.get('preserved', 0)} "
        f"errored={report.get('errored', 0)}"
    )
    tally = report.get("content_source_by_domain", {})
    if tally:
        print("content_source per domain:")
        for key in sorted(tally):
            print(f"  {key}: {tally[key]}")


def _build_regenerate_parser(subparsers):
    p = subparsers.add_parser(
        "regenerate", help="Backfill existing vault notes with synthesized prose"
    )
    p.add_argument("--date", default=None, help="Only notes stamped YYYY-MM-DD")
    p.add_argument("--all", action="store_true", help="Regenerate all notes")
    p.add_argument(
        "--min-score", type=int, default=None,
        help="Override the synthesis min_score gate",
    )
    return p


def cmd_reclassify(args, cfg):
    from agent.reclassifier import Reclassifier
    api_key = os.getenv("ANTHROPIC_API_KEY")
    rec = Reclassifier(vault_path=VAULT_PATH, api_key=api_key)
    date = getattr(args, "date", None)
    all_notes = getattr(args, "all", False)
    report = rec.reclassify(date=date, all_notes=all_notes)
    print(
        f"Reclassify complete. "
        f"reclassified={report.get('reclassified', 0)} "
        f"moved={report.get('moved', 0)} "
        f"errored={report.get('errored', 0)}"
    )


def _build_reclassify_parser(subparsers):
    p = subparsers.add_parser(
        "reclassify", help="Re-classify existing vault notes"
    )
    p.add_argument("--date", default=None, help="Only notes from this date (YYYY-MM-DD)")
    p.add_argument("--all", action="store_true", help="Re-classify all notes")
    return p


def cmd_start(args, cfg):
    from agent.scheduler import start_scheduler
    thresholds = cfg.get("thresholds", {})
    feeds = cfg.get("sources", {}).get("feeds", [])
    schedule = cfg.get("schedule", {})
    search_cfg = cfg.get("search", {})
    api_key = os.getenv("ANTHROPIC_API_KEY")
    print("Starting scheduler. Press Ctrl+C to stop.")
    start_scheduler(
        vault_path=VAULT_PATH,
        index_path=INDEX_PATH,
        thresholds=thresholds,
        api_key=api_key,
        feeds=feeds,
        daily_time=schedule.get("daily_sweep", "08:00"),
        weekly_day=schedule.get("weekly_deep", "sunday 08:00").split()[0],
        search_cfg=search_cfg,
    )


def cmd_sources(args, cfg):
    sources_file = VAULT_PATH / "sources.md"
    if sources_file.exists():
        print(sources_file.read_text())
    else:
        print("No sources file found. Run a sweep first.")


def cmd_status(args, cfg):
    strategies_dir = VAULT_PATH / "strategies"
    strategies = list(strategies_dir.glob("*.md")) if strategies_dir.exists() else []
    sources_file = VAULT_PATH / "sources.md"
    sources_count = 0
    if sources_file.exists():
        content = sources_file.read_text()
        sources_count = content.count("\n- ") + content.count("\n  - ")

    index_file = INDEX_PATH
    last_run = "never"
    if index_file.exists():
        import json
        try:
            idx = json.loads(index_file.read_text())
            urls = idx.get("urls", [])
            if urls:
                last_run = "has entries"
        except Exception:
            pass

    print(f"Strategies documented: {len(strategies)}")
    print(f"Sources tracked:       {sources_count}")
    print(f"Last run:              {last_run}")
    print(f"Vault:                 {VAULT_PATH}")


def main():
    cfg = load_config()
    parser = argparse.ArgumentParser(description="LLM Research Agent")
    sub = parser.add_subparsers(dest="command")

    _build_sweep_parser(sub)
    _build_regenerate_parser(sub)
    _build_reclassify_parser(sub)

    sub.add_parser("start", help="Start the scheduler (runs in foreground)")
    sub.add_parser("sources", help="List known sources")
    sub.add_parser("status", help="Show agent status and stats")

    args = parser.parse_args()
    if args.command == "sweep":
        cmd_sweep(args, cfg)
    elif args.command == "regenerate":
        cmd_regenerate(args, cfg)
    elif args.command == "reclassify":
        cmd_reclassify(args, cfg)
    elif args.command == "start":
        cmd_start(args, cfg)
    elif args.command == "sources":
        cmd_sources(args, cfg)
    elif args.command == "status":
        cmd_status(args, cfg)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
