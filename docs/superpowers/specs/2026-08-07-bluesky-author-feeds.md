<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0013 — Bluesky author-feed adapter with researcher registry](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0013-bluesky-author-feeds.md)**
<!-- docket:backlink:end -->

# Bluesky Author-Feed Adapter — Design Spec

**Date:** 2026-08-07
**Status:** Approved

---

## Overview

Follow a curated registry of AI researchers on Bluesky and ingest their posts as candidate items — paper announcements often surface there hours before aggregators. Verified 2026-08-07: `https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor=<handle>` returns 200 with no auth (generous public read limits); keyword search (`searchPosts`) is 403 unauthenticated and is deliberately **out of scope** — author feeds only, no account needed.

## Researcher registry — config

```yaml
sources:
  bluesky:
    enabled: true
    min_engagement: 5        # likes+reposts floor; posts below are noise-prone
    authors:                 # seed list; human-curated, grows over time
      - simonwillison.net
      - ... (~20-30 handles at ship time, chosen at build from verifiable active accounts)
```

The registry is a plain config list so the same handle set can later feed other per-author channels (S2 author papers, YouTube, arXiv `au:` queries) — but only Bluesky consumes it in this change.

## Adapter — `agent/fetchers/bluesky.py` (source: `bluesky/<handle>`)

- Poll `getAuthorFeed` per handle (limit ~25, lookback-window filtered via `indexedAt`; skip reposts/replies).
- **Item shape:** posts are short; the payload is the link. Extract outbound links / arXiv IDs from post facets+embeds; title = post text (truncated) or embed title when present; url = the outbound link when exactly one exists, else the post's own URL; `engagement` = likeCount + repostCount, thresholded by `min_engagement`.
- Posts with no outbound link and no arXiv ID are dropped (pure commentary).
- Fail-soft per handle (one dead handle never kills the source); config-gated; registered in `build_adapters`.

## Testing

Mocked httpx: facet/embed link extraction, arXiv-ID detection, repost/reply skipping, engagement threshold, per-handle fail-soft, factory gating. Live check at build time: fetch 2–3 real handles, record counts.

## Out of scope

- Authenticated search (`searchPosts`), custom feeds/firehose, Mastodon.
- Fanning the registry out to other channels (future changes reuse `sources.bluesky.authors` or a promoted shared key).
