---
id: 14
slug: cross-source-corroboration-ranking
title: Cross-source corroboration + citation-velocity signals
status: in-progress
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-08
depends_on: []
related: [10, 12]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-07-cross-source-corroboration-ranking-design.md
plan: docs/superpowers/plans/2026-08-08-cross-source-corroboration-ranking-plan.md
results:
trivial: false
auto_groomable: false
branch: feat/cross-source-corroboration-ranking
pr:
blocked_by:
claimed_at: 2026-08-08T03:52:28Z
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-07-cross-source-corroboration-ranking-design.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-cross-source-corroboration-ranking-design.md) |
| Plan | [2026-08-08-cross-source-corroboration-ranking-plan.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/cross-source-corroboration-ranking/docs/superpowers/plans/2026-08-08-cross-source-corroboration-ranking-plan.md) |
<!-- docket:artifacts:end -->

## Why

With ~10 sources feeding the funnel, the strongest cheap quality signal is *independent corroboration*: the same paper/link surfacing on 2+ sources within ~72h. The blocker is that items have **no canonical identity** — and reading the pipeline (`fetch → dedup → topic → cross_validate → eval → write`) shows that single gap causes three defects: identical-title items in one sweep silently overwrite each other's note file; near-title items produce duplicate notes; and cross-sweep re-surfaces are dropped by the persisted index, so corroboration-over-days never registers. `cross_validate` does compute `sources_count`, but it is inert metadata the evaluator never sees. Relatedly, citation velocity (weekly Δ of citationCount) can resurface sleeper hits the first-pass eval scored low.

## What changes

Introduce a canonical item identity (`arXiv-ID > DOI > normalized-URL > normalized-title`) and make it the dedup + corroboration key. Group by identity to collapse intra-sweep duplicates to one note and count distinct sources (`sources_count`/`validated`); persist `{canonical_id: {sources, first_seen, note_path}}` so a re-surface within a 72h window updates the existing note instead of being dropped; feed `sources_count` into the evaluator's score/validate prompts as a soft signal and surface it in the vault. Bundled: a weekly (deep-sweep) Semantic Scholar citation-velocity re-poll that records `citation_count`/Δ and re-ranks rising papers in the index (no LLM re-score). All config-gated and fail-soft. Design + staging in the linked spec.

## Out of scope

- OpenAlex citation backend (S2 chosen); LLM re-score of risen papers (re-rank only).
- Spend-gating / auto-keep on corroboration (grooming chose eval-signal, not a gate).
- Backfilling canonical_id / citation_count onto existing vault notes; embedding-based semantic dedup (that is change 0015).

## Open questions

_Resolved during grooming (scope, corroboration effect, cross-sweep inclusion, citation-velocity backend) — see the linked spec._

## Reconcile log

### 2026-08-08 — reconciled against current `main` (tip 832adca)

Re-read the spec against the live pipeline; the design holds with no scope drift and no work already done elsewhere. Confirmed:

- **Pipeline shape intact.** Both `scheduler.run_sweep` and `scheduler.search_sweep` run `fetch → dedup(`Deduplicator.is_duplicate`) → topic(`is_relevant`) → `cross_validate(after_topic)` → `Evaluator.score` → `_write_kept``. S2's replacement point (`cross_validate` → `corroborate`) and S4's eval-signal point are exactly where the spec says.
- **`RawItem`** (`agent/models.py`) already carries `validated` + `sources_count` (defaults `False`/`1`); it has **no** `canonical_id` — S1 adds it as specified.
- **Dedup index** is `vault/.index.json` with schema `{urls, titles}` (`Deduplicator._load`), wired from `cli.py` `INDEX_PATH`. S3's v2 `items` map + v1-migration (legacy keys read, absent `items` → empty map) is accurate. `cli.py cmd_status` also reads `.index.json["urls"]` — S3 must keep the legacy keys present so status does not break.
- **`Writer.regenerate_index()`** writes the **markdown** `vault/index.md` (distinct from the JSON dedup index); S5's "📈 marker / sort tiebreak" lands there. `write_note` names files `{date}-{slug(title)}.md` — the S2 collapse (one item per identity) is what removes defects 1–2.
- **S2 reuse (S5).** `agent/fetchers/semantic_scholar.py` uses the `/paper/search` endpoint with a one-shot 429 backoff + `S2_API_KEY` header + polite sleep. S5's citation-velocity re-poll needs the **`/paper/batch`** endpoint (different), so it is a new `agent/tools/citation_velocity.py` reusing the same key/backoff/pacing patterns — not the search adapter.
- **Weekly gating** for S5 uses the existing `deep: bool` param on `run_sweep` (already threaded from `cli.py`/`start_scheduler`).
- **Config threading.** New `corroboration` and `citation_velocity` sections must be read in `cli.py cmd_sweep`/`cmd_start` and passed into `run_sweep`/`search_sweep` alongside the existing `sources_cfg`/`synthesis_cfg`/`llm_cfg`; absent ⇒ byte-identical behavior (fail-soft, config-gated).
- **Dependencies:** `depends_on: []` satisfied; related changes 0010 and 0012 are both `done` (merged). No ADRs bear on this change (only ADR-0001 exists: LLM-provider abstraction).
- **Build/test note (learnings):** run the suite as `uv run python -m pytest` after `uv sync --extra dev` (pytest-shim finding). For the S5 live check, an S2 429 from the unkeyed pool is a *valid fail-soft verification*, not a deferral (live-testing finding); route any LLM live check through the repo-default OpenRouter provider.

Verdict: **build-ready, design valid.** No obsolescence, no fundamental invalidation. AUTO_CAPTURE disabled — no adjacent follow-ups minted this pass; none surfaced beyond the already-scoped out-of-scope items (OpenAlex adapter, LLM re-score, spend-gating, vault backfill).
