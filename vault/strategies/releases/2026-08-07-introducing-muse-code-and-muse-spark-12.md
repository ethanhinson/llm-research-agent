---
title: "Introducing Muse Code and Muse Spark 1.2"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, code-generation]
validated: false
sources_count: 1
content_source: full
status: new
---

# Introducing Muse Code and Muse Spark 1.2

## Summary
Meta released Muse Spark 1.2, a coding-focused update to Muse Spark 1.1, co-trained with Muse Code to improve code generation, debugging, codebase understanding, and developer workflows. The model was extensively trained on long-horizon coding tasks including whole-repository generation and large end-to-end projects.

## How It Works
Training compute on coding tasks was significantly scaled up with expanded training environment diversity. Muse Spark 1.2 was co-trained with Muse Code using rejection sampled harness trajectories, recipe optimizations for goals and subagents, and integration of the Muse Code toolset for harness compatibility. The model received extensive training on long-horizon tasks like whole-repository generation, large projects, and auto-research.

## Why It Matters
The release reflects the industry trend that long-sequence agentic tool calling has become the most important model characteristic. For practitioners, the dual pricing model—standard pricing at $1.25/$4.25 per million tokens versus a steep discount at $0.10/$0.20 for data-sharing contributors—creates a cost-sensitive decision point for production deployments, particularly for cost-conscious teams willing to share usage data.

## Sources
- [Introducing Muse Code and Muse Spark 1.2](https://simonwillison.net/2026/Aug/5/muse-code-and-muse-spark-12/#atom-everything) — web/Simon Willison's blog · 0

## Related
