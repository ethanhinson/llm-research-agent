---
title: "What Current AI Benchmarks Leave Unmeasured: Modality, Search, Citations, and Implications (for Safety Evaluations)"
date: 2026-08-07
type: benchmark
score: 8
score_label: authority
tags: [benchmark, evaluation, benchmarking, safety-alignment]
validated: false
sources_count: 1
content_source: full
status: new
---

# What Current AI Benchmarks Leave Unmeasured: Modality, Search, Citations, and Implications (for Safety Evaluations)

## Summary
This benchmark audit reveals that standard LLM safety evaluations systematically undercount behavioral variation by relying on single modalities, single runs per prompt, and accuracy-only metrics. Testing ChatGPT across chat UI and API with and without web search shows that modality, search enablement, and repeated sampling each produce significant performance shifts and inconsistencies relevant to safety claims.

## How It Works
The authors evaluated 401 prompts from BBQ and SafetyBench across ChatGPT's chat UI and OpenAI's API, with and without web search, collecting 4,812 responses across three repeated runs per prompt. Beyond accuracy, they measured response consistency, text similarity, citation grounding, and abstention behavior. Key findings: chat UI was less accurate than API (both without search); enabling search reduced accuracy by up to 8 percentage points and reversed modality performance trends on one benchmark; up to 21% of prompts showed inconsistent responses across repeated runs; and citation grounding and abstention patterns differed between modalities.

## Why It Matters
Practitioners and evaluators using benchmarks to justify safety and deployment readiness claims should recognize that single-modality, single-run, accuracy-focused evaluations can hide substantial variation in model behavior across deployment conditions. This work demonstrates that search integration, interface choice, and response consistency—factors present in real-world deployment—materially shift outcomes in ways standard metrics do not capture, making the audit findings directly applicable to more robust safety assessment design.

## Sources
- [What Current AI Benchmarks Leave Unmeasured: Modality, Search, Citations, and Implications (for Safety Evaluations)](http://arxiv.org/abs/2608.06202v1) — arxiv · 0

## Related
