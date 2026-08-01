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
    from agent.scheduler import run_sweep
    deep = getattr(args, "deep", False)
    thresholds = cfg.get("thresholds", {})
    subreddits = cfg.get("sources", {}).get("subreddits", [])
    feeds = cfg.get("sources", {}).get("feeds", [])
    api_key = os.getenv("ANTHROPIC_API_KEY")
    items = run_sweep(
        vault_path=VAULT_PATH,
        index_path=INDEX_PATH,
        thresholds=thresholds,
        api_key=api_key,
        subreddits=subreddits,
        feeds=feeds,
        deep=deep,
    )
    print(f"Sweep complete. {len(items)} new strategies documented.")


def cmd_start(args, cfg):
    from agent.scheduler import start_scheduler
    thresholds = cfg.get("thresholds", {})
    subreddits = cfg.get("sources", {}).get("subreddits", [])
    feeds = cfg.get("sources", {}).get("feeds", [])
    schedule = cfg.get("schedule", {})
    api_key = os.getenv("ANTHROPIC_API_KEY")
    print("Starting scheduler. Press Ctrl+C to stop.")
    start_scheduler(
        vault_path=VAULT_PATH,
        index_path=INDEX_PATH,
        thresholds=thresholds,
        api_key=api_key,
        subreddits=subreddits,
        feeds=feeds,
        daily_time=schedule.get("daily_sweep", "08:00"),
        weekly_day=schedule.get("weekly_deep", "sunday 08:00").split()[0],
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

    sweep_p = sub.add_parser("sweep", help="Run a one-shot sweep now")
    sweep_p.add_argument("--deep", action="store_true", help="Run a deep sweep")

    sub.add_parser("start", help="Start the scheduler (runs in foreground)")
    sub.add_parser("sources", help="List known sources")
    sub.add_parser("status", help="Show agent status and stats")

    args = parser.parse_args()
    if args.command == "sweep":
        cmd_sweep(args, cfg)
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
