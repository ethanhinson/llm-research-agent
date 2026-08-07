<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0009 — Unify article intake behind a SourceAdapter layer](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0009-source-adapter-layer.md)**
<!-- docket:backlink:end -->

# Source Adapter Layer Implementation Plan

> **For agentic workers:** Implement this plan task-by-task. Each task is a red→green→refactor cycle ending in one commit. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify article intake behind a single `SourceAdapter` protocol + config-driven `build_adapters` factory — the same protocol-plus-factory idiom as ADR-0001's `LLMClient`. A **pure refactor**: same sources, same items kept, proven by tests. Deletes the sweep-level substring engagement allowlists (moving engagement policy into each adapter) and removes the `reddit_threshold` `NameError` landmine (`scheduler.py:110`) with them, so change 0010's new sources become one adapter class plus config each.

**Architecture:** A new `agent/fetchers/base.py` defines a `SourceAdapter` Protocol (`name: str`, `fetch() -> list[RawItem]`). Existing fetchers gain a `name` and conform. `MultiSearchFetcher` becomes an adapter wrapping the internal `SearchClient` list. A `build_adapters(cfg, *, kind)` factory constructs the adapter set per kind (`"sweep"` → HN + arXiv + RSS feeds; `"search"` → the multi-search adapter), reading existing config knobs. `run_sweep` / `search_sweep` stop hard-coding fetcher construction and instead iterate `build_adapters(...)` with the existing per-adapter fail-soft `try/except`; the sweep-level engagement allowlists are deleted. The two sweep entry points, their schedules, and the downstream funnel (dedup → topic filter → cross-validate → evaluate → write) are unchanged.

**Tech Stack:** Python 3.12, `pytest` + `pytest-mock`, `pyyaml`. No new dependencies.

## Global Constraints

- **Pure refactor — behavior identical.** Same sources, same items kept, same funnel order and per-adapter fail-soft. The proof is the test suite: the existing suite keeps passing (with only construction-site / patch-target updates where a test reaches into `agent.scheduler`), plus new tests for the protocol, factory, and the removed trap.
- **Engagement policy moves into the adapter.** Each adapter returns only items that pass its own threshold. HN already does this (its API `numericFilters` and its post-filter both apply `points >= threshold`); arXiv/web/search have no engagement gate today (arxiv/web/search items pass unconditionally), so their adapters keep returning everything they fetch. **Net effect on real runs is nil** — the sweep-level allowlist was redundant with HN's own filter for real data and a silent-drop trap for anything else.
- **The `reddit_threshold` landmine is removed, not fixed.** Deleting `run_sweep`'s `after_engagement` allowlist deletes the `reddit_threshold` reference (`scheduler.py:110`). No Reddit adapter is added (out of scope; the landmine is removed with the allowlist).
- **Keep `agent.scheduler` symbols patchable.** The existing sweep tests patch `agent.scheduler.HNFetcher.fetch`, `agent.scheduler.ArxivFetcher.fetch`, `agent.scheduler.WebFetcher.fetch`, and `agent.scheduler.MultiSearchFetcher.fetch` by attribute. The factory must construct adapters from classes that remain importable under those names in `agent.scheduler` (re-export / import them there), OR the sweep tests' patch targets and the parity-drop test are updated (this plan does the latter where the semantics change — see Task 5). Either way the suite ends green.
- **No config schema change.** The factory reads existing knobs only (`thresholds.hn_points`, `sources.feeds`, `search.max_results_per_query`, etc.). No new keys.
- **Test command (CANONICAL — learnings `pytest-shim-and-venv-provisioning`):** provision with `uv sync --extra dev`, then run **`uv run python -m pytest`**. A bare `pytest` resolves to a global pyenv shim that autoloads a crashing global `deepeval` plugin (a `TracerProvider.get_tracer()` TypeError), and a fresh venv lacks project deps (`trafilatura`). A `TracerProvider.get_tracer()` TypeError or `ModuleNotFoundError: trafilatura` at pytest **startup** is environment pollution, NOT a red suite — provision and re-run; never treat it as a code failure or dispatch integration-repair for it.
- **No live-LLM check required.** This is a same-sources refactor; suite parity is the proof (learnings `live-testing-catches-what-mocks-miss`: a live run proves provider swaps, not a mechanical refactor).

---

### Task 1: Provision the venv + baseline the suite (setup — no commit of its own)

**Files:** none (environment only).

- [ ] **Step 1: Provision dev deps**

Run: `uv sync --extra dev`
Expected: succeeds; `pytest`, `pytest-mock`, `trafilatura`, project deps available in the project venv.

- [ ] **Step 2: Baseline green before any change**

Run: `uv run python -m pytest -q`
Expected: all existing tests PASS. Record the count (it is the parity anchor). If you see a `TracerProvider.get_tracer()` TypeError or `ModuleNotFoundError: trafilatura` at startup, that is environment pollution — you ran a bare `pytest` or skipped `uv sync`; re-run the canonical command.

---

### Task 2: `agent/fetchers/base.py` — the `SourceAdapter` protocol

