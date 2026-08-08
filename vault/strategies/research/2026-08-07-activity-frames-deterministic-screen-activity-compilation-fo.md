---
title: "Activity Frames: Deterministic Screen-Activity Compilation for Agent Memory and Replay"
date: 2026-08-07
type: research
score: 7
score_label: novelty
category: agentic
tags: [research, agentic, agent-frameworks, memory]
validated: false
sources_count: 1
content_source: full
status: new
---

# Activity Frames: Deterministic Screen-Activity Compilation for Agent Memory and Replay

## Summary
Activity Frames is a deterministic, model-free compiler that converts passively captured screen activity into structured agent memory without requiring model inference. On a single professional's 128,756-frame corpus, it compresses a day of raw capture 86x into a prompt-ready context block and enables agents to answer questions about the day at 98.4% accuracy, substantially outperforming LLM summaries of the same data.

## How It Works
The pipeline segments locally captured screen activity into typed activity frames—bounded episodes containing application, site, timing, input volume, and evidence pointers to raw data. Because no model participates in compilation, the output is byte-identical, cacheable, and auditable. Recurring routines can be replayed deterministically with the model fully out of the loop (zero model tokens on a cache hit). The compiler also measures two previously unmeasured agent-cost parameters from passive human activity: Routine Overhead Ratio R (60–343x, modeled upper bound) and delegable recurrence (~8% in-sample, ~7.7% out-of-sample).

## Why It Matters
Agents currently waste frontier inference re-deriving tasks users have already performed because agent memory records only what users said, not what they did. This work demonstrates that a simple, deterministic compilation pipeline can produce memory far more faithful and efficient than model-generated summaries, while also providing empirical grounding for agent cost models that previously lacked real measurements of routine overhead and recurrence. The open-source release and local-first design lower the barrier for practitioners to incorporate screen memory into agent systems.

## Sources
- [Activity Frames: Deterministic Screen-Activity Compilation for Agent Memory and Replay](https://huggingface.co/papers/2608.05784) — hf-papers · 8

## Related
