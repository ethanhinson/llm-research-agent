---
title: "Muon on the Stiefel Manifold Admits an Exact Closed-Form Update"
date: 2026-08-07
type: research
score: 7
score_label: novelty
category: architecture
tags: [research, architecture, optimization, matrix-methods]
validated: false
sources_count: 1
content_source: full
status: new
---

# Muon on the Stiefel Manifold Admits an Exact Closed-Form Update

## Summary
This work shows that Muon, a matrix-aware optimizer, has an exact closed-form update when applied to the Stiefel manifold (matrices with orthonormal columns). The authors use this insight to propose Skewon, a practical algorithm for orthogonality-constrained optimization, and prove first-order convergence guarantees.

## How It Works
Rather than relying on heuristic, approximate, or iterative updates to apply Muon to Stiefel manifold constraints, the authors derive a closed-form solution for the update step. This exact form is then implemented as Skewon, which handles orthogonality-constrained problems efficiently. Convergence is established in the smooth non-convex setting.

## Why It Matters
Orthogonality-constrained optimization is common in machine learning and scientific computing. An exact closed-form update avoids the computational overhead and approximation error of iterative or heuristic approaches, making Skewon a more direct and efficient option for practitioners working with problems naturally expressed on the Stiefel manifold.

## Sources
- [Muon on the Stiefel Manifold Admits an Exact Closed-Form Update](http://arxiv.org/abs/2608.06218v1) — arxiv · 0

## Related
