---
title: "mezmo/aura"
date: 2026-08-07
type: release
score: 8
score_label: significance
tags: [release, agent-frameworks, safety-alignment, observability]
validated: false
sources_count: 1
content_source: full
status: new
---

# mezmo/aura

## Summary
AURA is a production-ready SRE agent platform that deploys in minutes to automate incident investigation and infrastructure management. It provides guardrails, state management, and failure handling to safely run AI agents on production systems, with support for multiple LLM backends and integration with standard SRE tools.

## How It Works
AURA agents are configured in TOML, specifying orchestrated agent swarms, models, prompts, tools, and guardrails in a single file. Agents connect to infrastructure via Model Context Protocol (MCP) servers—including AWS, Kubernetes, Datadog, PagerDuty, and others—and can execute tool calls with optional human approval gates. The platform handles large tool outputs by storing them on disk and letting agents retrieve only needed slices, coordinates work across specialist agents via task DAGs, and exports OpenTelemetry traces for full observability. It supports any OpenAI-compatible LLM backend and can run locally, as a server, in Docker, on Kubernetes, or embedded as a Rust library.

## Why It Matters
SRE teams need agents that work safely within their existing infrastructure without vendor lock-in. AURA addresses this by running on-premises, supporting model and provider switching through config changes, and providing human approval workflows for sensitive operations. Its broad integration surface—covering cloud platforms, observability tools, incident management, and code repositories—makes it immediately useful for automating routine investigation and response tasks without requiring agents to learn custom APIs.

## Sources
- [mezmo/aura](https://github.com/mezmo/aura) — github · 247

## Related
