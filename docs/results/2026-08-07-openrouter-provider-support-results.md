<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0008 — OpenRouter provider support — full-system alternative to the Anthropic API](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0008-openrouter-provider-support.md)**
<!-- docket:backlink:end -->

# OpenRouter provider support — results
Change: #8 · Branch: feat/openrouter-provider-support · PR: (opened at close-out) · Plan: docs/superpowers/plans/2026-08-06-openrouter-provider-support-plan.md · ADRs: (see change file)

## Live end-to-end verification (OpenRouter)

The spec's "fully test the system" requirement — a live sweep on OpenRouter, no Anthropic credit needed — was run for real and passed.

- **Provider / model:** `llm.provider: openrouter`, default model `anthropic/claude-haiku-4.5` (via OpenRouter's OpenAI-compatible chat-completions API). The Anthropic key has no credit; this run needed none.
- **Command:** `uv run python cli.py sweep --lookback-days 3` (run with `config.yml` temporarily set to `provider: openrouter`; the committed default remains `provider: anthropic` and was restored after the run).
- **Outcome:** `Sweep complete. 93 new strategies documented.` (exit 0)

### Evidence each LLM path completed via OpenRouter

- **Dynamic query generation** (`SearchQueryGenerator._dynamic_queries`): a direct live probe with `llm_cfg={'provider': 'openrouter'}` returned 3 model-generated queries in addition to the fixed anchor — e.g. `speculative decoding LLM inference`, `adaptive compute scaling transformers`, `retrieval augmented generation improvements`. Proves an OpenRouter completion succeeded.
- **Evaluation** (`Evaluator` classify/score/validate): newly written notes carry a classified `type` (research/release/news/benchmark/tutorial), a numeric `score` in 1-10, the correct `score_label`, and a `category` for research items — all produced by the three-pass evaluator. Sample frontmatter:
  - `research` · `score: 6` · `score_label: novelty` · `category: use-case` · `tags: [research, use-case]` ("Multimodal Large Language Models: A Survey")
  - `research` · `score: 7` · `score_label: novelty` · `category: architecture` · `tags: [research, architecture]` ("Continual Learning in Transition")
- **Note synthesis** (`NoteSynthesizer`): above-threshold notes have populated `## Summary` / `## How It Works` / `## Why It Matters` sections with grounded prose (not the template fallback) and `content_source: full`.
- **Vault landing:** 93 notes written across the type subdirectories (research/benchmarks/news/releases/tutorials), each with sane content type, score, and tags.

### Non-fatal warnings observed (expected; unrelated to the provider)

- Several `[warn] enrich failed ... 403/404` for paywalled or blocked source sites (openai.com, medium.com, sciencedirect.com, a dead deepgrove.ai link) — enrichment is fail-soft and falls back to the item body; not an LLM/provider error.
- `[warn] BING_SEARCH_API_KEY not set` / `SERPAPI_KEY not set` — those search backends self-skip when unconfigured; only Tavily (key present) ran. Not a provider error.

No OpenRouter/provider errors occurred during the run.

## Findings

- **Backward compatibility preserved.** An absent `llm:` config section resolves to `provider: anthropic` + the default model `claude-haiku-4-5-20251001` (today's constant). The committed `config.yml` default stays `anthropic`; switching to OpenRouter is a one-line config change plus `OPENROUTER_API_KEY` in `.env`.
- **Architecture decision — injected `LLMClient` with a config-driven factory.** Each call-site class (`Evaluator`, `NoteSynthesizer`, `SourceDiscovery`, `SearchQueryGenerator`) gained an optional `*, client=None, llm_cfg=None` and builds via `agent.llm.get_client({"llm": llm_cfg or {}})` when no client is injected; tests inject a fake `LLMClient` rather than patching the `anthropic` SDK. This is captured as an ADR (see the change's `adrs:`).
- **Test/venv provisioning tell (learnings `pytest-shim-and-venv-provisioning`).** The suite is run as `uv run python -m pytest` after `uv sync --extra dev`; a bare `pytest` loads a crashing global `deepeval` plugin. Followed throughout; full suite is green (114 passed).
- **PR #7 (change 0006, `llm-topic-tags`) reconcile note.** 0006's unmerged `_tag_batch` routes through the same `Evaluator._call` this change abstracted, so its rebase onto a merged 0008 picks up the `LLMClient` abstraction automatically — no coordination change was needed here.

## Verify (human)

- [ ] (Optional) Re-run the live OpenRouter sweep locally if desired: set `config.yml` `llm.provider: openrouter`, ensure `OPENROUTER_API_KEY` is in `.env`, run `uv run python cli.py sweep --lookback-days 3`, then revert `config.yml`.
- [ ] Confirm the committed `config.yml` default is `provider: anthropic` (it is; the temporary openrouter flip was reverted before commit).

## Follow-ups

- None required for this change. (Per-call-site model overrides, cross-provider retry/fallback, streaming/tool-use are explicit non-goals in the spec.)
