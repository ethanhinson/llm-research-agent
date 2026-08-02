<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0002 — Multi-Backend Web Search — continuous internet search across Tavily, Bing, and SerpAPI](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0002-multi-backend-web-search.md)**
<!-- docket:backlink:end -->

# Implementation Plan — Multi-Backend Web Search (change 0002)

**Spec:** `docs/superpowers/specs/2026-08-01-multi-backend-web-search.md` (on `docket`)
**Branch:** `feat/multi-backend-web-search` from `origin/main`
**Method:** TDD, task-by-task. Each task: write failing test(s) → implement → green → commit.

> Plan authored inline (auto-fallback): the resolved plan skill `superpowers:writing-plans` was
> unavailable in the build session. Build role resolves to `superpowers:subagent-driven-development`.

## Ground truth (from reconcile)

- `RawItem` (`agent/models.py`) requires six fields: `title, body, url, source, engagement, timestamp`
  (a string); `novelty, validated, sources_count, category, tags` default. **Every search client
  must pass `timestamp`** — use the backend's published date when present, else `""`.
- Fetchers are duck-typed (`__init__` + `fetch() -> list[RawItem]`), no base class.
- `anthropic.Anthropic(api_key=...)` + model `claude-haiku-4-5-20251001` — reuse the
  `agent/tools/source_discovery.py` pattern for dynamic queries.
- Tests: `pytest` + `pytest-mock` (`mocker`). Mock `httpx.get` (Bing/SerpAPI) and the Tavily
  client object (Tavily). **No live API calls.** `TAVILY_API_KEY` in `.env` is manual-testing only.
- The scheduler seam is `start_scheduler` (`agent/scheduler.py`, `BlockingScheduler`); `cli.py`
  `cmd_start` threads config in.
- All search clients silently skip (log a warning, return `[]`) when their key is absent.

## Tasks

### Task 1 — Dependency + config scaffolding

Add the dependency and config so later tasks can read real values.

- `pyproject.toml`: add `"tavily-python>=0.3"` to `[project].dependencies`.
- `config.yml`: add the `search:` block:
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
- `.env.example`: append `TAVILY_API_KEY=`, `BING_SEARCH_API_KEY=`, `SERPAPI_KEY=` (placeholder values).

**Tests:** a small test asserting `config.yml` parses and exposes `search.interval_hours == 6`,
`search.fixed_queries` non-empty (parse via `yaml.safe_load`, mirroring existing config usage).
No live-API surface here.

**Commit:** `feat(0002): add tavily dep, search config block, env placeholders`

### Task 2 — `SearchClient` protocol + three clients (`agent/fetchers/web_search.py`)

Define `SearchClient` as a `typing.Protocol`:
```python
class SearchClient(Protocol):
    def search(self, query: str, max_results: int = 10) -> list[RawItem]: ...
```

Implement three concrete clients. Each reads its key from the environment in `__init__`
(via `os.getenv`); when the key is absent, `search()` logs a warning and returns `[]`.
Each maps results into `RawItem` with **all six required fields** (`engagement=0`,
`timestamp` = backend date string or `""`).

- **`TavilySearchClient`** — key `TAVILY_API_KEY`. Uses `tavily-python` (`TavilyClient(api_key=...)`,
  `.search(query, search_depth="basic", include_answer=False, max_results=...)`). Maps each result:
  `title` → title, `url` → url, `content` → body, `source="search/tavily"`. `timestamp` from
  `published_date` if present else `""`.
- **`BingSearchClient`** — key `BING_SEARCH_API_KEY`. `httpx.get`
  `https://api.bing.microsoft.com/v7.0/search`, header `Ocp-Apim-Subscription-Key`, params
  `q, count=max_results, freshness="Week"`. Maps `webPages.value[*]`: `name` → title,
  `snippet` → body, `url` → url, `source="search/bing"`, `timestamp` from `dateLastCrawled` if
  present else `""`.
- **`SerpAPISearchClient`** — key `SERPAPI_KEY`. `httpx.get` `https://serpapi.com/search.json`,
  params `q, engine="google", api_key, num=max_results`. Maps `organic_results[*]`:
  `title` → title, `link` → url, `snippet` → body, `source="search/serpapi"`, `timestamp` from
  `date` if present else `""`. Short `time.sleep(0.5)` per query for rate limits.

Each client wraps its network/parse in try/except and returns `[]` on failure (log a warning),
mirroring the existing fetchers' resilience.

**Tests (`tests/test_fetcher_web_search.py`):**
- Tavily: `mocker.patch` the `TavilyClient` so `.search()` returns a canned dict; assert mapping →
  `RawItem` fields (source, engagement=0, timestamp).
- Bing: `mocker.patch("agent.fetchers.web_search.httpx.get")` returning a fake response with
  `.json()`; assert mapping.
- SerpAPI: same `httpx.get` patch; assert mapping. Patch `time.sleep` to avoid real delay.
- Missing-key: instantiate each with the env var unset (`monkeypatch.delenv`); assert `search()`
  returns `[]` and does not call the network.
- Network error: patched call raises; assert `[]` returned, no exception escapes.

