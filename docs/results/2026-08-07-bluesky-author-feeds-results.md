<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0013 — Bluesky author-feed adapter with researcher registry](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0013-bluesky-author-feeds.md)**
<!-- docket:backlink:end -->

# Bluesky author-feed adapter — results
Change: #13 · Branch: feat/bluesky-author-feeds · PR: <set at PR open> · Plan: docs/superpowers/plans/2026-08-07-bluesky-author-feeds-plan.md · ADRs: none

## Live verification (public Bluesky `getAuthorFeed`)

The spec's build-time live check was performed against the public, unauthenticated
AppView endpoint `https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed`
(HTTP 200, no auth — re-verified 2026-08-07). Three real registry handles were fetched
through the actual `BlueskyAdapter.fetch()` (constructed inline; no config was flipped),
`min_engagement=5`, `lookback_days=30`:

| Handle | Kept `RawItem`s |
|---|---|
| `simonwillison.net` | 5 |
| `karpathy.bsky.social` | 0 |
| `rasbt.bsky.social` | 0 |

The `simonwillison.net` items carried real outbound links, likes+reposts engagement
above the floor, and `source == "bluesky/simonwillison.net"`. The two zero-count handles
are expected, not a failure: within the window their posts were either below the
engagement floor or pure commentary (no outbound link / arXiv ID), which the adapter
drops by design. This exercised the full path end-to-end: fetch → skip reposts/replies →
extract facet/embed links → engagement floor → lookback → `RawItem` mapping. No arXiv
links surfaced in this particular sample.

No LLM/OpenRouter step was involved — this change is a pure fetch/map adapter with no
evaluation stage. The adapter was constructed directly (not via a full sweep), so **no
config was changed and there is nothing to revert; no vault artifacts were produced**.
Registry handles were curated at build time and each verified HTTP 200 via `getProfile`
before inclusion (27 handles; unresolvable candidates dropped, none invented).

## Test suite

`uv sync --extra dev` then `uv run python -m pytest` in the feature worktree:
**238 passed**, 0 failures (209 baseline + new `test_fetcher_bluesky` coverage +
`test_build_adapters` factory-gating cases + the review-fix wave's added tests). No
`deepeval`/`TracerProvider` crash and no `trafilatura` ImportError — the
`pytest-shim-and-venv-provisioning` learning held (canonical `uv run python -m pytest`).

## Verify (human)

- [ ] Confirm the 27 curated handles in `config.yml` (`sources.bluesky.authors`) match the
      accounts you want followed; the registry is a plain config list, easy to edit.
- [ ] Optionally run a real sweep with `sources.bluesky.enabled: true` and confirm Bluesky
      items land in the vault as expected (build verified the adapter in isolation only).

## Findings

- Whole-branch review surfaced two should-fix items, both addressed on-branch (commit
  `aea673d`) before this results file:
  - `recordWithMedia#view` embeds (a quote/media post with a link card under
    `embed["media"]["external"]`) were not extracted, so link-bearing posts of that shape
    were silently dropped as commentary — a recall gap on exactly the paper-announcement
    posts this change targets. Fixed via a factored `_resolve_external()` helper.
  - The arXiv-URL normalizer left a trailing slash (`.../abs/<id>/`) uncleaned, weakening
    cross-source dedup. Fixed with `rstrip("/")` on the captured id, plus covering tests.
- No ADR was warranted: the design followed the spec and the sibling adapters
  (`semantic_scholar.py` / `github_trending.py` / `hf_papers.py`) directly; the
  recordWithMedia handling is a recall-correctness detail within the spec's stated
  "extract outbound links from facets+embeds", not an architectural decision.

## Follow-ups

Reported here (not minted — `auto_capture` is disabled in this repo). Genuine separate-change work:

- **Registry liveness / dead-handle report.** The config seeds 27 handles with no ongoing
  guard against a typo'd or renamed handle silently yielding zero items forever. A small
  periodic "dead handle" report (or a lint) would be its own change.
- **Fan the registry to other channels.** `sources.bluesky.authors` is deliberately a plain
  list so future changes can reuse it for S2 author-paper feeds, arXiv `au:` queries, etc.
  Explicitly out of scope for this change (per spec).
