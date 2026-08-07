<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0011 — Add verified curated feeds — newsletters + Lobste.rs](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0011-curated-feed-expansion.md)**
<!-- docket:backlink:end -->

# Plan — Curated feed expansion (change 0011)

> Plan authored by the docket implementer itself: the configured plan skill
> `superpowers:writing-plans` was not invocable in this environment, so per the
> docket *Skill layer* missing-skill rule the plan role degraded to `auto` + warn.

## Context

Change 0011 (`curated-feed-expansion`, `trivial: true`, type `chore`) adds six
externally-verified RSS/Atom feeds to the existing `WebFetcher` source list.
`config.yml` `sources.feeds` is a YAML list of `{name, url, type}` objects
consumed verbatim by `agent/fetchers/web.py::WebFetcher(feeds=...)` — the six
additions are pure config, zero production code. `WebFetcher.fetch()` is
fail-soft per feed (a broken feed is skipped, never aborts the sweep).

The only code touched is the test suite: one mocked `WebFetcher` parse test
proving a representative newsletter/blog payload maps into `RawItem`s, matching
the existing pattern in `tests/test_fetcher_web.py` (mock `httpx.get` with a
`MagicMock` whose `.content` is encoded RSS bytes).

Suite baseline: **179 tests**. Run via `uv run python -m pytest` after
`uv sync --extra dev` (learnings finding `pytest-shim-and-venv-provisioning` —
never a bare `pytest`, which loads a crashing global deepeval plugin).

## Task 1 — Add the six curated feeds to `config.yml`

Append to `config.yml` `sources.feeds` (preserving the existing eight entries
and their formatting), each as a `{name, url, type}` object:

| name | url | type |
|---|---|---|
| AlphaSignal | https://alphasignal.ai/feed.xml | newsletter |
| TLDR AI | https://tldr.tech/api/rss/ai | newsletter |
| Latent Space | https://www.latent.space/feed | newsletter |
| Ahead of AI (Sebastian Raschka) | https://magazine.sebastianraschka.com/feed | newsletter |
| Import AI (Jack Clark) | https://importai.substack.com/feed | newsletter |
| Lobste.rs AI tag | https://lobste.rs/t/ai.rss | blog |

Acceptance: `config.yml` parses as valid YAML; `sources.feeds` has 14 entries;
each new entry has `name`, `url`, `type`. No production `.py` file changes.

## Task 2 — Add a representative mocked `WebFetcher` parse test

In `tests/test_fetcher_web.py`, add one test that feeds a representative
newsletter-shaped RSS payload (mirroring one of the six sources) through
`WebFetcher` with `httpx.get` mocked (MagicMock `.content` = encoded RSS bytes,
pub date recent enough to survive the 7-day lookback filter) and asserts the
entry maps into a `RawItem` with `source == "web/<name>"`, correct `title`/`url`,
and `engagement == 0`.

Follow TDD: the test is the deliverable and must pass against the unchanged
`WebFetcher` (this change adds no fetcher code — the test documents that the six
new config feeds parse through the existing code path).

Acceptance: the new test passes; the full suite is green at **180** (179 + 1).

## Verification

- `uv sync --extra dev`
- `uv run python -m pytest` → green, 180 passed.
- Confirm `config.yml` `sources.feeds` contains the six new feeds.

## Out of scope (from the change body)

- Extracting outbound links from digest issues as candidate items.
- YouTube channel RSS.
- Lobste.rs JSON endpoint with scores.
