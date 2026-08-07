---
id: 9
slug: source-adapter-layer
title: Unify article intake behind a SourceAdapter layer
status: in-progress
priority: medium
type: refactor
created: 2026-08-07
updated: 2026-08-07
depends_on: []
related: [2, 8, 10]
discovered_from: []
adrs: [1]
spec: docs/superpowers/specs/2026-08-07-source-adapter-layer.md
plan:
results:
trivial: false
auto_groomable: false
branch: feat/source-adapter-layer
claimed_at: 2026-08-07T06:24:49Z
pr:
blocked_by:
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-07-source-adapter-layer.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-source-adapter-layer.md) |
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