**Commit:** `feat(0002): SearchClient protocol + Tavily/Bing/SerpAPI clients`

### Task 3 — `MultiSearchFetcher` (`agent/fetchers/multi_search.py`)

```python
class MultiSearchFetcher:
    def __init__(self, clients: list[SearchClient], queries: list[str],
                 max_results_per_query: int = 10): ...
    def fetch(self) -> list[RawItem]: ...
```
- Fan out all `(client, query)` pairs via `concurrent.futures.ThreadPoolExecutor`.
- Deduplicate by `url` across all results, **first-seen wins**.
- Stable order: client order → query order within each client (collect futures in submission order).

**Tests (`tests/test_multi_search.py`):**
- Two fake clients returning overlapping-URL items → assert dedup (first-seen wins) and stable
  order. Fake clients are plain objects with a `.search()` method — no network.
- Empty clients / empty queries → `[]`.
- A client that raises inside `search()` → its failure is isolated, other clients' results still
  returned.

**Commit:** `feat(0002): MultiSearchFetcher — parallel fan-out + URL dedup`

### Task 4 — `SearchQueryGenerator` (`agent/tools/search_query_generator.py`)

```python
class SearchQueryGenerator:
    def __init__(self, cfg: dict, api_key: str | None = None): ...
    def queries(self, recent_titles: list[str]) -> list[str]: ...
```
- Fixed anchors from `cfg["search"]["fixed_queries"]`.
- If `cfg["search"]["dynamic_queries_enabled"]` (default true) and an api_key is present, ask
  Claude Haiku (`claude-haiku-4-5-20251001`, `anthropic.Anthropic`) for 2–3 dynamic queries from
  `recent_titles`. Return `[]` from the dynamic step on any API error (non-fatal).
- Return `fixed + dynamic`, deduplicated, capped at `cfg["search"]["max_queries"]` (default 10).

**Tests (`tests/test_search_query_generator.py`):**
- Dynamic disabled → returns exactly the fixed anchors.
- Dynamic enabled → `mocker.patch` the anthropic client to return canned lines; assert
  fixed+dynamic merged, deduped, capped.
- Anthropic raises → dynamic step yields `[]`, fixed anchors still returned (non-fatal).
- No api_key → dynamic skipped.

**Commit:** `feat(0002): hybrid SearchQueryGenerator (fixed anchors + Haiku dynamic)`

### Task 5 — `search_sweep` + scheduler wiring (`agent/scheduler.py`, `cli.py`)

- `agent/scheduler.py`: add
  ```python
  def search_sweep(vault_path, index_path, search_cfg, api_key) -> list[RawItem]:
      # build clients (all three; each self-skips if unkeyed)
      # generate queries (recent titles read from the vault, best-effort)
      # MultiSearchFetcher(...).fetch()
      # → dedup → engagement pass-through (search/* like web/*) → topic → cross_validate
      #   → evaluate → novelty threshold → write
  ```
  Reuse the existing pipeline helpers (`Deduplicator`, `is_relevant`, `cross_validate`,
  `Evaluator`, `Writer`) exactly as `run_sweep` does. `search/*` sources pass the engagement
  filter unconditionally (same as `web/`).
- Extend `start_scheduler` with a `search_cfg: dict | None = None` parameter; when present and
  `search_cfg` is non-empty, register `search_sweep` as an interval job
  (`scheduler.add_job(search_sweep, "interval", hours=search_cfg["interval_hours"], kwargs=...)`,
  id `search_sweep`).
- `cli.py` `cmd_start`: read `cfg.get("search", {})` and pass it as `search_cfg`.

**Tests (`tests/test_scheduler.py` additions + `tests/test_cli.py`):**
- `search_sweep`: patch the fetcher/evaluator/writer boundaries (mirror `test_smoke.py`/
  `test_scheduler.py` style) so no network/LLM runs; assert it drives the pipeline and returns
  written items. Confirm `search/*` items survive the engagement filter.
- `start_scheduler` with `search_cfg` set registers a job with id `search_sweep`
  (use a `BlockingScheduler` and inspect `get_jobs()`, or patch `.start()` / `.add_job`).
- `start_scheduler` with `search_cfg` None/empty registers **no** search job (back-compat).
- `cmd_start` passes the `search` block through (extend the existing `cmd_start` test to assert
  `start_scheduler` received `search_cfg`).

**Commit:** `feat(0002): search_sweep job + start_scheduler/cli wiring`

### Task 6 — Full-suite green + docs touch-up

- Run the whole `pytest` suite; all green.
- If README/usage docs mention the search keys, add a one-line note (only if such docs exist;
  do not invent new doc files).

**Commit:** `test(0002): full suite green for multi-backend web search` (only if changes made)

## Out of scope (do not touch)

- Brave/Perplexity backends, result caching, cost tracking, a `search-sweep` CLI subcommand.
- The `reddit_threshold` NameError on `agent/scheduler.py` line 52 — latent, harmless today
  (no `reddit` source exists), flagged for a separate follow-up. **Leave it alone.**

## Verification

- `pytest` fully green with new tests.
- No live API calls in any test (all backends mocked).
- `python cli.py start` wiring imports cleanly (no execution needed in tests).
