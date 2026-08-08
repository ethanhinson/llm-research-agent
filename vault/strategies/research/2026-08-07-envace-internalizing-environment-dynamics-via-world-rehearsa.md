---
title: "EnvACE: Internalizing Environment Dynamics via World Rehearsal for Agentic Reinforcement Learning"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: agentic
tags: [research, agentic, agent-frameworks, rlhf]
validated: true
sources_count: 2
content_source: full
status: new
---

# EnvACE: Internalizing Environment Dynamics via World Rehearsal for Agentic Reinforcement Learning

## Summary
EnvACE is an agentic reinforcement learning method that trains LLM agents without relying on external environments during training. Instead, the policy learns to both act (generate tool calls) and simulate environment responses (play the role of the environment), internalizing environment dynamics as a world model within its parameters.

## How It Works
The policy alternates between two roles: (1) generating a tool call as the agent, and (2) producing the resulting environment response by simulating the environment. Both roles are jointly optimized end-to-end using task-success rewards. This rehearsal process allows the policy to internalize the relationship between actions and their consequences. At test time, the internalized world model can perform private rehearsal before committed execution without additional external interaction.

## Why It Matters
Training LLM agents typically requires costly construction and verification of external environments or difficult-to-ground simulators. EnvACE removes this bottleneck by eliminating the need for external environment interaction during training. The method demonstrates strong and transferable performance across multiple benchmarks (BFCL-v4, tau^2-Bench, VitaBench, FinMCP-Bench), outperforming environment-scaling baselines and showing consistent improvements across model scales, making it a practical path toward scaling agent training beyond environmental constraints.

## Sources
- [EnvACE: Internalizing Environment Dynamics via World Rehearsal for Agentic Reinforcement Learning](https://huggingface.co/papers/2608.06197) — hf-papers · 28

## Related
