<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0007 — Full-content retrieval + LLM note synthesis](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0007-full-content-note-synthesis.md)**
<!-- docket:backlink:end -->

# Full-content retrieval + LLM note synthesis — results

Change: #0007 · Branch: feat/full-content-note-synthesis · PR: (opened at close-out) · Plan: docs/superpowers/plans/2026-08-06-full-content-note-synthesis-plan.md · ADRs: none

## E2E acceptance run — DEFERRED (Anthropic API unavailable at build time)

The spec's "E2E validation (acceptance)" section requires a live end-to-end run as part of the
build. That run was **attempted and deferred**, not skipped — per the spec's explicit rule: *"If a
search backend or the API is unavailable at build time, the run is deferred to finalize, not skipped
silently."*

**What happened.** `python cli.py sweep --lookback-days 21` was run live from the feature worktree
with the repo's `.env` loaded (both `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` present and well-formed).
The search/fetch stages ran, but the pipeline hit a hard error at the evaluator's first Anthropic
call:

```
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error':
{'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the
Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}, 'request_id':
'req_011CdnCcpNv5Hi6i1MPAGBBd'}
```

This is an **account credit-balance** condition, not a code defect and not a missing key — the
request reached the API and returned a well-formed 400. Because the existing `agent/evaluator.py`
Anthropic calls are not fail-soft (pre-existing behavior, out of this change's scope — see Findings),
the sweep aborts before reaching enrichment/synthesis. `regenerate --all` shares the same Anthropic
dependency (via the synthesizer) and would defer for the same reason, so it was not separately run.

**Deferral status.** The live sweep + `regenerate --all` acceptance run must be completed once the
Anthropic account has credit. This can happen at the merge gate / during finalize.

## Verify (human) — required before/at merge

Run these once Anthropic API credit is available (the code is ready and unit-tested):

- [ ] `python cli.py sweep --lookback-days 21` completes; note count is plausible for a ~3-week window.
- [ ] `python cli.py regenerate --all` completes over the vault (currently 323 notes); capture the
      per-note report line (`regenerated / fetch-failed / skipped-below-threshold / preserved / errored`)
      and the `content_source per domain` tally.
- [ ] Above-threshold (score ≥ 6) notes contain synthesized prose: grep the vault for residual
      `[...]` elisions, mid-sentence `Read more` / truncation, the hardcoded `Engagement: N signals`
      line, and citation-list Summaries — there should be none in regenerated above-threshold notes.
- [ ] `content_source` distribution reported per domain; every `snippet` fallback listed with its
      domain (the first real answer to "which sites can't we retrieve?").
- [ ] Spot-read ≥ 5 notes across types (research / release / news / tutorial); paste one before/after
      pair below.
- [ ] `vault/index.md` regenerated and consistent with note frontmatter.

### Before/after pair (fill in at finalize)

Representative pre-synthesis note (real vault content, illustrates the problem this change fixes):

```
## Summary
Jul 8, 2026 — This paper presents a systematic study of data scaling, benchmarking, and reasoning
for VLM-based agents in this domain.

## How It Works
Jul 8, 2026 — This paper presents a systematic study ... To facilitate rigorous ...Read more

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.
```

(After: paste the regenerated note once the live run has produced it.)

## Findings

- **Anthropic account credit exhausted at build time.** Surfaced by the live E2E attempt (see above).
  Not a code issue; blocks the acceptance run until credit is added.
- **`agent/evaluator.py` is not fail-soft (pre-existing, out of scope).** A single Anthropic API
  outage raises out of `score()` and aborts the entire sweep — which is exactly what turned the
  credit-balance condition into a hard abort. This change deliberately made only the NEW
  enrichment/synthesis stages fail-soft (a sweep never fails because synthesis did); the evaluator's
  own resilience is a separate concern. Candidate follow-up.
- **Whole-branch review (independent) surfaced 1 BLOCKER + 2 SHOULD-FIX, all addressed:**
  - BLOCKER — the `regenerate` per-note loop was not fail-soft: `read_text` / YAML parse / `_rewrite`
    / `write_text` were unguarded, so one malformed note could abort the 323-note in-place run and
    leave the vault half-rewritten. Fixed: each note is wrapped in try/except and tallied as
    `errored`; the batch continues. Index regeneration is likewise guarded.
  - SHOULD-FIX — on a total synthesis failure (no full-text upgrade AND `synthesize()` returned `{}`),
    a note could be rewritten to a title-only body, silently dropping its existing content. Fixed:
    such notes are left untouched and tallied as `preserved`.
  - SHOULD-FIX — `yaml.safe_dump(sort_keys=True)` reorders frontmatter keys; verified semantically
    verbatim (all fields preserved, `content_source` added) and a no-op in practice since existing
    notes are already alphabetically ordered.
  - NICE-TO-HAVE (not changed; fail soft, low impact): arXiv id parsing ignores version suffixes
    (`v2`) and query strings; the Sources-URL regex truncates on a literal `)` in a URL.

## Follow-ups

- Complete the deferred live E2E acceptance run (sweep + `regenerate --all`) once Anthropic credit is
  available; fill in the Verify checklist and the before/after pair above.
- (Candidate change) Make `agent/evaluator.py` Anthropic calls resilient so a transient API
  outage degrades gracefully instead of aborting the whole sweep.
- (Candidate change) Fix the pre-existing undefined `reddit_threshold` reference in
  `agent/scheduler.py` `run_sweep` (dormant today; no reddit source configured).

_Auto-capture is disabled for this repo (`auto_capture.enabled: false`), so the two candidate changes
above are reported here rather than minted as stubs._
