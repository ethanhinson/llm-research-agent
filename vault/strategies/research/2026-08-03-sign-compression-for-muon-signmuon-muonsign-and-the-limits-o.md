---
title: "Sign compression for Muon: SignMuon, MuonSign, and the Limits of Error Feedback"
date: 2026-08-03
type: research
score: 6
score_label: novelty
category: architecture
tags: [research, architecture]
validated: false
sources_count: 1
status: new
---

# Sign compression for Muon: SignMuon, MuonSign, and the Limits of Error Feedback

## Summary
SignMuon compresses the Muon update to one bit per parameter by taking its elementwise sign, providing the most direct way to run a matrix-aware optimizer under an extremely low communication budget.

## How It Works
SignMuon compresses the Muon update to one bit per parameter by taking its elementwise sign, providing the most direct way to run a matrix-aware optimizer under an extremely low communication budget. It outperforms SignSGD in practice, yet it can ascend even on a linear function. Signing the gradient before the Linear Minimization Oracle (LMO), rather than after, does not repair this: we construct a small explicit instance on which sign-before (MuonUSign) and sign-on-both-sides (MuonSign) ascend

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [Sign compression for Muon: SignMuon, MuonSign, and the Limits of Error Feedback](http://arxiv.org/abs/2607.29674v1) — arxiv · 0

## Related