**Files:**
- Create: `agent/fetchers/base.py`
- Test: `tests/test_source_adapter.py`

**Interfaces:**
- Produces (later tasks rely on these EXACT names):
  - `class SourceAdapter(Protocol):` with `name: str` and `def fetch(self) -> list[RawItem]: ...`
- Consumes: `agent.models.RawItem`.

- [ ] **Step 1: Write a failing conformance test**

A `runtime_checkable`-based or structural test that a trivial object exposing `name: str` + `fetch() -> list[RawItem]` satisfies the protocol, and that each *shipped* fetcher class (added in Task 3) will be checked in Task 3's test. Keep this task's test to the protocol shape itself (a fake conforming class passes; a class missing `name` or `fetch` does not).

Suggested:
```python
# tests/test_source_adapter.py
from agent.fetchers.base import SourceAdapter
from agent.models import RawItem

class _Conforms:
    name = "x"
    def fetch(self) -> list[RawItem]:
        return []

def test_conforming_object_is_source_adapter():
    assert isinstance(_Conforms(), SourceAdapter)  # protocol is runtime_checkable
```

- [ ] **Step 2: Implement the protocol**

```python
# agent/fetchers/base.py
from typing import Protocol, runtime_checkable
from agent.models import RawItem

@runtime_checkable
class SourceAdapter(Protocol):
    name: str
    def fetch(self) -> list[RawItem]: ...
```

- [ ] **Step 3: Green + commit.** Run the canonical suite; commit `feat(0009): add SourceAdapter protocol`.

---

### Task 3: Migrate the four fetchers to the protocol (add `name`)

**Files:**
- Modify: `agent/fetchers/hackernews.py` (`HNFetcher`), `agent/fetchers/arxiv.py` (`ArxivFetcher`), `agent/fetchers/web.py` (`WebFetcher`), `agent/fetchers/multi_search.py` (`MultiSearchFetcher`)
- Test: extend `tests/test_source_adapter.py`

**Interfaces / constraints:**
- Each fetcher gains a `name: str` attribute so it conforms to `SourceAdapter`. Suggested values: `HNFetcher.name = "hackernews"`, `ArxivFetcher.name = "arxiv"`, `WebFetcher.name = "web"` (its items already carry per-feed `source=f"web/{feed['name']}"`; the adapter-level `name` is the source *family*), `MultiSearchFetcher.name = "search"`.
- **Do NOT change `fetch()` behavior or the per-item `RawItem.source` strings.** `name` is additive metadata; item `source` values stay exactly as today (`"hackernews"`, `"arxiv"`, `"web/<feed>"`, `"search/<backend>"`).
- HN already applies its own `points >= threshold` gate in `fetch()` — leave it. arXiv/web/search return all fetched items (no engagement gate) — leave them; that IS today's real-run behavior once the redundant sweep allowlist is gone.

- [ ] **Step 1: Failing test** — parametrize `isinstance(fetcher_instance, SourceAdapter)` over each of the four classes (constructing with minimal args / the existing constructors), asserting each conforms and exposes the expected `name`.
- [ ] **Step 2: Add `name` to each class.**
- [ ] **Step 3: Green + commit** `feat(0009): fetchers conform to SourceAdapter (add name)`.

---

### Task 4: `build_adapters(cfg, *, kind)` factory

