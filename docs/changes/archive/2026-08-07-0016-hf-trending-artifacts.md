---
id: 16
slug: hf-trending-artifacts
title: Hugging Face trending models/datasets adapter
status: done
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: [10]
related: [10]
discovered_from: []
adrs: []
spec:
plan: docs/superpowers/plans/2026-08-07-hf-trending-artifacts.md
results: docs/results/2026-08-07-hf-trending-artifacts-results.md
trivial: true
auto_groomable: false
branch: feat/hf-trending-artifacts
pr: https://github.com/ethanhinson/llm-research-agent/pull/14
blocked_by:
claimed_at: 
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Plan | [2026-08-07-hf-trending-artifacts.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/hf-trending-artifacts/docs/superpowers/plans/2026-08-07-hf-trending-artifacts.md) |
| Results | [2026-08-07-hf-trending-artifacts-results.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/hf-trending-artifacts/docs/results/2026-08-07-hf-trending-artifacts-results.md) |
| PR | [#14](https://github.com/ethanhinson/llm-research-agent/pull/14) |
<!-- docket:artifacts:end -->

## Why

New open-model and dataset releases often never appear as papers — 0010's daily-papers adapter misses them. HF's hub API surfaces trending artifacts with no auth: `https://huggingface.co/api/models?sort=trendingScore&limit=N` (verified live 2026-08-07; note `sort=trending` returns 400 — the param must be `trendingScore`; same shape for `/api/datasets`).

## What changes

A small `HFTrendingAdapter` (source `hf-trending`) on the 0009 layer, following the established adapter pattern (0010's HFPapersAdapter is the template): fetch top-N trending models + datasets, map id/description/downloads+likes → RawItem (likes as engagement), config-gated under `sources.hf_trending: {enabled, limit, min_likes}`, fail-soft, factory-registered, mocked tests. Trivial: the pattern, config shape, and endpoint are all established — no open design questions.

## Out of scope

- HF Spaces; paper linkage (dedup already collapses model-card→paper overlap by URL only).

## Reconcile log

### 2026-08-07

Reconciled against current `origin/main`. Dependency 0010 is merged (`done`,
archived), and 0009's adapter layer (`agent/fetchers/base.py::build_adapters`)
is in place. The change body remains accurate:

- **Template confirmed.** `HFPapersAdapter` (`agent/fetchers/hf_papers.py`) and
  `GitHubTrendingAdapter` (`agent/fetchers/github_trending.py`) are the closest
  templates — `httpx.get` + `raise_for_status` + fail-soft `except Exception:
  return []`, mapping to `RawItem(title, body, url, source, engagement,
  timestamp)`. `github_trending`'s downloads/likes-style engagement mapping and
  its mocked test file are the pattern to mirror.
- **Config gating.** `sources:` block in `config.yml` gates each source on
  `enabled`; `build_adapters` constructs only the enabled ones. `hf_trending`
  slots in there as `{enabled, limit, min_likes}`, mirroring the existing
  entries. New tests land in `tests/test_build_adapters.py` (enabled/disabled/
  ordering/lookback threading) and a new `tests/test_fetcher_hf_trending.py`.
- **Lookback threading.** `build_adapters` threads `**lb` (lookback_days) into
  *every* new source, and `test_sweep_threads_lookback_into_new_sources`
  asserts each adapter exposes `.lookback_days`. The HF trending endpoints have
  no recency parameter (trendingScore already encodes recency), so the adapter
  will **accept** `lookback_days` for interface parity but not use it to filter
  — matching the factory contract without a spurious API param.
- **Engagement = likes.** Per the change body, `likes` maps to
  `RawItem.engagement`; `min_likes` is the threshold, `limit` the per-endpoint
  top-N. `downloads` is carried informationally (not the engagement signal).
- **Two endpoints, one adapter.** `.../api/models?sort=trendingScore&limit=N`
  and `.../api/datasets?sort=trendingScore&limit=N` (no auth; `sort=trending`
  returns 400 — must be `trendingScore`). One `HFTrendingAdapter.fetch()`
  issues both requests, each fail-soft, source `"hf-trending"`.

No scope change; no obsolescence. `trivial: true` stands — pattern, config
shape, and endpoints are all established.
