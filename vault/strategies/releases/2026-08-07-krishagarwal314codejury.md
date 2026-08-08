---
title: "krishagarwal314/CodeJury"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, agent-frameworks, code-generation]
validated: false
sources_count: 1
content_source: full
status: new
---

# krishagarwal314/CodeJury

## Summary
CodeJury is a multi-model code review system that uses two or more LLMs from different providers to judge code changes independently, requiring unanimous approval before merge. It addresses the problem that a single reviewer—especially when trained on similar data as the writer—develops correlated blind spots and accepts plausible but incorrect changes.

## How It Works
Two jurors review the same diff under different briefs: one checks implementation and behaviour, the other checks systems fit and architecture. They never see each other's opinions, and both must approve for the change to ship; one dissent sends it back to the developer. An optional panel mode seats up to six specialists with a foreperson to reconcile. CodeJury indexes the repository once into a persistent code graph, then looks changes up rather than rediscovering them to keep costs low. The system runs across different providers and models at each stage (knowledge, PM, planner, dev, review), not locked into a single vendor's agent.

## Why It Matters
The ensemble review architecture is empirically validated: SE-Jury (Zhou et al., 2025) showed an ensemble of judges correlates with human correctness judgements at 64.3 versus 49.6 for the best single judge, and on program repair specifically (the core coding agent task) the gap widens to 76.2 versus 43.5. Cost is negligible—review is the cheapest pipeline stage, doubling it adds less than 3% to a typical run, or nothing on free-tier models. For teams building coding agents, this addresses a concrete reliability problem: diverse, uncorrelated review catches bugs that a single model trained on similar data will confidently miss.

## Sources
- [krishagarwal314/CodeJury](https://github.com/krishagarwal314/CodeJury) — github · 137

## Related
