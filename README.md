# LLM Research Agent

Monitors Reddit, Hacker News, arXiv, and AI blogs for emerging LLM strategies. Documents findings as Obsidian-compatible notes in `vault/strategies/`, auto-maintains `vault/index.md`, and scores novelty with Claude.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# Fill in ANTHROPIC_API_KEY.
# Optionally add web-search backend keys — TAVILY_API_KEY, BING_SEARCH_API_KEY,
# SERPAPI_KEY — to enable the continuous multi-backend search sweep. Any backend
# whose key is absent is silently skipped, so configuring even one is enough.
```

## CLI

```bash
python cli.py sweep          # one-shot sweep now
python cli.py sweep --deep   # deep sweep (broader arXiv, source discovery)
python cli.py start          # start scheduler (daily + weekly + a web-search sweep every search.interval_hours; runs in foreground)
python cli.py reclassify --all           # re-classify existing vault notes into correct type subdirs
python cli.py reclassify --date 2026-08-05  # re-classify only that date's notes
python cli.py sources        # list known sources
python cli.py status         # stats: strategies documented, last run, source count
```

## Vault structure

```
vault/
├── strategies/    # one .md per documented strategy
├── index.md       # auto-generated MOC by category, sorted by novelty
└── sources.md     # tracked sources (validated / unvalidated / flagged)
```

## How it works

Each sweep runs: **Fetch → Deduplicate → Engagement filter → Cross-validate → Claude novelty score → Write**

- Items below engagement thresholds (Reddit: 100 upvotes, HN: 50 points) are dropped
- Fuzzy deduplication (>90% title similarity) prevents re-documenting known strategies
- Items appearing in 2+ independent sources are tagged `validated: true`
- Claude scores each item 1–10 for novelty (metadata only, not a gate)

## Configuration

Edit `config.yml` to adjust thresholds, schedule, and sources. Put API keys in `.env` (see `.env.example`); `.env` is gitignored and must never be committed.

## Tests

```bash
pytest
```
