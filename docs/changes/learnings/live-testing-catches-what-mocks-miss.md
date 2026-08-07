---
name: live-testing-catches-what-mocks-miss
description: Unit tests with mocked fetchers/APIs missed three real integration bugs found only by running a live sweep
metadata:
  type: feedback
  promotion_state: candidate
  changes: [1, 2, 4, 7, 8, 10]
  updated: 2026-08-07
---

Unit tests with fully mocked fetchers and API clients passed clean but missed three real bugs that only appeared during a live `python cli.py sweep` run against real APIs.

**Why:** Mocks validate logic paths, not real API contracts or real data volumes.

**Findings from change 0001, PR #1:**

1. **HN Algolia API has no implicit date scope** — the API's `points>=N` filter returns all-time popular stories, not recent ones. "Stephen Hawking has died" (2018) passed the engagement filter. Fix: add `created_at_i>=<7-day cutoff>` to the `numericFilters` param.

2. **arXiv API 500s on `submittedDate:[X TO *]` range queries** — the `arxiv` client library's search query syntax does not support open-ended date ranges via Lucene `[X TO *]`. Fix: drop the query-level date filter; post-filter in Python by checking `result.published` against the lookback window after fetching.

3. **`max_tokens=512` too small to score 150+ items in one Claude call** — with 150 items the response was truncated mid-output and most items defaulted to novelty=5 with no category set. Fix: batch in groups of 20 items per API call (256 tokens is sufficient per batch).

**Findings from change 0002, PR #2:**

All 59 unit tests pass with mocked backends — deliberately so (user requested no live API calls during dev). The search pipeline (Tavily, Bing, SerpAPI) has not been smoke-tested against real endpoints yet. Known live-test gaps: actual search result shapes may differ from mocked fixtures; Tavily's `content` field truncation behavior is untested at real result lengths; SerpAPI's 0.5s post-call sleep may not be enough under burst conditions.

**Findings from change 0004, PR #4:**

Mocked evaluator tests passed with all three passes returning pre-formatted strings. Live e2e run against real Claude API (Haiku) revealed that `[<subcategory>]` bracket notation in the score prompt caused the model to treat the subcategory as optional and omit it entirely for research items — the index showed an empty sub-category column. Fix: rewrote the format spec to use explicit per-type lines ("research items: `<n>. <score> <subcategory>` (REQUIRED, not optional)") and added a concrete multi-type example to the prompt.

**Broader rule:** LLM prompt format bugs are structurally invisible to mocked tests — mocks return perfectly formatted strings, so any ambiguity in the prompt specification only surfaces with a real model. Square brackets (`[]`) are universally read as "optional" by LLMs, even when the surrounding text says "required." For any structured output format with conditionally-required fields, verify against real API responses and prefer explicit, redundant phrasing over brevity.

## War story — 2026-08-06 (#7, PR #5)

The spec's live E2E acceptance run was **deferred, not completed**, at build time — and the blocker was a failure mode distinct from every prior one in this family. Both required keys (`ANTHROPIC_API_KEY`, `TAVILY_API_KEY`) were present and well-formed, so the "missing key → self-skip" path never fired. Instead the first live Anthropic call returned a well-formed `400 invalid_request_error`: *"Your credit balance is too low."* An **account-state** condition, not a code defect and not a missing credential — the request reached the API and was rejected on billing.

Two compounding lessons:

1. **A valid key is not a live-API guarantee.** Account state (credit balance, rate/quota tiers, org suspension) can block a paid-API acceptance run even when the credential is present and correct. A build's "live keys available?" precheck should treat a well-formed `400`/`402` billing error as *deferred, exactly like a missing key* — the spec's "defer to finalize, not skip silently" rule is what saved this: the deferral rode into the results file with the exact error and a filled-in human verify-checklist, instead of the run being quietly dropped.

2. **A non-fail-soft dependency turns a soft outage into a hard abort.** `agent/evaluator.py`'s Anthropic calls are not fail-soft, so the credit-balance `400` raised out of `score()` and aborted the *entire* sweep before enrichment/synthesis ran. This change deliberately made only its NEW enrichment/synthesis stages fail-soft; the evaluator's own resilience was out of scope and remains a candidate follow-up. Rule: when adding fail-soft to a *new* stage, note whether an *existing upstream* stage can still hard-abort the pipeline before the new stage is even reached — a fail-soft leaf behind a fail-hard trunk never gets exercised.

