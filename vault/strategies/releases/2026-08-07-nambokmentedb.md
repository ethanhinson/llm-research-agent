---
title: "nambok/mentedb"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, memory, agent-frameworks, knowledge-graphs]
validated: false
sources_count: 1
content_source: full
status: new
---

# nambok/mentedb

## Summary
MenteDB is a purpose-built Rust storage engine for AI agent memory, designed to replace general-purpose and vector databases with a system that understands how LLMs consume data. It automatically extracts, structures, and curates memories from conversations to deliver clean, organized context rather than storing raw data or similarity-ranked noise.

## How It Works
A single `process_turn()` call runs a 14-step pipeline: embedding the user message, performing hybrid search (vector + BM25 + graph traversal), extracting typed entities and facts via LLM, detecting contradictions, and storing episodic memories with temporal metadata. Retrieval is ordered to fit token budgets and uses write-time intelligence (LLM extraction, quality filtering, deduplication, contradiction detection) to reject low-confidence or redundant data before storage. Available as a cloud service (API key), self-hosted Rust server, or embedded library; integrates with Claude, Cursor, LangChain, and CrewAI via SDK or REST.

## Why It Matters
Traditional and vector databases retrieve results ranked only by similarity, flooding context windows with irrelevant data (studies cited show up to 97% irrelevance). Since a transformer gets one forward pass with a fixed context window and cannot reorganize retrieved data, MenteDB's write-time curation—extracting only decisions, preferences, corrections, and facts—directly improves agent performance by ensuring every retrieved memory is relevant. Its entity graph, contradiction tracking, and belief propagation also allow agents to maintain coherent, updatable knowledge rather than static embeddings.

## Sources
- [nambok/mentedb](https://github.com/nambok/mentedb) — github · 111

## Related
