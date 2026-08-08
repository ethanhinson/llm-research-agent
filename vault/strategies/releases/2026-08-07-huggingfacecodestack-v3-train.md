---
title: "HuggingFaceCode/stack-v3-train"
date: 2026-08-07
type: release
score: 8
score_label: significance
tags: [release, code-generation]
validated: false
sources_count: 1
content_source: full
status: new
---

# HuggingFaceCode/stack-v3-train

## Summary
The Stack v3 is the largest open-source code dataset for training code LLMs, containing 15.9 TB of deduplicated source code across 713 programming languages from 173M repositories (~4.9 trillion tokens). It captures GitHub's state as of August 2025, representing a substantial increase over The Stack v2 released in 2023.

## How It Works
The Stack v3 is released as two complementary datasets. `stack-v3-train` is a near-deduplicated, heuristically filtered corpus grouped by repository with file contents embedded inline—ready for direct training use. `stack-v3-full` retains the complete unfiltered corpus with deduplication cluster IDs and metadata for all files, enabling custom filtering and research. Users can download via Hugging Face's `datasets` library with support for both local and streaming modes.

## Why It Matters
Practitioners building code LLMs can now train on substantially more recent and larger code corpora with full repository context preserved in a single self-contained download. The inclusion of inline file contents eliminates preprocessing overhead, and the dual-dataset design allows both production-ready training (via `stack-v3-train`) and research-grade flexibility (via `stack-v3-full`), making open and reproducible code model development more accessible.

## Sources
- [HuggingFaceCode/stack-v3-train](https://huggingface.co/datasets/HuggingFaceCode/stack-v3-train) — hf-trending · 316

## Related
