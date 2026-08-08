---
title: "datacurve/deep-swe"
date: 2026-08-07
type: benchmark
score: 8
score_label: authority
tags: [benchmark, code-generation, agent-frameworks]
validated: false
sources_count: 1
content_source: full
status: new
---

# datacurve/deep-swe

## Summary
DeepSWE is a gated benchmark of 113 original software engineering tasks across five programming languages, designed to evaluate frontier coding agents on long-horizon problems from active open-source repositories. Tasks include isolated execution environments and program-based verifiers that accept any solution with correct observable behavior.

## How It Works
Each task follows the Harbor format with metadata (repository, commit, language, resource limits), a natural-language instruction prompt, a Dockerfile-based environment, and a test verifier that exercises task requirements via a shell entry point and optional test patches. Tasks run in sandboxed environments through Pier, a Harbor-compatible framework that adds per-agent network allowlists, trajectory logging, and critique tools. Agents can be evaluated against multiple models (Claude, GPT, Gemini, etc.) either locally or in parallel on Modal infrastructure.

## Why It Matters
Practitioners building or evaluating coding agents need held-out benchmarks that measure real-world software engineering capability without contamination. DeepSWE's gated access and focus on behavior-based correctness (rather than code structure) make it a principled evaluation ground for measuring frontier agent progress. The framework supports multiple agent implementations and models, enabling reproducible comparisons across the coding-agent landscape.

## Sources
- [datacurve/deep-swe](https://huggingface.co/datasets/datacurve/deep-swe) — hf-trending · 53

## Related
