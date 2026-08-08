---
title: "PaddlePaddle/Real5-OmniDocBench"
date: 2026-08-07
type: benchmark
score: 7
score_label: authority
tags: [benchmark, multimodal, evaluation]
validated: false
sources_count: 1
content_source: full
status: new
---

# PaddlePaddle/Real5-OmniDocBench

## Summary
Real5-OmniDocBench is a benchmark dataset for document parsing built on OmniDocBench v1.5, containing 1,355 images per scenario across five real-world photographic conditions: Scanning, Warping, Screen-Photography, Illumination, and Skew. It was accepted to ECCV 2026 and enables rigorous evaluation of document parsing model robustness under practical distortions.

## How It Works
The dataset divides documents into five challenging scenarios representing common real-world capture conditions. Except for Scanning (device-captured), all images were manually acquired via handheld mobile devices to simulate authentic distortions (page curvature, perspective skew, moiré patterns, lighting variation). Each image set maintains one-to-one correspondence with original OmniDocBench pages and uses the same evaluation metrics (Normalized Edit Distance, BLEU, METEOR, TEDS, COCODet). Models output Markdown-formatted document parses that are assessed across five metrics: Overall, TextEdit, FormulaCDM, TableTEDS, and Reading OrderEdit.

## Why It Matters
Practitioners need a realistic benchmark because production document parsing encounters genuine photographic degradation that clean scans do not capture. Real5-OmniDocBench reveals that model performance degrades substantially under certain conditions—for example, specialized VLMs show sharp performance drops on Skew (PaddleOCR-VL-1.6: 92.66% vs. Scanning: 94.74%)—making it essential for assessing whether models will work reliably in mobile and camera-based document digitization workflows. The scenario-level breakdown enables targeted diagnosis of robustness gaps.

## Sources
- [PaddlePaddle/Real5-OmniDocBench](https://huggingface.co/datasets/PaddlePaddle/Real5-OmniDocBench) — hf-trending · 33

## Related
