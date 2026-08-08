<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0014 — Cross-source corroboration + citation-velocity signals](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0014-cross-source-corroboration-ranking.md)**
<!-- docket:backlink:end -->

# Cross-Source Corroboration + Citation-Velocity — Design Spec

**Date:** 2026-08-07
**Status:** Approved
**Change:** 0014

---

## Overview

Give the agent a **canonical item identity** and make it the dedup + corroboration key, replacing today's title-slug / fuzzy-title approach. This one primitive fixes three latent defects, turns `sources_count` into a real independent-corroboration signal that feeds evaluation and is surfaced in the vault, and — bundled per the grooming decision — adds a weekly Semantic Scholar **citation-velocity** re-poll that re-ranks sleeper papers whose citations are rising.

### Why (grounded in the current pipeline)

`scheduler.run_sweep` runs `fetch → dedup → topic → cross_validate → eval → write`. Reading it end to end surfaced that there is **no stable identity for an item**, and that single gap causes three distinct defects:

1. **Identical-title, same sweep → silent overwrite.** `Writer.write_note` names files `{date}-{slug(title)}.md`; a second source with the same title clobbers the first note file (its distinct URL/source lost). Dedup cannot catch it because `mark_seen` runs only *after* writing.
2. **Near-title, same sweep → duplicate notes.** Slightly different titles → different slugs → two files (the visible Kimi-K3 / Video-MME-v2 duplication in the vault).
3. **Across sweeps → corroboration lost.** The persisted dedup index drops a re-surfacing paper by exact URL / fuzzy title, so "seen on N sources over M days" never registers.

Separately, `cross_validate` already computes `sources_count`/`validated`, but it is **inert metadata** — the evaluator's score/validate prompts never see it, and it only appears as an index column.

### Staging (one change; land incrementally)

The grooming chose to keep everything in one change. The build should land it in this order, each independently testable:
**S1** canonical identity → **S2** intra-sweep collapse + corroboration (fixes defects 1–2) → **S3** cross-sweep corroboration in the persisted index (fixes defect 3) → **S4** eval signal → **S5** weekly citation-velocity re-poll.

Everything new is config-gated and fail-soft; with the new config sections absent, behavior is byte-identical to today.

---

## S1 — Canonical identity: `agent/canonical.py` (new)

`canonical_id(item: RawItem) -> str`, pure and dependency-free, with strict precedence:

1. **arXiv ID** — regex over `item.url` (`arxiv.org/abs/<id>`, `/pdf/<id>`, `huggingface.co/papers/<id>`) and an `[<id>]` prefix in `item.title`; strip the version suffix (`v1`/`v2`). → `arxiv:2410.12345`
2. **DOI** — from the URL path or S2-style identifiers, lowercased. → `doi:10.1145/...`
3. **Normalized URL** — lowercase host, drop scheme, leading `www.`, trailing slash, query string, fragment, and tracking params (`utm_*`, `ref`). → `url:host/path`
4. **Normalized title** (fallback for items with no stable URL — some releases/news) — lowercase, strip punctuation, collapse whitespace. → `title:...`

Add `canonical_id: str = ""` to `RawItem`; populate immediately after fetch (in `run_sweep` / `search_sweep`, before dedup).

## S2 — Intra-sweep collapse + corroboration (replaces `cross_validate`)

New `corroborate(items) -> list[RawItem]` (supersedes `agent/tools/cross_validate.py`):

