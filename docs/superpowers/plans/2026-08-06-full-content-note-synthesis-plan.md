<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0007 — Full-content retrieval + LLM note synthesis](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0007-full-content-note-synthesis.md)**
<!-- docket:backlink:end -->

# Implementation Plan — Full-content retrieval + LLM note synthesis (change 0007)

Spec: `docs/superpowers/specs/2026-08-06-full-content-note-synthesis.md` (on `docket` branch).
Change: 0007 · Branch: `feat/full-content-note-synthesis` · cut from `origin/main`.

> **Plan authored via the `auto` fallback** — the resolved plan skill `superpowers:writing-plans`
> was not invocable on this machine (missing-skill rule → degrade to auto + warn).

## Context carried from reconcile (read before starting)

- **Backends:** actual search backends are Tavily / Bing / SerpAPI (no Brave). Only `TAVILY_API_KEY`
  is present in `.env` (plus `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`); Bing/SerpAPI self-skip.
- **`cli.py sweep` gap:** `cmd_sweep` currently calls only `agent.scheduler.run_sweep` (HN/arXiv/RSS
  feeds) — NOT `search_sweep` (Tavily/Bing/SerpAPI). The spec's E2E `sweep --lookback-days 21`
  requires live **search backends**. Task 6 must make `sweep` exercise the search path.
- **Haiku model constant:** `claude-haiku-4-5-20251001` (see `agent/evaluator.py:7`). Reuse it.
- **Evaluator is the synthesizer's pattern reference:** structured plain-text prompt, `_call()`
  wrapper (`messages.create`, reads `message.content[0].text`), regex-tolerant parsing,
  fail-soft. Mirror it in `agent/synthesizer.py`.
- **Writer:** notes at `vault/strategies/<TYPE_DIRS subdir>/`, index at `vault/index.md`.
  `writer.py` templates `body[:500]` (`## How It Works`), first sentence (`## Summary`), and a
  hardcoded `## Why It's Gaining Traction`. `NOTE_TEMPLATE` must gain a `## Why It Matters`
  section and accept synthesized sections.
- **Vault scale:** 323 existing notes (research 97, releases 13, news 29, benchmarks 9,
  tutorials 8). Notes carry full YAML frontmatter (list-form tags) + a `## Sources` first URL,
  and lack `content_source` (regenerate adds it). Regenerate MUST preserve frontmatter verbatim.
- **Learnings (blocking read applied):** mocks miss real API-contract and prompt-format bugs;
  LLMs read `[brackets]` as "optional" — use explicit, redundant phrasing in the synthesis
  prompt and verify required output fields against the REAL model, not mocks. This is why the
  live E2E run (Task 9) is part of the build, not optional.

## Conventions

- TDD: each code task writes failing tests first, then implements to green.
- Test runner: `.venv/bin/python -m pytest` (dev deps already installed). Add tests under `tests/`.
- Every stage is **fail-soft**: enrichment failure → keep snippet; synthesis failure → template
  fallback. A sweep/regenerate NEVER aborts because enrichment or synthesis failed on one item.
- Commit per task (the build role commits each task).

---

## Task 1 — `content_source` on `RawItem`

**Files:** `agent/models.py`, `tests/` (extend an existing model/smoke test or add a small one).

1. Add field `content_source: str = "snippet"` to `RawItem` (after `tags`), documented `snippet | full`.
2. Test: a fresh `RawItem(...)` defaults `content_source == "snippet"`; it can be set to `"full"`.

**Done when:** field exists, default is `"snippet"`, tests green.

---

## Task 2 — `synthesis:` config block

**Files:** `config.yml`.

1. Add:
   ```yaml
   synthesis:
     enabled: true
     min_score: 6
     max_chars: 8000
   ```
2. No test needed beyond confirming `load_config()` still parses (covered by existing config tests /
   a smoke assertion). Keep the block self-contained; downstream code reads it with `.get()` defaults
   (`enabled` True, `min_score` 6, `max_chars` 8000) so a missing block degrades safely.

**Done when:** `config.yml` has the block; `cli.load_config()` parses without error.

