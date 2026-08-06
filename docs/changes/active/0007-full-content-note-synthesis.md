---
id: 7
slug: full-content-note-synthesis
title: Full-content retrieval + LLM note synthesis
status: in-progress
priority: high
type: feat
created: 2026-08-06
updated: 2026-08-06
claimed_at: 2026-08-06T21:09:13Z
depends_on: []
related: [4, 5, 6]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-06-full-content-note-synthesis.md
plan:
results:
trivial: false
auto_groomable: false
branch: feat/full-content-note-synthesis
pr:
blocked_by:
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-06-full-content-note-synthesis.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-06-full-content-note-synthesis.md) |
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
