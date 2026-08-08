---
title: "Epoch Hides a Game's Identity to Stop AI Labs From Cheating Benchmarks"
date: 2026-08-07
type: benchmark
score: 8
score_label: authority
tags: [benchmark, evaluation, benchmarking]
validated: false
sources_count: 1
content_source: full
status: new
---

# Epoch Hides a Game's Identity to Stop AI Labs From Cheating Benchmarks

## Summary
Epoch AI's Mystery Game Puzzles is a new benchmark that hides the identity of its underlying game to prevent models from being specifically tuned toward it. Currently, Opus 5 leads at 59%, with progress plateauing since April after rapid early gains.

## How It Works
The benchmark presents 100 positions from a well-known but undisclosed game, asking models to select the best next move. The game's identity, prompts, example positions, and model transcripts are all kept secret to block benchmark-specific fine-tuning. Models receive a 1M output token budget; top performers use under 400K, indicating reasoning limitations rather than compute constraints.

## Why It Matters
Public benchmarks suffer from contamination when labs tune models toward them. By withholding the game's identity, this design removes a major vector for gaming the test through targeted post-training. The format also measures reasoning capabilities—spatial reasoning and planning—that practitioners care about assessing, making it a harder-to-circumvent proxy for genuine model capability.

## Sources
- [Epoch Hides a Game's Identity to Stop AI Labs From Cheating Benchmarks](https://alphasignal.ai/news/epoch-hides-a-game-s-identity-to-stop-ai-labs-from-cheating-benchmarks) — web/AlphaSignal · 0

## Related
