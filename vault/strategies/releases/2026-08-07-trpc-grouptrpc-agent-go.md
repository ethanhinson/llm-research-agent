---
title: "trpc-group/trpc-agent-go"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, agent-frameworks, memory, tool-use]
validated: false
sources_count: 1
content_source: full
status: new
---

# trpc-group/trpc-agent-go

## Summary
tRPC-Agent-Go is a production-grade Go framework for building agent systems with built-in support for LLM agents, tool calling, persistent memory, workflow orchestration, and observability. It integrates with Go services natively and provides a complete stack for concurrent, observable agent applications ready for deployment.

## How It Works
The framework bundles LLM agent runtimes with streaming support and context cancellation; GraphAgent for type-safe multi-conditional workflows (functionally equivalent to LangGraph); tool ecosystems including function tools, MCP protocol, and web search; persistent session and memory state with knowledge retrieval; reusable Skills via SKILL.md specifications that agents can load and execute; agent self-evolution via session reviews that extract and gate new skills; and OpenTelemetry observability with Langfuse integration. Agents can be chained sequentially or run in parallel, and prompt caching provides automatic cost optimization.

## Why It Matters
Go developers building agent applications now have a purpose-built framework that eliminates the need to wire together scattered libraries, while maintaining Go's strengths in concurrency, observability, and service deployment. The inclusion of production features—persistent memory, skill evolution, evaluation tooling, and protocol interoperability (AG-UI, A2A, MCP)—lowers the barrier to shipping agent systems for customer support, data analysis, DevOps automation, and RAG-powered workflows at scale.

## Sources
- [trpc-group/trpc-agent-go](https://github.com/trpc-group/trpc-agent-go) — github · 1647

## Related
