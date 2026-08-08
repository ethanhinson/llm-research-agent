---
title: "GizClaw/flowcraft"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, agent-frameworks, memory, long-context]
validated: false
sources_count: 1
content_source: full
status: new
---

# GizClaw/flowcraft

## Summary
FlowCraft is a modular Go toolkit for building AI applications with pluggable memory, multi-provider inference, and agent execution primitives. It decouples application code from specific model providers and enforces execution contracts through layered, independently versioned modules.

## How It Works
The architecture separates concerns into three main layers: sdk/ defines core contracts (agent execution, graphs, tools, messages, inference, memory); memory/ implements long-term memory with three-lane retrieval (BM25 + vector + entity fused via Reciprocal Rank Fusion), component pipelines, and lifecycle management; sdkx/ provides provider adapters (Anthropic, OpenAI, DeepSeek, etc.) and generic assembly for deploy, runtime, and tool configuration. Applications can use sdk directly or adopt memory and sdkx layers only when needed. The runnable examples/forge demo includes interactive TUI, scenario configs, scripted tests, and simulation tools.

## Why It Matters
Practitioners building multi-agent or long-memory AI systems benefit from FlowCraft's plugin architecture—swapping inference providers or memory implementations does not require application code changes. The checkpoint/resume contracts, structured event bus, and independent module versioning reduce lock-in and allow incremental adoption. The fusion-based retrieval strategy and deterministic memory projection pipeline address real production concerns around context quality and reproducibility in agent workflows.

## Sources
- [GizClaw/flowcraft](https://github.com/GizClaw/flowcraft) — github · 484

## Related
