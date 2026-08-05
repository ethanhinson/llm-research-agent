---
title: "Build llama.cpp from source on Apple Silicon with Metal"
date: 2026-08-05
type: tutorial
score: 8
score_label: practicality
tags: [tutorial, llama.cpp, macos, apple-silicon, metal, cmake]
validated: false
sources_count: 3
status: new
---

# Build llama.cpp from source on Apple Silicon with Metal

## Summary
Build llama.cpp yourself when you want the latest `master`, custom compile
flags, or the ability to hack on the code. On Apple Silicon the CMake build
enables **Metal** (GPU) and the **Accelerate** framework (CPU BLAS)
automatically, so a stock Release build is already tuned for M-series chips.

## How It Works
### 1. Install the toolchain
```bash
# Xcode command line tools (clang, git)
xcode-select --install

# CMake — the build system llama.cpp uses
brew install cmake
```

### 2. Clone the repository
```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
```

### 3. Configure and build
```bash
cmake -B build
cmake --build build --config Release -j
```
- `-j` runs a parallel build across all cores; on an M-series Mac the whole
  thing compiles in a couple of minutes.
- **Metal is enabled by default on macOS** — no flag required. GPU offload is
  what makes local inference fast on Apple Silicon.
- **Accelerate (BLAS) is also on by default** on Mac; the standard build picks
  it up with no extra configuration.

The binaries land in `./build/bin/` — `llama-cli`, `llama-server`,
`llama-bench`, and friends.

### 4. Verify the build
```bash
# pulls a tiny model from Hugging Face and runs it on the GPU
./build/bin/llama-cli -hf ggml-org/gemma-3-1b-it-GGUF -ngl 99 -p "Say hi from Metal."
```
You should see Metal device info in the startup log (e.g. `ggml_metal_init:
found device: Apple M...`), confirming GPU offload is active.

### Useful build variants
- **CPU-only build** (for debugging or non-Metal boxes):
  ```bash
  cmake -B build -DGGML_METAL=OFF
  cmake --build build --config Release -j
  ```
  You can also keep the Metal build and disable GPU at runtime with `-ngl 0`.
- **Put the binaries on your PATH** so you can call them like the Homebrew
  install:
  ```bash
  cmake --install build --config Release   # installs into /usr/local by default
  ```
- **Update to the latest code later:**
  ```bash
  git pull && cmake --build build --config Release -j
  ```

### Troubleshooting
- **`cmake: command not found`** — run `brew install cmake` (or add Homebrew to
  your `PATH`).
- **`xcrun: error: invalid active developer path`** — re-run
  `xcode-select --install`, or `sudo xcode-select --reset`.
- **Build succeeds but inference is slow** — you're likely on CPU; pass
  `-ngl 99` and confirm the log shows a Metal device. Intel Macs have no Metal
  support and will always run on CPU.

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [llama.cpp build docs (docs/build.md)](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) — web/official · 0
- [llama.cpp README (ggml-org)](https://github.com/ggml-org/llama.cpp) — web/official · 0
- [Running llama.cpp on Mac](https://medium.com/@jackcheang5/running-llama-cpp-in-mac-22e71123b811) — web/Medium · 0

## Related
- [[strategies/tutorials/2026-08-05-install-llama-cpp-on-macos-with-homebrew.md|Install llama.cpp on macOS with Homebrew]]
- [[strategies/tutorials/2026-08-05-run-local-llms-on-mac-with-llama-cpp-server-and-models.md|Run local LLMs on Mac with llama.cpp: models & OpenAI-compatible server]]
