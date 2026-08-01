# LLM Research Agent — Design Spec

**Date:** 2026-08-01
**Status:** Approved

---

## Overview

A Python agent that monitors Reddit, Hacker News, arXiv, and a growing list of AI blogs and newsletters for emerging LLM strategies. It documents findings as individual Obsidian-compatible markdown notes in a git-tracked vault, organized by category with novelty and cross-source metadata.

---

## Architecture

```
~/dev/llm-research-agent/
├── agent/
│   ├── fetchers/
│   │   ├── reddit.py         # PRAW — configurable subreddit list
│   │   ├── hackernews.py     # HN Algolia API
│   │   ├── arxiv.py          # arXiv API (cs.AI, cs.CL, cs.LG)
│   │   └── web.py            # generic scraper for blogs/newsletters
│   ├── tools/
│   │   ├── source_discovery.py   # Claude finds new sources to add
│   │   └── cross_validate.py     # groups same strategy across sources
│   ├── evaluator.py          # engagement filter + novelty scoring via Claude
│   ├── writer.py             # formats and writes Obsidian .md notes
│   ├── deduplicator.py       # fuzzy match against existing vault notes
│   └── scheduler.py          # APScheduler — daily + weekly runs
├── cli.py                    # manual entry point
├── config.yml                # sources, thresholds, schedule
├── vault/                    # Obsidian vault (git-tracked)
│   ├── strategies/           # one .md per documented strategy
│   ├── sources.md            # auto-maintained source list
│   └── index.md              # auto-generated MOC by category
├── .env                      # API keys (gitignored)
└── pyproject.toml
```

---

## Data Pipeline

Each sweep runs this pipeline:

```
Fetch → Deduplicate → Engagement filter → Cross-validate → Claude novelty score → Write
```

1. **Fetch** — all fetchers run in parallel. Each returns a normalized `RawItem`:
   - `title`, `body`, `url`, `source`, `engagement`, `timestamp`

2. **Deduplicate** — check against a local JSON index of documented strategies. Drop exact URL matches and fuzzy title matches (>90% similarity).

3. **Engagement filter** — configurable per-source thresholds (defaults: Reddit 100+ upvotes, HN 50+ points, arXiv any). The only hard gate beyond deduplication.

4. **Cross-validate** — group items by semantic similarity. Items appearing in 2+ independent sources are tagged `validated: true` and get a `sources_count` field.

5. **Claude novelty score** — Claude evaluates each surviving item on a 1–10 scale: *Is this a genuinely new or meaningfully evolved LLM strategy?* The score becomes frontmatter metadata (`novelty: N`), not a filter gate. Everything that passes engagement is documented — novelty just helps prioritize reading.

6. **Write** — generate an Obsidian note, update `index.md`, update `sources.md` if new sources were discovered.

---

## Signal Philosophy

Novelty score is **metadata, not a gate.** A strategy that's not globally novel but is new to the vault is still worth documenting. Only two hard gates exist:
- Below engagement threshold (noise)
- Already in vault (deduplication)

Cross-source validation and novelty score are surfaced as Obsidian tags/fields so you can filter in-app.

---

## Note Format

`vault/strategies/YYYY-MM-DD-<slug>.md`:

```markdown
---
title: "Strategy Name"
date: 2026-08-01
category: architecture          # prompting | architecture | agentic | tooling | use-case
tags: [inference, speed, emerging]
novelty: 7                      # 1–10, Claude-scored
validated: true                 # true if 2+ independent sources agree
sources_count: 4
status: new
---

# Strategy Name

## Summary
One-paragraph plain-English description.

## How It Works
What it does, why it matters, known limitations.

## Why It's Gaining Traction
Engagement signal, cross-source pattern, notable context.

## Sources
- [Title](url) — r/LocalLLaMA · 2.3k upvotes
- [Title](url) — Hacker News · 847 points

## Related
[[Existing Strategy]] [[Another Strategy]]
```

`index.md` is auto-regenerated each run — a table grouped by category sorted by novelty score descending, so newest/most-interesting rises to the top.

---

## Source Discovery

Runs at the start of each sweep. Claude is given the existing source list and recent findings and asked to suggest new subreddits, blogs, newsletters, or feeds. Candidates are added to `sources.md` with `status: unvalidated`. After two sweeps where a source produces at least one documented strategy it graduates to `validated`. Sources with no signal in 30 days are flagged for review.

**Seed sources:**

Reddit: `r/LocalLLaMA`, `r/MachineLearning`, `r/ChatGPT`, `r/singularity`, `r/ClaudeAI`, `r/Oobabooga`, `r/StableDiffusion`, `r/artificial`, `r/GPT4`, `r/OpenAI`

Other: Hacker News, arXiv (cs.AI / cs.CL / cs.LG), Simon Willison's blog, Anthropic blog, OpenAI blog, Hugging Face blog, Ahead of AI newsletter, The Batch

---

## CLI

```bash
python cli.py sweep          # one-shot run now
python cli.py start          # start scheduler (runs in foreground)
python cli.py sources        # list/manage known sources
python cli.py status         # stats: strategies documented, last run, source count
```

---

## Scheduler

- **Daily sweep:** 8am — standard fetch + evaluate + write cycle
- **Weekly deep sweep:** Sunday — broader arXiv crawl, source discovery pass, re-index
- Both configurable in `config.yml`

---

## Dependencies

- `anthropic` — Claude API for novelty scoring, source discovery, backlink suggestions
- `praw` — Reddit API
- `httpx` — HN API, web fetching
- `arxiv` — arXiv API client
- `apscheduler` — scheduling
- `thefuzz` — fuzzy deduplication
- `pyyaml` — config parsing
- `python-dotenv` — env var loading

---

## Configuration (`config.yml`)

```yaml
thresholds:
  reddit_upvotes: 100
  hn_points: 50

schedule:
  daily_sweep: "08:00"
  weekly_deep: "sunday 08:00"

novelty:
  # no hard gate — all values are documented

sources:
  subreddits: [LocalLLaMA, MachineLearning, ...]
  feeds: [...]
```

---

## What's Out of Scope (v1)

- A web UI or dashboard
- Email/Slack digest delivery
- Fine-tuning or embeddings for deduplication (fuzzy string match is sufficient for v1)
- Multi-user / team features