**Files:**
- Modify: `agent/fetchers/base.py` (or a new `agent/fetchers/factory.py` — keep it in `base.py` to mirror ADR-0001's single-module idiom unless it reads cleaner split; either is fine, note the choice in the commit)
- Test: `tests/test_build_adapters.py`

**Interfaces:**
- `def build_adapters(cfg: dict, *, kind: str) -> list[SourceAdapter]`
  - `kind="sweep"` → `[HNFetcher(threshold=cfg["thresholds"]["hn_points"], **lb), ArxivFetcher(**lb)]` plus `WebFetcher(feeds=feeds, **lb)` **only when** `feeds` is non-empty — matching today's `run_sweep` guard (`if feeds:`). The lookback-window threading (`lb = {} if lookback_days is None else {"lookback_days": lookback_days}`) is preserved: accept `lookback_days` as a keyword on `build_adapters` (default `None`) so the factory owns the same conditional-widen logic `run_sweep` has today.
  - `kind="search"` → `[MultiSearchFetcher(clients, queries, max_results_per_query=...)]`. Because the search adapter needs the runtime `clients`, `queries`, and `max_results_per_query`, either (a) pass them through `build_adapters` as keyword args, or (b) keep the multi-search construction in `search_sweep` and have `build_adapters(kind="search")` return the assembled adapter given those inputs. Choose the shape that keeps `search_sweep`'s existing behavior byte-identical; document the chosen signature in the commit and in the factory docstring.
  - Unknown `kind` → raise `ValueError(f"unknown adapter kind: {kind!r}")` (fail loud, mirroring ADR-0001's unknown-provider posture).
  - Reads existing config knobs only; adds no new keys.

- [ ] **Step 1: Failing tests** — `kind="sweep"` returns HN + arXiv (+ web only when feeds present); HN threshold and lookback thread through; `kind="search"` returns the multi-search adapter with `max_results_per_query` threaded; unknown kind raises `ValueError`. Assert the returned objects satisfy `SourceAdapter`.
- [ ] **Step 2: Implement the factory.**
- [ ] **Step 3: Green + commit** `feat(0009): add build_adapters factory`.

---

### Task 5: Rewire the sweeps + delete the engagement allowlists

**Files:**
- Modify: `agent/scheduler.py` (`run_sweep`, `search_sweep`)
- Modify: `tests/test_scheduler.py`, `tests/test_search_sweep.py` (patch-target / parity updates)

**Interfaces / constraints:**
- `run_sweep`: replace the hard-coded `raw.extend(_fetch(lambda: HNFetcher(...).fetch()))` block with a loop over `build_adapters(...kind="sweep"...)`, wrapping each adapter's `.fetch()` in the existing `_fetch` fail-soft helper. **Delete** the `after_engagement = [...]` allowlist entirely — the funnel becomes `raw → dedup → topic → cross-validate → evaluate → write`. This removes the `reddit_threshold` `NameError`.
- `search_sweep`: replace the hard-coded `MultiSearchFetcher(...)` construction with `build_adapters(...kind="search"...)` (threading `clients`, `queries`, `max_results_per_query` per Task 4's chosen signature). **Delete** its `after_engagement` allowlist too (`search/*`, `web/`, HN gates) — those items already pass today; deletion is behavior-preserving for real runs and removes the second stringly-typed trap.
- Keep the class symbols importable from `agent.scheduler` (the tests patch `agent.scheduler.HNFetcher.fetch` etc.). Prefer: have `build_adapters` import the fetcher classes, and `scheduler.py` continues to import them (so `agent.scheduler.HNFetcher` resolves and `mocker.patch("agent.scheduler.HNFetcher.fetch")` still hits the object the factory constructs). If the factory lives in a different module, ensure the patched attribute and the constructed class are the same object.

- [ ] **Step 1: Update the parity test that encodes the OLD allowlist semantics.**

`tests/test_scheduler.py::test_run_sweep_filters_and_writes` currently mocks `HNFetcher.fetch` to return a below-threshold item (engagement=10) and asserts only the above-threshold item is written — a drop the *sweep-level* allowlist did, not the fetcher. After this refactor, engagement policy lives in the adapter, and a mock that replaces `HNFetcher.fetch` wholesale bypasses that gate. Update this test to reflect the new architecture: either (a) let the adapter's own filter do the drop by mocking at the API layer (`httpx.get`) so the real `HNFetcher.fetch` applies `points >= threshold`, or (b) re-express the test as "the funnel writes what the adapters return" (both items written, since the mock returns both and no sweep-level gate remains) — the honest post-refactor contract. Pick (b) if simpler and rename the test to describe the new behavior; the point is the test asserts the *true* new funnel, not the deleted allowlist. Document the choice in the commit message.

- [ ] **Step 2: Rewire `run_sweep` + `search_sweep`; delete both `after_engagement` blocks.**
- [ ] **Step 3: Update any sweep-test patch targets** if the factory changed where the fetcher classes are constructed, so `agent.scheduler.<Fetcher>.fetch` patches still apply.
- [ ] **Step 4: Green + commit** `refactor(0009): sweeps iterate build_adapters; delete engagement allowlists (removes reddit_threshold landmine)`.

---

### Task 6: Regression + full-suite parity gate

**Files:**
- Test: `tests/test_source_adapter.py` or a new `tests/test_sweep_no_silent_drop.py`

- [ ] **Step 1: Regression test for the removed trap.** An adapter whose items carry an *unknown* `source` string (one that would NOT have matched any old allowlist substring, e.g. `source="reddit"` or `source="mastodon"`) flows all the way through the funnel to the writer with no `NameError` and no silent drop (given topic-filter / score mocks that keep it). This is the exact trap this refactor exists to remove — assert it is gone.
- [ ] **Step 2: Full-suite parity.** Run `uv run python -m pytest` (canonical). Expected: green, count ≥ the Task 1 baseline (baseline minus any intentionally-rewritten test, plus the new protocol/factory/regression tests). No `reddit_threshold` reference remains (`grep -rn reddit_threshold agent/` returns nothing).
- [ ] **Step 3: Commit** any test-only additions `test(0009): regression — unknown-source item flows through, no silent drop`.

---

## Definition of done

- `agent/fetchers/base.py` defines `SourceAdapter` + `build_adapters`.
- The four fetchers conform (carry `name`); `MultiSearchFetcher` is an adapter over the internal `SearchClient` list.
- `run_sweep` / `search_sweep` iterate `build_adapters(...)`; both sweep-level engagement allowlists are deleted; `reddit_threshold` is gone (`grep` clean).
- Sweep entry points, schedules, item `source` strings, and the funnel order are unchanged.
- `uv run python -m pytest` is green; the regression test proves an unknown-source item flows through with no NameError and no silent drop.
- No new config keys, no new dependencies, no new source (0010's job).
