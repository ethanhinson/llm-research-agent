---
id: 17
slug: ensemble-novelty-scoring
title: Ensemble / rubric-calibrated novelty scoring with confidence
status: proposed
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: []
related: [4, 6, 7]
discovered_from: []
adrs: []
spec:
plan:
results:
trivial: false
auto_groomable: false
branch:
pr:
blocked_by:
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
<!-- docket:artifacts:end -->

## Why

`agent/evaluator.py` scores every item with a **single-pass, single-model judge over `item.body[:150]`** (title + 150 chars, before full-content synthesis). The knowledgebase this agent collects repeatedly documents that a lone LLM judge is fragile and biased: *Beyond a Single Judge: Simulating Social Persona Panels* (novelty 7), *RRC: Unlocking Generative Reward Models via Ranking-Based Reward Construction* (7), *Sycophancy Undermines Epistemic Vigilance in Cooperative Tasks* (4), *Learning When to Trust via Selective Context Preference Optimization* (validated). We are running the exact anti-pattern our own vault flags — and doing it on a 150-char snippet, so the score never sees the synthesized full text.

## What changes

(Needs brainstorm — design open.) Roughly: for borderline items (e.g. score 5–7) run a small ensemble — self-consistency (N samples) and/or a short persona/rubric panel — and aggregate; score on the enriched/synthesized body rather than `body[:150]`; attach a confidence signal and optionally an abstain path that routes low-confidence items to a review tag instead of silently keeping/dropping.

## Out of scope

- Replacing the batch classify/validate passes.
- Training a reward model (the KB's RRC direction) — this is inference-time only.

## Open questions

- Ensemble shape: self-consistency (same prompt, N samples, majority/mean) vs a small persona panel vs a stricter single-pass rubric — cost vs signal.
- Only escalate borderline items, or all? Escalation band definition.
- Score on `body[:N]`, the full enriched body, or the post-synthesis note? Ordering vs the synthesis step.
- How to surface confidence in the note frontmatter / index; does abstain create a new lifecycle state?

## Reconcile log
