---
title: "Graphify-Labs/graphify"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, rag, knowledge-graphs]
validated: false
sources_count: 1
content_source: full
status: new
---

# Graphify-Labs/graphify

## Summary
Graphify is a code intelligence tool that maps projects into queryable knowledge graphs by parsing code with tree-sitter AST and optionally enriching docs, PDFs, images, and video with semantic analysis. It runs locally for code parsing and integrates with AI coding assistants (Claude, Cursor, Copilot, and 15+ others) to enable graph-based navigation and queries instead of file grepping.

## How It Works
Code is deterministically parsed using tree-sitter AST (no LLM, no data leaves the machine) to extract cross-file links (calls, imports, inherits) across ~40 languages. Each edge is tagged EXTRACTED (explicit in source) or INFERRED (resolved by graphify). The output is a real graph (not embeddings or vector index) stored in graph.json, browsable in graph.html, and queryable via commands like `graphify explain`, `graphify path`, and `graphify query`. Docs, PDFs, images, and audio optionally pass through an LLM for semantic enrichment. The graph identifies "god nodes" (most-connected concepts) and community structure via Leiden clustering.

## Why It Matters
Practitioners benefit from a deterministic, local-first alternative to vector search and RAG systems. Benchmarks show graphify achieves 45.3% QA accuracy on LOCOMO (n=300) and 76% on LongMemEval-S, competitive with or exceeding dense RAG and memory systems, while requiring zero LLM credits for code parsing—a significant cost advantage. The ability to trace explicit connections (not inferred embeddings) and traverse real paths between concepts supports higher-confidence code exploration and architectural understanding, especially valuable in large or unfamiliar codebases.

## Sources
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — github · 104008

## Related
