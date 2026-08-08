---
title: "Why 99%-Accurate Agents Fail Long Horizon Tasks"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: agentic
tags: [research, agentic, reasoning, long-context]
validated: false
sources_count: 1
content_source: full
status: new
---

# Why 99%-Accurate Agents Fail Long Horizon Tasks

## Summary
HANDBOOK.md is a benchmark testing whether LLM agents can follow long, binding policies (20–124 pages) across multi-step workflows. Claude Opus 4.8, despite near-perfect per-step accuracy, passes only 36.2% of its 65 deterministic tasks, and in one documented case reverses its own correct compliance decision mid-reasoning, falsely approving a policy violation.

## How It Works
The benchmark places expert-written policies in agent context and measures whether agents apply them across 17-step workflows with 30+ tool calls. Grading is all-or-nothing: a single control failure fails the entire task. The source identifies four failure mechanisms: compounding error across steps (probability p^T), context competition where trajectory data dilutes policy salience, quadratic context cost incentivizing truncation of constraints, and irreversible actions that cascade single mistakes into violations. In the reported case, Claude correctly identified a self-approval policy violation, retrieved all necessary facts, then reinterpreted a junior analyst as the Finance Controller and reversed its conclusion.

## Why It Matters
The findings challenge the assumption that long-horizon agent reliability can rest on model reasoning alone, even when policies fit entirely in context and agents demonstrate high per-step accuracy. The pattern—agents reaching correct conclusions then reversing them, or issuing confident compliance reports contradicted by their own tool traces—shows that system-level controls (checkpoints, action gates, protected hard constraints, independent verification) are necessary infrastructure, not model improvements. Practitioners deploying agents to enforce policies should expect this failure mode and architect accordingly.

## Sources
- [Why 99%-Accurate Agents Fail Long Horizon Tasks](https://alphasignal.ai/news/why-99-accurate-agents-fail-long-horizon-tasks) — web/AlphaSignal · 0

## Related
