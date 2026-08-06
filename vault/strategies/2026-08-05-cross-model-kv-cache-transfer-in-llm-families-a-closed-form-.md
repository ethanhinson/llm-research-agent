---
title: "Cross-Model KV Cache Transfer in LLM Families: A Closed-Form Linear Mapping for Prefill Reuse"
date: 2026-08-05
category: architecture
tags: [emerging]
novelty: 7
validated: false
sources_count: 1
status: new
---

# Cross-Model KV Cache Transfer in LLM Families: A Closed-Form Linear Mapping for Prefill Reuse

## Summary
Production deployments often swap between different-sized models in a family for cost-quality cascading, mid-conversation switching, and routing, and each swap forces the receiver to repay the prefill from scratch.

## How It Works
Production deployments often swap between different-sized models in a family for cost-quality cascading, mid-conversation switching, and routing, and each swap forces the receiver to repay the prefill from scratch. We propose cross-model KV cache transfer, where the receiver reuses the source's KV cache, skipping prefill. We find that cross-model KV has substantial linear structure across matched-KV pairs, where source and target share KV head count and per-head dimension. On Qwen3 14B->32B, one

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [Cross-Model KV Cache Transfer in LLM Families: A Closed-Form Linear Mapping for Prefill Reuse](http://arxiv.org/abs/2608.03893v1) — arxiv · 0

## Related
