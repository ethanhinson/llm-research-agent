# Multi-Backend Web Search — Design Spec

**Date:** 2026-08-01
**Status:** Approved

<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0002 — Multi-Backend Web Search — continuous internet search across Tavily, Bing, and SerpAPI](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0002-multi-backend-web-search.md)**
<!-- docket:backlink:end -->

---

## Overview

Add a continuous web search layer to the LLM research agent. Rather than waiting for content to surface on HN, arXiv, or curated RSS feeds, this change introduces a multi-backend search fetcher that queries Tavily, Bing Web Search, and SerpAPI in parallel on a tighter cadence (every 6 hours by default). Hybrid query generation — fixed topic anchors plus Claude-generated dynamic queries — keeps the search adaptive over time.

Results flow through the existing evaluator → deduplicator → writer pipeline unchanged.

---

## Architecture changes

```
agent/
├── fetchers/
│   ├── web_search.py         # NEW: SearchClient protocol + Tavily/Bing/SerpAPI impls
│   └── multi_search.py       # NEW: MultiSearchFetcher — fan-out + URL dedup
├── tools/
│   └── search_query_generator.py  # NEW: hybrid query builder
└── scheduler.py              # MODIFIED: add search_sweep job
```

---

## SearchClient protocol

```python
class SearchClient(Protocol):
    def search(self, query: str, max_results: int = 10) -> list[RawItem]: ...
```

Three implementations in `agent/fetchers/web_search.py`:

### TavilySearchClient
- Uses the official `tavily-python` SDK
- `search_depth="basic"`, `include_answer=False`, `max_results` per query
- Maps result fields: `title`, `url`, `content` → `RawItem.body`, `source="search/tavily"`, `engagement=0`
- Auth: `TAVILY_API_KEY` env var

### BingSearchClient
- `httpx` call to `https://api.bing.microsoft.com/v7.0/search`
- `freshness=Week` for recency; `count=max_results`
- Maps `name` → title, `snippet` → body, `url` → url, `source="search/bing"`
- Auth: `BING_SEARCH_API_KEY` env var

### SerpAPISearchClient
- `httpx` call to `https://serpapi.com/search.json` with `engine=google`
- Maps `organic_results[*]`: `title`, `link` → url, `snippet` → body, `source="search/serpapi"`
- Auth: `SERPAPI_KEY` env var
- Respects SerpAPI's rate limits via a short per-query sleep (0.5s)

All three clients silently skip (log a warning, return `[]`) if their API key is absent — so unconfigured backends are just ignored, not fatal.

---

## MultiSearchFetcher

`agent/fetchers/multi_search.py`:

```python
class MultiSearchFetcher:
    def __init__(self, clients: list[SearchClient], queries: list[str], max_results_per_query: int = 10):
        ...

    def fetch(self) -> list[RawItem]:
        ...
```

- Fans out all `(client, query)` combinations using `concurrent.futures.ThreadPoolExecutor`
- Deduplicates by URL across all results (first-seen wins)
- Returns a flat `list[RawItem]`; order is stable (client order → query order within each client)

---

## SearchQueryGenerator

`agent/tools/search_query_generator.py`:

```python
class SearchQueryGenerator:
    def queries(self, recent_titles: list[str]) -> list[str]: ...
```

- **Fixed anchors** — read from `config.yml` key `search.fixed_queries` (list of strings). Default set:
  ```yaml
  - "LLM prompting techniques 2026"
  - "agentic AI patterns"
  - "multimodal language models"
  - "LLM inference optimization"
  - "AI agent frameworks"
  ```
- **Dynamic queries** — if `search.dynamic_queries_enabled: true` (default), ask Claude Haiku to generate 2–3 additional queries based on `recent_titles` from the vault. Uses the same `anthropic.Anthropic` client as `SourceDiscovery`. Returns `[]` on any API error (non-fatal).
- Returns `fixed + dynamic` (deduplicated, capped at `search.max_queries` default 10).

---

## Scheduler integration

New `search_sweep` function in `agent/scheduler.py`:

```python
def search_sweep(cfg: dict, api_key: str) -> None:
    queries = SearchQueryGenerator(cfg, api_key).queries(recent_titles=[...])
    clients = build_clients(cfg)          # one per configured + keyed backend
    fetcher = MultiSearchFetcher(clients, queries)
    items = fetcher.fetch()
    # → existing evaluator → deduplicator → writer pipeline
```

Registered with APScheduler as:
```python
scheduler.add_job(search_sweep, "interval", hours=cfg["search"]["interval_hours"])
```

`interval_hours` default: `6`. Configurable in `config.yml` under `search.interval_hours`.

The `cli.py` `start` command registers this job alongside the existing daily/weekly sweep jobs.

---

## Config additions (`config.yml`)

```yaml
search:
  interval_hours: 6
  max_results_per_query: 10
  max_queries: 10
  dynamic_queries_enabled: true
  fixed_queries:
    - "LLM prompting techniques 2026"
    - "agentic AI patterns"
    - "multimodal language models"
    - "LLM inference optimization"
    - "AI agent frameworks"
```

Backend API keys go in `.env` (gitignored):
```
TAVILY_API_KEY=...
BING_SEARCH_API_KEY=...
SERPAPI_KEY=...
```

---

## Pipeline integration

Search results enter the pipeline as `RawItem` objects with `engagement=0`. The engagement filter already treats `web/*` sources with a threshold of `0` (pass-through). The `source` prefix `search/tavily`, `search/bing`, `search/serpapi` routes them through the same evaluator and writer as existing fetchers — no pipeline changes needed.

Vault notes get `source: search/tavily` (etc.) in frontmatter, which makes it easy to filter by origin inside Obsidian.

---

## New dependencies

```toml
tavily-python = ">=0.3"
```

Bing and SerpAPI use only `httpx` (already a dependency).

---

## Out of scope

- Brave Search, Perplexity, or other backends beyond the three above
- Result caching between search sweeps
- Per-query result quotas or cost tracking
- A `search-sweep` CLI subcommand (the existing `sweep` command already triggers all fetchers in the main sweep; the search sweep runs on its own timer under `start`)

---

## Open questions

None — design settled with the user.
