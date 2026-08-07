<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0016 — Hugging Face trending models/datasets adapter](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0016-hf-trending-artifacts.md)**
<!-- docket:backlink:end -->

# Hugging Face trending models/datasets adapter — results

Change: #16 · Branch: feat/hf-trending-artifacts · PR: (opened at close-out) · Plan: docs/superpowers/plans/2026-08-07-hf-trending-artifacts.md · ADRs: none

## Verify (human)

- [x] Live call to `GET https://huggingface.co/api/models?sort=trendingScore&limit=20` — HTTP 200, **20 entries** (top: `MiniMaxAI/MiniMax-H3`, likes 2930).
- [x] Live call to `GET https://huggingface.co/api/datasets?sort=trendingScore&limit=20` — HTTP 200, **20 entries** (top: `HuggingFaceFW/fineweb`, likes 3112).
- [x] Full adapter run (`limit=20, min_likes=10`) live: **40 items** (20 models + 20 datasets), `likes` mapped to `RawItem.engagement`.
- [x] Gotcha confirmed live: `sort=trending` → **HTTP 400** (the param must be `trendingScore`).
- [ ] Optional at merge gate: re-run one live call to each endpoint to reconfirm the API is still reachable (counts will vary as trending shifts).

## Findings

- **Model list payloads carry no `description`** (live-probed): the `/api/models` list items expose `id, likes, downloads, createdAt, trendingScore, tags, pipeline_tag, ...` but **no** `description`, so a model's `RawItem.body` defaults to `""`. Datasets **do** carry `description`. Not a bug — a shape detail baked into the mapping and its tests.
- **`downloads` is deliberately not the engagement signal** — `likes` is, per the change body. `downloads` is left informational and not stored on `RawItem`.
- **`lookback_days` is interface-only** here. `build_adapters` threads `**lb` into every source and `test_sweep_threads_lookback_into_*` asserts each adapter exposes `.lookback_days`; the HF trending endpoints have no recency parameter (trendingScore already encodes recency), so the adapter stores `lookback_days` but never uses it to filter or as an API param.
- **Two endpoints, one adapter, independently fail-soft** — a failure of the models endpoint still returns datasets, and vice-versa (covered by `test_partial_failure_*`).
- **No ADR warranted** — the adapter strictly follows the established 0009/0010 protocol-plus-factory pattern (ADR-0001) and 0010's config-gating and fail-soft conventions; no non-obvious decision was made.

### Build-environment degradations (worth the human's awareness)

- The configured `plan`, `build`, and `review` skills (`superpowers:writing-plans`,
  `superpowers:subagent-driven-development`, `superpowers:requesting-code-review`)
  were **not invokable on this machine** ("Unknown skill"). Per the docket Skill
  layer *missing-skill rule*, each degraded to `auto`: the plan was authored
  inline, the plan executed inline with TDD (tests-first, then implementation),
  and a whole-branch review performed inline before the PR. Not a repo-state
  issue — skill availability is per-machine.

## Test results

- Baseline: **238 passed**. After this change: **255 passed** (`+17`: 12 in
  `tests/test_fetcher_hf_trending.py`, 5 in `tests/test_build_adapters.py`).
- Suite run canonically: `uv sync --extra dev` then `uv run python -m pytest`
  (never a bare `pytest` — a global pyenv deepeval plugin crashes at startup;
  see the `pytest-shim-and-venv-provisioning` learning). No `deepeval` /
  `TracerProvider` crash, no `trafilatura` ImportError.

## Follow-ups

None. Auto-capture is disabled repo-wide; no distinct follow-up work surfaced during reconcile or review.
