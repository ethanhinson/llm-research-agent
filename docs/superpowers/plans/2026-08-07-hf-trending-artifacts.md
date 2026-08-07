<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0016 — Hugging Face trending models/datasets adapter](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0016-hf-trending-artifacts.md)**
<!-- docket:backlink:end -->

# Plan — 0016 Hugging Face trending models/datasets adapter

**Change:** 0016 `hf-trending-artifacts` (trivial; no spec — design in the change body + reconcile log)
**Branch:** `feat/hf-trending-artifacts` (from `origin/main`)

> Plan authored inline (degraded to `auto`): the configured plan skill
> `superpowers:writing-plans` was not invokable on this machine, so the running
> agent authored this plan per the Skill layer missing-skill rule.

## Goal

Add a small `HFTrendingAdapter` (source id `hf-trending`) on the 0009 adapter
layer that surfaces top-N trending Hugging Face **models** and **datasets** —
release-type artifacts that never appear as papers (0010's daily-papers adapter
misses them). Config-gated, fail-soft, factory-registered, mocked tests.

## Established context (verified against `origin/main` + a live probe)

- **Templates:** `agent/fetchers/hf_papers.py` and `agent/fetchers/github_trending.py`
  (httpx.get + raise_for_status + `except Exception: return []`, mapping to
  `RawItem`). Mirror `github_trending`'s test file
  (`tests/test_fetcher_github_trending.py`) for style.
- **RawItem** (`agent/models.py`): `RawItem(title, body, url, source, engagement, timestamp, ...)`.
- **Factory:** `agent/fetchers/base.py::build_adapters(kind="sweep")` constructs
  each config-gated source under the `sources:` block, threading `**lb`
  (lookback_days) into every one.
- **Suite:** `uv sync --extra dev` then **`uv run python -m pytest`** (NEVER bare
  `pytest` — a global pyenv deepeval plugin crashes at startup; a
  `TracerProvider.get_tracer()` TypeError or `ModuleNotFoundError: trafilatura`
  at startup is env pollution, not a red suite). Baseline: **238 passing**.

### Live API shape (probed 2026-08-07, both HTTP 200)

`GET https://huggingface.co/api/models?sort=trendingScore&limit=N`
- list item keys: `id, likes, downloads, createdAt, trendingScore, tags, pipeline_tag, library_name, modelId, private, _id`
- **No `description` field on model list items** → `body` defaults to `""` for models.
- `createdAt` present (ISO-8601). Canonical URL: `https://huggingface.co/<id>`.

`GET https://huggingface.co/api/datasets?sort=trendingScore&limit=N`
- list item keys: `id, likes, downloads, description, createdAt, lastModified, author, tags, trendingScore, ...`
- **`description` present** → `body <- description` for datasets.
- `lastModified` and `createdAt` present. Canonical URL: `https://huggingface.co/datasets/<id>`.

`sort=trending` returns **HTTP 400** — the param MUST be `sort=trendingScore`.
No auth required on either endpoint.

## Design

`agent/fetchers/hf_trending.py`:

```
HF_MODELS_API   = "https://huggingface.co/api/models"
HF_DATASETS_API = "https://huggingface.co/api/datasets"
LOOKBACK_DAYS   = 7  # interface parity only — endpoints have no recency param

class HFTrendingAdapter:
    name = "hf-trending"
    def __init__(self, limit: int = 20, min_likes: int = 0,
                 lookback_days: int = LOOKBACK_DAYS): ...
    def fetch(self) -> list[RawItem]:
        # issue BOTH requests, each independently fail-soft; concatenate results
```

- **One `fetch()` issues both requests.** Each endpoint is wrapped in its own
  try/except so a failure of one still returns the other's items (helper e.g.
  `_fetch_endpoint(url, kind)`).
- **Params:** `{"sort": "trendingScore", "limit": self.limit}`, `timeout=15`.
- **Mapping per entry:**
  - `title <- entry["id"]` (skip entries with no `id`).
  - `body  <- entry.get("description") or ""` (models have none → `""`; datasets populated).
  - `url`: models → `https://huggingface.co/<id>`; datasets → `https://huggingface.co/datasets/<id>`.
  - `source <- "hf-trending"`.
  - `engagement <- entry.get("likes") or 0` — **likes is the engagement signal**, not downloads.
  - `timestamp <- entry.get("lastModified") or entry.get("createdAt") or ""`.
  - `downloads` is NOT mapped to engagement (informational only; not stored on RawItem).
