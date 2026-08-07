<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0006 — LLM-generated freeform topic tags](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0006-llm-topic-tags.md)**
<!-- docket:backlink:end -->

# LLM-generated freeform topic tags — results
Change: #0006 · Branch: feat/llm-topic-tags · PR: <set at PR open> · Plan: docs/superpowers/plans/2026-08-07-llm-topic-tags.md · ADRs: none

## Verify (human)

Automated tests are green (102 passed) but a **live** end-to-end run that exercises the real Haiku tag pass was NOT performed — the Anthropic account currently returns `400 credit-balance-too-low`, so the Evaluator's live calls cannot run. Deferred exactly as changes 0005 / 0007 deferred their live runs for the same account condition. Once the account has credit, at the merge gate:

- [ ] Run the agent's normal ingest flow (or a `reclassify` run) against a **copy** of the vault and confirm freshly written notes carry 2–4 topic tags appended after the structural tag(s) in frontmatter (e.g. `tags: [research, agentic, rag, chain-of-thought]`).
- [ ] Spot-check that topic tags are lowercase-hyphenated and are genuinely topical (not "research"/"news"/"release" duplicates of the structural tag).
- [ ] Confirm the Obsidian tag pane now surfaces topic tags (`#rag`, `#fine-tuning`, …) as browseable facets.
- [ ] Reclassify path: because `Reclassifier.reclassify()` routes through `Evaluator.score()`, retroactively reclassified notes should also gain topic tags — verify on a copy with `python cli.py reclassify --date <YYYY-MM-DD>`.

## Findings

- **Fourth `_call` broke three existing tests (caught at reconcile).** Adding `_tag_batch` makes `Evaluator.score()` issue a fourth `_call` per batch; the three full-`score()` tests seeded `messages.create` with exactly 3 `side_effect` responses and would `StopIteration` on the 4th. Each was given a 4th (tag-pass) mock response. Folded into scope at reconcile time; no assertion changes.
- **Plan deviation — tag normalization (deliberate, better than spec).** The spec's `_tag_batch` split raw tags with a single `re.split(r"[,\s]+", ...)`, which would fragment a comma-delimited multi-word tag ("Fine Tuning" → `fine`, `tuning`). The implementation splits on commas first (hyphenating intra-token spaces), falling back to whitespace only when no comma is present, so `"RAG, Fine Tuning, reasoning"` → `["rag", "fine-tuning", "reasoning"]`. Covered by `test_tag_batch_normalizes_commas_and_case`.
- **Reclassify follow-up resolved by placement (recorded in the Reconcile log).** The change's original open scope note ("Change 0005's reclassify command should also run `_tag_batch`") is moot — reclassify routes through `score()`, so topic tags flow in automatically. No `reclassifier.py`/`cli.py` change was needed.
- **Test-environment quirk (build lesson, already in learnings).** The suite must be run as `uv run python -m pytest` after `uv sync --extra dev`; a bare `pytest` resolves to a global pyenv shim that loads a crashing `deepeval` plugin. Used that form throughout; baseline 98 → final 102 passed.

## Follow-ups

Auto-capture is disabled in this repo (`auto_capture.enabled: false`), so these are recorded here rather than minted as stubs — a human can file them via `docket-new-change`:

- **(Carried forward from change 0005, now more acute) Make `Evaluator.score()` fail-soft.** `score()` now makes four un-guarded Anthropic calls per batch instead of three; a runtime credit-balance `400` (or any API error) still raises out of the trunk and aborts the whole batch. The tag pass widens this surface. A follow-up should make the evaluator fail-soft (e.g. skip a failed pass and continue) or have callers short-circuit to a clean report on a batch-level evaluator failure. Out of scope for 0006.
- **(Minor, optional) Idempotency of topic tags on re-tag.** `_tag_batch` unconditionally appends; if an already-tagged note is re-run through `score()` (e.g. repeated reclassify), topic tags could accumulate/duplicate. Consider de-duping `item.tags` after the tag pass if repeated reclassification of the same notes becomes a real workflow. Not observed as a bug in the current single-pass ingest.
