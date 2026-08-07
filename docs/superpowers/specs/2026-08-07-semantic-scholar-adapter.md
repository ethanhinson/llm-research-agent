<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0012 — Semantic Scholar keyword-search adapter](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/archive/2026-08-07-0012-semantic-scholar-adapter.md)**
<!-- docket:backlink:end -->

# Semantic Scholar Adapter — Design Spec

**Date:** 2026-08-07
**Status:** Approved

---

## Overview

Add a `SemanticScholarAdapter` on the `SourceAdapter` layer (change 0009) giving the agent keyword paper search beyond arXiv's category firehose — abstracts, citation counts, and tldr summaries in one call. Verified 2026-08-07: `https://api.semanticscholar.org/graph/v1/paper/search` is live; unauthenticated access uses a shared, aggressively-throttled pool (429s expected); a free API key (requested by email) gives a dedicated 1 RPS tier.

## Adapter — `agent/fetchers/semantic_scholar.py` (source: `s2`)

- `GET /graph/v1/paper/search` with `query` from config `sources.s2_queries` (reuse/mirror the arXiv keyword list by default), `fields=title,abstract,url,citationCount,tldr,publicationDate,externalIds`, year/date bounded to the lookback window, capped per query.
- Map to `RawItem`: title; body = tldr text or abstract (2000-char truncation like arXiv); url = S2 url (prefer arXiv link from `externalIds` when present, aiding cross-source dedup); `engagement` = citationCount; timestamp = publicationDate.
- **Rate handling:** honor `S2_API_KEY` env when present (header `x-api-key`); one retry with exponential backoff on 429; fail-soft after that (skip source, never abort the sweep). Sequential queries with a small inter-request sleep — this adapter must be a polite citizen of the shared pool when unkeyed.
- Config-gated: `sources.semantic_scholar: {enabled: true, max_per_query: 10}`; `s2_queries` defaulting to `sources.arxiv_queries` when unset.
- Register in `build_adapters` (`kind="sweep"`); `.env.example` gains optional `S2_API_KEY`.

## Testing

Mocked httpx: mapping (tldr-over-abstract, arXiv-url preference), lookback bounding, 429 retry-then-skip, keyed vs unkeyed header, factory gating. Live check at build time (one real query, counts recorded in results).

## Out of scope

- S2 Recommendations API loop and SPECTER2 embeddings (separate changes — see the embedding-prefilter and corroboration stubs).
- OpenAlex (candidate future adapter; needs a key decision from the human).
