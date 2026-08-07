<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0012 — Semantic Scholar keyword-search adapter](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0012-semantic-scholar-adapter.md)**
<!-- docket:backlink:end -->

# Semantic Scholar Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a config-gated `SemanticScholarAdapter` (source `s2`) on the 0009 `SourceAdapter` layer that keyword-searches the Semantic Scholar Graph API and maps results to `RawItem`.

**Architecture:** A new `agent/fetchers/semantic_scholar.py` module mirroring the `GitHubTrendingAdapter`/`HFPapersAdapter` shape: a plain `httpx.get` sweep adapter with fail-soft error handling, one query per configured search string, a single 429 backoff-then-fail-soft retry, and `RawItem` mapping (tldr-over-abstract body, citationCount engagement, arXiv-URL preference for dedup). It is registered in the `build_adapters` factory (`kind="sweep"`) under a new `sources.semantic_scholar` config block, with `sources.s2_queries` defaulting to `sources.arxiv_queries`. Optional `S2_API_KEY` env sends an `x-api-key` header.

**Tech Stack:** Python, `httpx` (already a dep, used by the sibling adapters), `pytest` + `pytest-mock` (`mocker`), `uv`.

## Global Constraints

- Suite runs as **`uv run python -m pytest`** after `uv sync --extra dev` — never a bare `pytest` (global pyenv shim loads a crashing deepeval plugin). Baseline is **180 passed**; this change adds tests on top.
- The adapter must be **fail-soft**: any error (network, HTTP status, malformed payload) skips the source and returns `[]`, never raises into the sweep.
- Body text truncated to **2000 chars** (matches arXiv/HF adapters).
- Never print, log, or commit any API key. `S2_API_KEY` is read from env only.
- Follow the existing adapter idiom exactly (`name` class attribute, `fetch() -> list[RawItem]`, per-adapter engagement policy). Do NOT re-filter at the sweep level.
- `RawItem` fields: `title`, `body`, `url`, `source`, `engagement` (int), `timestamp` (str). Extra fields default.

---

### Task 1: `SemanticScholarAdapter` — mapping, queries, and fail-soft

**Files:**
- Create: `agent/fetchers/semantic_scholar.py`
- Test: `tests/test_fetcher_semantic_scholar.py`

**Interfaces:**
- Consumes: `RawItem` from `agent.models`.
- Produces: class `SemanticScholarAdapter` with:
  - `name = "s2"` (class attribute)
  - `__init__(self, queries: list[str], max_per_query: int = 10, lookback_days: int = 7)`
  - `fetch(self) -> list[RawItem]`
  - Module constants: `S2_SEARCH_API = "https://api.semanticscholar.org/graph/v1/paper/search"`, `S2_FIELDS = "title,abstract,url,citationCount,tldr,publicationDate,externalIds"`, `LOOKBACK_DAYS = 7`.

**Behavior to implement:**
- For each query string, issue one `httpx.get(S2_SEARCH_API, params={"query": q, "fields": S2_FIELDS, "limit": max_per_query}, headers=..., timeout=15)`.
- Headers: `{}` by default; when `os.getenv("S2_API_KEY")` is set, add `{"x-api-key": <key>}`.
- Parse `resp.json().get("data", [])` (list of paper dicts).
- Per paper → `RawItem`:
  - `title` = `paper.get("title") or ""`
  - `body` = tldr text if present else abstract, truncated to 2000: `(_tldr_text(paper) or paper.get("abstract") or "")[:2000]` where `_tldr_text` reads `paper["tldr"]["text"]` guarding `None`/missing.
  - `url` = **prefer arXiv link** from `externalIds`: if `externalIds.get("ArXiv")` present, `f"https://arxiv.org/abs/{arxiv_id}"`; else `paper.get("url") or ""`.
  - `source` = `"s2"`
  - `engagement` = `paper.get("citationCount") or 0`
  - `timestamp` = `paper.get("publicationDate") or ""`
