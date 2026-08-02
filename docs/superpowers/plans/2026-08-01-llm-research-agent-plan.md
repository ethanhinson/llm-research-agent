<!-- docket:backlink:start (generated — do not hand-edit) -->
| | |
|---|---|
| **Change** | [0001 — LLM Research Agent](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0001-llm-research-agent.md) |
<!-- docket:backlink:end -->

# Plan: LLM Research Agent

**Change:** 0001 — LLM Research Agent — Reddit/HN/arXiv monitor with Obsidian vault output
**Spec:** docs/superpowers/specs/2026-08-01-llm-research-agent-design.md

> ⚠️ `superpowers:writing-plans` unavailable in this runtime — plan authored inline (auto mode).

---

## Task 1 — Project scaffold + dependencies

Set up the Python project structure with `pyproject.toml`, `.env.example`, `config.yml`, `.gitignore` additions, and the empty package directories.

**Tests first:** Verify `python -m agent` importable; `python cli.py status` exits 0.

Files:
- `pyproject.toml`
- `config.yml`
- `.env.example`
- `agent/__init__.py`
- `agent/fetchers/__init__.py`
- `agent/tools/__init__.py`

---

## Task 2 — Data models + deduplicator

Define the shared `RawItem` dataclass and the `Deduplicator` class that maintains a JSON index (`vault/.index.json`) of documented strategy URLs and titles, using `thefuzz` for title fuzzy matching.

**Tests first:** Unit tests covering exact-URL dedup, fuzzy-title dedup (>90% threshold), and a new item that passes through.

Files:
- `agent/models.py`
- `agent/deduplicator.py`
- `tests/test_deduplicator.py`

---

## Task 3 — HN fetcher

Implement `agent/fetchers/hackernews.py` — calls the HN Algolia API (`hn.algolia.com/api/v1/search`) for stories tagged `story` with `points >= threshold`, maps them to `RawItem`.

**Tests first:** Unit test with a mocked HTTP response confirming correct field mapping and engagement filtering.

Files:
- `agent/fetchers/hackernews.py`
- `tests/test_fetcher_hn.py`

---

## Task 4 — Reddit fetcher

Implement `agent/fetchers/reddit.py` using PRAW. Iterates configured subreddits, fetches `hot` (limit 100), filters by upvote threshold, maps to `RawItem`.

**Tests first:** Unit test with a mocked PRAW submission confirming field mapping and threshold filter.

Files:
- `agent/fetchers/reddit.py`
- `tests/test_fetcher_reddit.py`

---

## Task 5 — arXiv fetcher

Implement `agent/fetchers/arxiv.py` using the `arxiv` client library. Searches `cs.AI + cs.CL + cs.LG`, last 7 days, returns all results (no engagement threshold for arXiv).

**Tests first:** Unit test with a mocked arxiv.Result confirming correct field mapping (engagement=0 for arXiv).

Files:
- `agent/fetchers/arxiv.py`
- `tests/test_fetcher_arxiv.py`

---

## Task 6 — Web fetcher

Implement `agent/fetchers/web.py` using `httpx`. Fetches generic RSS/Atom feeds or blog pages. Parses titles and URLs from feed entries; body is truncated to 2000 chars. Engagement defaults to 0.

**Tests first:** Unit test with a mocked HTTP response from a sample RSS feed.

Files:
- `agent/fetchers/web.py`
- `tests/test_fetcher_web.py`

---

## Task 7 — Cross-validator

Implement `agent/tools/cross_validate.py`. Groups a list of `RawItem`s by fuzzy-title similarity (>85% match → same group). Items in groups of size ≥ 2 are tagged `validated=True` and `sources_count` is set to the group size.

**Tests first:** Unit test with two items with near-identical titles from different sources → both validated; two items with dissimilar titles → both unvalidated.

Files:
- `agent/tools/cross_validate.py`
- `tests/test_cross_validate.py`

---

## Task 8 — Evaluator (Claude novelty scoring)

