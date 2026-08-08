---
id: 14
slug: cross-source-corroboration-ranking
title: Cross-source corroboration + citation-velocity signals
status: in-progress
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-08
depends_on: []
related: [10, 12]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-07-cross-source-corroboration-ranking-design.md
plan:
results:
trivial: false
auto_groomable: false
branch: feat/cross-source-corroboration-ranking
pr:
blocked_by:
claimed_at: 2026-08-08T03:45:02Z
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-07-cross-source-corroboration-ranking-design.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-cross-source-corroboration-ranking-design.md) |
<!-- docket:artifacts:end -->

## Why

With ~10 sources feeding the funnel, the strongest cheap quality signal is *independent corroboration*: the same paper/link surfacing on 2+ sources within ~72h. The blocker is that items have **no canonical identity** — and reading the pipeline (`fetch → dedup → topic → cross_validate → eval → write`) shows that single gap causes three defects: identical-title items in one sweep silently overwrite each other's note file; near-title items produce duplicate notes; and cross-sweep re-surfaces are dropped by the persisted index, so corroboration-over-days never registers. `cross_validate` does compute `sources_count`, but it is inert metadata the evaluator never sees. Relatedly, citation velocity (weekly Δ of citationCount) can resurface sleeper hits the first-pass eval scored low.

## What changes

Introduce a canonical item identity (`arXiv-ID > DOI > normalized-URL > normalized-title`) and make it the dedup + corroboration key. Group by identity to collapse intra-sweep duplicates to one note and count distinct sources (`sources_count`/`validated`); persist `{canonical_id: {sources, first_seen, note_path}}` so a re-surface within a 72h window updates the existing note instead of being dropped; feed `sources_count` into the evaluator's score/validate prompts as a soft signal and surface it in the vault. Bundled: a weekly (deep-sweep) Semantic Scholar citation-velocity re-poll that records `citation_count`/Δ and re-ranks rising papers in the index (no LLM re-score). All config-gated and fail-soft. Design + staging in the linked spec.

## Out of scope

- OpenAlex citation backend (S2 chosen); LLM re-score of risen papers (re-rank only).
- Spend-gating / auto-keep on corroboration (grooming chose eval-signal, not a gate).
- Backfilling canonical_id / citation_count onto existing vault notes; embedding-based semantic dedup (that is change 0015).

## Open questions

_Resolved during grooming (scope, corroboration effect, cross-sweep inclusion, citation-velocity backend) — see the linked spec._

## Reconcile log
