---
title: "xuiltul/animaworks"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, memory, agent-frameworks, multi-agent]
validated: false
sources_count: 1
content_source: full
status: new
---

# xuiltul/animaworks

## Summary
AnimaWorks is a framework that organizes AI agents as persistent team members with individual names, roles, personalities, and long-term memory rather than one-off tools. Agents coordinate via messaging, delegate tasks, and ask humans for confirmation when needed, running continuously with their own schedules and reflection cycles.

## How It Works
Each agent ("Anima") runs in an isolated OS process with IPC coordination and automatic restart. The system uses neuroscience-inspired memory combining RAG (Chroma + graph), consolidation, active forgetting, and automatic recall. Agents operate on a heartbeat cycle (observe → plan → reflect), execute cron jobs, delegate tasks hierarchically, and consolidate episodic memory into knowledge during downtime. A web dashboard shows org structure, role, status, and real-time activity; a 3D workspace visualizes agent interactions. Setup requires an API key and Docker, launching a three-agent demo in 60 seconds.

## Why It Matters
Practitioners treating AI agents as persistent team members rather than stateless tools gain continuity across operations and can delegate work at scale without re-briefing. Long-term memory retrieval eliminates the need to stuff full context into every prompt, and autonomous scheduling means agents can monitor, reflect, and coordinate without human intervention between actions. The framework supports multiple LLM providers (Claude, GPT, Gemini, local models) and deployed multilingual UI, making it practical for real business operations where teams need to grow and remember decisions over time.

## Sources
- [xuiltul/animaworks](https://github.com/xuiltul/animaworks) — github · 253

## Related