- **Threshold:** drop entries with `likes < self.min_likes`.
- **`lookback_days`** is stored for interface parity but **never used** to filter
  or as an API param (trendingScore already encodes recency).
- **Fail-soft:** each endpoint call caught by `except Exception: return []` for
  that endpoint; a non-list JSON payload → `[]` for that endpoint.

## Tasks

### Task 1 — `HFTrendingAdapter` + unit tests (TDD)

New `tests/test_fetcher_hf_trending.py` (mirror the github_trending test: `mocker`,
`monkeypatch`, `httpx.get` mocked with a MagicMock whose `.json()` returns the
payload and `.raise_for_status()` is a no-op or raises). Because `fetch()` hits
two URLs, mock `httpx.get` with a `side_effect` function that dispatches on the
URL (models vs datasets payload).

Cover:
- **Query construction:** both endpoints hit exactly once; `params["sort"] == "trendingScore"`; `params["limit"]` equals the configured limit.
- **Mapping — models:** title == id, url == `https://huggingface.co/<id>`, engagement == likes, source == `hf-trending`, body == `""` (no description), timestamp from createdAt.
- **Mapping — datasets:** url == `https://huggingface.co/datasets/<id>`, body == the description, timestamp from lastModified (or createdAt fallback).
- **min_likes threshold** drops low-likes entries from both endpoints.
- **Fail-soft:** httpx error, HTTP status error, malformed (non-list) payload, empty payload → `[]` (or drop that endpoint).
- **Partial failure:** one endpoint raises, the other succeeds → only the succeeding endpoint's items are returned (never aborts, never empty when the other is healthy).
- **lookback_days accepted and stored** (constructor accepts it; `.lookback_days` attribute exists) but does not appear in request params.

Then create `agent/fetchers/hf_trending.py` to make the tests green.

**Success:** `uv run python -m pytest tests/test_fetcher_hf_trending.py` green; the new adapter file exists and matches the design above.

### Task 2 — Factory registration + config + factory tests

- **`agent/fetchers/base.py`:** inside `build_adapters(kind="sweep")`, **append**
  (after the existing `bluesky` block, so existing ordering assertions are
  undisturbed) a gated block:
  ```
  hf_trending_cfg = sources.get("hf_trending") or {}
  if hf_trending_cfg.get("enabled"):
      adapters.append(
          HFTrendingAdapter(
              limit=hf_trending_cfg.get("limit", 20),
              min_likes=hf_trending_cfg.get("min_likes", 0),
              **lb,
          )
      )
  ```
  Add the local import `from agent.fetchers.hf_trending import HFTrendingAdapter`
  alongside the other adapter imports in the function.
- **`config.yml`:** add an `hf_trending:` entry to the `sources:` block, mirroring
  the comment style of the neighbours:
  ```
  hf_trending:          # Change 0016: trending HF models + datasets (release-type artifacts)
    enabled: true       # no auth; top-N by trendingScore across models + datasets
    limit: 20           # per-endpoint top-N (models and datasets each)
    min_likes: 10       # likes floor (engagement); below is noise-prone
  ```
- **`tests/test_build_adapters.py`:** add additive cases (do not disturb existing
  ordering assertions — `test_sweep_all_new_sources_registered_in_order` does not
  enable `hf_trending`, so appending is safe):
  - adds `HFTrendingAdapter` when `sources.hf_trending.enabled` true, asserting `limit`/`min_likes` threaded;
  - omits when disabled;
  - lookback threaded (`.lookback_days`) into it when `lookback_days` widened.

**Success:** `uv run python -m pytest tests/test_build_adapters.py` green.

### Task 3 — Full suite + live verification

- **Full suite:** `uv sync --extra dev` then `uv run python -m pytest` — all
  green, count = 238 baseline + the new tests, no `deepeval`/`trafilatura`
  startup crash.
- **Live verification (required by the change):** one real call to EACH endpoint
  (`.../api/models?sort=trendingScore&limit=N` and `.../api/datasets?...`),
  recording the returned counts. Any LLM step (none expected here — this is a
  pure fetch adapter) would use OpenRouter (`llm.provider: openrouter`). Revert
  any live-run config change; discard any live-run vault artifacts.

**Success:** suite green at the expected count; both endpoints return items live;
counts recorded in the results file.

## Out of scope

- HF Spaces; paper linkage (dedup already collapses model-card→paper overlap by URL only).

## Notes / deviations

- Models list payload has **no `description`** — body defaults to `""` for models
  (a live-probed shape detail; not a bug). Datasets carry `description`.
- `downloads` is deliberately not the engagement signal (likes is), per the change body.
