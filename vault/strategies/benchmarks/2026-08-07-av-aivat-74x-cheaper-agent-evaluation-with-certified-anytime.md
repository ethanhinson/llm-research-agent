---
title: "AV-AIVAT: 74x Cheaper Agent Evaluation with Certified Anytime-Valid Stopping in Imperfect-Information Games"
date: 2026-08-07
type: benchmark
score: 8
score_label: authority
tags: [benchmark, agent-frameworks, evaluation]
validated: true
sources_count: 2
content_source: full
status: new
---

# AV-AIVAT: 74x Cheaper Agent Evaluation with Certified Anytime-Valid Stopping in Imperfect-Information Games

## Summary
AV-AIVAT is a method for efficiently comparing two agents in imperfect-information games by combining variance reduction (AIVAT) with anytime-valid confidence sequences. It enables statistically valid early stopping, reducing the number of games needed by a median 74× compared to raw outcomes across 71,439 Heads-Up No-Limit Hold'em hands.

## How It Works
AIVAT applies conditional mean-zero corrections to reduce variance in imperfect-information games (median 54× reduction). AV-AIVAT wraps this with continuously monitored confidence sequences—either asymptotic (AsympCS) or exact finite-sample (EB-CS)—that maintain their validity guarantee even when stopping is decided adaptively. The online value model learns only from past games to avoid bias. Stopping occurs the moment the confidence interval's width is narrow enough to declare a winner at the target precision level (e.g., ±1 Big Blind at 95% confidence).

## Why It Matters
Agent evaluation is expensive because the required sample size is unknown in advance. Fixed budgets waste resources by overshooting or understating the evidence. AV-AIVAT converts variance reduction into a principled stopping rule that practitioners can execute in real time and audit post-hoc, eliminating the statistical invalidation of naive optional stopping while dramatically cutting evaluation cost. This makes it practical to certify agent skill differences without overspending on games.

## Sources
- [AV-AIVAT: 74x Cheaper Agent Evaluation with Certified Anytime-Valid Stopping in Imperfect-Information Games](http://arxiv.org/abs/2608.06362v1) — arxiv/search · 0

## Related
