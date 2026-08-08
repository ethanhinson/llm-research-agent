---
title: "oleksiijko/pmb"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, memory, agent-frameworks, tool-use]
validated: false
sources_count: 1
content_source: full
status: new
---

# oleksiijko/pmb

## Summary
PMB is a local-first memory system for AI agents that persists decisions, lessons, and project context across sessions using SQLite and MCP. It stores 3,800+ entities and 41,000+ connections automatically, retrieving relevant memory in 6–35 ms without cloud calls or API keys.

## How It Works
PMB runs as an MCP server child process, intercepting agent messages via a single `prepare(message)` call that returns project context, lessons, recent activity, and open goals in 4–16 ms. Storage uses SQLite as the durable source of truth with rebuildable LanceDB vector indexes; recall combines BM25 lexical search, dense vector similarity, entity-graph traversal, and optional cross-encoder reranking via Reciprocal-Rank-Fusion. Writes are async (under 1 ms to return). Deduplication runs four layers: exact text match, then cosine thresholds (0.92 auto-merge, 0.80–0.92 flagged for review). The dashboard visualizes memory as a live entity graph, timeline, and nine diagnostic tabs.

## Why It Matters
Practitioners stop re-explaining the same constraints and decisions to agents across restarts and model switches—memory survives because it lives in a local workspace users own, with no subscription or account overhead. The tool reports which lessons actually changed outcomes rather than claiming generic impact percentages, and multilingual embedding (50+ languages, no per-language setup) makes it practical across projects. Fast local recall and zero-network read path eliminate latency and privacy friction compared to cloud-based memory systems.

## Sources
- [oleksiijko/pmb](https://github.com/oleksiijko/pmb) — github · 284

## Related
