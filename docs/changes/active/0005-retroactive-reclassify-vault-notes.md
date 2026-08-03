---
id: 5
slug: retroactive-reclassify-vault-notes
title: Retroactive re-classification of existing vault notes
status: proposed
priority: medium
type: chore
created: 2026-08-03
updated: 2026-08-03
depends_on: [4]
related: [4]
discovered_from: [4]
adrs: []
spec: docs/superpowers/specs/2026-08-03-retroactive-reclassify-vault-notes.md
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
| Spec | [2026-08-03-retroactive-reclassify-vault-notes.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-03-retroactive-reclassify-vault-notes.md) |
<!-- docket:artifacts:end -->

## Why

Before change 0004 shipped the three-pass evaluator, all content was treated as `type: research` regardless of what it actually was. The vault now has ~51 Aug 1 notes in `strategies/research/` that may include product releases, news, benchmarks, and tutorials mislabeled as research. The index and tag pane are misleading until these are re-classified.

## What

Add a `cli.py reclassify` command that reads existing vault notes, runs them through the three-pass evaluator, updates their frontmatter in-place, moves them to the correct subdirectory if the type changed, and regenerates the index.

## Scope

- New `cmd_reclassify()` function in `cli.py` with `--date` and `--all` flags
- No changes to `agent/evaluator.py`, `agent/writer.py`, or `agent/models.py`
- Vault migration: move misclassified notes from `research/` to their correct `releases/`, `news/`, `benchmarks/`, or `tutorials/` subdir
- Regenerate `vault/index.md` after migration
- Tests: unit test the new CLI command with mocked evaluator
