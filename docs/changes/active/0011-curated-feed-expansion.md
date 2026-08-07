---
id: 11
slug: curated-feed-expansion
title: Add verified curated feeds — newsletters + Lobste.rs
status: in-progress
priority: medium
type: chore
created: 2026-08-07
updated: 2026-08-07
depends_on: []
related: [10]
discovered_from: []
adrs: []
spec:
plan:
results:
trivial: true
auto_groomable: false
branch: feat/curated-feed-expansion
claimed_at: 2026-08-07T07:47:30Z
pr:
blocked_by:
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
<!-- docket:artifacts:end -->

## Why

Human-curated digests are free editorial filtering upstream of the LLM eval. Six high-signal feeds were verified live on 2026-08-07 and can be added with zero code via the existing RSS fetcher.

## What changes

Add to `config.yml` `sources.feeds`:

- AlphaSignal — `https://alphasignal.ai/feed.xml` (newsletter)
- TLDR AI — `https://tldr.tech/api/rss/ai` (newsletter)
- Latent Space — `https://www.latent.space/feed` (newsletter)
- Ahead of AI (Sebastian Raschka) — `https://magazine.sebastianraschka.com/feed` (newsletter)
- Import AI (Jack Clark) — `https://importai.substack.com/feed` (newsletter)
- Lobste.rs AI tag — `https://lobste.rs/t/ai.rss` (blog)

Verify each parses through `WebFetcher` (one mocked test with a representative payload is sufficient; feeds themselves verified externally).

## Out of scope

- Extracting outbound links from digest issues as individual candidate items (future approach work; see the cross-source-corroboration stub).
- YouTube channel RSS (needs curated channel-id selection — add later with the author registry).
- Lobste.rs JSON endpoint with scores (an adapter, not a feed — not worth it at this volume).
