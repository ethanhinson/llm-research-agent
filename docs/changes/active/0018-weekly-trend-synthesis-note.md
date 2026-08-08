---
id: 18
slug: weekly-trend-synthesis-note
title: Weekly trend/cluster synthesis note over the vault
status: proposed
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: []
related: [14]
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

The vault is 172 atomic notes with only a flat, per-item `index.md` MOC. It visibly clusters — ~8 on-policy self-distillation / OPSD notes, a large agent-memory cluster (mem0, MemOS, memtrace, *AI Agent Memory Architectures*), a large failure-mode / trajectory-drift cluster — yet nothing synthesizes emergent themes. The KB itself shows the appetite: it is full of *survey* notes, which is exactly the higher-order artifact a reader wants. A weekly "what's trending across everything I collected" note is the natural output of a monitoring agent and turns the firehose into a signal.

## What changes

(Needs brainstorm — design open.) Roughly: a scheduled job (weekly, alongside the deep sweep) that reads the week's kept notes, clusters them into emergent themes (by tag co-occurrence, embedding clusters, or an LLM pass over titles+summaries), and writes a dated "Weekly Themes" MOC note to the vault linking the constituent notes per theme, with a one-paragraph "what changed this week" per cluster.

## Out of scope

- Replacing `index.md` (this augments it).
- Cross-week longitudinal trend tracking (possible follow-up).

## Open questions

- Clustering method: tag co-occurrence (cheap, no new deps) vs embeddings (ties to 0015) vs a single LLM synthesis pass over the week's titles+summaries.
- Where it lives: `vault/digests/` vs top-level; how it links from `index.md`.
- Scheduling: reuse the weekly deep-sweep slot or a separate job; what window (7d) and what minimum cluster size.
- LLM cost/context: summarize from stored note summaries vs re-reading full notes.

## Reconcile log
