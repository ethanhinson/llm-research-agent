<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0005 — Retroactive re-classification of existing vault notes](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0005-retroactive-reclassify-vault-notes.md)**
<!-- docket:backlink:end -->

# Retroactive re-classification of existing vault notes — results
Change: #0005 · Branch: feat/retroactive-reclassify-vault-notes · PR: <set at PR open> · Plan: docs/superpowers/plans/2026-08-07-retroactive-reclassify-vault-notes.md · ADRs: none

## Verify (human)

Automated tests are green (98 passed) but a **live** reclassify run against real vault notes was NOT performed — the Anthropic account currently returns `400 credit-balance-too-low`, so the Evaluator's live Haiku calls cannot run. This is deferred, exactly as change 0007's E2E run was deferred for the same account condition. Once the account has credit, run these at the merge gate:

- [ ] `python cli.py reclassify --date 2026-08-05` on a **copy** of the vault (or a git-clean checkout you can revert) — the command mutates notes in place and moves files.
- [ ] Confirm the summary line prints `reclassified=N moved=M errored=K` with a plausible N (~55 for 2026-08-05) and errored=0.
- [ ] Spot-check 3–4 moved notes: each now has `type:` set, the legacy `novelty:` key gone, `score:`/`score_label:` present, `category:` only on research notes, and the file now lives in the correct `strategies/<type-dir>/` subdir.
- [ ] Confirm `vault/index.md` regenerated and groups the reclassified notes under the right type sections.
- [ ] Then run `--all` (167 flat top-level notes were the reconcile-identified target set) once the per-date run looks right.

## Findings

- **Test-environment quirk (build lesson).** `uv run pytest` in this repo resolves `pytest` to a global **pyenv shim** (`~/.pyenv/shims/pytest`), which imports a stray `deepeval` pytest plugin from the pyenv global site-packages and errors at collection. The project venv did not even have pytest until `uv sync --extra dev`. The canonical, reliable test command is **`uv run python -m pytest`** after `uv sync --extra dev`. All dispatched build/test steps used that form; baseline and final suite were green (92 → 98 passed).
- **YAML date-scalar handling.** `yaml.safe_load` parses a frontmatter `date: 2026-08-03` into a `datetime.date`, which `yaml.safe_dump` re-emits as a bare YAML date (not a quoted string), breaking round-trip string equality. Handled with a module-scoped `class _YamlDumper(yaml.SafeDumper)` subclass carrying `date`/`datetime` string representers — scoped to the reclassifier only, never mutating the global `yaml.SafeDumper` (caught and fixed in review, commit `d50adab`).
- **Reconcile drift (recorded in the change's Reconcile log).** The spec's premise ("~51 Aug 1 notes in `research/`") was stale; the real target set is 167 flat top-level `vault/strategies/*.md` notes (08-03/04/05) under the old `category:`/`novelty:` schema with no `type:`. Scope adjusted, intent unchanged.

## Follow-ups

Auto-capture is disabled in this repo (`auto_capture.enabled: false`), so these are recorded here rather than minted as stubs — a human can file them via `docket-new-change`:

- **(Important) Make `Evaluator.score()` fail-soft, or wrap it in reclassify.** `agent/evaluator.py`'s Anthropic calls are not fail-soft; a runtime credit-balance-`400` raises out of `score()` and aborts the entire reclassify batch before any note is rewritten, surfacing a traceback instead of a clean `errored` tally. Same fail-hard-trunk pattern flagged in change 0007's learnings. A follow-up should either make the evaluator fail-soft or have reclassify short-circuit to a clean report on a batch-level evaluator failure. Out of scope for 0005 (which must not modify `agent/evaluator.py`).
- **(Minor) Add two tests.** The `-2` filename-collision suffix path (`_rewrite_and_move`) and the old-schema `novelty`→`score` fallback in `_build_item` are implemented but not directly covered by a test.
- **(Minor, optional polish) `_rewrite_and_move` redundant read.** It re-reads and re-splits the file rather than using the already-split `body`; functionally equivalent (both use `split("---", 2)`), no bug — a tidy-up if the file is touched again.
