---
id: 20
slug: tiered-model-eval-cascade
title: Tiered model cascade for evaluation (cheap first-pass, escalate borderline)
status: proposed
priority: low
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: []
related: [8, 17]
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

Every evaluator/synthesizer call runs at a single model tier. With ~10 sources feeding the funnel, most items are obvious keeps or obvious noise a cheap model handles fine; only borderline items need a strong model. The KB makes the cost case directly — *Beyond Benchmarks: The Economics of AI Inference*, plus a wave of routing releases (*Warp's Agent CLI smart routers that auto-switch models per task*, *Google Cloud API Gateway serverless multi-model routing*, *Databricks Unity AI Gateway*). The agent already has multi-provider support via OpenRouter (0008), so per-call model selection is a small step that cuts spend.

## What changes

(Needs brainstorm — design open.) Roughly: run classify + first-pass score on a cheap model; escalate only borderline items (e.g. score 5–7, or low-confidence from 0017) to a strong model for a re-score and for synthesis. Config-gated cheap/strong model pair, defaulting to single-tier when unset.

## Out of scope

- A learned/dynamic router (the KB's smart-router direction) — this is a static band-based cascade.
- Provider abstraction changes (0008 already provides the seam).

## Open questions

- Escalation trigger: fixed score band vs 0017's confidence signal (natural pairing — hence related).
- Which stages escalate (score only, or synthesis too) and the cheap/strong model defaults per provider.
- Config shape: extend `llm:` with `cheap_model` / `strong_model`, or a dedicated `eval.cascade` block.
- Measure actual $ / quality delta before defaulting it on.

## Reconcile log
