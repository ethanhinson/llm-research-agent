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
plan: docs/superpowers/plans/2026-08-07-curated-feed-expansion.md
results:
trivial: true
auto_groomable: false
branch: feat/curated-feed-expansion
claimed_at: 2026-08-07T07:52:00Z
pr:
blocked_by:
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Plan | [2026-08-07-curated-feed-expansion.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/curated-feed-expansion/docs/superpowers/plans/2026-08-07-curated-feed-expansion.md) |
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

## Reconcile log

- 2026-08-07 — Reconciled against current `main` (related change 0010 merged, e1f301e). Confirmed the scope holds unchanged: `config.yml` `sources.feeds` is a list of `{name, url, type}` objects consumed verbatim by `WebFetcher(feeds=...)` (`cli.py` reads `sources.feeds` → `run_sweep`/`run_deep` → `WebFetcher`), so the six additions are pure config with zero code. `WebFetcher.fetch()` iterates `feed["url"]`/`feed["name"]` and is fail-soft per feed. The change body lists URLs+types only; each gets a human-readable `name` on write. One mocked `WebFetcher` parse test with a representative newsletter/blog RSS payload is added per the body — feeds themselves verified externally on 2026-08-07, no live-LLM verification warranted. Suite baseline 179 (learnings finding pytest-shim-and-venv-provisioning); run via `uv run python -m pytest`. No obsolescence, no scope change.
