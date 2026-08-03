---
name: live-testing-catches-what-mocks-miss
description: Unit tests with mocked fetchers/APIs missed three real integration bugs found only by running a live sweep
metadata:
  type: feedback
  promotion_state: candidate
  changes: [1, 2, 4]
  updated: 2026-08-03
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

**How to apply:** Before declaring a new agent/pipeline implementation done, run a live end-to-end sweep against real API endpoints with a small but realistic dataset. At minimum: verify item count is plausible for the time window, spot-check a few output notes for correct field values, and confirm Claude scored the full batch (no mass-defaulting to the fallback score). For search backends specifically: validate that at least one backend returns results for each fixed query anchor before relying on the hybrid query generator output. For any LLM-structured-output prompt: verify required fields are actually present in real model responses, not just in mock strings.
