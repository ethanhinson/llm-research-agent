---
id: 6
slug: llm-topic-tags
title: LLM-generated freeform topic tags
status: implemented
priority: medium
type: feat
created: 2026-08-03
updated: 2026-08-07
depends_on: [4]
related: [4, 5]
discovered_from: [4]
adrs: []
spec: docs/superpowers/specs/2026-08-03-llm-topic-tags.md
plan: docs/superpowers/plans/2026-08-07-llm-topic-tags.md
results: docs/results/2026-08-07-llm-topic-tags-results.md
trivial: false
auto_groomable: false
branch: feat/llm-topic-tags
claimed_at: 2026-08-07T02:03:45Z
pr: https://github.com/ethanhinson/llm-research-agent/pull/7
blocked_by:
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-03-llm-topic-tags.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-03-llm-topic-tags.md) |
| Plan | [2026-08-07-llm-topic-tags.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/llm-topic-tags/docs/superpowers/plans/2026-08-07-llm-topic-tags.md) |
| Results | [2026-08-07-llm-topic-tags-results.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/llm-topic-tags/docs/results/2026-08-07-llm-topic-tags-results.md) |
| PR | [#7](https://github.com/ethanhinson/llm-research-agent/pull/7) |
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
- Update the three existing full-`score()` tests in `tests/test_evaluator.py` to supply a 4th (tag-pass) mock response — the tag pass adds a fourth `_call` per batch, and those tests currently seed `side_effect` with exactly 3 responses (see Reconcile log 2026-08-07)
- Reclassify (change 0005) needs NO separate change: `Reclassifier.reclassify()` routes through `Evaluator.score()`, so topic tags flow into retroactive reclassification automatically once `_tag_batch` is in the `score()` loop (see Reconcile log 2026-08-07)

## Reconcile log

### 2026-08-07

Reconciled at claim time against current `main` (tip `22d14db`, PR #6 merged) and current code.

- **`depends_on: [4]` satisfied** — change 0004 (multi-type-content-evaluation) is archived `done`. Build-ready confirmed.
- **Change 0005 (retroactive-reclassify) also landed `done`.** This resolves the change's original open scope note ("Change 0005's reclassify command should also run `_tag_batch`"). `agent/reclassifier.py:Reclassifier.reclassify()` calls `self._evaluator.score(...)` (line 56), so once `_tag_batch` is appended to the `score()` per-batch loop, retroactively reclassified notes receive topic tags **automatically** — no change to `reclassifier.py` or `cli.py` is required. Dropped that follow-up from scope.
- **Existing tests must be updated (new constraint).** Adding `_tag_batch` makes `Evaluator.score()` issue a **fourth** `_call` per batch. Three tests in `tests/test_evaluator.py` (`test_evaluator_three_passes_sets_fields`, `test_evaluator_missing_classify_line_keeps_default`, `test_evaluator_subcategory_only_set_for_research`) mock `messages.create` with `side_effect` lists of exactly 3 responses and will raise `StopIteration` on the 4th call. Each needs a 4th (tag-pass) mock response added. Folded into scope.
- **Code assumptions in the spec still hold** — `agent/evaluator.py` has `import re`, `_set_tags`, the `score()` loop, and `_call` exactly as the spec anticipates; `agent/models.py:RawItem.tags` is a `list`; `agent/writer.py` joins `item.tags` with `", ".join(...)` (line 74), handling any length. No changes needed to writer/models/scheduler, per spec.
- **Vault dir naming nit (cosmetic, no code impact).** Spec prose says `vault/`; the live vault subtree the writer/reclassifier use is `strategies/…`. Does not affect this change — tag serialization is dir-agnostic. Left as-is.
- **Live-API note.** The Anthropic account has insufficient credit (live calls 400 credit-balance-too-low). Build and verify with mocks per TDD; any live end-to-end tagging run is deferred, not a blocker.
- Auto-capture is disabled (`AUTO_CAPTURE_ENABLED=false`); the dropped/absorbed follow-up above is recorded here in the reconcile log rather than minted.
