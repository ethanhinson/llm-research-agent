---
title: "openai/gsm8k"
date: 2026-08-07
type: benchmark
score: 8
score_label: authority
tags: [benchmark, chain-of-thought, reasoning]
validated: false
sources_count: 1
content_source: full
status: new
---

# openai/gsm8k

## Summary
GSM8K is a benchmark dataset of grade-school math word problems with step-by-step solutions. It contains diverse arithmetic and algebraic problems paired with worked answers that show intermediate calculation steps.

## How It Works
Each example in the dataset consists of a natural-language word problem and a corresponding answer that breaks down the solution into explicit steps, showing intermediate calculations with their results formatted as `<<calculation>>result`. Problems range in complexity from simple arithmetic (e.g., "Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May") to multi-step reasoning requiring proportional relationships and variable solving.

## Why It Matters
GSM8K serves as a standard evaluation benchmark for assessing whether language models can perform grade-school-level mathematical reasoning. The dataset's explicit step-by-step solutions make it useful for both training models to decompose problems and evaluating their ability to follow logical chains of reasoning over multiple arithmetic operations.

## Sources
- [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k) — hf-trending · 1552

## Related
