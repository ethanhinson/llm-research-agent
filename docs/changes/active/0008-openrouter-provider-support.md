---
id: 8
slug: openrouter-provider-support
title: OpenRouter provider support — full-system alternative to the Anthropic API
status: in-progress
priority: medium
type: feat
created: 2026-08-06
updated: 2026-08-07
depends_on: [7]
related: [7]
discovered_from: []
adrs: []
spec: docs/superpowers/specs/2026-08-06-openrouter-provider-support.md
plan: docs/superpowers/plans/2026-08-06-openrouter-provider-support-plan.md
results:
trivial: false
auto_groomable: false
branch: feat/openrouter-provider-support
claimed_at: 2026-08-07T02:52:47Z
pr:
blocked_by:
reconciled: true
---

## Artifacts

<!-- docket:artifacts:start (generated — do not hand-edit) -->
| Artifact | Link |
|---|---|
| Spec | [2026-08-06-openrouter-provider-support.md](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/superpowers/specs/2026-08-06-openrouter-provider-support.md) |
| Plan | [2026-08-06-openrouter-provider-support-plan.md](https://github.com/ethanhinson/llm-research-agent/blob/feat/openrouter-provider-support/docs/superpowers/plans/2026-08-06-openrouter-provider-support-plan.md) |
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

### 2026-08-07 — reconciled against origin/main

Verified the spec against current code on `origin/main` (authoritative), cited/recent ADRs (the ADR ledger is empty — no ADRs to fold in), the `related: [7]` change, and the learnings ledger. The spec is accurate and remains build-ready as written — no scope change required. Findings:

- **Four call sites confirmed on `origin/main`, exactly as the spec lists:** `agent/evaluator.py` (`Evaluator._call`, routing classify/score/validate batches), `agent/synthesizer.py` (`NoteSynthesizer._call` — the note synthesizer from change #7, now merged and `done` at `archive/2026-08-07-0007-full-content-note-synthesis.md`), `agent/tools/search_query_generator.py` (`SearchQueryGenerator._dynamic_queries`), and `agent/tools/source_discovery.py` (`SourceDiscovery`). `agent/topic_filter.py`'s "anthropic" token is a keyword-regex string, not an LLM call — not a call site.
- **PR #7 (change 0006, `llm-topic-tags`) reconcile note:** change 0006's PR (GitHub #7, branch `feat/llm-topic-tags`) is `implemented`/unmerged and is NOT on `origin/main`. It adds a fourth Anthropic call inside `Evaluator` (`_tag_batch`) that routes through the same `Evaluator._call`. This change therefore migrates the call sites **as they exist on `origin/main`** — `Evaluator._call` is the single Anthropic routing point and covers all of Evaluator's batches. When change 0006's PR later rebases onto a merged 0008, its `_tag_batch` picks up the `LLMClient` abstraction **automatically** with no extra work, because it calls the already-abstracted `_call`. No coordination edit is needed here; recording it so the 0006 rebase is expected to be clean.
- **Model constants:** `MODEL = "claude-haiku-4-5-20251001"` is defined in three modules (evaluator, search_query_generator, source_discovery) and imported by synthesizer from evaluator. The spec's plan to remove the per-module constants and drive the model from the `llm:` config (per-provider defaults) holds.
- **Wiring / factory integration point:** `cli.py` reads `ANTHROPIC_API_KEY` at four commands and threads `api_key` down through `scheduler.run_sweep`/`search_sweep`/`start_scheduler`, `Regenerator`, and `Reclassifier` to the client constructors. `cli.py` loads `config.yml` but does not currently thread the parsed `cfg` into the client-constructing modules. The migration must thread the resolved `LLMClient` (or the `llm:` config + provider key) through these same paths. `search_query_generator.py`'s `if dynamic_enabled and self._api_key:` guard (line 33) generalizes to "the configured provider's key is present," per the spec.
- **Dependencies:** `httpx>=0.27` is already a direct dependency (used in `agent/enricher.py`); the OpenRouter backend needs no new dependency, matching the spec.
- **Test/venv provisioning (learnings `pytest-shim-and-venv-provisioning`):** the suite must be run as `uv run python -m pytest` after `uv sync --extra dev`; a bare `pytest` loads a crashing global `deepeval` plugin (a `TracerProvider.get_tracer()` TypeError) and a fresh venv lacks project deps (`trafilatura`). This is environment pollution, not a red suite — carried into the plan so build/test steps use the canonical command.
- **Live end-to-end (spec §"Live end-to-end"):** now POSSIBLE and EXPECTED — a working `OPENROUTER_API_KEY` is present in `.env`. The live sweep runs with `llm.provider: openrouter` (the Anthropic key has no credit), verifying dynamic queries + evaluation + synthesis + vault notes end to end, with the outcome recorded in the results file. Not deferred.

Auto-capture is disabled (`AUTO_CAPTURE_ENABLED=false`); no adjacent follow-up work surfaced that would warrant a stub — all findings above are in-scope for this change.
