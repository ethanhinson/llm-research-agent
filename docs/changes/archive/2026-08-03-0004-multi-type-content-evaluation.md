---
id: 4
slug: multi-type-content-evaluation
title: Multi-type content evaluation — expand tagging beyond novelty
status: done
priority: medium
type: feat
created: 2026-08-02
updated: 2026-08-03
depends_on: []
related: [1, 2]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-02-multi-type-content-evaluation.md
plan:
results:
trivial: false
auto_groomable: false
branch: feat/multi-type-content-evaluation
pr: https://github.com/ethanhinson/llm-research-agent/pull/4
blocked_by:
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-02-multi-type-content-evaluation.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-02-multi-type-content-evaluation.md) |
<!-- docket:artifacts:end -->

## Why

The current evaluator treats all LLM/AI content as "research to score for novelty." Product launches, benchmark comparisons, industry news, and tutorials all get scored 1 and are effectively discarded — even when they are high-signal for different reasons. The novelty framing made sense for an arXiv-focused agent but is too narrow now that the agent monitors a broader set of sources via web search.

## What changes

Replace the single-pass novelty evaluator with a three-pass pipeline:
1. **Classify** — LLM assigns one of five content types: research | release | news | benchmark | tutorial
2. **Score** — LLM scores each item on a type-appropriate axis (novelty for research, significance for releases, timeliness for news, authority for benchmarks, practicality for tutorials); research items also get an existing sub-category
3. **Validate** — LLM makes an explicit keep/skip decision; no hardcoded numeric thresholds

Vault output gains per-type subdirectories (`strategies/research/`, `strategies/releases/`, etc.) and the index groups notes by type with type-appropriate column headers.

The `RawItem` model gains `content_type`, `score`, `score_label`, and `keep`; `novelty` is removed.

## Out of scope

- Changing fetchers or sources
- Retroactive re-classification of existing vault notes
- Per-type engagement thresholds
- Obsidian Dataview plugin integration

## Open questions

None — resolved in brainstorm.

## Reconcile log

<!-- Appended by docket-implement-next's reconcile pass: dated entries of what changed. -->
