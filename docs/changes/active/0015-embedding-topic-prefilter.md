---
id: 15
slug: embedding-topic-prefilter
title: Embedding-based topic pre-filter (replace/augment regex filter)
status: proposed
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: []
related: [12]
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

`agent/topic_filter.py` is a regex allowlist — it misses relevant items phrased outside its vocabulary ("state-space models" when the regex knows "transformer") and its recall ceiling caps every source added upstream. An embedding similarity filter against a centroid/k-NN index built from notes already kept in the vault would raise recall and cut LLM-eval spend on obvious noise. S2 returns SPECTER2 embeddings free for papers; non-paper items need a local sentence-transformer (a new dependency — the main design decision).

## What changes

(Needs brainstorm — design open.) Roughly: build an embedding index from kept vault notes; score incoming items by cosine similarity; threshold as a pre-eval filter, regex kept as a cheap first pass or retired.

## Out of scope

## Open questions

- New dependency policy (sentence-transformers is heavy; ONNX or API-based embedding alternatives?).
- Threshold calibration and cold-start; how often the centroid/index refreshes.
- Replace the regex filter or layer behind it?

## Reconcile log
