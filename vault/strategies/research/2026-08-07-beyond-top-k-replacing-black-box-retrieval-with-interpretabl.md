---
title: "Beyond Top-K: Replacing Black-Box Retrieval with Interpretable Agentic Operations"
date: 2026-08-07
type: research
score: 7
score_label: novelty
category: agentic
tags: [research, agentic, rag, agent-frameworks, interpretability]
validated: false
sources_count: 1
content_source: full
status: new
---

# Beyond Top-K: Replacing Black-Box Retrieval with Interpretable Agentic Operations

## Summary
This work challenges the standard chunk-embed-retrieve-top-k pipeline for retrieval-augmented generation over structured documents like financial statements. The authors demonstrate that dense retrieval fundamentally fails on such documents—where units are separated from values by table structure—and propose READ, an embedding-free agentic system that uses deterministic operations (lexical search, structural navigation, span reads) over the Model Context Protocol to produce auditable, replayable retrieval traces.

## How It Works
READ exposes three deterministic operations to an agent: normalized lexical search over raw text, structural navigation (traversing document layout), and bounded span reads. The agent orchestrates these operations to locate and retrieve relevant passages, with each action recorded as part of a replayable audit trail. This contrasts with opaque similarity scoring; the agent operates on the raw document rather than pre-chunked embeddings, avoiding the structural problems that plague dense retrieval (e.g., table headers separated from numeric values by chunk boundaries, unit ambiguity).

## Why It Matters
On a 51-question benchmark over real financial documents, READ achieved 58.8% accuracy compared to dense retrieval's 15.7%, with strong statistical significance. Even when tuned, dense retrieval only reached 35.3% versus READ's 58.8% (23.5 point gap). Critically, the gain stems from the embedding-free interface rather than agentic iteration alone—agents given a top-k tool performed far worse. For practitioners working with regulatory, financial, or highly structured documents, this shows that embedding-based retrieval may be fundamentally mismatched to the task, and that deterministic, interpretable operations can dramatically outperform learned similarity metrics.

## Sources
- [Beyond Top-K: Replacing Black-Box Retrieval with Interpretable Agentic Operations](http://arxiv.org/abs/2608.06305v1) — arxiv · 0

## Related
