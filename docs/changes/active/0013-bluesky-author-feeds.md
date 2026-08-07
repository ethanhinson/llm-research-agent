---
id: 13
slug: bluesky-author-feeds
title: Bluesky author-feed adapter with researcher registry
status: proposed
priority: medium
type: feat
created: 2026-08-07
updated: 2026-08-07
depends_on: [10]
related: [9, 10, 12]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-07-bluesky-author-feeds.md
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
| Spec | [2026-08-07-bluesky-author-feeds.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-07-bluesky-author-feeds.md) |
<!-- docket:artifacts:end -->

## Why

Much of ML-research discourse moved to Bluesky; paper announcements appear there hours before aggregators. The public AppView's `getAuthorFeed` needs no auth (verified 2026-08-07), so following a curated researcher registry is cheap and high-signal. Keyword search requires auth and is excluded.

## What changes

A `BlueskyAdapter` (source `bluesky/<handle>`) polling `getAuthorFeed` for a config researcher registry (~20–30 handles curated at build): extract outbound links/arXiv IDs from posts, likes+reposts as engagement with a floor, drop pure commentary, per-handle fail-soft. Registry lives in config so future changes can fan it out to other per-author channels. Mocked tests + live check on 2–3 handles.

## Out of scope

- Authenticated search, custom feeds/firehose, Mastodon, non-Bluesky author channels.

## Reconcile log