**How to apply:** Before declaring a new agent/pipeline implementation done, run a live end-to-end sweep against real API endpoints with a small but realistic dataset. At minimum: verify item count is plausible for the time window, spot-check a few output notes for correct field values, and confirm Claude scored the full batch (no mass-defaulting to the fallback score). For search backends specifically: validate that at least one backend returns results for each fixed query anchor before relying on the hybrid query generator output. For any LLM-structured-output prompt: verify required fields are actually present in real model responses, not just in mock strings.

## War story — 2026-08-07 (#8, PR #8)

Change 0008 (OpenRouter provider support) completed the live E2E acceptance run that #7 had to **defer** on the Anthropic credit-balance `400` — and the resolution was itself the lesson's payoff. Because the whole point of the change was a provider abstraction, the live sweep ran with `llm.provider: openrouter` (default model `anthropic/claude-haiku-4.5` via OpenRouter's OpenAI-compatible chat-completions API), which needs **no** Anthropic credit. `uv run python cli.py sweep --lookback-days 3` returned `Sweep complete. 93 new strategies documented.` (exit 0), and every LLM path was verified end to end against the real provider: dynamic query generation returned model-authored queries, the three-pass evaluator produced classified `type` + numeric `score` + `score_label` + research `category`, the synthesizer wrote grounded (non-template) `## Summary`/`## How It Works`/`## Why It Matters` sections with `content_source: full`, and 93 notes landed across the type subdirectories.

Lessons reinforced and added:

1. **A live run is what proves a provider swap actually works** — the mocked backend tests (injected `FakeLLM`) passed clean and validated logic paths, but only the real OpenRouter sweep proved the OpenAI-compatible request shape, the model id, and the end-to-end note pipeline all hold against a *different* real API. Mocks can't validate a second provider's contract any more than they could validate the first's.
2. **The #7 credit-balance blocker had a cheaper unblock than "top up the account": run the acceptance sweep through an alternate provider.** When a paid-API acceptance run is blocked on account state (billing/quota) rather than a code defect, a config-swappable provider abstraction lets the live verification run on whichever backend has credit — the deferral from #7 was cleared not by fixing Anthropic billing but by pointing the same pipeline at OpenRouter.
3. **Non-fatal enrichment/search warnings are expected and provider-orthogonal.** The run logged `enrich failed 403/404` on paywalled sources and `BING_SEARCH_API_KEY/SERPAPI_KEY not set` self-skips — all fail-soft, none an LLM/provider error. Reading the sweep log, separate provider errors (there were none) from these expected soft-degradations before concluding a live run failed.

## War story — 2026-08-07 (#10, PR #10)

Change 0010 (three new source adapters — HF daily papers, arXiv keyword search, GitHub trending — plus wired `SourceDiscovery`) completed its live sweep verification at build time **via OpenRouter** (`llm.provider: openrouter`, `anthropic/claude-haiku-4.5`), because the Anthropic key still has no credit — the #7/#8 credit-balance-`400` pattern, unblocked by the provider swap exactly as this finding prescribes, not by topping up billing. The live run is what the mocked adapter tests could not do: it validated each new adapter's **real API contract and data volume**, not just its logic path.

What only the live run proved:

1. **The mocked-payload shape assumptions held against the real APIs.** The worker had flagged the `HFPapersAdapter` daily-papers JSON shape as an assumption; against the real endpoint 46 items mapped cleanly (title, summary, `upvotes`→engagement, `publishedAt`→timestamp). Per-source raw fetch counts confirmed real volume: HF papers 46, arXiv keyword search 10 (2 queries × cap 5), GitHub trending 100 — none of which a mock could have surfaced.
2. **Every new source reached the funnel and the vault write path end-to-end.** The full minimal-scope sweep kept **134 items** through fetch → dedup → topic filter → cross-validate → OpenRouter evaluation → write (`hackernews` 20, `arxiv` 29, `hf-papers` 8, `github` 77), 128 notes written, and the `discover-sources` path appended its dated `## Suggested (pending review)` section to `sources.md`. Only expected fail-soft soft-degradations (paywalled enrich, missing search-backend keys) appeared — no LLM/provider errors — reinforcing lesson #3 above about reading the sweep log.
3. **Reinforced #2's unblock-via-provider-swap rule for a second change in a row.** The provider abstraction from #8 is now the standing mechanism for running paid-API acceptance sweeps while Anthropic billing is blocked — 0010's verification never touched Anthropic. (Adjacent, unminted: `agent/evaluator.py`'s Anthropic path is still non-fail-soft, so a credit-balance `400` there would hard-abort a sweep before the new fail-soft sources are reached — orthogonal here because the live run used OpenRouter, but the same latent fail-hard trunk flagged in the #7 war story.)
