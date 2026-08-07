---
id: 13
slug: bluesky-author-feeds
title: Bluesky author-feed adapter with researcher registry
status: done
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: [10]
related: [9, 10, 12]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-07-bluesky-author-feeds.md
plan: docs/superpowers/plans/2026-08-07-bluesky-author-feeds-plan.md
results: docs/results/2026-08-07-bluesky-author-feeds-results.md
trivial: false
auto_groomable: false
branch: feat/bluesky-author-feeds
pr: https://github.com/ethanhinson/llm-research-agent/pull/13
blocked_by:
reconciled: true
claimed_at: 
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-07-bluesky-author-feeds.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-bluesky-author-feeds.md) |
| Plan | [2026-08-07-bluesky-author-feeds-plan.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/bluesky-author-feeds/docs/superpowers/plans/2026-08-07-bluesky-author-feeds-plan.md) |
| Results | [2026-08-07-bluesky-author-feeds-results.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/bluesky-author-feeds/docs/results/2026-08-07-bluesky-author-feeds-results.md) |
| PR | [#13](https://github.com/ethanhinson/llm-research-agent/pull/13) |
<!-- docket:artifacts:end -->

## Why

Much of ML-research discourse moved to Bluesky; paper announcements appear there hours before aggregators. The public AppView's `getAuthorFeed` needs no auth (verified 2026-08-07), so following a curated researcher registry is cheap and high-signal. Keyword search requires auth and is excluded.

## What changes

A `BlueskyAdapter` (source `bluesky/<handle>`) polling `getAuthorFeed` for a config researcher registry (~20–30 handles curated at build): extract outbound links/arXiv IDs from posts, likes+reposts as engagement with a floor, drop pure commentary, per-handle fail-soft. Registry lives in config so future changes can fan it out to other per-author channels. Mocked tests + live check on 2–3 handles.

## Out of scope

- Authenticated search, custom feeds/firehose, Mastodon, non-Bluesky author channels.

## Reconcile log

### 2026-08-07 — reconcile before build

- **Dependency 0010 (`expand-article-sources`) is `done`** (archived `2026-08-07-0010-expand-article-sources.md`); the 0009 adapter layer + 0012 Semantic Scholar adapter also merged. `depends_on` satisfied — build-ready confirmed.
- **Spec is current, no changes needed.** The landed `agent/fetchers/base.py` (`SourceAdapter` protocol + `build_adapters` `kind="sweep"` factory) and the `config.yml` `sources:` block match the spec's assumptions exactly. `HFPapersAdapter`/`GitHubTrendingAdapter`/`SemanticScholarAdapter` are the intended templates: `name` class attr, `httpx.get` with `timeout=15`, fail-soft `except Exception: return []`, `RawItem` mapping, `lookback_days` threading, `runtime_checkable` protocol conformance, factory config-gating with `sources.get(...)`.
- **Public API re-verified live 2026-08-07:** `getAuthorFeed` returns HTTP 200 with no auth; `getProfile` used to validate handles. Confirmed the JSON shape the adapter must map: reposts carry a top-level `reason` on the feed item (skip); replies carry `reply` under `post.record` (skip); facet links live at `record.facets[].features[]` with `$type` `app.bsky.richtext.facet#link`; external embeds at `post.embed` `$type` `app.bsky.embed.external#view` (`external.uri`/`external.title`); engagement = `post.likeCount + post.repostCount`; timestamp = `post.indexedAt`.
- **Registry curated at build (27 handles), each verified 200 via `getProfile`:** simonwillison.net, karpathy, soumith, emollick, jeremyphoward, rasbt, giffmana.ai, natolambert, tomgoldstein, jbhuang0604, sedielem, chelseafinn, merve, andrewwhite, gm8xx8, hardmaru, tunguz, osanseviero, danielvanstrien, arankomatsuzaki, johnowhitaker, lateinteraction, neelnanda, jxmnop, srush, yoavgo, vikhyat (bsky.social suffix where applicable). Candidates that returned 400 (ylecun, sarahookr, colinraffel.com, vboykis.com, cwolferesearch, …) were dropped, not invented.
- No design invalidation, no scope drift, no new ADR-forcing constraint surfaced. Auto-capture disabled (`AUTO_CAPTURE_ENABLED=false`) — no stubs minted.
