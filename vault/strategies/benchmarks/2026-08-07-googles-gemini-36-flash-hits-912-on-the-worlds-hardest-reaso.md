---
title: "Google's Gemini 3.6 Flash Hits 91.2% on the World's Hardest Reasoning Test"
date: 2026-08-07
type: benchmark
score: 8
score_label: authority
tags: [benchmark, reasoning, evaluation]
validated: false
sources_count: 1
content_source: full
status: new
---

# Google's Gemini 3.6 Flash Hits 91.2% on the World's Hardest Reasoning Test

## Summary
Google's Gemini 3.6 Flash achieves 91.2% on ARC-AGI-1 and 60.4% on the harder ARC-AGI-2 benchmark at $0.61 per task. ARC-AGI measures fluid intelligence through grid-transformation puzzles that require inferring rules from minimal examples with no partial credit, positioning it as a test of genuine problem-solving rather than memorization.

## How It Works
ARC-AGI presents input-output grid pairs made of colored squares; models must infer the transformation rule and apply it to a novel input with at most three attempts and exact-match grading. Testing occurs across four reasoning effort levels (High, Medium, Low, Minimal) that control compute budget; Gemini 3.6 Flash's scores drop sharply from 60.4% to 2.6% between High and Minimal effort on ARC-AGI-2. Gemini 3.5 Flash-Lite scores 10.3% at lower cost ($0.14/task) as a budget alternative.

## Why It Matters
ARC-AGI deliberately resists memorization and focuses on adaptability to novel problems—what creator François Chollet calls "the only thing that actually matters in intelligence." Gemini 3.6 Flash's 60.4% on ARC-AGI-2 places it in competitive mid-tier (behind GPT-5.6 Sol at 92.5% and Claude Opus 5 at 90.4%), above the human average of 66% but below the >85% grand prize threshold. The sharp reasoning-effort cliff suggests practitioners need to budget substantial compute for hard reasoning tasks, while the cost-performance gap between Flash and Flash-Lite indicates a meaningful tradeoff for resource-constrained deployments.

## Sources
- [Google's Gemini 3.6 Flash Hits 91.2% on the World's Hardest Reasoning Test](https://alphasignal.ai/news/google-s-gemini-3-6-flash-hits-91-2-on-the-world-s-hardest-reasoning-test) — web/AlphaSignal · 0

## Related