---

## Task 3 — `agent/enricher.py` (full-text fetch + extraction)

**Files:** new `agent/enricher.py`, new `tests/test_enricher.py`. Dependency: add `trafilatura` to
`pyproject.toml` `dependencies` and install into `.venv` (`.venv/bin/pip install trafilatura` or
`uv pip install trafilatura`).

Design a `ContentEnricher` class:

- `__init__(self, max_chars: int = 8000)`.
- `enrich(self, item: RawItem) -> RawItem` — mutates/returns the item:
  - **arXiv branch:** if the URL is an arXiv URL (`arxiv.org/abs/…` or `/pdf/…`), fetch the abstract
    via the arXiv API (reuse the approach in `agent/fetchers/arxiv.py` — the `arxiv` library is a
    declared dep). On success set `item.body = abstract` (capped), `item.content_source = "full"`.
  - **Generic branch:** `httpx.get(url, timeout=…, follow_redirects=True, headers={"User-Agent": <browser-ish>})`,
    then `trafilatura.extract(html)`. If the response is non-HTML (`content-type` not text/html) skip
    extraction.
  - **Cap:** truncate extracted text to `max_chars`.
  - **Min-length guard:** if extraction yields `< 400` chars (or fetch/extract raised, or non-HTML),
    KEEP the original snippet body and leave `content_source = "snippet"`. Never raise out of `enrich`.
- Optionally a helper `enrich_all(items)` looping `enrich` with per-item try/except.

**Tests (`tests/test_enricher.py`, mock httpx + arxiv):**
1. Generic happy path — mocked HTML → trafilatura returns >400 chars → `body` replaced, `content_source == "full"`, capped at `max_chars`.
2. arXiv branch — arXiv URL → abstract path taken, `content_source == "full"`.
3. Fetch failure (httpx raises) → body unchanged, `content_source == "snippet"`, no exception.
4. Sub-400-char extraction → falls back to snippet, `content_source == "snippet"`.
5. Non-HTML content-type → falls back to snippet.

**Done when:** enricher exists, `trafilatura` declared+installed, all tests green.

---

## Task 4 — `agent/synthesizer.py` (Haiku section synthesis)

**Files:** new `agent/synthesizer.py`, new `tests/test_synthesizer.py`.

Mirror `agent/evaluator.py` structure:

