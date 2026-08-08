---
title: "AgentOPSD: Recursive Self-Distillation for Agentic Reinforcement Learning"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: agentic
tags: [research, agentic, agent-frameworks, rlhf, self-distillation]
validated: false
sources_count: 1
content_source: full
status: new
---

# AgentOPSD: Recursive Self-Distillation for Agentic Reinforcement Learning

## Summary
AgentOPSD is a critic-free method for turn-level credit assignment in agentic reinforcement learning that converts sparse outcome rewards into dense turn-level signals. It aggregates token-level log-probability gaps into turn-level evidence and recursively updates a Bayesian belief state to identify pivotal decisions in long-horizon tasks.

## How It Works
The method operates without a separate critic or additional rollouts. It aggregates token-level teacher-student log-probability gaps into turn-level evidence, then recursively updates a Bayesian belief state in log-odds space. This process yields a reweighting scheme that identifies pivotal turns through marginal belief revision between consecutive states, enabling principled conversion of sparse outcome supervision into dense turn-level credit signals.

## Why It Matters
Practitioners working on multi-turn agentic tasks face the fundamental problem that standard RL with trajectory-level rewards fails to credit the few decisions that actually determine success. AgentOPSD addresses this by providing turn-level credit signals compatible with standard policy optimization, demonstrating improvements over GRPO and self-distillation baselines on benchmarks like ALFWorld, WebShop, and Search-QA, reaching 89.1% success on ALFWorld with Qwen2.5-7B.

## Sources
- [AgentOPSD: Recursive Self-Distillation for Agentic Reinforcement Learning](https://huggingface.co/papers/2608.05987) — hf-papers · 66

## Related
