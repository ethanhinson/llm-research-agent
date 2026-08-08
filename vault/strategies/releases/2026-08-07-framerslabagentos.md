---
title: "framerslab/agentos"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, agent-frameworks, memory, multi-agent]
validated: false
sources_count: 1
content_source: full
status: new
---

# framerslab/agentos

## Summary
AgentOS is an open-source TypeScript framework for persistent AI agents that remember context across sessions, dynamically forge their own tools at runtime, and coordinate across multiple LLM providers. It achieves industry-leading benchmarks on long-context memory tasks—85.6% on LongMemEval-S and 70.2% on LongMemEval-M—with reproducible methodology and full cost transparency.

## How It Works
Sessions maintain lossless conversation transcripts (bounded by ~120K tokens by default) and compose three layers: persistent cognitive memory (8 neuroscience-backed mechanisms including Ebbinghaus decay and reconsolidation), a dynamic tool surface (agents write and sandbox-execute TypeScript functions with Zod schemas, approved by an LLM judge, then reuse them cheaply), and optional HEXACO personality traits that bias retrieval and routing decisions. Multi-agent orchestration supports six strategies (sequential, parallel, debate, review-loop, hierarchical, graph). Zero-config prompt caching spans 11 LLM providers (OpenAI, Anthropic, Gemini, Groq, Ollama, OpenRouter, Together, Mistral, xAI, and two local CLIs).

## Why It Matters
Practitioners building long-running AI systems need agents that retain context without explosive token growth and can adapt their capabilities without redeployment—AgentOS addresses both through reproducibly validated memory benchmarks and runtime tool forging. The published LongMemEval numbers (with bootstrap confidence intervals and judge-FPR probes) and unified orchestration across 11 providers reduce friction when deploying multi-agent workflows at scale. The framework's measurable personality and guardrail tiers (5 security levels, 6 packs) make it viable for production use where consistency and auditability matter.

## Sources
- [framerslab/agentos](https://github.com/framerslab/agentos) — github · 613

## Related