- **Lookback bounding:** filter out papers whose `publicationDate` (YYYY-MM-DD) is older than the UTC `today - lookback_days` cutoff. Papers with a missing/unparseable `publicationDate` are kept (no date to reject on) — mirror the tolerant posture; do not crash on bad dates.
- **429 handling:** on a `429` status, sleep a short backoff (e.g. `time.sleep(2)`) and retry the request **once**; if the retry is also 429 (or any other error), skip that query (fail-soft, continue to next query). Never abort the whole `fetch`.
- **Politeness:** a small inter-request `time.sleep` between queries when unkeyed keeps the adapter a good shared-pool citizen. Keep it small (e.g. 1s) and guard so tests can run without real delays being material — tests mock `httpx.get`, so the sleeps just need to not break them (or patch `time.sleep`).
- Whole-`fetch` `try/except` is per-query, so one bad query never sinks the others; an empty `queries` list returns `[]` immediately.

- [ ] **Step 1: Write the failing tests** in `tests/test_fetcher_semantic_scholar.py` (mirror `test_fetcher_github_trending.py`). A `_mock_get` helper returning a `MagicMock` with `.json()` and `.raise_for_status()`, plus a `.status_code` attribute for the 429 path. Cover:
  - `test_query_construction` — one `httpx.get` per query; params carry `query`, `fields` (the full field list), `limit`; endpoint URL correct.
  - `test_mapping_tldr_preferred_over_abstract` — a paper with both tldr and abstract maps `body` to the tldr text.
  - `test_mapping_falls_back_to_abstract_when_no_tldr` — tldr `None`/absent → body is the abstract (2000-char truncated).
  - `test_arxiv_url_preference` — a paper with `externalIds.ArXiv` maps `url` to `https://arxiv.org/abs/<id>`; a paper without it uses `paper["url"]`.
  - `test_engagement_is_citation_count` — `engagement == citationCount`; missing → 0.
  - `test_timestamp_is_publication_date` and `source == "s2"`.
  - `test_lookback_bounding_drops_old` — a paper dated before the cutoff is dropped; a recent one kept; a paper with no/blank `publicationDate` is kept.
  - `test_api_key_sends_header` — `S2_API_KEY` set → `x-api-key` header present with the value.
  - `test_no_key_no_header` — env unset → no `x-api-key` header.
  - `test_429_retry_then_skip` — first call returns a 429-shaped resp, retry also 429 → that query yields nothing (fail-soft), `httpx.get` called twice for the one query; patch `time.sleep`.
  - `test_429_retry_then_success` — first 429, retry 200 with data → items returned; `httpx.get` called twice.
  - `test_fail_soft_on_httpx_error` — `httpx.get` side_effect `ConnectError` → `fetch() == []`.
  - `test_fail_soft_on_status_error` — non-200/non-429 `raise_for_status` raising → that query skipped.
  - `test_fail_soft_on_malformed_payload` — `{"unexpected": "shape"}` → `[]`.
  - `test_empty_queries_returns_empty` — `SemanticScholarAdapter(queries=[])` → `fetch() == []` with no HTTP call.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_fetcher_semantic_scholar.py -v`
Expected: FAIL (module `agent.fetchers.semantic_scholar` does not exist yet).

- [ ] **Step 3: Write `agent/fetchers/semantic_scholar.py`** implementing the behavior above. Patch `time.sleep` in tests so retries/politeness sleeps don't slow the suite.

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `uv run python -m pytest tests/test_fetcher_semantic_scholar.py -v`
Expected: PASS (all new tests green).

- [ ] **Step 5: Commit** — `feat(0012): SemanticScholarAdapter — s2 keyword search on the adapter layer`

---

### Task 2: Factory registration + config wiring

**Files:**
- Modify: `agent/fetchers/base.py` (inside `build_adapters`, `kind == "sweep"` block)
- Modify: `config.yml` (add a `sources.semantic_scholar` block; `s2_queries` optional)
- Modify: `.env.example` (add optional `S2_API_KEY`)
- Test: `tests/test_build_adapters.py`

**Interfaces:**
- Consumes: `SemanticScholarAdapter` from `agent.fetchers.semantic_scholar` (imported inside `build_adapters` alongside the other lazy imports, matching the existing import-cycle-avoidance pattern).
- Produces: the sweep adapter list now includes a `SemanticScholarAdapter` when `sources.semantic_scholar.enabled` is truthy.

**Behavior to implement:**
- In `build_adapters`, after the `github_trending` block, read `s2_cfg = sources.get("semantic_scholar") or {}`. When `s2_cfg.get("enabled")`:
  - Resolve queries: `s2_queries = sources.get("s2_queries") or sources.get("arxiv_queries") or []` (default to the arXiv keyword list).
  - Append `SemanticScholarAdapter(queries=list(s2_queries), max_per_query=s2_cfg.get("max_per_query", 10), **lb)`.
  - Only construct when enabled AND there is at least one query, OR construct unconditionally-when-enabled and let an empty query list produce `[]` at fetch time. **Choose: construct when enabled** (mirrors `hf_papers`/`github_trending` which construct on `enabled` regardless of param emptiness). Keep the registration order last (after github_trending) so `test_sweep_all_new_sources_registered_in_order` in the existing suite is unaffected unless s2 is also enabled in that fixture.
- `config.yml` gains under `sources:`:
  ```yaml
    semantic_scholar:
      enabled: true          # Semantic Scholar Graph API keyword search
      max_per_query: 10
    # s2_queries defaults to arxiv_queries above when unset; uncomment to override
    # s2_queries:
    #   - "LLM agents"
  ```
- `.env.example` gains a commented/optional line: `S2_API_KEY=your_semantic_scholar_api_key_here` (optional — the unkeyed shared pool works with backoff).

- [ ] **Step 1: Write the failing tests** in `tests/test_build_adapters.py`:
  - `test_sweep_adds_semantic_scholar_when_enabled` — cfg with `sources.semantic_scholar.enabled: True` and `arxiv_queries: ["q"]` → exactly one `SemanticScholarAdapter` in the list; its `queries == ["q"]` (defaulted from arxiv_queries); `max_per_query` threaded.
  - `test_sweep_s2_uses_explicit_s2_queries_over_arxiv` — when `sources.s2_queries` is set, the adapter's `queries` uses it, not `arxiv_queries`.
  - `test_sweep_omits_semantic_scholar_when_disabled` — `enabled: False` → no `SemanticScholarAdapter`.
  - `test_sweep_omits_semantic_scholar_when_absent` — no `semantic_scholar` key → no adapter (and the existing `test_sweep_omits_new_sources_when_sources_block_absent` still holds).
  - `test_sweep_threads_lookback_into_semantic_scholar` — `lookback_days=30` reaches the s2 adapter.
  - Extend/confirm the ordering test only if s2 is added to its fixture; otherwise leave `test_sweep_all_new_sources_registered_in_order` untouched.
  - Assert the s2 adapter `isinstance(a, SourceAdapter)`.

- [ ] **Step 2: Run the new/affected tests to verify they fail**

Run: `uv run python -m pytest tests/test_build_adapters.py -v`
Expected: FAIL on the new s2 assertions (adapter not yet registered).

- [ ] **Step 3: Wire `build_adapters`, `config.yml`, `.env.example`** per the behavior above.

- [ ] **Step 4: Run the affected tests to verify they pass**

Run: `uv run python -m pytest tests/test_build_adapters.py -v`
Expected: PASS.

- [ ] **Step 5: Commit** — `feat(0012): register SemanticScholarAdapter in build_adapters; config + env`

---

### Task 3: Full-suite green + source-discovery wiring check

**Files:**
- Possibly touch: `tests/test_source_discovery.py` (only if it enumerates expected sweep sources and now needs `s2` — inspect first; do not restructure).

- [ ] **Step 1: Provision + run the whole suite**

Run: `uv sync --extra dev && uv run python -m pytest`
Expected: the prior **180** plus the new `test_fetcher_semantic_scholar.py` and `test_build_adapters.py` cases, all green, with no `deepeval`/`TracerProvider` crash and no `trafilatura` ImportError. If either tell appears, it is an environment provisioning issue (see the `pytest-shim-and-venv-provisioning` learning) — re-provision, do not treat as a code failure.

- [ ] **Step 2: Inspect `test_source_discovery.py`** — if it asserts the set of sweep sources and would now miss `s2`, update it minimally to include the new source; otherwise leave untouched.

- [ ] **Step 3: Commit** any test-wiring adjustment — `test(0012): source-discovery wiring for s2` (skip if no change needed).
