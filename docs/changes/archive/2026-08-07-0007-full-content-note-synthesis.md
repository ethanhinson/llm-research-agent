---
id: 7
slug: full-content-note-synthesis
title: Full-content retrieval + LLM note synthesis
status: done
priority: high
type: feat
created: 2026-08-06
updated: 2026-08-07
claimed_at: 
depends_on: []
related: [4, 5, 6]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-06-full-content-note-synthesis.md
plan: docs/superpowers/plans/2026-08-06-full-content-note-synthesis-plan.md
results: docs/results/2026-08-06-full-content-note-synthesis-results.md
trivial: false
auto_groomable: false
branch: feat/full-content-note-synthesis
pr: https://github.com/ethanhinson/llm-research-agent/pull/5
blocked_by:
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-06-full-content-note-synthesis.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-06-full-content-note-synthesis.md) |
| Plan | [2026-08-06-full-content-note-synthesis-plan.md](https://github.com/ethanhinson/llm-research-agent/blob/main/docs/superpowers/plans/2026-08-06-full-content-note-synthesis-plan.md) |
| Results | [2026-08-06-full-content-note-synthesis-results.md](https://github.com/ethanhinson/llm-research-agent/blob/main/docs/results/2026-08-06-full-content-note-synthesis-results.md) |
| PR | [#5](https://github.com/ethanhinson/llm-research-agent/pull/5) |
<!-- docket:artifacts:end -->

## Why

Vault notes don't fill out well — they are garbled snippet dumps, not research notes. Two confirmed root causes: (1) retrieval is shallow — `RawItem.body` is just the search backend's snippet (Tavily `content` / Brave `snippet`), which for academic sites is often citation-list junk with `[...]` elisions; (2) the writer does zero synthesis — `agent/writer.py` templates `body[:500]` into the sections and hardcodes "Why It's Gaining Traction". No LLM touches note content, so even perfect retrieval would still produce raw excerpts.

## What

For kept items scoring at or above a configurable threshold: fetch the full page (trafilatura; arXiv abstracts via API), then have Claude Haiku write the Summary / How It Works / Why It Matters sections grounded in the fetched text. Below-threshold items keep the cheap template path. A new `cli.py regenerate` command backfills existing vault notes in place (body sections only; frontmatter preserved) and regenerates the index. A `content_source: snippet|full` frontmatter field makes retrieval failures greppable per site.

## Scope

- New `agent/enricher.py` (full-text fetch + extraction, failure falls back to snippet)
- New `agent/synthesizer.py` (Haiku section synthesis, failure falls back to current template)
- `agent/writer.py` wired to synthesized sections; `agent/models.py` gains `content_source`
- `config.yml`: new `synthesis:` block (`enabled`, `min_score` default 6, `max_chars` default 8000)
- New `cli.py regenerate` command (`--date`, `--all`, `--min-score`) for backfill
- New `sweep --lookback-days N` flag to widen the crawl window into the past
- New dependency: trafilatura
- Tests for enricher, synthesizer, writer wiring, and the regenerate command
- **E2E acceptance run (required, live APIs)**: a backdated sweep (`--lookback-days 21`) plus `regenerate --all` over the existing vault; verify synthesized prose (no `[...]`/truncation/hardcoded lines), report `content_source` per domain, spot-read ≥5 notes — evidence recorded in the results file. The run's notes are real product output, not fixtures.

## Out of scope

- Search backend / query generation changes
- Tag or frontmatter schema redesign (change 0006 owns tags)
- Type/score re-classification (change 0005; `regenerate` preserves frontmatter so they compose)
- Cross-run page caching

## Open questions

## Reconcile log

### 2026-08-06 (docket-implement-next)

Reconciled the change + spec against current `main` code. Design holds; no obsolescence, no fundamental invalidation. Adjustments folded in:

- **Search backends drift (descriptive).** Spec's Problem section names "Brave/fallback snippet". Actual backends in `agent/fetchers/web_search.py` are **Tavily, Bing, SerpAPI** (no Brave). The enricher operates on `RawItem.url` and `content_source` is backend-agnostic, so the design is unaffected — noting the corrected backend set for the plan.
- **`sweep` command does NOT exercise search backends (substantive, plan-relevant).** `cli.py`'s `cmd_sweep` calls only `agent.scheduler.run_sweep`, which fetches HN/arXiv/RSS feeds — NOT `search_sweep` (Tavily/Bing/SerpAPI), which is currently wired only into the scheduler (`start`). The spec's E2E acceptance requires `python cli.py sweep --lookback-days 21` against **live search backends + Anthropic API**. The plan must thread `--lookback-days` such that the `sweep` command actually runs the search-backend path (e.g. run both `run_sweep` and `search_sweep`, or route the flag to a combined path) so live search backends are genuinely exercised, and thread `lookback_days` into `WebFetcher(lookback_days=…)` (already parameterized) and the search recency filters where present.
- **Live-key availability.** `.env` has `TAVILY_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`. `BING_SEARCH_API_KEY` / `SERPAPI_KEY` are absent, so **Tavily is the only live search backend** (Bing/SerpAPI self-skip). One live search backend satisfies the spec's "live search backends" — no deferral needed on that basis.
- **`trafilatura` not installed.** New dependency; build must add it to `pyproject.toml` and install it in `.venv`.
- **Vault scale drift (descriptive).** Spec says "~100 snippet-junk notes"; the vault now holds **323 notes** (research 97, releases 13, news 29, benchmarks 9, tutorials 8) under `vault/strategies/<subdir>/`, index at `vault/index.md`. Backfill scope is larger but the design is unchanged. Notes have parseable `## Sources` first-URL and full YAML frontmatter (list-form tags post-migration) that `regenerate` must preserve verbatim; existing notes lack `content_source` (regenerate adds it).
- **`reclassify` not built.** Spec says `regenerate` flags "mirror `reclassify`"; change 0005 (which owns `reclassify`) is still `proposed`/unbuilt, so no `reclassify` command exists yet. The `regenerate` flags (`--date`, `--all`, `--min-score`) are fully specified independently — treat the "mirror" as stylistic, not a dependency.
- **Latent pre-existing bug (out of scope).** `agent/scheduler.py:57` references undefined `reddit_threshold` in `run_sweep`; only triggers if a `reddit` source exists (none currently). Already flagged out-of-scope by an in-code comment (line 123). Not this change's fix — reported here, not minted (auto-capture disabled this run).

Related changes 4 (done — multi-type evaluation, added `content_type`/`score_label`/`category`/`tags` to `RawItem`), 5 (proposed — reclassify), 6 (proposed — topic tags) reviewed: `regenerate` preserves frontmatter, so it composes with 5/6 in either order as the spec's Out-of-scope states. No ADRs cited or produced yet.
