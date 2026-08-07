<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0010 — Expand article sources — HF daily papers, arXiv keyword search, GitHub trending, wired SourceDiscovery](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0010-expand-article-sources.md)**
<!-- docket:backlink:end -->

# Expand article sources — results
Change: #10 · Branch: feat/expand-article-sources · PR: <set at PR open> · Plan: docs/superpowers/plans/2026-08-07-expand-article-sources.md · ADRs: none

## Live verification (OpenRouter)

The spec's live sweep verification was **completed at build time via OpenRouter**
(`llm.provider: openrouter`, model `anthropic/claude-haiku-4.5`) — the Anthropic key
has no credit (the #7/#8 credit-balance-`400` pattern), so the live run was pointed at
OpenRouter exactly as the `live-testing-catches-what-mocks-miss` learning prescribes.
The temporary `provider: openrouter` config flip and all live-run vault artifacts were
reverted/discarded; only code + tests are committed. The key was never printed or committed.

**Per-source raw fetch counts** (direct adapter fetch against real APIs):

| Source | Adapter | Params | Raw items |
|---|---|---|---|
| HF daily papers | `HFPapersAdapter` | lookback 7, min_upvotes 0 | 46 |
| arXiv keyword search | `ArxivSearchAdapter` | 2 queries × cap 5, lookback 7 | 10 |
| GitHub trending | `GitHubTrendingAdapter` | topics llm+rag, min_stars 100, lookback 30 | 100 |

The HF payload shape assumption (worker-flagged) **held against the real API** — 46 items
mapped cleanly (title, summary, `upvotes`→engagement, `publishedAt`→timestamp, papers URL).

**Full-pipeline live sweep** (minimal scope: three new sources + HN/arXiv baseline, `feeds=[]`,
lookback 2–3, deep=True, OpenRouter evaluation): **134 items KEPT** through
fetch → dedup → topic filter → cross-validate → **OpenRouter evaluation** → write.

Kept per source-family: `hackernews` 20, `arxiv` 29 (firehose + `arxiv/search`),
**`hf-papers` 8**, **`github` 77**. 128 notes written to the vault. The `discover-sources`
path appended a dated `## Suggested (pending review)` section to `sources.md`. Every new
source reached the funnel and the vault write path; only expected fail-soft soft-degradations
(paywalled enrich, missing search-backend keys) appeared — no LLM/provider errors.

## Verify (human)

- [ ] Sanity-check the three source defaults in `config.yml` (`sources.hf_papers`,
      `arxiv_queries`, `github_trending`) match your intended sweep breadth before the first
      production run.
- [ ] Optionally set `GITHUB_TOKEN` in `.env` to raise the GitHub search rate limit (never required).
- [ ] After a real deep sweep, review `vault/sources.md`'s `## Suggested (pending review)`
      section and promote any good suggestions into `config.yml` by hand (the LLM never edits config).

## Findings

- **Live verification unblocked via provider swap, not billing.** The Anthropic credit-balance
  `400` (from changes #7/#8) again blocked a paid-API acceptance run; pointing the same pipeline
  at OpenRouter cleared it — reinforcing the `live-testing-catches-what-mocks-miss` candidate finding.
- **Review fix (whole-line dedup).** The whole-branch review flagged `append_suggestions`'
  non-URL dedup as a substring scan that could over-drop a short suggestion appearing inside a
  longer existing line. Fixed to whole-line matching with a regression test (commit `c5dd4bd`).
  It only over-dropped (never corrupted/duplicated), so no data risk — tightened for correctness.

## Follow-ups

- Adjacent, not minted (auto-capture disabled): `agent/evaluator.py`'s Anthropic path is still
  non-fail-soft, so a credit-balance `400` there hard-aborts a sweep before the new fail-soft
  sources are even reached. Orthogonal to this change; the live run used OpenRouter so it never
  fired. A human may file this as its own change if evaluator resilience is wanted.
