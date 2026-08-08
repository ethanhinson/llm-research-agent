---
title: "GST-Bench: Can VLMs Develop Global Spatial Awareness from Video?"
date: 2026-08-07
type: benchmark
score: 6
score_label: authority
tags: [benchmark, multimodal, vision, evaluation]
validated: false
sources_count: 1
content_source: full
status: new
---

# GST-Bench: Can VLMs Develop Global Spatial Awareness from Video?

## Summary
GST-Bench is a video VQA benchmark designed to measure global spatial awareness in vision-language models. It exposes a large performance gap between state-of-the-art VLMs (42.68% best zero-shot) and humans (79.08%), driven by models' inability to consolidate long-horizon observations into globally consistent scene representations.

## How It Works
The benchmark comprises 6,790 minutes of synthetically generated video with human-verified questions. It requires models to perform spatial inference from novel viewpoints not seen in the input video and to map egocentric observations onto global top-down images. A companion analysis (GST-Bench-Local) isolates whether failures stem from local or global spatial reasoning by testing the same task formulation on localized contexts.

## Why It Matters
Existing spatial benchmarks focus on local perception from limited viewpoints, but embodied agents require global spatial awareness over extended visual streams. This benchmark identifies a concrete failure mode—consolidating long-horizon observations into consistent 3D scene models—that distinguishes current VLM limitations from human capability, suggesting a priority area for improving video understanding in embodied AI applications.

## Sources
- [GST-Bench: Can VLMs Develop Global Spatial Awareness from Video?](https://huggingface.co/papers/2608.05747) — hf-papers · 30

## Related
