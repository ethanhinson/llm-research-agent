<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0010 — Expand article sources — HF daily papers, arXiv keyword search, GitHub trending, wired SourceDiscovery](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0010-expand-article-sources.md)**
<!-- docket:backlink:end -->

# Plan — Expand Article Sources (change 0010)

> Spec: `docs/superpowers/specs/2026-08-07-expand-article-sources.md` (on the `docket` branch)
> Depends on 0009 (source-adapter-layer, merged). Builds on `agent/fetchers/base.py`'s
> `SourceAdapter` protocol + `build_adapters` factory.

**Plan authored inline (auto-fallback):** the resolved `superpowers:writing-plans` skill was
not invocable at runtime, so this plan was written by the implementer per the docket Skill-layer
missing-skill rule. Build proceeds via the resolved `$SKILL_BUILD` (`superpowers:subagent-driven-development`),
falling back the same way if unavailable.

## Approach

Three new fail-soft `SourceAdapter` classes registered through 0009's `build_adapters` factory,
config-gated under the existing `sources:` block; then wire the dead `SourceDiscovery` tool into
the weekly deep sweep and a new `discover-sources` CLI command. Each task is TDD: focused mocked
unit test first, then implementation, then a per-task check. A live OpenRouter sweep verification
closes the change and records per-source counts.

Each adapter mirrors the existing fetcher shape (`name` class attr, `fetch() -> list[RawItem]`,
own lookback filter, own engagement policy, all errors swallowed to fail-soft). Config threads
from `cfg["sources"]` through `build_adapters(kind="sweep", ...)`.

## Tasks

### Task 1 — `HFPapersAdapter` (`agent/fetchers/hf_papers.py`, source `hf-papers`)

- **Test** (`tests/test_fetcher_hf_papers.py`): mock `httpx.get` returning a daily_papers JSON
  payload (list of `{paper: {title, summary, upvotes, publishedAt, id}}`-shaped dicts, matching
  HF's actual shape); assert mapping to `RawItem` (title, `summary[:2000]` body, HF/arXiv URL,
  `upvotes` → engagement, publishedAt → timestamp), lookback filtering (default 7 days, threaded
  `lookback_days`), `min_upvotes` engagement policy (default 0 keeps all), and fail-soft: HTTP
  error and malformed payload both return `[]` without raising.
- **Implement**: `HFPapersAdapter` with `name = "hf-papers"`, `__init__(self, min_upvotes=0,
  lookback_days=7)`, `fetch()` hitting `https://huggingface.co/api/daily_papers`. URL built from
  the paper id as `https://huggingface.co/papers/<id>` (or the arXiv id when present). Parse
  `publishedAt`/`published` date; drop items older than the window; drop items below `min_upvotes`.
  Wrap the whole fetch body so any exception yields `[]` (the sweep's `_fetch` wrapper also
  catches, but adapter-level fail-soft keeps a single malformed feed from losing the batch — mirror
  `WebFetcher`).

### Task 2 — `ArxivSearchAdapter` (extend `agent/fetchers/arxiv.py`, source `arxiv/search`)

- **Test** (extend `tests/test_fetcher_arxiv.py`): patch `arxiv.Client.results` to return fake
  results; assert one keyword `arxiv.Search(query=...)` per configured query, sorted by submitted
  date, lookback-windowed and capped per query, mapped to `RawItem(source="arxiv/search")`; empty
  query list → no fetch, `[]`; fail-soft on a raising search.
- **Implement**: `ArxivSearchAdapter(queries: list[str], max_results_per_query=10, lookback_days=7)`
  with `name = "arxiv"` (family id; per-item `source="arxiv/search"`). For each query run
  `arxiv.Search(query=q, max_results=max_results_per_query, sort_by=SubmittedDate)`, post-filter by
  `published` against the window (per the live-testing learning: arXiv 500s on `[X TO *]` range
  queries — filter in Python, never in the query). Reuse the existing mapping (`summary[:2000]`,
  `entry_id` URL). Keep the existing `ArxivFetcher` firehose untouched.

### Task 3 — `GitHubTrendingAdapter` (`agent/fetchers/github_trending.py`, source `github`)

- **Test** (`tests/test_fetcher_github_trending.py`): mock `httpx.get` on the search API returning
  a `{items: [{full_name, description, html_url, stargazers_count, pushed_at}]}` payload; assert
  topic + pushed-within-window query construction, `min_stars` engagement threshold, mapping
  (`full_name` + description → title/body, html_url, stars → engagement, pushed_at → timestamp),
  `GITHUB_TOKEN` honored from env when present (Authorization header) and omitted when absent, and
  fail-soft on HTTP error / malformed payload.
- **Implement**: `GitHubTrendingAdapter(topics: list[str], min_stars=100, lookback_days=7)` with
  `name = "github"`. Build a search query `topic:<t> ... pushed:>=<cutoff-date>` (OR across topics
  or one request per topic — one request per topic keeps each query simple), `sort=stars`,
  `order=desc`; call `https://api.github.com/search/repositories`. Add `Authorization: Bearer
  <GITHUB_TOKEN>` header only when the env var is set. Drop repos below `min_stars`. Fail-soft.

