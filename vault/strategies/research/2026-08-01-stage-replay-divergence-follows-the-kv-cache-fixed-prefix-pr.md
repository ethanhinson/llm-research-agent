---
category: architecture
date: 2026-08-01
score: 7
score_label: novelty
sources_count: 1
status: new
tags:
- research
- architecture
title: 'Stage-Replay Divergence Follows the KV Cache: Fixed-Prefix Precision Controls
  and Bidirectional Cache Transplantation'
type: research
validated: false
---

# Stage-Replay Divergence Follows the KV Cache: Fixed-Prefix Precision Controls and Bidirectional Cache Transplantation

## Summary
Stage-replay diagnostics reconstruct intermediate token prefixes and treat fresh-prefill continuation as continuation from the decoder state that originally reached the prefix.

## How It Works
Stage-replay diagnostics reconstruct intermediate token prefixes and treat fresh-prefill continuation as continuation from the decoder state that originally reached the prefix. We audit that assumption at a whole reasoning-stage boundary in a Qwen2.5-derived system. A matched 200-item experiment compares retained live cache with one-shot prefill of identical integer tokens and places an exact replica on both sides. In BF16, replicas remain exact while the constructions differ on 166 suffixes and

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [Stage-Replay Divergence Follows the KV Cache: Fixed-Prefix Precision Controls and Bidirectional Cache Transplantation](http://arxiv.org/abs/2607.28495v1) — arxiv · 0

## Related
