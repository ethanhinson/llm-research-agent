<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0008 — OpenRouter provider support — full-system alternative to the Anthropic API](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/archive/2026-08-07-0008-openrouter-provider-support.md)**
<!-- docket:backlink:end -->

# OpenRouter Provider Support — Design Spec

**Date:** 2026-08-06
**Status:** Approved

---

## Overview

The agent currently hard-codes the `anthropic` SDK at every LLM call site. This change introduces a small provider abstraction so the whole system can run against **OpenRouter** (OpenAI-compatible chat-completions API) as an alternative to the direct Anthropic API, selected via configuration. The change is validated with mocked unit tests for both backends plus a live end-to-end sweep run against the real OpenRouter API.

Call sites to migrate (four, once change #7's synthesis PR merges — this change `depends_on: [7]`):

- `agent/evaluator.py` — `Evaluator._call()` (classify / score / validate / tag batches)
- `agent/tools/search_query_generator.py` — `SearchQueryGenerator._dynamic_queries()`
- `agent/tools/source_discovery.py` — source discovery suggestions
- the note synthesizer introduced by change #7 (path per the merged PR)

---

## Provider abstraction — `agent/llm.py`

A minimal completion interface; no new dependencies (OpenRouter is reached via `httpx`, already a dependency).

```python
class LLMClient(Protocol):
    def complete(self, prompt: str, max_tokens: int) -> str: ...
```

- **`AnthropicClient`** — wraps the existing `anthropic.Anthropic` usage: `messages.create(model=..., max_tokens=..., messages=[{"role": "user", "content": prompt}])`, returning `message.content[0].text` (empty string on a malformed/empty response, preserving today's behavior).
- **`OpenRouterClient`** — `httpx.post("https://openrouter.ai/api/v1/chat/completions", ...)` with:
  - headers: `Authorization: Bearer <OPENROUTER_API_KEY>`, plus the conventional `HTTP-Referer` / `X-Title` attribution headers (repo URL / "llm-research-agent")
  - body: `{"model": ..., "max_tokens": ..., "messages": [{"role": "user", "content": prompt}]}`
  - returns `choices[0].message.content`; empty string on a malformed/empty response
  - a sensible timeout (30s) and `raise_for_status()` so HTTP errors surface as exceptions, matching how anthropic SDK errors surface today

### Factory

```python
def get_client(cfg: dict) -> LLMClient
```

Reads the `llm:` config section (below), resolves the API key from the environment (`ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY`), and returns the right backend. An unknown `provider:` value raises a clear `ValueError` at startup — fail loud, not mid-sweep.

All call sites switch from constructing `anthropic.Anthropic` to accepting/constructing an `LLMClient` via the factory. The per-module `MODEL` constants are removed; the model comes from config with per-provider defaults.

---

## Configuration

New `config.yml` section:

```yaml
llm:
  provider: anthropic        # anthropic (default) | openrouter
  model:                     # optional; per-provider default when unset
```

- Per-provider default models: `anthropic` → `claude-haiku-4-5-20251001` (today's constant); `openrouter` → `anthropic/claude-haiku-4.5` (the same model via OpenRouter's slug), so switching provider alone changes transport, not behavior.
- An absent `llm:` section ⇒ anthropic + default model — existing deployments keep working byte-identically.
- API keys stay in `.env`: add `OPENROUTER_API_KEY` to `.env.example`.
- The existing "dynamic queries only when an API key is present" guard in `SearchQueryGenerator` generalizes to "when the *configured provider's* key is present."

---

## Testing

### Unit (mocked; run in CI / `pytest`)

- Factory: provider selection, per-provider default models, explicit model override, unknown-provider `ValueError`, missing-key behavior.
- `OpenRouterClient`: request shape (URL, auth header, body), happy-path text extraction, malformed-response → empty string, HTTP error propagation (mock `httpx`).
- `AnthropicClient`: parity of the extraction behavior with today's inline code.
- Call-site tests updated to inject a fake `LLMClient` instead of patching `anthropic`.

### Live end-to-end (the "fully test the system" requirement)

With `llm.provider: openrouter` and a real `OPENROUTER_API_KEY`:

1. Run a full sweep (`cli.py` sweep path) end to end.
2. Verify dynamic query generation, evaluation (classify/score/validate/tags), and note synthesis all completed via OpenRouter (no Anthropic key needed in the environment for the run).
3. Verify notes land in the vault with sane content types, scores, and tags.
4. Record the run outcome (counts, any provider errors) in the change's results file.

The live run is a build-time verification step, not a committed CI test — it needs a funded key.

---

## Out of scope

- Streaming, tool use, or multi-turn conversations — every call site is single-shot prompt → text.
- Per-call-site model overrides (one global `llm.model` knob is enough for now).
- Retry/fallback across providers (e.g. OpenRouter down → Anthropic) — the existing per-site error handling (non-fatal dynamic queries, etc.) is preserved as-is.
- Adopting the `openai` SDK or `litellm` — decided against; `httpx` keeps the dependency surface unchanged.
