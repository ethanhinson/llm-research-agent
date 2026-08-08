---
title: "r0b0tlab/qwen3.8-max-glm5.2-kimi-k3-distillation"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, fine-tuning, synthetic-data]
validated: false
sources_count: 1
content_source: full
status: new
---

# r0b0tlab/qwen3.8-max-glm5.2-kimi-k3-distillation

## Summary
This is a curated distillation dataset combining reasoning, instruction-following, and mathematical problem-solving tasks. The dataset draws from multiple open-source benchmarks (ARC, CommonsenseQA, MetaMathQA, SciQ, OrcaMath, Tulu-3) and uses Qwen 3.8-max-preview as the teacher model for supervised fine-tuning.

## How It Works
The dataset is structured as a table of training examples, each containing: a prompt with explicit reasoning format instructions (e.g., "<think>…</think>" wrappers), ground truth answers or completions, and metadata tags. Examples span task types including reasoning (ARC-Easy, CommonsenseQA), mathematics (MetaMathQA, OrcaMath), and general instruction-following (Tulu-3). Each row includes quality signals such as verifier pass status, format scores (ranging 6–10), and reference agreement flags to track data quality.

## Why It Matters
Practitioners should care because distillation datasets like this one enable efficient fine-tuning of smaller models by capturing teacher outputs across diverse, structured reasoning tasks. The presence of high format scores, verifier passes, and quality flags suggests the data has undergone vetting; this reduces noise in training signal and supports reproducible SFT workflows. The mix of reasoning and math tasks reflects a push toward instruction-aligned, reasoning-capable models without requiring massive proprietary datasets.

## Sources
- [r0b0tlab/qwen3.8-max-glm5.2-kimi-k3-distillation](https://huggingface.co/datasets/r0b0tlab/qwen3.8-max-glm5.2-kimi-k3-distillation) — hf-trending · 46

## Related
