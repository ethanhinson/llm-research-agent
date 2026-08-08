---
title: "Qyrou/reasoning-corpus-4K-5M-v1"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, chain-of-thought, reasoning]
validated: false
sources_count: 1
content_source: full
status: new
---

# Qyrou/reasoning-corpus-4K-5M-v1

## Summary
Qyrou/reasoning-corpus-4K-5M-v1 is a dataset of reasoning traces paired with LLM outputs, containing diverse problem-solving scenarios (VB.NET programming, public health campaigns, mathematics education, DevOps, logic puzzles) with token lengths ranging from ~1K to 5K. The dataset captures intermediate reasoning steps alongside assistant responses in ChatML format.

## How It Works
The dataset is structured as a table with columns for repo_id, token length, user prompt, thought_trace (reasoning steps), assistant response, and ChatML-formatted conversation. Each row represents a single task instance where the thought_trace column captures the model's intermediate reasoning before generating the final assistant response. Examples span technical, educational, and scenario-based domains.

## Why It Matters
Practitioners working on reasoning-focused LLM training or evaluation can use this corpus to study how models decompose problems and generate step-by-step solutions across diverse domains. The explicit pairing of reasoning traces with outputs provides direct supervision signal for training verifiable reasoning capabilities, and the scale (up to 5M tokens) supports both fine-tuning and analysis of reasoning patterns at meaningful volume.

## Sources
- [Qyrou/reasoning-corpus-4K-5M-v1](https://huggingface.co/datasets/Qyrou/reasoning-corpus-4K-5M-v1) — hf-trending · 191

## Related
