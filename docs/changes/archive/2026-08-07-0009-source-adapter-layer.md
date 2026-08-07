---
id: 9
slug: source-adapter-layer
title: Unify article intake behind a SourceAdapter layer
status: done
priority: medium
type: refactor
created: 2026-08-07
updated: 2026-08-07
depends_on: []
related: [2, 8, 10]
discovered_from: []
adrs: [1]
spec: docs/superpowers/specs/2026-08-07-source-adapter-layer.md
plan: docs/superpowers/plans/2026-08-07-source-adapter-layer.md
results:
trivial: false
auto_groomable: false
branch: feat/source-adapter-layer
claimed_at: 
pr: https://github.com/ethanhinson/llm-research-agent/pull/9
blocked_by:
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-07-source-adapter-layer.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-source-adapter-layer.md) |
| Plan | [2026-08-07-source-adapter-layer.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/source-adapter-layer/docs/superpowers/plans/2026-08-07-source-adapter-layer.md) |
| PR | [#9](https://github.com/ethanhinson/llm-research-agent/pull/9) |
| ADRs | [ADR-0001](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/adrs/0001-llm-provider-abstraction-injected-client.md) |
<!-- docket:artifacts:end -->

## Why

Article intake has no adapter layer — two half-protocols (implicit `.fetch()` on HN/arXiv/RSS fetchers, formal `SearchClient` for the search backends) and both sweep functions hard-code fetcher construction plus stringly-typed engagement allowlists. Adding a source means editing `scheduler.py` in multiple places, and a source string missing from an allowlist is silently dropped after fetching. `run_sweep` also carries a live `NameError` landmine (`reddit_threshold`, undefined, scheduler.py:110). Change 0010 wants to add three new sources; this layer must exist first so each is one adapter class plus config.

## What changes

- A `SourceAdapter` protocol (`agent/fetchers/base.py`) + config-driven `build_adapters` factory — the same protocol-plus-factory idiom as the `LLMClient` abstraction (ADR-0001).
- Existing fetchers (HN, arXiv, RSS, multi-search) migrate to the protocol; engagement policy moves into each adapter; the sweep-level substring allowlists are deleted (removing the `reddit_threshold` landmine with them).
- Both sweeps iterate the factory's adapter set with the existing per-adapter fail-soft behavior. Pure refactor: same sources, same items kept, proven by parity tests.

## Out of scope

- Any new source (change 0010, which depends on this).
- Reviving Reddit; changing sweep cadences or funnel order; `SourceDiscovery`.

## Reconcile log

### 2026-08-07 — reconciled against current code, spec, ADR-0001, related [2, 8, 10]

- **Spec still accurate; no design invalidation, not obsolete.** `agent/scheduler.py` matches the spec's description exactly: `run_sweep` (lines 106-112) and `search_sweep` (lines 177-183) each hard-code a substring-match engagement allowlist, and the `reddit_threshold` NameError landmine is live at `scheduler.py:110` (`run_sweep`'s `after_engagement`). The two half-protocols exist as described: implicit `.fetch() -> list[RawItem]` on `HNFetcher`/`ArxivFetcher`/`WebFetcher`, and the formal `SearchClient` Protocol (`agent/fetchers/web_search.py`) wrapped by `MultiSearchFetcher`. `agent/fetchers/__init__.py` is empty. `RawItem` (`agent/models.py`) carries `source`, `engagement`.
- **Related changes:** 2 (multi-search) and 8 (LLM provider abstraction) are `done`; 10 (expand-article-sources) is `proposed`, `depends_on: [9]`, correctly waiting on this. ADR-0001 (injected `LLMClient` Protocol + `get_client` factory) is the idiom to mirror for the `SourceAdapter` Protocol + `build_adapters` factory.
- **Parity risk surfaced for the plan (not a scope change).** `tests/test_scheduler.py::test_run_sweep_filters_and_writes` mocks `agent.scheduler.HNFetcher.fetch` to return a below-threshold item (engagement=10) alongside an above-threshold one, and asserts only 1 is written — the drop is currently done by the *sweep-level* allowlist, not the fetcher. When engagement policy moves into the adapter (per spec) and the sweep-level allowlist is deleted, a raw-`.fetch()` mock bypasses the adapter's own filter, so this existing test must be updated to mock at the *adapter* seam (or assert the new behavior). The sweep tests also patch `agent.scheduler.{HNFetcher,ArxivFetcher,WebFetcher,MultiSearchFetcher}.fetch` by attribute — the refactor must keep those symbols importable from `agent.scheduler` (or the plan updates the patch targets, which the spec explicitly permits: "existing suite keeps passing with only construction-site updates").
- **Verification posture:** pure refactor — suite parity is the proof; no live-LLM check required (per run context + the `live-testing-catches-what-mocks-miss` finding, a live run proves provider swaps, not a same-sources refactor). If any live check were warranted, the Anthropic key has no credit (400); `OPENROUTER_API_KEY` in `.env` works (`llm.provider: openrouter`).
- **Follow-ups noted (auto-capture disabled — reported, not minted):** the evaluator's non-fail-soft trunk (`agent/evaluator.py` can hard-abort a sweep before downstream stages) remains a candidate follow-up from the `live-testing-catches-what-mocks-miss` finding — out of scope here. No new constraints to fold in; scope unchanged.
