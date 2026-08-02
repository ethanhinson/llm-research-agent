---
id: 1
slug: llm-research-agent
title: LLM Research Agent — Reddit/HN/arXiv monitor with Obsidian vault output
status: done
priority: high
type: feat
created: 2026-08-01
updated: 2026-08-02
depends_on: []
related: []
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-01-llm-research-agent-design.md
plan: docs/superpowers/plans/2026-08-01-llm-research-agent-plan.md
results:
trivial: false
auto_groomable: false
branch: feat/llm-research-agent
claimed_at: 
pr: https://github.com/ethanhinson/llm-research-agent/pull/1
issue:
blocked_by:
reconciled: true
---

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-01-llm-research-agent-design.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-01-llm-research-agent-design.md) |
<!-- docket:artifacts:end -->

## Why

We want an agent that continuously monitors Reddit, Hacker News, arXiv, and AI blogs/newsletters for emerging LLM strategies and documents them as structured Obsidian notes in a git-tracked vault. The goal is to stay on top of new prompting techniques, architecture innovations, agentic patterns, tooling, and use-case breakthroughs without manually trawling sources.

## What changes

- New Python project at `~/dev/llm-research-agent/`
- Fetchers for Reddit (PRAW), HN (Algolia API), arXiv, and generic web sources
- Signal evaluation pipeline: engagement filter → cross-source validation → Claude novelty scoring
- Obsidian-formatted markdown notes written to `vault/strategies/`
- Auto-maintained `vault/index.md` and `vault/sources.md`
- Source discovery tool (Claude suggests new sources each sweep)
- CLI: `sweep`, `start` (scheduler), `sources`, `status`
- Daily + weekly scheduled sweeps via APScheduler

## Out of scope

- Web UI or dashboard
- Email/Slack digest delivery
- Embeddings-based deduplication (fuzzy string match for v1)
- Multi-user features

## Open questions

None — design fully approved.