- Group items by `canonical_id`. For each group: pick a **representative** (prefer an arXiv/DOI-keyed URL, else the first), set `sources_count = number of distinct `item.source` values`, `validated = sources_count >= 2`, and collect the per-source `(source, url, engagement)` tuples for the note's `## Sources` block. Return **one item per identity**.
- For the `title:`-fallback bucket **only**, retain a secondary fuzzy merge (`fuzz.ratio >= 85`, today's `cross_validate` threshold) so near-title non-paper items still corroborate — no regression versus current behavior.
- Wire in both sweeps: replace `cross_validate(after_topic)` with `corroborate(after_topic)`. Because one identity now yields one item and thus one note, defects 1–2 disappear as a side effect.

## S3 — Cross-sweep corroboration: `Deduplicator` + index schema v2

- **Index schema v2** (`vault/.index.json`): add `"items": { <canonical_id>: {"sources": [...], "first_seen": <ISO8601>, "note_path": <str>, "title": <str>} }`. Keep reading legacy `urls`/`titles` for migration; a v1 index (no `items`) loads as an empty map — no crash, no purge.
- Replace the URL/title dedup semantics with canonical-id logic:
  - **New identity** (no record): write the note; record `first_seen = now`, `sources`, `note_path`.
  - **Re-surface within the window** (`now − first_seen <= corroboration.window_hours`, default **72**) contributing a *new* source: **update the existing note** — bump `sources_count`, set `validated`, append the new source line to `## Sources` — do **not** create a new note; extend the index record's `sources`.
  - **Re-surface outside the window, or a source already counted:** skip (already documented), exactly as today.
- **Note-update mechanic:** `Writer.update_corroboration(note_path, sources_count, validated, new_source_line)` — targeted frontmatter rewrite (`sources_count`, `validated`) + `## Sources` append, **no body regeneration**; fail-soft (a bad/missing file logs and is skipped). Re-run `regenerate_index()` after updates so the index reflects new counts.
- **Config:** `corroboration: {enabled: true, window_hours: 72}`.

## S4 — Corroboration as an eval signal

In `Evaluator._score_batch` and `_validate_batch`, append `[corroborated by N sources]` to an item's line when `sources_count >= 2`. Prompt wording frames corroboration as **evidence of relevance/significance, not an automatic keep** (soft signal, no gate — matches the grooming decision). No change when `sources_count < 2`.

## S5 — Weekly citation-velocity re-poll: `agent/tools/citation_velocity.py` (new)

Runs **only on the weekly deep sweep** (`run_sweep(deep=True)`), after the normal sweep completes:

- Gather recent vault `research`/`benchmark` notes carrying a resolvable paper id (arXiv ID or DOI from the note's `## Sources` URL, or a stored id).
- Batch-query Semantic Scholar `POST /graph/v1/paper/batch` with `fields=citationCount` (reuses the 0012 integration; honor `S2_API_KEY`; one backoff on 429 then fail-soft skip; polite pacing). **S2 chosen over OpenAlex** (already wired, has `citationCount`, batch endpoint) — OpenAlex deferred.
- Per note, store frontmatter `citation_count` and `citation_checked: <date>`; compute `citation_delta` versus the previously stored value. Flag notes with `citation_delta >= citation_velocity.min_delta` as `rising: true`.
- `regenerate_index` gains a 📈 marker / sort tiebreak that surfaces rising papers — **re-rank only, no LLM re-score** (matches the grooming decision; keeps added cost near zero).
- **Config:** `citation_velocity: {enabled: true, min_delta: 25}`. Fully gated + fail-soft; disabled ⇒ no-op.

---

## Testing

- **`canonical.py`:** arXiv-id extraction across all URL shapes + `[id]` title prefix, version-suffix strip, DOI, URL normalization (utm/query/fragment/www/trailing-slash), title fallback, precedence ordering.
- **`corroborate`:** identity grouping, representative selection, `sources_count`/`validated`, title-fallback fuzzy merge, single-item passthrough.
- **`Deduplicator` v2:** v1-index migration (no `items` key), new-identity record, within-window re-surface updates note + index record, outside-window skip, already-counted source not double-counted.
- **`Writer.update_corroboration`:** frontmatter + `## Sources` append, body untouched, idempotent on re-apply.
- **Evaluator:** corroboration line present only when `sources_count >= 2` (assert via captured prompt); scores unaffected otherwise.
- **Citation-velocity:** S2 batch mapping, delta computation, `rising` threshold, 429 backoff-then-skip, weekly-only trigger, disabled no-op.
- **Live check at build:** one real S2 `/paper/batch` call, counts recorded in the results doc (per the 0012 live-check precedent; run the suite as `uv run python -m pytest` — see learnings/pytest-shim).

## Out of scope

- **OpenAlex** citation backend (S2 chosen; OpenAlex a possible future adapter).
- **LLM re-score** of risen papers (re-rank only).
- **Spend-gating** on corroboration (auto-keep / skip-eval for strongly-corroborated items) — grooming chose eval-signal, not a gate; a possible follow-up.
- **Backfilling** `canonical_id` / `citation_count` onto the existing ~172 vault notes — new notes only; a `regenerate`-style migration could follow.
- **Embedding-based semantic dedup** — that is change 0015's territory; identity here is exact-key + title-fuzzy fallback.

## Open questions

_All resolved during grooming (scope, corroboration effect, cross-sweep inclusion, citation-velocity backend); the design above reflects those decisions._
