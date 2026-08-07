---
id: 5
slug: retroactive-reclassify-vault-notes
title: Retroactive re-classification of existing vault notes
status: in-progress
priority: medium
type: chore
created: 2026-08-03
updated: 2026-08-07
depends_on: [4]
related: [4]
discovered_from: [4]
adrs: []
spec: docs/superpowers/specs/2026-08-03-retroactive-reclassify-vault-notes.md
plan:
results:
trivial: false
auto_groomable: false
branch: feat/retroactive-reclassify-vault-notes
claimed_at: 2026-08-07T01:06:00Z
pr:
blocked_by:
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-03-retroactive-reclassify-vault-notes.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-03-retroactive-reclassify-vault-notes.md) |
<!-- docket:artifacts:end -->

## Why

Before change 0004 shipped the three-pass evaluator, content had no type system. Reconcile (2026-08-07) found the vault reality has drifted from the original premise: rather than "~51 Aug 1 notes in `research/`", there are now **167 flat top-level notes** at `vault/strategies/*.md` (dated 2026-08-03/04/05) written under the *old* schema — `category:`/`novelty:` frontmatter, **no `type:` field**, and never moved into a type subdirectory. The 156 already-classified notes in the `research/`, `releases/`, `news/`, `benchmarks/`, `tutorials/` subdirs already carry the new schema. The 167 flat notes are misclassified/untyped and pollute the index and tag pane until re-classified. The intent is unchanged (re-classify pre-type-system notes and file them into correct subdirs); only the target set is now the flat top-level notes.

## What

Add a `cli.py reclassify` command that reads existing vault notes, runs them through the three-pass evaluator, rewrites their frontmatter to the new schema in-place, moves them to the correct type subdirectory, and regenerates the index.

## Scope

- New `cmd_reclassify(args, cfg)` function + `_build_reclassify_parser()` in `cli.py` with `--date` and `--all` flags, dispatched via the existing `main()` if/elif chain (the codebase does NOT use `set_defaults(func=...)`)
- Read old-schema frontmatter (`category`/`novelty`, no `type`) and new-schema (`type`/`score`/`score_label`) alike; build a `RawItem` per note; run `Evaluator.score()` (all three passes + tags)
- Rewrite frontmatter to the new schema: `type`, `score`, `score_label`, `category` (research only), `tags`; preserve `title`, `date`, `validated`, `sources_count`, `status`, `content_source`
- Move each note to `strategies/<TYPE_DIRS[content_type]>/` (via `agent.writer.TYPE_DIRS`); a flat top-level note always moves; `-2` suffix on slug collision
- Call `Writer(vault_path).regenerate_index()` after processing
- Reuse `agent.regenerator.split_note()` for frontmatter/body parsing
- No changes to `agent/evaluator.py`, `agent/writer.py`, or `agent/models.py`
- Tests: unit-test the new CLI command + parser with a mocked `Evaluator` (no live API — the Anthropic account currently has insufficient credit, so live verification is deferred)

## Reconcile log

### 2026-08-07

Reconciled against current `origin/main` (HEAD `c689131`, after change 0007 merged as PR #5). Findings folded into `## Why` / `## What` / `## Scope`:

- **Target set changed.** The spec's premise ("~51 Aug 1 notes in `strategies/research/`") is stale. Reality: 167 flat top-level notes at `vault/strategies/*.md` (dated 08-03/04/05) under the OLD schema (`category:`/`novelty:`, no `type:` field), never filed into a subdir. The 156 subdir notes already carry the new schema. The reclassify target is now the 167 flat notes. Intent unchanged.
- **CLI dispatch pattern.** cli.py uses `cmd_*(args, cfg)` + `_build_*_parser()` + an explicit if/elif chain in `main()` — NOT the spec's `set_defaults(func=...)`. Follow the `cmd_regenerate`/`_build_regenerate_parser` pair (change 0007) as the template.
- **Index regen.** `Writer(vault_path).regenerate_index()` (instance method) is the real call — matches spec intent.
- **Reusable helper.** `agent.regenerator.split_note(content) -> (fm, body)` already exists; reuse it rather than re-parsing frontmatter.
- **Old-schema read.** Flat notes lack `type`/`score`/`score_label`; they carry `novelty:` and `category:`. Reclassify must read old-schema fields defensively and always write the new schema.
- **Live-API deferred.** `Evaluator.score()` makes live Anthropic Haiku calls; the account currently returns 400 credit-balance-too-low. Build + test entirely against a mocked `Evaluator` per TDD; a live end-to-end reclassify run is recorded as deferred, not a blocker.
- No auto-capture (repo `auto_capture.enabled: false`); no adjacent stubs minted.
