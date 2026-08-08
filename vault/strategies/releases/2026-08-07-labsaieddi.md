---
title: "labsai/EDDI"
date: 2026-08-07
type: release
score: 8
score_label: significance
tags: [release, agent-frameworks, mcp, rag]
validated: false
sources_count: 1
content_source: full
status: new
---

# labsai/EDDI

## Summary
EDDI (Enhanced Dialog Driven Interface) is a production-grade, config-driven middleware for orchestrating multi-agent conversational AI systems. It coordinates users, agents, and business systems through intelligent routing, persistent memory, and API orchestration without requiring code, built on Java 25 and Quarkus with Red Hat certification.

## How It Works
EDDI deploys via one-command Docker installer and operates as a deterministic orchestration engine rather than a code library. Agent logic lives in versioned JSON configurations (updatable without redeployment), conversations are routed intelligently across agent pools, and multi-agent workflows support six built-in discussion styles (Round Table, Peer Review, Delphi, etc.). It integrates with OpenAI, Anthropic, Azure, Bedrock, and self-hosted endpoints; supports MCP, A2A communication, Slack, and OAuth 2.0; and provides immutable audit trails via HMAC-SHA256 cryptographic signing.

## Why It Matters
Most multi-agent frameworks (LangGraph, CrewAI, AutoGen) prioritize prototyping ease but require custom governance for production. EDDI inverts this: it trades embedded code flexibility for deterministic control, vault-encrypted secrets, built-in GDPR/HIPAA/EU AI Act infrastructure, and true OS-level concurrency via Java Virtual Threads. For teams deploying conversational AI at scale, EDDI's philosophy—"the engine is strict so the AI can be creative"—addresses a real operational gap between research tools and compliant, auditable production systems.

## Sources
- [labsai/EDDI](https://github.com/labsai/EDDI) — github · 364

## Related
