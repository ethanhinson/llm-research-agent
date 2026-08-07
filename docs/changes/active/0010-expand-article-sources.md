---
id: 10
slug: expand-article-sources
title: Expand article sources — HF daily papers, arXiv keyword search, GitHub trending, wired SourceDiscovery
status: proposed
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: [9]
related: [2, 9]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-07-expand-article-sources.md
plan:
results:
trivial: false
auto_groomable: false
branch:
pr:
blocked_by:
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-07-expand-article-sources.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-expand-article-sources.md) |
<!-- docket:artifacts:end -->

## Why

The agent's net is narrow: an arXiv category firehose capped at 50 results, HN, eight RSS feeds, and generic web search. High-signal streams (curated HF daily papers, keyword-targeted arXiv search, trending LLM tooling on GitHub) are missed entirely, and the `SourceDiscovery` tool that suggests new sources is dead code — its suggestions go nowhere. More articles in means a richer vault out.

## What changes

- Three new source adapters on 0009's layer: `HFPapersAdapter` (daily-papers API), `ArxivSearchAdapter` (config-driven keyword queries alongside the firehose), `GitHubTrendingAdapter` (search API, topic + star-threshold). Each fail-soft, config-gated under a new `sources:` block.
- `SourceDiscovery` wired into the loop: weekly deep sweep + a `discover-sources` CLI command append deduped suggestions to `vault/sources.md` for human review; a human promotes them to config — the LLM never edits config.
- Mocked unit tests per adapter + a live sweep verification (LLM steps via OpenRouter) recording per-source counts in the results file.

## Out of scope

- Reddit, Lobste.rs, Semantic Scholar, Bluesky/X adapters.
- Auto-promoting discovered sources into config; scraping GitHub's trending HTML.

## Reconcile log
