<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0012 — Semantic Scholar keyword-search adapter](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0012-semantic-scholar-adapter.md)**
<!-- docket:backlink:end -->

# Semantic Scholar adapter — results
Change: #12 · Branch: feat/semantic-scholar-adapter · PR: <set at PR open> · Plan: docs/superpowers/plans/2026-08-07-semantic-scholar-adapter.md · ADRs: none

## Live verification (Semantic Scholar Graph API)

The spec's build-time live check — one real query against the unkeyed
`https://api.semanticscholar.org/graph/v1/paper/search` endpoint — was performed.
No API key was used (none was available; none was printed or committed). The shared,
aggressively-throttled unkeyed pool returned **HTTP 429** on every attempt across two
queries (`"LLM agents"`, `"retrieval augmented generation"`), including three retries
with an 8s inter-attempt backoff:

| Query | Attempts | Result | Items returned |
|---|---|---|---|
| `LLM agents` | 1 | 429 (throttled pool) | 0 (fail-soft) |
| `retrieval augmented generation` | 3 (with 8s backoff) | 429 on all | 0 (fail-soft) |

This is the **expected** shared-pool behavior called out in the spec and the run brief —
and it exercises exactly the path the adapter must handle: on a 429 the adapter backs off
once, retries once, and if still throttled skips that query and returns `[]` for it,
**never aborting the sweep**. The live 429 body shape (`{"message": "...", "code": "429"}`)
matched the adapter's `status_code == 429` handling. No LLM/OpenRouter step was needed —
this change is a pure fetch/map adapter with no evaluation stage in its verification.

No config was flipped for the live run (the query was issued directly, not through a
sweep), so there is nothing to revert; no vault artifacts were produced.

## Test suite

`uv sync --extra dev` then `uv run python -m pytest` in the feature worktree:
**209 passed** (180 baseline + 24 `test_fetcher_semantic_scholar` + 5 new
`test_build_adapters` cases), no `deepeval`/`TracerProvider` crash, no `trafilatura`
ImportError (the `pytest-shim-and-venv-provisioning` learning held).

## Verify (human)

- [ ] The unkeyed shared pool is heavily throttled; a **free `S2_API_KEY`** (env; sent as
      `x-api-key`) is strongly recommended before relying on this source in a production sweep.
      `.env.example` documents it as optional. Without a key the adapter fail-soft-skips under load.
- [ ] Confirm `sources.semantic_scholar` in `config.yml` (`enabled: true`, `max_per_query: 10`)
      matches your intended breadth; `s2_queries` defaults to `arxiv_queries` — uncomment the
      `s2_queries` block to diverge them.
- [ ] Optionally run one live query with a real key to observe the 200-path mapping
      (tldr-over-abstract body, arXiv-URL preference, citationCount engagement) end-to-end.

## Findings

- **Live 429 confirms the fail-soft contract, not a defect.** The unkeyed pool would not
  serve a single 200 during the build window; the adapter's backoff-then-skip kept it a
  polite citizen and returned cleanly. The 200-path mapping is covered by mocked tests
  (`test_mapping_*`, `test_arxiv_url_preference`, `test_429_retry_then_success`).
- **Review outcome: clean.** The whole-branch review found no blocking or should-fix issues.
  Two nice-to-have test-coverage gaps it flagged were folded in (commit strengthening the
  polite-sleep gating and `externalIds` non-dict / missing-url fallback edges).

## Follow-ups

- None minted (auto-capture disabled). Out-of-scope future work noted in the spec — S2
  Recommendations loop, SPECTER2 embeddings, OpenAlex — remains separate stubs/changes.
