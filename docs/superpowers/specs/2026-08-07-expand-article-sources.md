<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0010 — Expand article sources — HF daily papers, arXiv keyword search, GitHub trending, wired SourceDiscovery](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/archive/2026-08-07-0010-expand-article-sources.md)**
<!-- docket:backlink:end -->

# Expand Article Sources — Design Spec

**Date:** 2026-08-07
**Status:** Approved

---

## Overview

Widen the article-discovery net with three new sources — **Hugging Face daily papers**, **arXiv keyword search**, and **GitHub trending repos** — each implemented as a `SourceAdapter` (per change 0009's layer; this change `depends_on: [9]`), plus **wiring the currently-dead `SourceDiscovery` tool into the loop** so the system proposes new sources for human review instead of suggesting into the void.

## New adapters

### 1. `HFPapersAdapter` — `agent/fetchers/hf_papers.py` (source: `hf-papers`)

- `GET https://huggingface.co/api/daily_papers` via httpx; human-curated, high signal.
- Map to `RawItem`: paper title, summary (truncated like arXiv's 2000 chars), arXiv/HF paper URL, upvotes → `engagement`, published date → `timestamp`.
- Lookback-window filter like other fetchers (default 7 days, threaded `lookback_days`).
- Engagement policy: none by default (curation is the filter); optional `min_upvotes` config knob.

### 2. `ArxivSearchAdapter` — extend `agent/fetchers/arxiv.py` (source: `arxiv/search`)

- Targeted `arxiv.Search(query=...)` alongside the existing category firehose (which stays as-is).
- Queries from config `sources.arxiv_queries` (a static list, e.g. "LLM agents", "prompt optimization", "retrieval augmented generation"); each run `ti:/abs:` keyword search sorted by submitted date within the lookback window, capped per query.
- Dedup by URL already collapses overlap with the firehose downstream.

### 3. `GitHubTrendingAdapter` — `agent/fetchers/github_trending.py` (source: `github`)

- GitHub has no official trending API; use the **search API** (documented, stable, no key required at our rate): repos matching configured topics (`llm`, `ai-agents`, `rag`) pushed within the lookback window, sorted by stars, `min_stars` threshold as engagement policy.
- Map: repo full name + description → title/body, html_url, stargazers_count → `engagement`, pushed_at → `timestamp`.
- Unauthenticated rate limits are fine at sweep cadence; `GITHUB_TOKEN` honored from env when present (higher limit), never required.

All three: fail-soft (adapter errors skip that source, never abort the sweep), registered via 0009's factory, enable/disable per source under a new `sources:` config block:

```yaml
sources:
  hf_papers: {enabled: true, min_upvotes: 0}
  arxiv_queries: ["LLM agents", "prompt optimization", "retrieval augmented generation"]
  github_trending: {enabled: true, topics: [llm, ai-agents, rag], min_stars: 100}
```

## Wiring `SourceDiscovery` (close the loop, human in the gate)

- After the **weekly deep sweep** (and via a new `cli.py discover-sources` command), run `SourceDiscovery.suggest(recent_titles)` and append genuinely-new suggestions (deduped against `config.yml` feeds and prior suggestions) to `vault/sources.md` under a `## Suggested (pending review)` section with a date stamp.
- A human reviews and promotes suggestions into `config.yml` — the LLM never edits config. Suggestions routed through the configured LLM provider (works on OpenRouter).

## Testing

- Per-adapter unit tests with mocked HTTP/arxiv responses: mapping, lookback filtering, engagement policy, fail-soft on HTTP errors and malformed payloads.
- Factory registration tests: config flags add/omit each adapter.
- SourceDiscovery wiring: suggestions appended once (idempotent re-run), dedup against existing feeds, section formatting.
- **Live verification** (build-time, via OpenRouter for LLM steps): one real sweep with the new adapters enabled; confirm items from each new source reach the funnel and at least the vault write path; record counts in the results file.

## Out of scope

- Reddit, Lobste.rs, Semantic Scholar, Bluesky/X (future candidates; each would be one adapter now).
- Auto-promoting discovered sources into config (human gate is deliberate).
- Scraping GitHub's trending HTML page (search API only).