Implement `agent/evaluator.py`. Takes a list of `RawItem`s (post-filter, post-cross-validate) and calls Claude via the Anthropic SDK with a batch prompt to score each item 1–10 for novelty. Returns the items with `novelty` field set.

Source discovery also lives here: given the current source list + recent findings, ask Claude to suggest new sources. Returns a list of suggested source strings.

**Tests first:** Unit test with a mocked Anthropic client (monkeypatch) verifying correct prompt construction and score extraction.

Files:
- `agent/evaluator.py`
- `tests/test_evaluator.py`

---

## Task 9 — Source discovery tool

Implement `agent/tools/source_discovery.py`. Reads `vault/sources.md`, passes current sources + recent strategy titles to Claude, asks for new source suggestions. Returns list of `{name, url, type}` dicts. Handles `unvalidated` → `validated` promotion logic (2 sweeps with ≥1 hit) and 30-day no-signal flagging.

**Tests first:** Unit test with mocked Claude response verifying suggestion extraction and promotion counter logic.

Files:
- `agent/tools/source_discovery.py`
- `tests/test_source_discovery.py`

---

## Task 10 — Writer (Obsidian note generation)

Implement `agent/writer.py`. Takes a scored `RawItem` and generates an Obsidian-compatible markdown file in `vault/strategies/YYYY-MM-DD-<slug>.md` with the correct frontmatter and sections. Also regenerates `vault/index.md` (table sorted by category then novelty desc) and updates `vault/sources.md` if new sources were discovered.

**Tests first:** Unit test verifying the generated frontmatter YAML is valid and the file slug is correctly derived from the title.

Files:
- `agent/writer.py`
- `vault/strategies/.gitkeep`
- `vault/index.md` (template)
- `vault/sources.md` (seed sources)
- `tests/test_writer.py`

---

## Task 11 — Sweep orchestrator

Implement `agent/scheduler.py` — the `run_sweep(deep=False)` function that:
1. Runs source discovery (deep sweep only)
2. Fetches from all configured sources in parallel (`asyncio.gather` or `ThreadPoolExecutor`)
3. Deduplicates
4. Filters by engagement threshold
5. Cross-validates
6. Evaluates (Claude novelty scoring)
7. Writes notes

**Tests first:** Integration-style unit test with all fetchers and evaluator mocked, verifying the orchestration order and that writer is called once per surviving item.

Files:
- `agent/scheduler.py`
- `tests/test_scheduler.py`

---

## Task 12 — APScheduler integration

Add APScheduler to `agent/scheduler.py`: `start_scheduler()` function that schedules the daily sweep (8am) and weekly deep sweep (Sunday 8am) using `APScheduler.BlockingScheduler`. Uses values from `config.yml`.

**Tests first:** Unit test verifying the scheduler registers exactly two jobs with correct triggers.

Files:
- `agent/scheduler.py` (extend)
- `tests/test_scheduler.py` (extend)

---

## Task 13 — CLI

Implement `cli.py` using `argparse` or plain `sys.argv`. Four subcommands:
- `sweep` — calls `run_sweep(deep=False)`
- `start` — calls `start_scheduler()`
- `sources` — prints `vault/sources.md`
- `status` — prints stats (strategy count, last-run timestamp, source count)

**Tests first:** Unit test each subcommand invocation with mocked orchestrator calls.

Files:
- `cli.py`
- `tests/test_cli.py`

---

## Task 14 — Vault seed files + README

Populate `vault/sources.md` with the seed sources from the spec. Create `vault/index.md` with the initial empty table. Update `README.md` with project description, setup instructions, and CLI usage.

No test needed (static content, no logic).

Files:
- `vault/sources.md`
- `vault/index.md`
- `README.md`

---

## Task 15 — End-to-end smoke test + CI config

Write a smoke test that runs the full pipeline against a tiny mocked dataset (2 items, 1 above threshold, 1 below). Verify 1 note is written to `vault/strategies/`. Add a `Makefile` with `make test` and optionally a minimal GitHub Actions workflow.

Files:
- `tests/test_smoke.py`
- `Makefile`
- `.github/workflows/ci.yml` (optional)
