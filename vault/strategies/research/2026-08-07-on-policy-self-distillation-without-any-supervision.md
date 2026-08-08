---
title: "On-Policy Self-Distillation without Any Supervision"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: prompting
tags: [research, prompting, fine-tuning, self-distillation]
validated: false
sources_count: 1
content_source: full
status: new
---

# On-Policy Self-Distillation without Any Supervision

## Summary
Unsupervised On-Policy Self-Distillation (U-OPSD) achieves on-policy self-distillation for LLMs without external supervision by leveraging only the model's own generations. The method uses internal consistency via majority voting to create pseudo-solutions, then distills a teacher distribution into the model's incorrect completions to enable self-correction.

## How It Works
U-OPSD samples multiple rollouts from the model and constructs a pseudo-solution through majority voting under a self-consistency threshold. It then conditions a teacher distribution on the shortest pseudo-solution and distills this into prefixes of the model's longest incorrect completion. This allows the model to learn corrections at points where it is confidently wrong, without requiring ground-truth labels or external feedback.

## Why It Matters
U-OPSD removes the dependency on external supervision (ground-truth signals, environmental feedback, or larger models) that limits existing on-policy distillation methods. Across multiple mathematical reasoning benchmarks, it consistently improves base models and matches or exceeds supervised baselines like OPSD and GRPO, demonstrating that genuine self-distillation without any external guidance is viable and effective for post-training.

## Sources
- [On-Policy Self-Distillation without Any Supervision](http://arxiv.org/abs/2608.06296v1) — arxiv · 0

## Related
