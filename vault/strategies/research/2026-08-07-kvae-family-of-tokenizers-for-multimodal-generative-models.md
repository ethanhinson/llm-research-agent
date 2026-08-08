---
title: "KVAE: Family of Tokenizers for Multimodal Generative Models"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: architecture
tags: [research, architecture, multimodal, embeddings, tokenization]
validated: false
sources_count: 1
content_source: full
status: new
---

# KVAE: Family of Tokenizers for Multimodal Generative Models

## Summary
KVAE is a family of tokenizers for audio, image, and video designed to compress multimodal signals for use in latent diffusion models (LDMs). The tokenizers—KVAE-Audio, KVAE-2D, and KVAE-3D—achieve reconstruction and generation quality that matches or exceeds comparable open-source models across objective and subjective metrics.

## How It Works
The family includes three specialized tokenizers: KVAE-Audio, a continuous 48 kHz tokenizer with 50 Hz latent rate and 64 channels; KVAE-2D, an image tokenizer compressing inputs by 8× with 32 channels; and KVAE-3D, two causal video tokenizers with 4×16×16 and 4×8×8 compression ratios. Performance is evaluated using reconstruction metrics (PSNR, LPIPS, PESQ) and generation metrics (Fréchet Distance, CLIP score, CLAP score), alongside side-by-side human evaluation. Training details, model selection methods, and design ablations are provided with public code and weights.

## Why It Matters
Tokenizers are critical components in diffusion-based generation pipelines—they directly affect learning speed, sample quality, and downstream application performance. Practitioners working on text-conditioned multimodal generation benefit from having open-source tokenizers that demonstrate competitive or superior performance to frontier models (VAEs from Wan-2.2, HunyuanVideo, FLUX.2, MovieGen, StableAudio, MMAudio) while providing full transparency on training and design choices.

## Sources
- [KVAE: Family of Tokenizers for Multimodal Generative Models](https://huggingface.co/papers/2608.05798) — hf-papers · 10

## Related
