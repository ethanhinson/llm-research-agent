<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0007 — Full-content retrieval + LLM note synthesis](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0007-full-content-note-synthesis.md)**
<!-- docket:backlink:end -->

# Full-content retrieval + LLM note synthesis

## Problem

Vault notes read as garbled snippet dumps rather than research notes. Two root causes, confirmed in code:

1. **Shallow retrieval.** `agent/fetchers/web_search.py` sets `RawItem.body` to the search backend's snippet — Tavily's `content` field (line 41) or Brave/fallback `snippet` (lines 76, 116). Snippets are a few hundred characters, contain `[...]` elision markers, and for academic/paywalled pages are often navigation or citation-list junk (e.g. the OUP "survey on multimodal LLMs" note whose Summary is "Wang Z et al."). RSS items (`agent/fetchers/web.py:34`) fare somewhat better (feed summary, capped at 2000 chars) but are still not the article.
2. **No synthesis.** `agent/writer.py:74-76` templates raw text directly: `## How It Works` is `body[:500]`, `## Summary` is the first sentence of that, and `## Why It's Gaining Traction` is a hardcoded string ("Engagement: N signals. Cross-source validated: X."). No LLM ever touches note content, even though the pipeline already calls Claude Haiku in the evaluator and search-query generator.

Fixing retrieval alone still yields raw excerpts; fixing synthesis alone leaves it summarizing citation junk. Both are needed.

## Design

Two new pipeline stages between evaluation and writing, gated by score to bound cost.

### 1. Content enrichment (full-text fetch)

New `agent/enricher.py` with a `ContentEnricher` that, for each kept item at or above the synthesis threshold, replaces the snippet body with extracted full-page text:

- **arXiv URLs**: use the abstract via the arXiv API (matching the existing `agent/fetchers/arxiv.py` approach) — abstracts are clean and sufficient.
- **Everything else**: `httpx` GET (timeout, redirects, browser-ish User-Agent) + **trafilatura** (new dependency) to extract main article text from the HTML.
- Cap extracted text at `synthesis.max_chars` (default 8000) before it reaches the LLM.
- **Failure posture**: fetch error, non-HTML content, or extraction yielding under ~400 chars ⇒ keep the original snippet body and mark the item so the writer knows synthesis input is thin. Enrichment failures never drop an item.

`RawItem` gains a `content_source: str = "snippet"` field (`"snippet" | "full"`) recorded into note frontmatter for observability — this directly answers "which sites are we failing to retrieve?" by making it greppable across the vault.

### 2. LLM note synthesis

New `agent/synthesizer.py` calling Claude Haiku (`claude-haiku-4-5-20251001`, same model as the evaluator), one call per note, input = title + enriched body + type/score/validation metadata. Output = the three body sections, replacing the template fill-ins:

- `## Summary` — 2–3 sentences, what this is and the key claim/result.
- `## How It Works` — a short grounded explanation (prose or bullets) of the technique/release/finding. Instructed to state only what the source text supports; if input is snippet-only, stay brief rather than pad.
- `## Why It Matters` — replaces the hardcoded "Why It's Gaining Traction": one short grounded paragraph on why a practitioner should care, folding in the engagement/validation signals instead of printing them raw.

Parsing follows the evaluator's existing pattern (structured plain-text output, regex-tolerant parsing). On API failure: fall back to the current template body — a sweep never fails because synthesis did.

### 3. Cost gate

New `config.yml` block:

```yaml
synthesis:
  enabled: true
  min_score: 6        # matches the evaluator's "6+ warrants keeping" guidance
  max_chars: 8000
```

Items scoring below `min_score` keep the current cheap template path (no fetch, no LLM call). `enabled: false` disables both stages entirely.

### 4. Backfill of existing notes

New `cli.py regenerate` command (flags mirroring `reclassify`: `--date`, `--all`, plus `--min-score`):

- Walk existing vault notes; for each, read frontmatter + the first `## Sources` URL.
- Re-fetch via the enricher, re-synthesize the three body sections, rewrite the note body **in place** — frontmatter (type, score, tags, category, validated, status) is preserved untouched, plus the new `content_source` field is added.
- Notes whose fetch fails and whose existing body is snippet junk are still re-synthesized from whatever body text exists (thin but coherent beats garbled).
- Regenerate `vault/index.md` at the end; print a per-note report (regenerated / fetch-failed / skipped-below-threshold).

Backfill respects the same `min_score` gate against the note's existing score.

### 5. Backdated sweeps (`--lookback-days`)

`cli.py sweep` currently exposes only `--deep`; there is no way to widen the crawl window. Add `--lookback-days N` (and optional `--date YYYY-MM-DD` for the note date stamp), threaded to `WebFetcher(lookback_days=…)` and to the search fetchers' recency filters where they have one. This exists primarily so the E2E validation below can crawl a few weeks of past content, but it is a generally useful knob (e.g. re-seeding the vault after downtime).

## Out of scope

- Changing search backends or query generation.
- Note schema/frontmatter redesign, tag changes (change 0006 owns tags).
- Re-classification of types/scores — change 0005 owns that; `regenerate` deliberately preserves frontmatter so the two compose in either order.
- Caching fetched pages across runs.

## Testing

- `tests/test_enricher.py` — extraction happy path (mocked httpx), arXiv branch, failure fallback to snippet, min-length guard.
- `tests/test_synthesizer.py` — prompt assembly, response parsing, API-failure fallback (mocked anthropic client, matching existing evaluator test style).
- `tests/test_writer.py` — extended: synthesized sections land in the template; below-threshold items keep the old path.
- `tests/test_cli.py` — `regenerate` command with mocked enricher/synthesizer: in-place rewrite preserves frontmatter, index regenerated; `sweep --lookback-days` threads the window to the fetchers.

## E2E validation (acceptance — real APIs, part of this change's build)

Unit tests alone don't prove the notes actually read well; the build MUST finish with a live end-to-end run of the analysis, using backdated crawling so the run itself produces real vault value:

1. **Backdated live sweep**: `python cli.py sweep --lookback-days 21` against live search backends + the Anthropic API — crawls roughly three weeks into the past so the run writes a meaningful batch of new notes rather than an empty same-day window.
2. **Live backfill**: `python cli.py regenerate --all` over the existing ~100 snippet-junk notes.
3. **Acceptance checks on the resulting vault** (recorded in the change's results file):
   - Above-threshold notes contain synthesized prose: no `[...]` elision markers, no mid-sentence truncation, no hardcoded "Engagement: N signals" line, no citation-list Summaries.
   - `content_source` distribution reported per domain — the majority of above-threshold notes should be `full`; every `snippet` fallback is listed with its domain, giving the first real answer to "which sites can't we retrieve?".
   - Spot-read at least 5 notes across types (research/release/news/tutorial) and paste one before/after pair into the results file.
   - `vault/index.md` regenerated and consistent with the note frontmatter.

The E2E run costs real API calls by design — the score gate bounds it, and the resulting notes are the product, not a fixture. If a search backend or the API is unavailable at build time, the run is deferred to finalize, not skipped silently.

## Decisions taken

- **trafilatura over Tavily Extract / `include_raw_content`**: works for every source (RSS, HN, Brave, Tavily), no extra API cost, no backend coupling. Tavily raw-content can be a later optimization.
- **Haiku over a bigger model**: consistent with the rest of the pipeline; synthesis is grounded summarization, not open-ended reasoning. Model is a constant next to the evaluator's, upgradeable in one place.
- **Per-note synthesis calls (no batching)**: the score gate keeps volume small; per-note calls keep parsing trivial and failures isolated.
