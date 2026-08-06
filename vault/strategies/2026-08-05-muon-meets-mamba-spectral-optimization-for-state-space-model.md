---
title: "Muon Meets Mamba: Spectral Optimization for State Space Models"
date: 2026-08-05
category: architecture
tags: [emerging]
novelty: 6
validated: false
sources_count: 1
status: new
---

# Muon Meets Mamba: Spectral Optimization for State Space Models

## Summary
Muon is a recent optimizer that orthogonalizes the update to each weight matrix with a Newton-Schulz iteration, which performs steepest descent under the spectral norm.

## How It Works
Muon is a recent optimizer that orthogonalizes the update to each weight matrix with a Newton-Schulz iteration, which performs steepest descent under the spectral norm. Almost all the evidence for it comes from Transformer models, and its behavior on state-space models is largely unreported. We compare Muon with AdamW on Mamba-2 130M under a controlled protocol that varies only which weight groups are trained with Muon. The benefit is localized. Muon on the output projection alone beats Muon on 

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [Muon Meets Mamba: Spectral Optimization for State Space Models](http://arxiv.org/abs/2608.03941v1) — arxiv · 0

## Related
