---
id: 14
slug: cross-source-corroboration-ranking
title: Cross-source corroboration + citation-velocity signals
status: proposed
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: []
related: [10, 12]
discovered_from: []
adrs: []
spec:
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
<!-- docket:artifacts:end -->

## Why

With ~10 sources feeding the funnel, the strongest cheap quality signal becomes *independent corroboration*: the same paper/link surfacing on 2+ sources within ~72h. Today dedup throws that information away (first URL wins, duplicates are dropped silently). Relatedly, citation velocity (weekly delta of citationCount via S2/OpenAlex) can surface sleeper hits the first-pass eval scored low. Both are ranking/gating signals that could also cut LLM-eval spend by prioritizing corroborated items.

## What changes

(Needs brainstorm — design open.) Roughly: canonicalize items to arXiv ID / DOI / normalized URL at dedup; count independent surfaces instead of dropping duplicates; feed the count to the evaluator or use it to gate/boost; optionally a weekly citation-velocity re-poll job over recent vault papers.

## Out of scope

## Open questions

- Where does corroboration act — pre-eval gate, eval prompt input, or score boost?
- Canonicalization rules (arXiv ID vs DOI vs URL-normalization precedence); storage in the dedup index.
- Citation-velocity: same change or split; which backend (S2 vs OpenAlex key decision); re-score or just re-rank?

## Reconcile log