### Task 4 — Register the three adapters in `build_adapters` + config threading

- **Test** (extend `tests/test_build_adapters.py`): `kind="sweep"` with a `sources` config block
  enabling each new source appends the right adapter(s) in a deterministic order; each disabled/
  absent → omitted; `arxiv_queries` empty/absent → no `ArxivSearchAdapter`; existing HN/arXiv/web
  behavior unchanged (regression). Thread `lookback_days` into the new adapters too.
- **Implement**: extend `build_adapters(kind="sweep", ...)` to read a `sources` sub-dict from `cfg`
  (`cfg["sources"]`): `hf_papers.{enabled,min_upvotes}` → `HFPapersAdapter`; `arxiv_queries` (list)
  → `ArxivSearchAdapter`; `github_trending.{enabled,topics,min_stars}` → `GitHubTrendingAdapter`.
  Import the new classes lazily inside the function (matching the existing cycle-avoidance pattern).
  Re-export the new classes into `agent/scheduler.py` as patch seams (matching the `# noqa: F401`
  block). Pass `cfg["sources"]` through from `run_sweep` (it currently builds
  `{"thresholds": thresholds}` — widen to include `sources`).

### Task 5 — Thread `sources` config from `cli.py`/`run_sweep` into the sweep

- **Test** (extend `tests/test_cli.py` or a scheduler test): a config with `sources.hf_papers` etc.
  reaches `build_adapters`; a config without them behaves exactly as today. Verify `run_sweep`
  passes the `sources` dict.
- **Implement**: in `agent/scheduler.py:run_sweep`, add a `sources_cfg: dict | None = None`
  param (default `None` → `{}`) and pass it into `build_adapters` as `cfg["sources"]`. In
  `cli.py:cmd_sweep` and `cmd_start`, read `cfg.get("sources", {})` and thread it through. Keep
  `feeds` extraction as-is (it already reads `cfg["sources"]["feeds"]`).

### Task 6 — Wire `SourceDiscovery` into the weekly deep sweep + `discover-sources` CLI

- **Test** (extend `tests/test_source_discovery.py` + a scheduler/cli test with a `FakeLLM`):
  a helper `append_suggestions(sources_path, suggestions)` writes a dated `## Suggested (pending
  review)` section; re-running with the same suggestions is idempotent (no duplicate lines);
  suggestions already present as configured feeds are deduped out; the LLM never writes config.
  Deep sweep (`deep=True`) triggers discovery; daily sweep (`deep=False`) does not.
- **Implement**:
  - A small `append_suggestions` writer (in `source_discovery.py` or the scheduler) that appends
    only genuinely-new, deduped suggestions to `vault/sources.md` under a dated
    `## Suggested (pending review)` heading. Dedup against existing feed URLs/names in the file
    and against prior suggestions.
  - In `run_sweep`, when `deep=True`, after the write path, gather recent titles
    (`_recent_strategy_titles`), call `SourceDiscovery(sources_path=vault/sources.md,
    llm_cfg=llm_cfg).suggest(recent_titles)`, and append. Fail-soft (a discovery error never
    aborts the sweep).
  - New CLI `discover-sources` command (`cmd_discover_sources` + parser): run the same
    discovery+append path once on demand, print a count. Route LLM through the configured provider
    (`llm_cfg`) so it works on OpenRouter.

### Task 7 — Config documentation + example block

- **Implement**: add the `sources:` keys (`hf_papers`, `arxiv_queries`, `github_trending`) to
  `config.yml` alongside `feeds` with the spec's defaults, enabled. (No test — config data.)

### Task 8 — Full suite gate

- Run `uv sync --extra dev` then `uv run python -m pytest` (canonical command per the
  pytest-shim learning). All green before the live verification.

### Task 9 — Live sweep verification (OpenRouter) — do NOT defer

- Temporarily set `llm.provider: openrouter` in `config.yml` (Anthropic key has no credit — the
  #7/#8 pattern; OpenRouter needs no Anthropic credit). Enable the three new sources.
- Run `uv run python cli.py sweep --lookback-days 3` (or a small window) and, separately,
  `uv run python cli.py discover-sources`. Confirm items from each new source reach the funnel and
  the vault write path; separate expected soft-degradations (paywalled `enrich failed 403/404`,
  missing search-backend keys) from real errors per the live-testing learning.
- **Record per-source counts** in the results file (`docs/results/2026-08-07-expand-article-sources-results.md`).
- **Revert** the `provider: openrouter` config change (and any source-enable toggles used only for
  the live run) before committing. **Discard live-run vault artifacts** (new notes, sources.md
  suggestions) — do not commit them. Never print or commit the API key.

## Risks / notes

- HF `daily_papers` payload shape is assumed from the public API; the live run validates the real
  shape (mocks can't — live-testing learning). If the real shape differs, adjust mapping in Task 9
  follow-up before the results file is written.
- GitHub search API unauthenticated rate limit (10 req/min) is ample at sweep cadence.
- `deep` param is currently threaded but unused in `run_sweep`; Task 6 gives it its first real use.
