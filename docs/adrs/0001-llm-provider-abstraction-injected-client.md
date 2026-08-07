---
id: 1
slug: llm-provider-abstraction-injected-client
title: LLM provider abstraction via an injected LLMClient + config-driven factory (not an SDK adapter or global client)
status: Accepted
date: 2026-08-06
supersedes: []
reverses: []
relates_to: []
change: 8
---

## Context

Every LLM call site (`agent/evaluator.py`, `agent/synthesizer.py`, `agent/tools/search_query_generator.py`, `agent/tools/source_discovery.py`) hard-coded the `anthropic` SDK and a duplicated `MODEL = "claude-haiku-4-5-20251001"` constant, locking the system to one provider and one billing relationship.

The goal (change 0008, openrouter-provider-support) was to run the whole system on OpenRouter (OpenAI-compatible chat-completions) as a config-selected alternative, with an absent config leaving today's Anthropic behavior byte-identical.

Options considered:

- (a) Adopt the `openai` SDK or `litellm` as a universal client.
- (b) A thin in-house abstraction reached via `httpx` (already a dependency).
- (c) A global/singleton client vs. dependency-injected per-call-site clients.

## Decision

Introduce `agent/llm.py`:

- An `LLMClient` **Protocol** with a single `complete(prompt, max_tokens) -> str` method.
- An `AnthropicClient` wrapping the existing SDK.
- An `OpenRouterClient` using `httpx` (already a dependency — no new deps) against the REST chat-completions endpoint.
- A factory `get_client(cfg) -> LLMClient` reading an `llm:` config section (provider default `anthropic`; optional model with per-provider defaults) and resolving the provider's API key from the environment. An unknown provider raises `ValueError` at startup (fail loud).

Each call-site class accepts an optional injected client via `*, client=None, llm_cfg=None`, constructing one through the factory only when no client is injected. Config (`llm_cfg`) is threaded from `cli.py` through scheduler / regenerator / reclassifier. `api_key` params are retained for caller backward-compat.

Rejected:

- Adopting `openai`/`litellm` — keeps the dependency surface unchanged; the single-shot prompt->text need is tiny.
- A global client — dependency injection makes call sites unit-testable with a fake `LLMClient` instead of patching the `anthropic` SDK, and avoids hidden global state.

## Consequences

- Enables provider flexibility (Anthropic or OpenRouter, and easily more) via one config knob; per-provider default models keep switching provider a transport change, not a behavior change.
- Backward compatible: absent `llm:` => anthropic + the old model constant, byte-identical.
- Tests inject a fake `LLMClient` rather than patching `anthropic`, simplifying the call-site tests.
- Costs: a small amount of wiring to thread `llm_cfg`; the `api_key` params become partly vestigial (kept for compat); no cross-provider retry/fallback, streaming, tool use, or per-call-site model overrides (explicit non-goals).
- Validated by a live end-to-end OpenRouter sweep (93 notes) plus a green mocked unit suite (114 passed).
