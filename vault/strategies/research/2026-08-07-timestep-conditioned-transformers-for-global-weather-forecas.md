---
title: "Timestep-Conditioned Transformers for Global Weather Forecasting"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: architecture
tags: [research, architecture, time-series, forecasting, autoregressive]
validated: false
sources_count: 1
content_source: full
status: new
---

# Timestep-Conditioned Transformers for Global Weather Forecasting

## Summary
GEM-3 is a probabilistic global weather forecasting transformer that resolves a core trade-off in autoregressive weather models by allowing the timestep to be configured at inference time rather than fixed during training. A single trained model can generate forecasts at multiple timesteps (e.g., 1–24 hours), balancing fine atmospheric resolution against error accumulation depending on the forecast use case.

## How It Works
GEM-3 uses a lightweight neighborhood-attention transformer (~134M parameters) on an equirectangular grid and trains on mixed timesteps rather than a single fixed timestep. This allows the model to produce predictions at different temporal resolutions at inference time without retraining. The architecture includes several advancements over its predecessor GEM-2 and supports probabilistic output for uncertainty quantification.

## Why It Matters
Practitioners face a hard choice: short timesteps capture sub-daily weather dynamics but accumulate prediction error over longer horizons, while long timesteps reduce error growth but miss high-value short-range forecasts. GEM-3's configurable timestep at inference eliminates this forced choice—a single model weights set handles both near-term and medium-range forecasts with stable rollouts and efficient computation, making it more practical for operational weather systems that must serve multiple forecast horizons simultaneously.

## Sources
- [Timestep-Conditioned Transformers for Global Weather Forecasting](http://arxiv.org/abs/2608.06241v1) — arxiv · 0

## Related
