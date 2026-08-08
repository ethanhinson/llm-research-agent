---
title: "Anthropic's Claude Code Auto Mode Catches Dangerous Commands 89% of the Time"
date: 2026-08-07
type: benchmark
score: 7
score_label: authority
tags: [benchmark, safety-alignment, code-generation]
validated: false
sources_count: 1
content_source: full
status: new
---

# Anthropic's Claude Code Auto Mode Catches Dangerous Commands 89% of the Time

## Summary
Anthropic's Claude Code auto mode is a two-layer safety classifier that blocks dangerous commands before execution, replacing manual human approval. In a 1,053-person study, it blocked 89% of dangerous commands compared to 13.6% caught by human review, and it becomes the default for Pro, Max, and Team plans on August 14.

## How It Works
The system uses two layers: an input-layer probe scans external sources (files, web fetches, shell output) for prompt injections and adds warnings to Claude's context; an output-layer two-stage classifier evaluates every tool call before execution, with a fast Stage 1 filter and a Stage 2 chain-of-thought reasoner that runs only on flagged actions, reducing false positives to 0.4%. The classifier sees only user messages and raw tool calls, not Claude's reasoning, making it structurally resistant to prompt injection attacks. Zero prompt injection attacks succeeded in a third-party evaluation of 720 scenarios.

## Why It Matters
Human approval for tool execution had become ineffective—users approved 97% of permission prompts, and the catch rate for dangerous commands dropped to ~5% after 50+ prompts in a session. Auto mode outperforms human review on every measured safety metric while also removing friction: Teams and Enterprise users shipped 25% more pull requests under auto mode, and classifier costs no longer count toward usage limits. This addresses a real problem where the safety mechanism was being actively circumvented by users themselves.

## Sources
- [Anthropic's Claude Code Auto Mode Catches Dangerous Commands 89% of the Time](https://alphasignal.ai/news/anthropic-s-claude-code-auto-mode-catches-dangerous-commands-89-of-the-time) — web/AlphaSignal · 0

## Related
