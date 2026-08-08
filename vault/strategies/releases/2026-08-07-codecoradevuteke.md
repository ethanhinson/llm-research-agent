---
title: "codecoradev/uteke"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, memory, agent-frameworks, embeddings]
validated: false
sources_count: 1
content_source: full
status: new
---

# codecoradev/uteke

## Summary
Uteke is a local-first, offline persistent memory system for AI agents—a single Rust binary that stores and recalls memories with ~45ms latency using hybrid vector and full-text search. It requires no API keys, cloud services, or runtime dependencies, addressing the problem that AI tools forget context between sessions.

## How It Works
Uteke stores memories locally using SQLite and ONNX embeddings (768-dimensional, ~188MB one-time download). Search is hybrid: vector similarity plus FTS5 full-text, merged via Reciprocal Rank Fusion. It supports metadata (tags, entities, categories), multi-agent "Rooms" for shared memory with author attribution, and time-travel queries. Setup is a single curl command; interaction is CLI-based (e.g., `uteke remember`, `uteke recall`). Benchmarks show 42ms P50 recall latency on 10K memories and ~10KB storage per memory.

## Why It Matters
For practitioners building AI agents or privacy-sensitive applications (healthcare, finance, legal), Uteke eliminates the cost and risk of cloud-dependent memory layers. Unlike competitors (Mem0, Letta, Zep) that require API keys and Docker, or single-binary tools (Engram) limited to keyword search, Uteke combines zero dependencies with semantic + keyword search in one binary. Teams can use Rooms to share persistent, attributed knowledge across agents without manual sync or external infrastructure—making it practical for both solo developers and multi-agent workflows where data residency and offline capability are non-negotiable.

## Sources
- [codecoradev/uteke](https://github.com/codecoradev/uteke) — github · 193

## Related
