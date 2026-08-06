---
title: "Structured Memory for Edge Language Models: Persistent Context and Corpus Retrieval via O(1) SSM State Injection"
date: 2026-08-04
category: architecture
tags: [emerging]
novelty: 7
validated: false
sources_count: 1
status: new
---

# Structured Memory for Edge Language Models: Persistent Context and Corpus Retrieval via O(1) SSM State Injection

## Summary
Retrieval-augmented generation (RAG) imposes a prefill cost proportional to retrieved context length, and -- with Transformer backbones -- a KV-cache that grows with each generated token.

## How It Works
Retrieval-augmented generation (RAG) imposes a prefill cost proportional to retrieved context length, and -- with Transformer backbones -- a KV-cache that grows with each generated token. State-Space Models (SSMs) avoid the second cost by construction; we eliminate the first, collapsing prefill from $O(L_{context})$ to $O(1)$ per query. We introduce PRECOG (Pre-Computed Context Injection), a retrieval mechanism that exploits a property unique to SSMs: the fixed-size, position-agnostic recurrent 

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [Structured Memory for Edge Language Models: Persistent Context and Corpus Retrieval via O(1) SSM State Injection](http://arxiv.org/abs/2608.02560v1) — arxiv · 0

## Related
