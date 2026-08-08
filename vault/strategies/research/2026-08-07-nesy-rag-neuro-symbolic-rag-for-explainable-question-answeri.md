---
title: "NeSy-RAG: Neuro-Symbolic RAG for Explainable Question Answering"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: agentic
tags: [research, agentic, rag, neuro-symbolic, reasoning]
validated: false
sources_count: 1
content_source: full
status: new
---

# NeSy-RAG: Neuro-Symbolic RAG for Explainable Question Answering

## Summary
NeSy-RAG is a neuro-symbolic retrieval-augmented generation framework that converts retrieved text into Prolog modules to make question-answering reasoning transparent and verifiable. It outperforms standard RAG on the ShARC benchmark by grounding each reasoning step in specific evidence and detecting missing user context.

## How It Works
For each retrieved text chunk, NeSy-RAG generates semantically meaningful Prolog predicates encoding Boolean claims. These predicates are retrieved and composed into Prolog queries using joint natural language-code embeddings. A symbolic knowledge-gap detection mechanism identifies missing user facts that affect the query outcome and triggers follow-up interactions. Executing the Prolog queries produces deterministic answers with transparent execution traces linking each step to its source.

## Why It Matters
Standard RAG systems lack verifiable intermediate reasoning steps and struggle to detect incomplete context. Practitioners benefit from NeSy-RAG's explicit Prolog-based execution model because it provides both attribution (tying answers to sources) and explainability (showing reasoning traces), while the knowledge-gap detection addresses a common failure mode of incomplete answers without domain-specific tuning.

## Sources
- [NeSy-RAG: Neuro-Symbolic RAG for Explainable Question Answering](http://arxiv.org/abs/2608.06292v1) — arxiv · 0

## Related
