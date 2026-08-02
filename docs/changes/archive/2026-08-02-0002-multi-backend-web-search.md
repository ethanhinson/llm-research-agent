---
id: 2
slug: multi-backend-web-search
title: Multi-Backend Web Search — continuous internet search across Tavily, Bing, and SerpAPI
status: done
priority: medium
type: feat
created: 2026-08-01
updated: 2026-08-02
depends_on: []
related: [1]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-01-multi-backend-web-search.md
plan: docs/superpowers/plans/2026-08-02-multi-backend-web-search.md
results:
trivial: false
auto_groomable: false
branch: feat/multi-backend-web-search
claimed_at: 
pr: https://github.com/ethanhinson/llm-research-agent/pull/2
issue:
blocked_by:
reconciled: true
---

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-01-multi-backend-web-search.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-01-multi-backend-web-search.md) |
| Plan | [2026-08-02-multi-backend-web-search.md](https://github.com/ethanhinson/llm-research-agent/blob/main/docs/superpowers/plans/2026-08-02-multi-backend-web-search.md) |
| PR | [#2](https://github.com/ethanhinson/llm-research-agent/pull/2) |
<!-- docket:artifacts:end -->

## Why

The existing agent only monitors known feeds (HN, arXiv, curated RSS). Breaking content on blogs, forums, and general web can go undetected for days or never surface at all. Adding parallel queries across Tavily, Bing, and SerpAPI on a 6-hour loop catches relevant LLM content within hours of publication, dramatically widening source coverage without any manual curation.

## What changes

- New `agent/fetchers/web_search.py` — `SearchClient` protocol with `TavilySearchClient`, `BingSearchClient`, and `SerpAPISearchClient` implementations; unconfigured backends are silently skipped
- New `agent/fetchers/multi_search.py` — `MultiSearchFetcher` that fans out all (client, query) pairs in parallel and deduplicates results by URL
- New `agent/tools/search_query_generator.py` — hybrid query builder: fixed topic anchors from `config.yml` plus 2–3 Claude Haiku–generated dynamic queries per sweep
- `agent/scheduler.py` — new `search_sweep` function + a new `search` config parameter on `start_scheduler`, which registers the sweep as an APScheduler interval job every `search.interval_hours` (default 6)
- `cli.py` — `cmd_start` threads the `config.yml` `search:` block (and vault/sources context for recent titles) into `start_scheduler`
- `config.yml` — new `search:` block (interval, max results, fixed queries, dynamic toggle)
- `.env.example` documents the new keys: `TAVILY_API_KEY`, `BING_SEARCH_API_KEY`, `SERPAPI_KEY`
- New dep: `tavily-python >=0.3`

Each search client constructs `RawItem` with **all six required fields** — `title`, `body`, `url`, `source`, `engagement=0`, and `timestamp` (a string, following `agent/fetchers/web.py`; use the backend's published date when available, else `""`).

## Out of scope

- Brave Search, Perplexity, or other backends
- Result caching between search sweeps
- Per-query cost tracking
- A dedicated `search-sweep` CLI subcommand

## Open questions

None — design settled.

## Reconcile log

### 2026-08-02

Reconciled against current `main` (tip `0b19baa`). Spec is **valid**; only small integration-seam adjustments, no design invalidation. Confirmed against live code:

- `RawItem` (`agent/models.py`) requires six fields — `title, body, url, source, engagement, timestamp`; the rest default. The spec's per-client mappings omitted `timestamp` (required). Folded into `## What changes`: every client supplies `timestamp` as a string (empty allowed, per `web.py`).
- Fetchers are **duck-typed** (no base class); each is `__init__` + `fetch() -> list[RawItem]`. `SearchClient` as a `typing.Protocol` and `MultiSearchFetcher` in its own `multi_search.py` fit the existing shape.
- The real scheduler seam is **`start_scheduler`** (`agent/scheduler.py`), which takes `thresholds, api_key, feeds, daily_time, weekly_day` and builds a `BlockingScheduler` — it registers no interval job today. `search_sweep` is added there behind a new `search` config parameter; `cli.py`'s `cmd_start` threads the `search:` block through. `cli.py` DOES exist at the repo root (spec's reference was accurate).
- Engagement filter (`scheduler.py`) passes `web/` sources unconditionally; the `search/*` prefix will need the same allow-listing when results flow through `run_sweep`'s filter — but `search_sweep` runs its own pipeline, so this is the plan's call. Confirmed pass-through intent holds.
- Reuse `anthropic.Anthropic(api_key=...)` + model `claude-haiku-4-5-20251001` (`agent/tools/source_discovery.py`) for the dynamic query generator.
- Tests: `pytest` + `pytest-mock` (`mocker`); existing tests patch `httpx.get` and `mocker.patch.object` on clients. New tests mock `httpx.get` (Bing/SerpAPI) and the `TavilyClient` (Tavily) — **no live API calls**. `TAVILY_API_KEY` in `.env` is for manual testing only.
- `tavily-python` is **not** yet in `pyproject.toml`; `httpx` is. `.env.example` currently holds only `ANTHROPIC_API_KEY`.

**Reported, not acted on** (auto-capture disabled):
- Latent bug: `agent/scheduler.py` line 52 references an undefined `reddit_threshold` in the engagement filter. Harmless today (Reddit was dropped in `0b19baa`, so no item carries a `reddit` source), but a `NameError` waiting to fire. Out of scope for this change; worth a follow-up fix.
