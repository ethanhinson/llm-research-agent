---
id: 2
slug: multi-backend-web-search
title: Multi-Backend Web Search — continuous internet search across Tavily, Bing, and SerpAPI
status: proposed
priority: medium
type: feat
created: 2026-08-01
updated: 2026-08-01
depends_on: []
related: [1]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-01-multi-backend-web-search.md
plan:
results:
trivial: false
auto_groomable: false
branch:
claimed_at:
pr:
issue:
blocked_by:
reconciled: false
---

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-01-multi-backend-web-search.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-01-multi-backend-web-search.md) |
<!-- docket:artifacts:end -->

## Why

The existing agent only monitors known feeds (HN, arXiv, curated RSS). Breaking content on blogs, forums, and general web can go undetected for days or never surface at all. Adding parallel queries across Tavily, Bing, and SerpAPI on a 6-hour loop catches relevant LLM content within hours of publication, dramatically widening source coverage without any manual curation.

## What changes

- New `agent/fetchers/web_search.py` — `SearchClient` protocol with `TavilySearchClient`, `BingSearchClient`, and `SerpAPISearchClient` implementations; unconfigured backends are silently skipped
- New `agent/fetchers/multi_search.py` — `MultiSearchFetcher` that fans out all (client, query) pairs in parallel and deduplicates results by URL
- New `agent/tools/search_query_generator.py` — hybrid query builder: fixed topic anchors from `config.yml` plus 2–3 Claude Haiku–generated dynamic queries per sweep
- `agent/scheduler.py` — new `search_sweep` APScheduler job running every `search.interval_hours` (default 6)
- `config.yml` — new `search:` block (interval, max results, fixed queries, dynamic toggle)
- `.env` additions documented: `TAVILY_API_KEY`, `BING_SEARCH_API_KEY`, `SERPAPI_KEY`
- New dep: `tavily-python >=0.3`

## Out of scope

- Brave Search, Perplexity, or other backends
- Result caching between search sweeps
- Per-query cost tracking
- A dedicated `search-sweep` CLI subcommand

## Open questions

None — design settled.
