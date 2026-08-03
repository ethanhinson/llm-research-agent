---
id: 6
slug: llm-topic-tags
title: LLM-generated freeform topic tags
status: proposed
priority: medium
type: feat
created: 2026-08-03
updated: 2026-08-03
depends_on: [4]
related: [4, 5]
discovered_from: [4]
adrs: []
spec: docs/superpowers/specs/2026-08-03-llm-topic-tags.md
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
| Artifact | Link |
|---|---|
| Spec | [2026-08-03-llm-topic-tags.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-03-llm-topic-tags.md) |
<!-- docket:artifacts:end -->

## Why

Current tags are purely structural: `[research, agentic]` or `[release]`. This makes the Obsidian tag pane useless for topic-based browsing — you can't filter by `rag`, `fine-tuning`, or `reasoning` because those concepts never appear as tags. Adding LLM-generated topic tags fills the gap without manual labeling.

## What

Add a fourth evaluator pass that generates 2–4 lowercase hyphenated topic tags per item (e.g. `rag`, `chain-of-thought`, `inference-efficiency`, `multimodal`). These topic tags are appended to `item.tags` after the structural tags. The writer and note format require no changes — `item.tags` is already serialized as a comma-separated list in frontmatter.

## Scope

- New `TAG_PROMPT` constant and `_tag_batch()` method in `agent/evaluator.py`
- `_tag_batch()` called after `_set_tags()` in `Evaluator.score()`
- No changes to `agent/writer.py`, `agent/models.py`, or `agent/scheduler.py`
- Tests: mock `_tag_batch` response, verify tags appended to structural tags
- Change 0005's reclassify command should also run `_tag_batch` (add to scope after 0005 lands, or update 0005's spec)