- `MODEL = "claude-haiku-4-5-20251001"` (import or restate; keep a single source if easy).
- `class NoteSynthesizer`: `__init__(self, api_key: str | None = None)` → `anthropic.Anthropic(api_key=…)`.
- `_call(prompt) -> str` mirroring evaluator's (reads `message.content[0].text`, empty-safe).
- `synthesize(self, item: RawItem) -> dict` returning `{"summary", "how_it_works", "why_it_matters"}`:
  - Build a prompt with title + enriched `body` (already capped) + `content_type`/`score`/
    `score_label`/`validated`/`engagement`/`sources_count`.
  - Ask for THREE labelled sections in structured plain text. **Prompt discipline (learnings):**
    explicit, redundant field labels; NO `[optional]`-style bracket notation; give a short concrete
    example of the exact output shape so the model can't treat a section as optional. Instruct:
    ground strictly in the provided text; if input is thin/snippet-only, stay brief, do not invent.
  - Parse with regex-tolerant section extraction (mirror evaluator's `re.MULTILINE` approach),
    keyed on the three section headers.
  - **Fail-soft:** on API error OR unparseable output, return `{}` (or a sentinel) so the writer
    uses its template fallback. Never raise.

**Tests (`tests/test_synthesizer.py`, mock the anthropic client like `test_evaluator.py`):**
1. Prompt assembly includes title + body + type/score.
2. Well-formed mocked response parses into all three sections.
3. API failure (client raises) → returns empty/sentinel, no exception.
4. Partial/garbled response → returns what parsed, missing sections empty (writer falls back per-section or wholesale — pick one and test it).

**Done when:** synthesizer exists, tests green, prompt uses explicit (non-bracket) required-field phrasing.

---

## Task 5 — Wire synthesized sections into the writer

**Files:** `agent/writer.py`, `tests/test_writer.py` (extend).

1. Update `NOTE_TEMPLATE`: rename `## Why It's Gaining Traction` → `## Why It Matters`; make the three
   body sections (`Summary`, `How It Works`, `Why It Matters`) accept synthesized values, and add a
   `content_source: {content_source}` line to the frontmatter.
2. `Writer.write_note` gains an optional synthesized-sections argument (e.g. `sections: dict | None`).
   When `sections` is provided and non-empty, use them; otherwise fall back to the CURRENT template
   behavior (`body[:500]`, first-sentence summary, engagement/validation line) — so below-threshold
   items and synthesis failures keep the cheap path. Write `item.content_source` into frontmatter.
3. Keep `regenerate_index` working; if the index reads any changed field, keep it consistent.

**Tests (extend `tests/test_writer.py`):**
1. With synthesized `sections`, the note body contains the synthesized Summary/How It Works/Why It
   Matters and NO hardcoded "Engagement: N signals" line.
2. Without `sections` (below threshold / failure), the note keeps the legacy template output.
3. `content_source` appears in frontmatter with the item's value.

**Done when:** writer emits synthesized sections when given, legacy path otherwise, `content_source` in frontmatter, tests green.

---

## Task 6 — Pipeline gating + `sweep --lookback-days`

**Files:** `agent/scheduler.py`, `cli.py`, `tests/test_cli.py` + `tests/test_scheduler.py`/`tests/test_search_sweep.py` (extend).

**6a — thread enrichment+synthesis into the sweep pipelines.** In `run_sweep` AND `search_sweep`,
after `evaluator.score` and the `keep` filter, before writing:
- Read the `synthesis` config (`enabled`, `min_score`, `max_chars`). Thread it in from `cli.py`
  (add a `synthesis_cfg`/params argument to the sweep functions; default to enabled/6/8000).
- For each kept item with `score >= min_score` and `enabled`: `ContentEnricher(max_chars).enrich(item)`
  then `NoteSynthesizer(api_key).synthesize(item)`; pass the sections to `writer.write_note(item, sections)`.
- Below threshold or `enabled: false`: `writer.write_note(item)` (legacy path, no fetch/LLM).
- Keep everything fail-soft (per-item try/except; a failure writes the legacy note).

**6b — `--lookback-days` (and `--date`) on `sweep`.** Add `--lookback-days N` and `--date YYYY-MM-DD`
to the `sweep` subparser. Thread `lookback_days` into `run_sweep` → `WebFetcher(feeds=feeds,
lookback_days=N)` (already parameterized). Thread `--date` into `Writer(vault_path, date=…)`.

**6c — make `sweep` exercise search backends (reconcile fix).** `cmd_sweep` must run the search-backend
path so the live E2E genuinely hits live search backends. Simplest: after `run_sweep`, also call
`search_sweep(vault_path, index_path, search_cfg, api_key)` (pull `search_cfg = cfg.get("search", {})`),
and thread `lookback_days` into search recency where a backend supports it (Tavily has no explicit
lookback param — leave a comment; Bing uses `freshness`). Sum both counts in the printed summary.
Keep both fail-soft so one backend's outage doesn't abort the sweep.

**Tests:**
1. `test_cli`: `sweep --lookback-days 21` parses and threads `lookback_days=21` to the fetcher(s)
   (mock `run_sweep`/`search_sweep`; assert kwargs).
2. `test_cli`: `sweep` invokes the search path (assert `search_sweep` called).
3. scheduler/search-sweep test: kept item ≥ min_score gets enriched+synthesized (mock enricher/synth,
   assert `write_note` received sections); below-threshold item takes legacy path.

**Done when:** `sweep --lookback-days N` works, exercises search backends, gates enrichment/synthesis by score, tests green.

---

## Task 7 — `cli.py regenerate` (backfill)

**Files:** `cli.py`, `tests/test_cli.py` (extend). Likely a small helper module or a function in
`cli.py`/`agent/` for the per-note rewrite (keep it testable).

Add a `regenerate` subcommand with flags `--date YYYY-MM-DD`, `--all`, `--min-score N`.

Per note under `vault/strategies/**/*.md` (filtered by `--date` prefix, or all with `--all`):
1. Parse frontmatter (yaml) + extract the first `## Sources` URL.
2. If the note's existing `score` (frontmatter) `>= min_score` (default from config `synthesis.min_score`
   or `--min-score`): re-fetch via `ContentEnricher`, re-synthesize via `NoteSynthesizer`, rewrite the
   **body** sections (`## Summary`, `## How It Works`, `## Why It Matters`) in place. If fetch fails,
   re-synthesize from whatever body text exists (thin-but-coherent). Below threshold → skip (report).
