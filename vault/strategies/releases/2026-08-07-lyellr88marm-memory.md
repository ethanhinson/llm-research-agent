---
title: "Lyellr88/marm-memory"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, memory, mcp, tool-use]
validated: false
sources_count: 1
content_source: full
status: new
---

# Lyellr88/marm-memory

## Summary
MARM Memory is a local runtime that gives AI agents persistent, searchable memory across chat sessions. It stores conversations, code context, and concept relationships so agents can recall project history and decisions without losing context when switching between Claude, Gemini, Codex, or other LLM clients.

## How It Works
MARM provides 14 tools across three layers: Core Memory (7 tools) stores sessions and notes; Code Graph (5 tools) indexes repositories for symbol lookup and architecture navigation; Concept Graph (2 tools) links decisions, errors, and people back to relevant code. All tools work over HTTP or STDIO transport. The system uses SQLite with connection pooling, semantic re-ranking, and write-time deduplication to scale from solo developers to multi-agent swarms. Agents query a single local memory store instead of starting fresh each session.

## Why It Matters
Practitioners lose significant context switching between AI tools or resuming work—a problem MARM directly addresses by making project history, code structure, and decision trails searchable and shared. The lightweight token footprint (semantic re-rank before retrieval, write-time deduplication) keeps recall costs predictable as memory grows. Multiple deployment profiles (solo HTTP, STDIO, multi-agent swarm, trusted server) let teams run private local memory or shared agent memory without architectural changes, reducing friction for adoption across different team sizes and workflows.

## Sources
- [Lyellr88/marm-memory](https://github.com/Lyellr88/marm-memory) — github · 326

## Related
