---
title: "TeleAI-UAGI/telemem"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, memory, multimodal, long-context]
validated: false
sources_count: 1
content_source: full
status: new
---

# TeleAI-UAGI/telemem

## Summary
TeleMem is an agent memory management layer designed as a high-performance drop-in replacement for Mem0, optimized for multi-turn dialogues, character modeling, and long-term information storage. It adds character-isolated memory profiles, video understanding, and multimodal reasoning while maintaining API compatibility with Mem0 through a single-line import.

## How It Works
TeleMem processes dialogue through a character-aware pipeline: summarization (global + per-character) → semantic embedding and retrieval → write buffering with batch flushing → LLM-based semantic clustering and fusion → storage in FAISS indices with JSON metadata. For video, it implements frame extraction, caption generation, and vector database construction, enabling ReAct-style multi-step video question-answering. The system runs fully local by default using Qwen models and FAISS, with no cloud dependency.

## Why It Matters
Practitioners working with conversational AI and multi-character scenarios benefit from TeleMem's documented 86.33% accuracy on long-dialogue Chinese benchmarks (19% above Mem0), 2–3× faster write performance via batch flushing, and automatic per-character memory isolation that prevents character confusion—critical for role-play, companion AI, and NPC systems. The mem0-compatible API and video pipeline extension enable adoption into existing LangChain and LlamaIndex workflows without refactoring, while the fully local design eliminates data privacy concerns.

## Sources
- [TeleAI-UAGI/telemem](https://github.com/TeleAI-UAGI/telemem) — github · 478

## Related
