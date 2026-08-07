---
id: 16
slug: hf-trending-artifacts
title: Hugging Face trending models/datasets adapter
status: in-progress
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: [10]
related: [10]
discovered_from: []
adrs: []
spec:
plan:
results:
trivial: true
auto_groomable: false
branch: feat/hf-trending-artifacts
pr:
blocked_by:
claimed_at: 2026-08-07T20:26:17Z
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
<!-- docket:artifacts:end -->

## Why

New open-model and dataset releases often never appear as papers — 0010's daily-papers adapter misses them. HF's hub API surfaces trending artifacts with no auth: `https://huggingface.co/api/models?sort=trendingScore&limit=N` (verified live 2026-08-07; note `sort=trending` returns 400 — the param must be `trendingScore`; same shape for `/api/datasets`).

## What changes

A small `HFTrendingAdapter` (source `hf-trending`) on the 0009 layer, following the established adapter pattern (0010's HFPapersAdapter is the template): fetch top-N trending models + datasets, map id/description/downloads+likes → RawItem (likes as engagement), config-gated under `sources.hf_trending: {enabled, limit, min_likes}`, fail-soft, factory-registered, mocked tests. Trivial: the pattern, config shape, and endpoint are all established — no open design questions.

## Out of scope

- HF Spaces; paper linkage (dedup already collapses model-card→paper overlap by URL only).

## Reconcile log
