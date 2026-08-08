---
title: "yonatangross/orchestkit"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, agent-frameworks, tool-use, multi-agent]
validated: false
sources_count: 1
content_source: full
status: new
---

# yonatangross/orchestkit

## Summary
OrchestKit is a Claude Code plugin that gives AI agents persistent knowledge of a developer's production patterns, tech stack, and quality gates. It bundles 105 skills, 36 specialized agents, and 218 hooks to automate tasks from setup through deployment without repeating context.

## How It Works
Installation is `/plugin install ork`. The `/ork:setup` wizard scans your codebase, detects your tech stack, and configures recommended MCP servers (Context7, Memory, Sequential Thinking). Skills load on-demand with zero overhead; agents route tasks to specialized personas (backend-architect, frontend-dev, security-auditor); hooks enforce gates at 29 lifecycle events (pre-commit checks, git protection, secret-write blocking, file guards). Commands like `/ork:implement`, `/ork:commit`, and `/ork:review-pr` wrap these components. All local state writes to `~/.local/state/orchestkit/events.jsonl` with no remote sync by default; network calls are opt-in only via explicit environment variables.

## Why It Matters
Developers currently re-explain their stack and patterns to Claude in every session. OrchestKit eliminates that friction by storing production conventions once and applying them automatically—turning "Use FastAPI with async SQLAlchemy 2.0 and cursor pagination" into a one-command `/ork:auto` that routes correctly the first time. The 218 hooks act as invisible safety rails, catching bad commits and secret writes before they ship, which reduces manual review overhead and makes multi-agent workflows safer for real codebases.

## Sources
- [yonatangross/orchestkit](https://github.com/yonatangross/orchestkit) — github · 215

## Related
