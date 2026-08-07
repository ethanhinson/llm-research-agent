<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0009 — Unify article intake behind a SourceAdapter layer](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/archive/2026-08-07-0009-source-adapter-layer.md)**
<!-- docket:backlink:end -->

# Source Adapter Layer — Design Spec

**Date:** 2026-08-07
**Status:** Approved

---

## Overview

Unify article intake behind a single **`SourceAdapter`** protocol + config-driven factory — the same protocol-plus-factory idiom as the `LLMClient` abstraction (ADR-0001). Today there are two half-protocols (an implicit `.fetch() -> list[RawItem]` shared by `HNFetcher`/`ArxivFetcher`/`WebFetcher`, and the formal `SearchClient` for Tavily/Bing/SerpAPI), and both sweep functions hard-code fetcher construction plus a stringly-typed engagement allowlist. This is a **pure refactor**: same sources, same items kept, proven by tests — it exists so that every *future* source (change 0010) is one adapter class plus config, not a two-function edit with a silent-drop trap.

## Problems being fixed

- `scheduler.py` `run_sweep` / `search_sweep` each hard-code fetcher construction and a substring-match engagement allowlist (`"web/" in item.source`, …). A new source must be added in multiple places or its items are **silently dropped** after fetching.
- `scheduler.py:110` references `reddit_threshold` — never defined; any item whose source contains "reddit" raises `NameError` mid-sweep. There is no Reddit fetcher (only a stale `.pyc`).
- No seam for change 0010's new sources.

## Design

### Protocol — `agent/fetchers/base.py`

```python
class SourceAdapter(Protocol):
    name: str                          # source id, e.g. "hackernews", "arxiv", "web/<feed>"
    def fetch(self) -> list[RawItem]: ...
```

**Engagement policy moves into the adapter**: each adapter returns only items that pass its own threshold (HN already does — its API call and post-filter both apply `points >= threshold`). The sweep-level engagement allowlists are **deleted**, which also removes the `reddit_threshold` landmine. The funnel becomes: fetch (per-adapter, fail-soft) → dedup → topic filter → cross-validate → evaluate → write.

### Migrations (no behavior change)

- `HNFetcher`, `ArxivFetcher`, `WebFetcher` — already conform; add `name`, register.
- `MultiSearchFetcher` — becomes an adapter wrapping the `SearchClient` list (it already exposes `fetch()`); `SearchClient` remains its internal protocol.

### Factory — `build_adapters(cfg, *, kind) -> list[SourceAdapter]`

Constructs the adapter set from config: `kind="sweep"` → HN + arXiv + RSS feeds (what `run_sweep` uses today); `kind="search"` → the multi-search adapter (what `search_sweep` uses). The two sweep entry points and their schedules are **unchanged** — they just iterate `build_adapters(...)` with the existing per-adapter fail-soft `try/except` instead of hard-coding construction.

### Config

No new keys required in this change. Existing knobs (`thresholds.hn_points`, `sources.feeds`, `search.*`) are read by the factory instead of by the sweeps.

## Testing

- Protocol-conformance test parametrized over every shipped adapter.
- Factory: adapter sets per `kind`, config threading (hn threshold, feeds, max_results).
- Sweep parity: `run_sweep`/`search_sweep` with faked adapters produce identical funnel behavior to today's tests (existing suite keeps passing with only construction-site updates).
- Regression: an adapter with an unknown `name` string flows through the funnel (no silent drop, no NameError) — the trap this refactor exists to remove.

## Out of scope

- Any new source (change 0010, depends on this).
- Reddit (deliberately not revived; the landmine is removed with the allowlist).
- Changing sweep cadences, the funnel order, or `SourceDiscovery` (0010 wires it in).
