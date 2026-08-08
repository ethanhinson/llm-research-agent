<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0014 — Cross-source corroboration + citation-velocity signals](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0014-cross-source-corroboration-ranking.md)**
<!-- docket:backlink:end -->

# Cross-Source Corroboration + Citation-Velocity — Results

**Change:** 0014 · **Date:** 2026-08-08 · **Branch:** feat/cross-source-corroboration-ranking

## What shipped

Staged per the spec (S1→S6), each landed as its own TDD commit:

- **S1** `agent/canonical.py` — `canonical_id(item)` with precedence arXiv > DOI > normalized-URL > normalized-title; `RawItem.canonical_id` field.
- **S2** `agent/tools/corroborate.py` — `corroborate()` groups by identity, collapses intra-sweep duplicates to one representative, counts distinct sources, sets `validated`; replaces `agent/tools/cross_validate.py` (deleted); wired into `run_sweep` + `search_sweep`.
- **S3** `agent/deduplicator.py` — index schema v2 (`items` map) with v1 migration (legacy `urls`/`titles` preserved so `cli.py cmd_status` still works), a 72h corroboration window, `record()` + `corroboration_update()`; `Writer.update_corroboration()` does a targeted frontmatter + `## Sources` rewrite with no body regeneration; `_write_kept` updates the existing note on a within-window re-surface instead of writing a duplicate.
- **S4** `agent/evaluator.py` — a `[corroborated by N sources]` soft signal appended to score/validate prompts when `sources_count >= 2`, framed as evidence, not an auto-keep.
- **S5** `agent/tools/citation_velocity.py` — weekly-deep-sweep-only Semantic Scholar `/paper/batch` re-poll (reuses the 0012 `S2_API_KEY`/429-backoff/pacing patterns), stores `citation_count`/`citation_delta`/`citation_checked`, flags `rising`; a 📈 marker + rising-first sort tiebreak in `Writer.regenerate_index`.
- **S6** config threading — `corroboration` + `citation_velocity` sections in `config.yml`, threaded through `cli.py` into `run_sweep`/`search_sweep`/`start_scheduler`.

Everything new is config-gated and fail-soft; `corroborate()`/`record()` (intra-sweep identity collapse) is the standing baseline, and `corroboration.enabled: false` now gates only the cross-sweep note-update path.

## Verification

- **Automated suite:** `uv sync --extra dev && uv run python -m pytest -q` → **293 passed, 3 failed**. The 3 failures are **pre-existing on `origin/main`** (baseline `832adca`), unrelated to this change: `tests/test_cli.py::test_load_config_surfaces_llm_section` and two in `tests/test_fetcher_arxiv.py` (arxiv-lib mock seam). This change introduced **zero** new failures. New tests added across the six tasks + review fixes: ~40.
- **Whole-branch review:** performed before PR (review-role auto-fallback — see below). **No blockers.** Three SHOULD-FIX findings were fixed in-branch with TDD (commit `8383b4d`): (1) honor `corroboration.enabled: false`; (2) clear the `rising` flag when a paper falls below `min_delta` (was sticky-forever); (3) tighten the DOI regex so an ordinary URL containing a `/10.NNNN/` path segment is not misread as a DOI (was a false-dedup hole; fixed in both `canonical.py` and `citation_velocity.py`).

## Human checklist at the merge gate

- [ ] **Live S2 `/paper/batch` check (not yet run):** the spec's live-check task and the build-time smoke were **not executed** in this run — no `S2_API_KEY` / paid-LLM budget was exercised here. Before or after merge, run one real batch call, e.g. `uv run python -c "import os,agent.tools.citation_velocity as cv; print(cv.fetch_citation_counts(['ARXIV:1706.03762'], api_key=os.getenv('S2_API_KEY')))"`. Per the `live-testing-catches-what-mocks-miss` learning: a 429 from the unkeyed pool is a **valid fail-soft verification**, not a failure. A 200 with a citation count confirms the happy path.
- [ ] **Optional live deep sweep:** `uv run python cli.py sweep --deep --lookback-days 2` (LLM via the repo-default OpenRouter provider, which needs no Anthropic credit) to exercise corroboration + the citation-velocity re-poll end-to-end. Non-fatal enrich/search self-skips are expected.
- [ ] **Pre-existing baseline failures:** the 3 red tests above exist on `main` today and are out of scope here — worth a separate `fix` change (arxiv fetcher mock + cli config assertion).

## Follow-ups (reported, not minted — auto-capture disabled)

- **NICE-TO-HAVE (review):** broaden the tracking-param strip list in `canonical.py` (currently `utm_*` + `ref`; add `fbclid`/`gclid`/`ref_src`/…) — its own small change.
- **NICE-TO-HAVE (review):** `Writer.update_corroboration` replaces but does not *insert* absent `sources_count`/`validated` frontmatter keys (fail-soft, not a crash); consider insert-if-missing like `citation_velocity._rewrite_frontmatter`.
- **Enhancement:** surface corroboration counts / rising papers in `cli.py cmd_status` (it still reads only the legacy `urls` key — not a regression, an opportunity).
- **Pre-existing:** the 3 baseline test failures on `main` (see checklist) warrant their own fix change.
