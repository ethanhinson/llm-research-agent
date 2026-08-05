---
title: "Run local LLMs on Mac with llama.cpp: models & OpenAI-compatible server"
date: 2026-08-05
type: tutorial
score: 8
score_label: practicality
tags: [tutorial, llama.cpp, macos, local-llm, server, gguf]
validated: false
sources_count: 3
status: new
---

# Run local LLMs on Mac with llama.cpp: models & OpenAI-compatible server

## Summary
Once llama.cpp is installed (via Homebrew or a source build), this is how you
actually use it: pull GGUF models from Hugging Face, chat from the CLI, and
stand up an OpenAI-compatible HTTP server so existing SDKs and apps can point at
your Mac instead of a cloud API.

## How It Works
> Commands below assume the binaries are on your `PATH` (Homebrew install). For
> a source build, prefix them with `./build/bin/` (e.g. `./build/bin/llama-cli`).

### 1. Understand the model format: GGUF
llama.cpp runs models in the **GGUF** format, which bundles the quantized
weights and metadata in one file. Lower quantization = smaller + faster but
slightly lower quality. Common choices:
- `Q4_K_M` — the usual sweet spot for quality vs. size
- `Q8_0` — near-full quality, larger
- `Q6_K` — a middle ground

### 2. Pull and run a model in one step
The `-hf` flag downloads the GGUF from Hugging Face and caches it locally:
```bash
llama-cli -hf ggml-org/gemma-3-1b-it-GGUF -ngl 99
```
- `-ngl 99` offloads all layers to the GPU (Metal). Drop or lower it if a big
  model doesn't fit in memory.
- One-shot prompt instead of interactive chat:
  ```bash
  llama-cli -hf ggml-org/gemma-3-1b-it-GGUF -ngl 99 -p "Summarize GGUF in one line." -no-cnv
  ```
- Run a model file you already downloaded:
  ```bash
  llama-cli -m ~/models/my-model.Q4_K_M.gguf -ngl 99
  ```

### 3. Start the OpenAI-compatible server
```bash
llama-server -hf ggml-org/gemma-3-1b-it-GGUF -ngl 99 --port 8080
```
- Web chat UI: open **http://localhost:8080** in a browser.
- OpenAI-compatible endpoint: **http://localhost:8080/v1/chat/completions**.

Point any OpenAI client at it — the API key is ignored locally:
```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local",
    "messages": [{"role": "user", "content": "Hello from my Mac"}]
  }'
```
Or with the OpenAI Python SDK:
```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")
resp = client.chat.completions.create(
    model="local",
    messages=[{"role": "user", "content": "Hello from my Mac"}],
)
print(resp.choices[0].message.content)
```

### 4. Handy flags
- `-c 8192` — set context window size (tokens).
- `-t 8` — number of CPU threads (defaults are usually fine on Apple Silicon).
- `--host 0.0.0.0` — expose the server to other devices on your LAN.
- `-ngl 0` — force CPU-only (useful for A/B testing GPU vs. CPU).

### 5. Benchmark your setup
```bash
llama-bench -m ~/models/my-model.Q4_K_M.gguf
```
On M3/M4 Macs a well-quantized small model commonly runs at 50–100+ tokens/sec
with Metal offload, so `llama-bench` is a quick way to confirm you're actually
using the GPU.

### Troubleshooting
- **Out of memory / model won't load** — pick a smaller quant (e.g. `Q4_K_M`),
  reduce `-c`, or lower `-ngl` to keep some layers on CPU.
- **Port already in use** — change `--port`.
- **Client can't connect from another machine** — start the server with
  `--host 0.0.0.0` and allow the port through the macOS firewall.

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [llama.cpp README — quickstart & server (ggml-org)](https://github.com/ggml-org/llama.cpp) — web/official · 0
- [All You Need to Start Using llama.cpp](https://xhinker.medium.com/all-you-need-to-start-using-llama-cpp-e58a8a23c3a3) — web/Medium · 0
- [Getting Started with LLaMA.cpp — Complete Installation Guide](https://llama-cpp.com/getting-started/) — web/llama-cpp.com · 0

## Related
- [[strategies/tutorials/2026-08-05-install-llama-cpp-on-macos-with-homebrew.md|Install llama.cpp on macOS with Homebrew]]
- [[strategies/tutorials/2026-08-05-build-llama-cpp-from-source-on-apple-silicon-with-metal.md|Build llama.cpp from source on Apple Silicon with Metal]]