3. **Preserve frontmatter verbatim**, and ADD/UPDATE `content_source`. Do NOT touch type/score/tags/
   category/validated/status. Preserve `## Sources` and `## Related` sections.
4. After processing, regenerate `vault/index.md` (`Writer.regenerate_index`).
5. Print a per-note report: `regenerated | fetch-failed | skipped-below-threshold`, plus a
   `content_source` per-domain tally.

**Tests (`test_cli.py`, mock enricher+synthesizer, use a tmp vault):**
1. In-place rewrite preserves ALL frontmatter fields and adds `content_source`.
2. `## Sources`/`## Related` preserved; only the three body sections change.
3. Below-`min_score` note is skipped (report line), body untouched.
4. Index regenerated.
5. Old `## Why It's Gaining Traction` heading replaced by `## Why It Matters` (or handled) on rewrite.

**Done when:** `regenerate --all` / `--date` / `--min-score` work, frontmatter preserved, index regenerated, tests green.

---

## Task 8 — Full suite green + housekeeping

1. `.venv/bin/python -m pytest -q` — entire suite green.
2. Confirm `trafilatura` in `pyproject.toml` and `uv.lock` refreshed if the repo pins the lock
   (run `uv lock` if `uv` manages it; otherwise note it).
3. No stray debug prints; fail-soft paths log a `[warn]` line consistent with existing style.

**Done when:** whole suite green, dependency recorded.

---

## Task 9 — E2E acceptance run (REQUIRED, live APIs) + results file

Per the spec's "E2E validation (acceptance)" — this is part of the build, not optional. Run from the
**feature worktree** with the repo `.env` loaded (Tavily + Anthropic keys present).

1. **Live backdated sweep:** `.venv/bin/python cli.py sweep --lookback-days 21`
   (live Tavily search backend + live Anthropic Haiku). Capture stdout (note count, any `[warn]`).
2. **Live backfill:** `.venv/bin/python cli.py regenerate --all` over the existing vault. Capture the
   per-note report + `content_source` per-domain tally.
3. **Acceptance checks (record all in the results file):**
   - Above-threshold notes contain synthesized prose: grep the vault for residual `[...]` elision,
     mid-sentence `Read more`/truncation, the hardcoded `Engagement: N signals` line, citation-list
     Summaries — there should be none in regenerated above-threshold notes.
   - `content_source` distribution per domain; list every `snippet` fallback with its domain.
   - Spot-read ≥5 notes across types (research/release/news/tutorial); paste one before/after pair.
   - `vault/index.md` regenerated and consistent with frontmatter.
4. **Deferral rule:** if Tavily OR the Anthropic API is genuinely unavailable at run time, record the
   deferral in the results file per the spec (do NOT skip silently) and surface it in the run report.

**Results file:** write `docs/results/2026-08-06-full-content-note-synthesis-results.md` in the feature
worktree (from the results template) with the acceptance evidence, `content_source` tally, and the
before/after pair. Commit it on the feature branch. (The `results:` FIELD is set on `docket` at step 7.)

**Done when:** the live sweep + regenerate ran (or a deferral is recorded), acceptance evidence is in
the results file, committed on the feature branch.

---

## Out of scope (do not do)

- Search backend / query-generation changes; tag/frontmatter schema redesign (0006); type/score
  re-classification (0005); cross-run page caching.
- The pre-existing undefined `reddit_threshold` in `run_sweep` (flagged, not this change's fix).
