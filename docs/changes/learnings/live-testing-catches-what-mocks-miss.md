---
name: live-testing-catches-what-mocks-miss
description: Unit tests with mocked fetchers/APIs missed three real integration bugs found only by running a live sweep
metadata:
  type: feedback
  promotion_state: candidate
  changes: [1, 2]
  updated: 2026-08-02
---

Unit tests with fully mocked fetchers and API clients passed clean but missed three real bugs that only appeared during a live `python cli.py sweep` run against real APIs.

**Why:** Mocks validate logic paths, not real API contracts or real data volumes.

**Findings from change 0001, PR #1:**

1. **HN Algolia API has no implicit date scope** — the API's `points>=N` filter returns all-time popular stories, not recent ones. "Stephen Hawking has died" (2018) passed the engagement filter. Fix: add `created_at_i>=<7-day cutoff>` to the `numericFilters` param.

2. **arXiv API 500s on `submittedDate:[X TO *]` range queries** — the `arxiv` client library's search query syntax does not support open-ended date ranges via Lucene `[X TO *]`. Fix: drop the query-level date filter; post-filter in Python by checking `result.published` against the lookback window after fetching.

3. **`max_tokens=512` too small to score 150+ items in one Claude call** — with 150 items the response was truncated mid-output and most items defaulted to novelty=5 with no category set. Fix: batch in groups of 20 items per API call (256 tokens is sufficient per batch).

**Findings from change 0002, PR #2:**

All 59 unit tests pass with mocked backends — deliberately so (user requested no live API calls during dev). The search pipeline (Tavily, Bing, SerpAPI) has not been smoke-tested against real endpoints yet. Known live-test gaps: actual search result shapes may differ from mocked fixtures; Tavily's `content` field truncation behavior is untested at real result lengths; SerpAPI's 0.5s post-call sleep may not be enough under burst conditions.

**How to apply:** Before declaring a new agent/pipeline implementation done, run a live end-to-end sweep against real API endpoints with a small but realistic dataset. At minimum: verify item count is plausible for the time window, spot-check a few output notes for correct field values, and confirm Claude scored the full batch (no mass-defaulting to the fallback score). For search backends specifically: validate that at least one backend returns results for each fixed query anchor before relying on the hybrid query generator output.
