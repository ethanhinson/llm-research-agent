---
id: 12
slug: semantic-scholar-adapter
title: Semantic Scholar keyword-search adapter
status: proposed
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: [10]
related: [9, 10, 13]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-07-semantic-scholar-adapter.md
plan:
results:
trivial: false
auto_groomable: false
branch:
pr:
blocked_by:
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-07-semantic-scholar-adapter.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-semantic-scholar-adapter.md) |
<!-- docket:artifacts:end -->

## Why

arXiv keyword search (0010) only covers arXiv. Semantic Scholar's Graph API adds cross-venue keyword search with abstracts, tldr summaries, and citation counts in one call — the best signal-per-line-of-code of the verified candidates, and its citation data later feeds citation-velocity ranking. Endpoint verified live 2026-08-07; free 1 RPS key available, unkeyed shared pool usable with backoff.

## What changes

One `SemanticScholarAdapter` (source `s2`) on the 0009 layer: config-driven queries (defaulting to `sources.arxiv_queries`), tldr-or-abstract bodies, citationCount as engagement, arXiv-URL preference for cross-source dedup, 429 backoff-then-fail-soft, optional `S2_API_KEY`. Config-gated, factory-registered, mocked tests + one live query at build time.

## Out of scope

- S2 Recommendations loop, SPECTER2 embeddings, OpenAlex (separate changes/stubs).

## Reconcile log
