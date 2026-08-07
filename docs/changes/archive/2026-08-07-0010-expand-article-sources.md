---
id: 10
slug: expand-article-sources
title: Expand article sources — HF daily papers, arXiv keyword search, GitHub trending, wired SourceDiscovery
status: done
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: [9]
related: [2, 9]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-07-expand-article-sources.md
plan: docs/superpowers/plans/2026-08-07-expand-article-sources.md
results: docs/results/2026-08-07-expand-article-sources-results.md
trivial: false
auto_groomable: false
branch: feat/expand-article-sources
claimed_at: 
pr: https://github.com/ethanhinson/llm-research-agent/pull/10
blocked_by:
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-07-expand-article-sources.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-expand-article-sources.md) |
| Plan | [2026-08-07-expand-article-sources.md](https://github.com/ethanhinson/llm-research-agent/blob/main/docs/superpowers/plans/2026-08-07-expand-article-sources.md) |
| Results | [2026-08-07-expand-article-sources-results.md](https://github.com/ethanhinson/llm-research-agent/blob/main/docs/results/2026-08-07-expand-article-sources-results.md) |
| PR | [#10](https://github.com/ethanhinson/llm-research-agent/pull/10) |
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

### 2026-08-07 — reconciled against current main

- **Dependency 0009 landed and matches spec assumptions.** `agent/fetchers/base.py` ships the `SourceAdapter` protocol (`name`, `fetch() -> list[RawItem]`) and the `build_adapters(cfg, *, kind, ...)` factory. `kind="sweep"` currently returns `HNFetcher`, `ArxivFetcher`, and `WebFetcher` (feeds-gated). The three new adapters register through this factory as the spec directs; no protocol change needed.
- **`sources:` config block already exists** (holds `feeds:`). The new keys (`hf_papers`, `arxiv_queries`, `github_trending`) go alongside `feeds` under `sources:`, not a fresh top-level block — the spec's YAML is illustrative. `cli.py` reads `cfg["sources"]["feeds"]`; the new adapter config threads from the same `cfg["sources"]` dict into `build_adapters`.
- **LLM via OpenRouter fully supported.** `agent/llm.py:get_client({"llm": llm_cfg})` selects `OpenRouterClient` on `provider: openrouter`, reading `OPENROUTER_API_KEY`. `SourceDiscovery` already routes through `get_client`, so its live suggest call runs on OpenRouter unchanged. This is the path the live sweep verification uses (Anthropic key has no credit — the #7/#8 pattern).
- **`SourceDiscovery` is dead code today** (`agent/tools/source_discovery.py` exists, tested in isolation, never called by the loop or CLI). Wiring: append deduped suggestions to `vault/sources.md` under a dated `## Suggested (pending review)` section after the weekly deep sweep, plus a new `discover-sources` CLI command. Human promotes to config; the LLM never edits config.
- **Baseline suite green:** `uv run python -m pytest` = 133 passed (canonical command per the pytest-shim learning; no deepeval/trafilatura pollution).
- **No scope drift, no obsolescence, design valid.** Adjacent observation (not minted; auto-capture disabled): the evaluator's non-fail-soft Anthropic path (per the live-testing learning #7) remains a latent hard-abort trunk, but it is orthogonal to this change and the live run here uses OpenRouter, sidestepping it.
