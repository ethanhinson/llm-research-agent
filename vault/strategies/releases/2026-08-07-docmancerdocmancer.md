---
title: "docmancer/docmancer"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, memory, agent-frameworks]
validated: false
sources_count: 1
content_source: full
status: new
---

# docmancer/docmancer

## Summary
Docmancer is a shared-memory harness for multiple coding agents that consolidates fragmented agent knowledge into a single canonical Markdown-based memory store. It solves the problem of re-explaining project context to each new agent by indexing existing agent memory (from Claude Code, Cursor, Codex, etc.) and delivering consistent context to all connected tools.

## How It Works
Docmancer discovers and indexes memory files already written by supported coding agents, arranges them as editable local Markdown organized by machine-wide and per-project scopes, and installs agent-specific skill files that teach each tool when to query the shared memory. On first run, `docmancer setup` finds all supported agents, shows a privacy plan, then builds the canonical memory and installs integrations. Commands like `docmancer ask` return answers with citations to source agent evidence; `docmancer write` and `docmancer edit` use content hashes to prevent concurrent overwrites. Core features run offline using SQLite FTS5 and a vendored embedding model. Optional paid Personal Sync adds encrypted cross-device synchronization with recovery kits.

## Why It Matters
Teams using multiple coding agents waste time repeating project decisions and working style to each tool. Docmancer consolidates that scattered knowledge into one readable, editable source of truth that every agent can access, eliminating duplicate explanation and ensuring decisions made once propagate to all agents immediately. Because memory lives as plain local files you own and control, with diffs shown before any write and citations always attached, practitioners can audit what agents learned about their project and maintain confidence in the consistency of agent behavior across tools.

## Sources
- [docmancer/docmancer](https://github.com/docmancer/docmancer) — github · 119

## Related
