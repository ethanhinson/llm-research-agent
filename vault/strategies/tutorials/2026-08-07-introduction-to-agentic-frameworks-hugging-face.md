---
title: "Introduction to Agentic Frameworks · Hugging Face"
date: 2026-08-07
type: tutorial
score: 6
score_label: practicality
tags: [tutorial, agent-frameworks, tool-use]
validated: false
sources_count: 1
content_source: full
status: new
---

# Introduction to Agentic Frameworks · Hugging Face

## Summary
This is an introductory tutorial to agentic frameworks—software abstractions for building LLM-powered agents. It argues that frameworks become valuable when agent workflows grow complex, such as when LLMs need to call functions or coordinate multiple agents, but may be unnecessary for simple prompt chains.

## How It Works
The tutorial identifies core requirements that agentic frameworks address: an LLM engine, a tool registry, a parser to extract tool calls from LLM output, a system prompt aligned with the parser, memory management, and error handling with retry logic. It then covers three specific frameworks—smolagents (Hugging Face's offering), LlamaIndex (production-oriented tooling), and LangGraph (stateful agent orchestration)—in separate units.

## Why It Matters
Practitioners benefit from recognizing when to reach for a framework versus plain code. For simple workflows, plain code offers transparency and control; for complex multi-agent or tool-calling scenarios, frameworks reduce boilerplate and provide battle-tested abstractions for tool invocation, memory, and error recovery—concerns that become burdensome to implement repeatedly from scratch.

## Sources
- [Introduction to Agentic Frameworks · Hugging Face](https://huggingface.co/learn/agents-course/en/unit2/introduction) — search/tavily · 0

## Related
