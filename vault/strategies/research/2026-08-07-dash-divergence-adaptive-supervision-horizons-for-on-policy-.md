---
title: "DASH: Divergence-Adaptive Supervision Horizons for On-Policy Self-Distillation of Reasoning Models"
date: 2026-08-07
type: research
score: 7
score_label: novelty
category: prompting
tags: [research, prompting, rlhf, reasoning, chain-of-thought]
validated: false
sources_count: 1
content_source: full
status: new
---

# DASH: Divergence-Adaptive Supervision Horizons for On-Policy Self-Distillation of Reasoning Models

## Summary
DASH (Divergence-Adaptive Supervision Horizons) improves on-policy self-distillation for reasoning models by adapting token-level supervision weights based on how divergences evolve during generation. It uses adaptive gates to control backward aggregation of distillation signals, moving beyond the uniform weighting used in standard OPSD.

## How It Works
DASH computes the gap between each local distillation signal and the sequence-level mean divergence, maps this gap to an adaptive propagation gate, and uses these gates to control multi-step backward aggregation. This allows supervision weights to reflect the temporal structure and discrepancy history of the rollout rather than treating all local divergences uniformly. The method reuses teacher and student distributions already computed by OPSD, requiring no additional forward passes.

## Why It Matters
Standard OPSD assigns identical coefficients to all token-level divergences regardless of context, missing the temporal patterns in how student–teacher mismatch evolves. DASH's adaptive weighting aligns supervision intensity with realized divergence sequences, yielding consistent improvements across three mathematical reasoning benchmarks at three model scales without extra computational cost.

## Sources
- [DASH: Divergence-Adaptive Supervision Horizons for On-Policy Self-Distillation of Reasoning Models](http://arxiv.org/abs/2608.06243v1) — arxiv · 0

## Related
