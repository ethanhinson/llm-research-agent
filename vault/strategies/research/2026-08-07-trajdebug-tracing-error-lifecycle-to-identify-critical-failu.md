---
title: "TRAJDEBUG: Tracing Error Lifecycle to Identify Critical Failures in Long-Horizon Agent Trajectories"
date: 2026-08-07
type: research
score: 7
score_label: novelty
category: agentic
tags: [research, agentic, agent-frameworks, debugging, long-context]
validated: true
sources_count: 2
content_source: full
status: new
---

# TRAJDEBUG: Tracing Error Lifecycle to Identify Critical Failures in Long-Horizon Agent Trajectories

## Summary
TrajDebug is a framework for identifying critical errors in failed LLM agent trajectories by tracing error lifecycles and determining which early mistakes actually caused final failure. The work addresses the dual challenge of pinpointing errors across long sequences and distinguishing between local errors that have downstream impact versus those that do not.

## How It Works
TrajDebug uses multi-granularity history compression to manage long trajectories and applies evidence-based error identification to locate mistakes. It traces each error's resolution status and terminal impact to attribute which errors are truly responsible for the final failure. The authors created TrajErrBench, a benchmark of 486 manually annotated failed trajectories from tool-use and coding scenarios, to evaluate the approach against baselines.

## Why It Matters
LLM agents currently suffer from cascading errors and poor debuggability in complex long-horizon tasks. TrajDebug addresses a practical bottleneck by enabling practitioners to diagnose agent failures systematically and extract actionable feedback for improving agent success rates, rather than treating failed trajectories as opaque failures.

## Sources
- [TRAJDEBUG: Tracing Error Lifecycle to Identify Critical Failures in Long-Horizon Agent Trajectories](http://arxiv.org/abs/2608.06346v1) — arxiv/search · 0

## Related
