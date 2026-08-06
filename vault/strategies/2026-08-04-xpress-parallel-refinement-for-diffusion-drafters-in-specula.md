---
title: "xPress: Parallel Refinement for Diffusion Drafters in Speculative Decoding"
date: 2026-08-04
category: architecture
tags: [emerging]
novelty: 6
validated: false
sources_count: 1
status: new
---

# xPress: Parallel Refinement for Diffusion Drafters in Speculative Decoding

## Summary
Block-diffusion drafters like dFlash generate an entire block of draft tokens in a single forward pass, drastically reducing the overhead of multiple-token drafting in speculative decoding.

## How It Works
Block-diffusion drafters like dFlash generate an entire block of draft tokens in a single forward pass, drastically reducing the overhead of multiple-token drafting in speculative decoding. The crucial final step of the single-pass discrete denoising process involves using the logit distribution at each position to sample conditionally independent tokens. The resulting draft is thus a set of per-position marginals, rather than a joint distribution: no draft token is guaranteed to depend on its p

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [xPress: Parallel Refinement for Diffusion Drafters in Speculative Decoding](http://arxiv.org/abs/2608.02438v1) — arxiv · 0

## Related
