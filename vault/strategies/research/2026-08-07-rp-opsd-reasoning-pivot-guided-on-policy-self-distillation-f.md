---
title: "RP-OPSD: Reasoning-Pivot-Guided On-Policy Self-Distillation for Multilingual Reasoning Transfer"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: prompting
tags: [research, prompting, chain-of-thought, reasoning, multilingual]
validated: true
sources_count: 2
content_source: full
status: new
---

# RP-OPSD: Reasoning-Pivot-Guided On-Policy Self-Distillation for Multilingual Reasoning Transfer

## Summary
RP-OPSD is a method for improving multilingual reasoning in LLMs through on-policy self-distillation guided by reasoning pivots—key decision points that advance the reasoning process. It uses distributional shifts between teacher views with and without English reference solutions to concentrate supervision on pivots most critical for cross-lingual transfer.

## How It Works
The method identifies reasoning pivots as tokens representing decisions that steer the reasoning trajectory, distinct from surface text generation. It applies privileged distillation by comparing matched teacher outputs with and without an English reference solution, using the distributional divergence as a signal to weight supervision more heavily on reasoning-control and problem-conditioned state-update tokens while downweighting surface realization tokens. Experiments span 17 languages and multiple difficulty levels on mathematical reasoning benchmarks.

## Why It Matters
Practitioners working on multilingual LLMs need methods that transfer reasoning capabilities to low-resource languages efficiently. RP-OPSD outperforms existing OPSD variants and multilingual baselines by focusing learning signal where it matters most—on the reasoning structure itself rather than uniform token-level supervision—making it a more targeted approach to the core challenge of cross-lingual reasoning generalization.

## Sources
- [RP-OPSD: Reasoning-Pivot-Guided On-Policy Self-Distillation for Multilingual Reasoning Transfer](http://arxiv.org/abs/2608.06347v1) — arxiv · 0

## Related
