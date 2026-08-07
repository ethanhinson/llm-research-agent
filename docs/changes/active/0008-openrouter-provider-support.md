---
id: 8
slug: openrouter-provider-support
title: OpenRouter provider support — full-system alternative to the Anthropic API
status: proposed
priority: medium
type: feat
created: 2026-08-06
updated: 2026-08-06
depends_on: [7]
related: [7]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-06-openrouter-provider-support.md
plan:
results:
trivial: false
auto_groomable: false
branch:
pr:
blocked_by:
reconciled: false
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-06-openrouter-provider-support.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-06-openrouter-provider-support.md) |
<!-- docket:artifacts:end -->

## Why

Every LLM call site hard-codes the `anthropic` SDK and a Claude Haiku model constant, so the system is locked to one provider and one billing relationship. OpenRouter fronts the same models (and many others) behind an OpenAI-compatible API, enabling provider flexibility, cost comparison, and model experimentation without code changes. The whole system should be provably runnable on OpenRouter end to end.

## What changes

- New `agent/llm.py` provider abstraction: a minimal `complete(prompt, max_tokens) -> str` interface with an Anthropic backend (existing SDK) and an OpenRouter backend (httpx against the chat-completions REST API — no new dependencies).
- All four LLM call sites (evaluator, dynamic query generator, source discovery, and the note synthesizer from #7) migrate to the abstraction via a config-driven factory.
- New `llm:` config section (`provider`, optional `model` with per-provider defaults); `OPENROUTER_API_KEY` added to `.env.example`. Absent config ⇒ today's Anthropic behavior, unchanged.
- Mocked unit tests for the factory and both backends; plus a live end-to-end sweep run on OpenRouter verifying queries, evaluation, synthesis, and vault notes, recorded in the results file.

## Out of scope

- Streaming, tool use, multi-turn calls; per-call-site model overrides.
- Cross-provider retry/fallback.
- `openai` SDK or `litellm` adoption (decided against in the spec).

## Reconcile log
