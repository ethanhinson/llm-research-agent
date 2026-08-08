---
title: "Anthropic/hh-rlhf"
date: 2026-08-07
type: release
score: 8
score_label: significance
tags: [release, rlhf, safety-alignment]
validated: false
sources_count: 1
content_source: full
status: new
---

# Anthropic/hh-rlhf

## Summary
The hh-rlhf dataset is Anthropic's public release of human feedback data used to train helpful, harmless, and honest AI assistants. It contains pairs of chosen and rejected assistant responses to the same human prompts, spanning benign queries through sensitive and harmful requests.

## How It Works
Each example pairs a "chosen" response (preferred by human raters) with a "rejected" response to identical prompts. The dataset covers a broad range of scenarios: straightforward questions (workout routines, dinosaur sounds), requests for harmful information (theft, violence, privacy violations), offensive content (slurs, racist stereotypes), and other edge cases. The chosen responses typically refuse harmful requests or provide safe alternatives, while rejected responses often comply with harmful requests or provide problematic advice.

## Why It Matters
This dataset codifies the human preferences that RLHF training uses to steer models toward safer, more helpful behavior. By publicly releasing this data, Anthropic enables reproducibility of alignment research and provides practitioners with concrete examples of desired vs. undesired model behavior across harmful request categories, making it a foundational resource for understanding how to train models to refuse dangerous requests while remaining useful.

## Sources
- [Anthropic/hh-rlhf](https://huggingface.co/datasets/Anthropic/hh-rlhf) — hf-trending · 1918

## Related
