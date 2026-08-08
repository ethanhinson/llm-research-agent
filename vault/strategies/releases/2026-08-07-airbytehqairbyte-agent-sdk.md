---
title: "airbytehq/airbyte-agent-sdk"
date: 2026-08-07
type: release
score: 8
score_label: significance
tags: [release, tool-use, agent-frameworks]
validated: false
sources_count: 1
content_source: full
status: new
---

# airbytehq/airbyte-agent-sdk

## Summary
The Airbyte Agent SDK is a type-safe framework that exposes 50+ third-party APIs as LLM tools through strongly typed, well-documented connectors. It provides decorators and builders to integrate connectors with major LLM frameworks (pydantic-ai, LangChain, OpenAI Agents, FastMCP) while handling credential management, rate limiting, retries, and framework-specific error signalling.

## How It Works
The SDK offers three main patterns: `build_connector_tools()` for hosted connectors (exposes inspect, docs, and execute callables with progressive documentation), `@<Connector>.tool_utils` for typed connectors on supported frameworks (auto-detects framework and translates exceptions), and `@<Connector>.agent_tool()` for custom tool functions. All patterns preserve async callables and docstrings, support internal retries on transient failures (429/5xx, network, timeout), and guard output size by converting oversized results to framework-specific retry signals. The SDK detects double-decoration and prevents it; exception translation is unified via `@translate_exceptions` for any callable.

## Why It Matters
Practitioners building LLM agents benefit from a single, type-safe abstraction that eliminates boilerplate for credential handling, rate limiting, and framework integration across multiple LLM runtimes. The progressive docs flow (inspect → read docs → execute) and silent internal retries reduce agent hallucination and transient failure recovery, while framework-specific error signalling ensures seamless integration without custom exception handlers. Early adoption signals (131 engagements) suggest the pattern resonates with teams standardizing agent tool composition.

## Sources
- [airbytehq/airbyte-agent-sdk](https://github.com/airbytehq/airbyte-agent-sdk) — github · 131

## Related
