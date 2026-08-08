---
title: "XYZAILab/XYZ-Aquila-SFT"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, tool-use, agent-frameworks]
validated: false
sources_count: 1
content_source: full
status: new
---

# XYZAILab/XYZ-Aquila-SFT

## Summary
XYZ-Aquila SFT is a bilingual supervised fine-tuning dataset of 7,000 multi-turn tool-use trajectories (5,000 English, 2,000 Chinese) capturing agent interactions with search tools. Models trained on the broader SFT corpus achieve strong performance on agentic-search benchmarks, with XYZ-Aquila-pro scoring 97.1 on GAIA and 84.8–92.5 on domain-specific tasks.

## How It Works
Each example comprises a question, final answer, tool-call count, and a multi-turn trajectory that includes system instructions, user requests, assistant reasoning with tool invocations, and tool responses. Tool definitions (web_search, scrape_and_extract_info, run_python_code) are embedded in the first system message in Qwen3 chat template format. The data is provided as separate English and Chinese JSONL shards and includes utilities (convert_tools.py) to extract or render tool schemas for different pipeline requirements.

## Why It Matters
Practitioners building search-oriented agentic systems need realistic multi-turn tool-use supervision data to train models that reliably reason through retrieval and execution steps. This dataset provides a concrete, production-scale example with strong benchmark validation across English and Chinese, reducing the friction of collecting and formatting agent trajectories from scratch while demonstrating that bilingual tool-use training is feasible at this scale.

## Sources
- [XYZAILab/XYZ-Aquila-SFT](https://huggingface.co/datasets/XYZAILab/XYZ-Aquila-SFT) — hf-trending · 366

## Related
