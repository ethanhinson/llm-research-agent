---
title: "DeepSeek V4 Flash 0731"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, inference-efficiency, speculative-decoding]
validated: false
sources_count: 1
content_source: full
status: new
---

# DeepSeek V4 Flash 0731

## Summary
DeepSeek V4 Flash 0731 is a reasoning-enabled model released in July 2026 with three compute variants. At maximum effort, it achieves 89.0% on ARC-AGI-1 Semi-Private and 61.4% on ARC-AGI-2 Semi-Private, with cost-per-task pricing of $0.02 and $0.04 respectively.

## How It Works
The model operates across three reasoning variants—Max, High, and Low—that trade off computational cost against performance. Performance degrades predictably across variants: on ARC-AGI-1 the Max variant scores 89.0%, High scores 87.0%, and Low scores 84.0%. On the harder ARC-AGI-2 benchmark, the scores drop to 61.4%, 56.0%, and 46.0% respectively. Task-level results show the Max variant succeeds on the majority of ARC-AGI-1 public eval tasks (400 total), while both High and Low variants show reduced success rates, particularly on harder problems.

## Why It Matters
Practitioners benchmarking on ARC-AGI—a standard for abstract reasoning—should note that DeepSeek V4 Flash demonstrates strong performance on the easier benchmark (ARC-AGI-1) but faces a steeper performance cliff on harder variants. The tiered variant structure lets users trade reasoning cost against accuracy, making it relevant for applications where computational budget must be balanced against solution quality on novel pattern-recognition tasks.

## Sources
- [DeepSeek V4 Flash 0731](https://arcprize.org/results/deepseek-v4-flash-0731) — hackernews · 348

## Related
