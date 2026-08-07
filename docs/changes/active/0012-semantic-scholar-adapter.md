---
id: 12
slug: semantic-scholar-adapter
title: Semantic Scholar keyword-search adapter
status: in-progress
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: [10]
related: [9, 10, 13]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-07-semantic-scholar-adapter.md
plan: docs/superpowers/plans/2026-08-07-semantic-scholar-adapter.md
results:
trivial: false
auto_groomable: false
branch: feat/semantic-scholar-adapter
pr:
claimed_at: 2026-08-07T19:31:36Z
blocked_by:
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-07-semantic-scholar-adapter.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-semantic-scholar-adapter.md) |
| Plan | [2026-08-07-semantic-scholar-adapter.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/semantic-scholar-adapter/docs/superpowers/plans/2026-08-07-semantic-scholar-adapter.md) |
<!-- docket:artifacts:end -->

## Why

arXiv keyword search (0010) only covers arXiv. Semantic Scholar's Graph API adds cross-venue keyword search with abstracts, tldr summaries, and citation counts in one call — the best signal-per-line-of-code of the verified candidates, and its citation data later feeds citation-velocity ranking. Endpoint verified live 2026-08-07; free 1 RPS key available, unkeyed shared pool usable with backoff.

## What changes

One `SemanticScholarAdapter` (source `s2`) on the 0009 layer: config-driven queries (defaulting to `sources.arxiv_queries`), tldr-or-abstract bodies, citationCount as engagement, arXiv-URL preference for cross-source dedup, 429 backoff-then-fail-soft, optional `S2_API_KEY`. Config-gated, factory-registered, mocked tests + one live query at build time.

## Out of scope

- S2 Recommendations loop, SPECTER2 embeddings, OpenAlex (separate changes/stubs).

## Reconcile log

- 2026-08-07 — Reconciled against current `main`. Dependency 0010 (expand-article-sources) is merged/done (archived alongside 0009); the 0009 `SourceAdapter` protocol + `build_adapters` factory (`agent/fetchers/base.py`) and the 0010 templates (`agent/fetchers/hf_papers.py`, `github_trending.py`) are landed exactly as the spec assumes. Config already carries `sources.arxiv_queries` (used as the default query list) and no `sources.semantic_scholar` / `sources.s2_queries` block yet — this change adds both, config-gated. `RawItem` shape (title/body/url/source/engagement/timestamp) matches the spec's mapping. `.env.example` lists provider/search keys but no `S2_API_KEY` — to be added optionally. No scope drift: spec is buildable as written. Test baseline is 180 (learnings finding `pytest-shim-and-venv-provisioning`); suite runs via `uv run python -m pytest` after `uv sync --extra dev`. No follow-up work surfaced (auto-capture disabled regardless).
