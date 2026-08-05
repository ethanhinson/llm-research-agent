---
title: "Install llama.cpp on macOS with Homebrew"
date: 2026-08-05
type: tutorial
score: 9
score_label: practicality
tags: [tutorial, llama.cpp, macos, local-llm, apple-silicon]
validated: false
sources_count: 3
status: new
---

# Install llama.cpp on macOS with Homebrew

## Summary
The fastest way to get llama.cpp running on a Mac. Homebrew ships a pre-built,
Metal-accelerated formula, so a single `brew install` gives you the `llama-cli`,
`llama-server`, and `llama-bench` binaries with no compiler toolchain to set up.
Best for anyone who just wants to run a local model today and doesn't need to
patch the source.

## How It Works
### 1. Install Homebrew (skip if you already have it)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
On Apple Silicon, make sure `/opt/homebrew/bin` is on your `PATH` (the installer
prints the two `eval` lines to add to `~/.zprofile`).

### 2. Install llama.cpp
```bash
brew install llama.cpp
```
This pulls a bottle already compiled with **Metal** (GPU) and **Accelerate**
(CPU BLAS) support enabled — the two things that make inference fast on Apple
Silicon. It installs several binaries onto your `PATH`:

- `llama-cli` — interactive / one-shot chat and completion
- `llama-server` — OpenAI-compatible HTTP server + web UI
- `llama-bench` — throughput benchmarking

### 3. Run a model
`llama.cpp` can pull GGUF models straight from Hugging Face with the `-hf` flag,
so you don't have to download files by hand:
```bash
# small, fast model — good for a first smoke test
llama-cli -hf ggml-org/gemma-3-1b-it-GGUF
```
Add `-ngl 99` to offload all layers to the GPU (Metal). On recent bottles GPU
offload is on by default, but being explicit never hurts:
```bash
llama-cli -hf ggml-org/gemma-3-1b-it-GGUF -ngl 99 -p "Explain Metal offloading in one sentence."
```

### 4. Keep it updated
```bash
brew upgrade llama.cpp
```
llama.cpp moves fast — upgrading every week or two is worth it for new model
support and speedups.

### Troubleshooting
- **`command not found: llama-cli`** — Homebrew's bin dir isn't on your `PATH`;
  re-run the `eval "$(/opt/homebrew/bin/brew shellenv)"` line and restart the shell.
- **Slow / CPU-only inference** — pass `-ngl 99` and confirm you're on an
  Apple Silicon Mac; Metal is not available on Intel Macs.
- **Want the absolute latest commit or custom build flags** — use the
  build-from-source tutorial instead; the bottle tracks tagged releases, not `master`.

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [llama.cpp README (ggml-org)](https://github.com/ggml-org/llama.cpp) — web/official · 0
- [How to run llama.cpp on Mac: Local AI on Apple Silicon](https://t81dev.medium.com/how-to-run-llama-cpp-on-mac-in-2025-local-ai-on-apple-silicon-2e4f8aba70e4) — web/Medium · 0
- [Setting Up llama.cpp on macOS: What Actually Worked](https://aiarchitectplaybook.com/p/setting-up-llamacpp-on-macos-what) — web/AI Architect Playbook · 0

## Related
- [[strategies/tutorials/2026-08-05-build-llama-cpp-from-source-on-apple-silicon-with-metal.md|Build llama.cpp from source on Apple Silicon with Metal]]
- [[strategies/tutorials/2026-08-05-run-local-llms-on-mac-with-llama-cpp-server-and-models.md|Run local LLMs on Mac with llama.cpp: models & OpenAI-compatible server]]
