<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0005 — Retroactive re-classification of existing vault notes](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0005-retroactive-reclassify-vault-notes.md)**
<!-- docket:backlink:end -->

# Retroactive Re-classification of Vault Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `python cli.py reclassify` command that re-types existing vault notes through the three-pass evaluator, rewrites their frontmatter to the new schema, and files each note into the correct type subdirectory.

**Architecture:** A new `agent/reclassifier.py` module holds a `Reclassifier` class (parallel to `agent/regenerator.py`) that owns note collection, `RawItem` construction, evaluator invocation, frontmatter rewrite, and file move. `cli.py` gets a thin `cmd_reclassify(args, cfg)` + `_build_reclassify_parser()` pair and an if/elif dispatch branch, following the existing `cmd_regenerate` pattern. All logic lives in the module so it is unit-testable with a mocked `Evaluator`.

**Tech Stack:** Python 3, `pyyaml`, `pytest` + `pytest-mock`, existing `agent.evaluator.Evaluator`, `agent.writer.Writer`/`TYPE_DIRS`, `agent.regenerator.split_note`/`extract_first_source_url`, `agent.models.RawItem`.

## Global Constraints

- No changes to `agent/evaluator.py`, `agent/writer.py`, or `agent/models.py` (spec scope).
- No live Anthropic API calls in tests — mock `Evaluator`. The account currently returns `400 credit-balance-too-low`; a live end-to-end reclassify run is **deferred**, recorded in the results file, never blocking.
- Reuse `agent.regenerator.split_note(content) -> (fm, body)` and `agent.regenerator.extract_first_source_url(body) -> str | None` rather than re-parsing.
- File the note via `agent.writer.TYPE_DIRS` (`research→research`, `release→releases`, `news→news`, `benchmark→benchmarks`, `tutorial→tutorials`).
- The reclassifier does NOT touch the deduplicator index (`.index.json`) — reclassification is a metadata update, not an ingest.
- Rewrite frontmatter to the new schema: set `type`, `score`, `score_label`, `category` (research only — remove the key for other types), `tags`; drop the legacy `novelty:` key; preserve `title`, `date`, `validated`, `sources_count`, `status`, `content_source` and any other keys verbatim.
- `--date YYYY-MM-DD` filters to notes whose filename starts with that date; `--all` targets every note; default (neither flag) = yesterday's date.

---

## File Structure

- **Create** `agent/reclassifier.py` — `Reclassifier` class: note collection, per-note `RawItem` build, batch `Evaluator.score()`, frontmatter rewrite + move, index regen. Pure logic, no argparse.
- **Create** `tests/test_reclassifier.py` — unit tests with a mocked `Evaluator`.
- **Modify** `cli.py` — add `cmd_reclassify(args, cfg)`, `_build_reclassify_parser(subparsers)`, wire into `main()`.
- **Modify** `tests/test_cli.py` — add CLI dispatch + parser tests.

---

## Task 1: Reclassifier core — collect, build RawItems, rewrite frontmatter, move

**Files:**
- Create: `agent/reclassifier.py`
- Test: `tests/test_reclassifier.py`

**Interfaces:**
- Consumes: `agent.evaluator.Evaluator` (`.score(list[RawItem]) -> list[RawItem]`), `agent.writer.Writer` (`.regenerate_index()`) + `agent.writer.TYPE_DIRS`, `agent.regenerator.split_note`/`extract_first_source_url`, `agent.models.RawItem`.
- Produces:
  - `class Reclassifier(vault_path, api_key: str | None = None)`
  - `Reclassifier.reclassify(date: str | None = None, all_notes: bool = False) -> dict` — returns a report `{"reclassified": int, "moved": int, "errored": int}`.
  - `Reclassifier._collect_notes(date, all_notes) -> list[Path]`
  - `Reclassifier._build_item(fm: dict, body: str, path: Path) -> RawItem`
  - `Reclassifier._rewrite_and_move(path, item) -> bool` (returns True if the file was moved)

- [ ] **Step 1: Write the failing test — frontmatter rewrite to new schema**

```python
# tests/test_reclassifier.py
from pathlib import Path
from unittest.mock import MagicMock

import yaml

from agent.reclassifier import Reclassifier
from agent.models import RawItem


LEGACY_FLAT_NOTE = """\
---
title: "Agent frameworks"
date: 2026-08-03
category: agentic
tags: [emerging]
novelty: 7
validated: false
sources_count: 1
status: new
---

# Agent frameworks

## Summary
An AI agent framework provides reusable abstractions.

## How It Works
An AI agent framework provides reusable abstractions for building agents.

## Sources
- [Agent frameworks](https://example.com/agents) — search/tavily · 0

## Related
"""


def _write_flat(tmp_path, content, name="2026-08-03-agent-frameworks.md"):
    d = tmp_path / "vault" / "strategies"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(content)
    (tmp_path / "vault" / "index.md").write_text("# Index\n")
    return p


def _mock_evaluator(content_type, score, score_label, category="", tags=None):
    """Return an Evaluator whose .score() stamps the given fields on every item."""
    ev = MagicMock()

    def _score(items):
        for it in items:
            it.content_type = content_type
            it.score = score
            it.score_label = score_label
            it.category = category
            it.tags = tags if tags is not None else [content_type]
        return items

    ev.score.side_effect = _score
    return ev


def test_reclassify_updates_frontmatter(tmp_path, mocker):
    p = _write_flat(tmp_path, LEGACY_FLAT_NOTE)
    ev = _mock_evaluator("release", 8, "significance")
    mocker.patch("agent.reclassifier.Evaluator", return_value=ev)

    r = Reclassifier(vault_path=tmp_path / "vault")
    r.reclassify(all_notes=True)

    # note moved to releases/, old flat path gone
    moved = tmp_path / "vault" / "strategies" / "releases" / "2026-08-03-agent-frameworks.md"
    assert moved.exists()
    assert not p.exists()

    fm = yaml.safe_load(moved.read_text().split("---")[1])
    assert fm["type"] == "release"
    assert fm["score"] == 8
    assert fm["score_label"] == "significance"
    assert fm["tags"] == ["release"]
    assert "novelty" not in fm          # legacy key dropped
    assert "category" not in fm         # not research → no category key
    assert fm["title"] == "Agent frameworks"
    assert fm["date"] == "2026-08-03"   # preserved
    assert fm["status"] == "new"        # preserved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_reclassifier.py::test_reclassify_updates_frontmatter -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.reclassifier'`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/reclassifier.py
"""Retroactive re-classification of existing vault notes.

Reads existing vault notes (old pre-type-system schema or new schema alike),
runs them through the three-pass Evaluator, rewrites their frontmatter to the
new schema, and moves each note into the correct type subdirectory. Does NOT
touch the deduplicator index — this is a metadata update, not an ingest.
"""
import datetime
from pathlib import Path

import yaml

from agent.evaluator import Evaluator
from agent.models import RawItem
from agent.regenerator import extract_first_source_url, split_note
from agent.writer import TYPE_DIRS, Writer

# Frontmatter keys the evaluator owns and we rewrite; everything else is preserved.
_MANAGED_KEYS = {"type", "score", "score_label", "category", "tags", "novelty"}


class Reclassifier:
    def __init__(self, vault_path, api_key: str | None = None):
        self._vault = Path(vault_path)
        self._strategies = self._vault / "strategies"
        self._evaluator = Evaluator(api_key=api_key)
        self._writer = Writer(vault_path=self._vault)

    def reclassify(self, date: str | None = None, all_notes: bool = False) -> dict:
        report = {"reclassified": 0, "moved": 0, "errored": 0}
        notes = self._collect_notes(date, all_notes)
        items: list[tuple[Path, dict, str, RawItem]] = []
        for path in notes:
            try:
                fm, body = split_note(path.read_text())
                if not fm:
                    continue
                item = self._build_item(fm, body, path)
                items.append((path, fm, body, item))
            except Exception as exc:  # one bad note must not abort the batch
                print(f"[warn] reclassify read failed for {path.name}: {exc}")
                report["errored"] += 1

        if items:
            self._evaluator.score([it for (_, _, _, it) in items])

        for path, fm, body, item in items:
            try:
                moved = self._rewrite_and_move(path, fm, item)
                report["reclassified"] += 1
                if moved:
                    report["moved"] += 1
            except Exception as exc:
                print(f"[warn] reclassify write failed for {path.name}: {exc}")
                report["errored"] += 1

        try:
            self._writer.regenerate_index()
        except Exception as exc:
            print(f"[warn] index regeneration failed: {exc}")
        return report

    def _collect_notes(self, date: str | None, all_notes: bool) -> list[Path]:
        if not self._strategies.exists():
            return []
        notes = sorted(self._strategies.glob("**/*.md"))
        if all_notes:
            return notes
        target = date or str(datetime.date.today() - datetime.timedelta(days=1))
        return [p for p in notes if p.name.startswith(target)]

    def _build_item(self, fm: dict, body: str, path: Path) -> RawItem:
        return RawItem(
            title=str(fm.get("title", path.stem)),
            body=body,
            url=extract_first_source_url(body) or str(fm.get("url", "")),
            source=str(fm.get("source", "")),
            engagement=0,
            timestamp=str(fm.get("date", "")),
            content_type=str(fm.get("type", "research")),
            score=int(fm.get("score", fm.get("novelty", 0)) or 0),
            score_label=str(fm.get("score_label", "novelty")),
            validated=bool(fm.get("validated", False)),
            sources_count=int(fm.get("sources_count", 1)),
            category=str(fm.get("category", "")),
            tags=list(fm.get("tags", []) or []),
        )

    def _rewrite_and_move(self, path: Path, fm: dict, item: RawItem) -> bool:
        new_fm = {k: v for k, v in fm.items() if k not in _MANAGED_KEYS}
        new_fm["type"] = item.content_type
        new_fm["score"] = item.score
        new_fm["score_label"] = item.score_label
        new_fm["tags"] = item.tags
        if item.content_type == "research" and item.category:
            new_fm["category"] = item.category

        # Rebuild the file: rewritten frontmatter + original body verbatim.
        body = path.read_text().split("---", 2)[2].lstrip("\n")
        fm_text = yaml.safe_dump(new_fm, sort_keys=True, allow_unicode=True).strip()
        content = f"---\n{fm_text}\n---\n\n{body}"

        subdir = TYPE_DIRS.get(item.content_type, item.content_type)
        dest_dir = self._strategies / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        moved = dest.resolve() != path.resolve()
        if moved and dest.exists():
            dest = dest_dir / f"{path.stem}-2{path.suffix}"

        dest.write_text(content)
        if moved and path.exists():
            path.unlink()
        return moved
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_reclassifier.py::test_reclassify_updates_frontmatter -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/reclassifier.py tests/test_reclassifier.py
git commit -m "feat(0005): add Reclassifier — rewrite frontmatter + move to type subdir"
```

---

## Task 2: Reclassifier — research category kept, unchanged-type note stays put, index regen

**Files:**
- Modify: `agent/reclassifier.py` (only if a test surfaces a gap — likely none)
- Test: `tests/test_reclassifier.py`

**Interfaces:**
- Consumes: `Reclassifier` from Task 1.
- Produces: no new public API.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_reclassifier.py  (append)

SUBDIR_RESEARCH_NOTE = """\
---
category: architecture
date: 2026-08-01
score: 6
score_label: novelty
sources_count: 1
status: new
tags:
- research
- architecture
title: Scaling laws for native multimodal models
type: research
validated: false
---

# Scaling laws for native multimodal models

## Summary
A study of data scaling.

## Sources
- [Scaling laws](https://example.com/scaling) — search/tavily · 0

## Related
"""


def _write_subdir(tmp_path, content, subdir="research",
                  name="2026-08-01-scaling-laws.md"):
    d = tmp_path / "vault" / "strategies" / subdir
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(content)
    (tmp_path / "vault" / "index.md").write_text("# Index\n")
    return p


def test_reclassify_keeps_research_category(tmp_path, mocker):
    p = _write_subdir(tmp_path, SUBDIR_RESEARCH_NOTE)
    ev = _mock_evaluator("research", 7, "novelty", category="architecture",
                         tags=["research", "architecture"])
    mocker.patch("agent.reclassifier.Evaluator", return_value=ev)

    r = Reclassifier(vault_path=tmp_path / "vault")
    report = r.reclassify(all_notes=True)

    # type unchanged → file stays in research/, not moved
    assert p.exists()
    assert report["moved"] == 0
    fm = yaml.safe_load(p.read_text().split("---")[1])
    assert fm["type"] == "research"
    assert fm["category"] == "architecture"
    assert fm["score"] == 7


def test_reclassify_regenerates_index(tmp_path, mocker):
    _write_flat(tmp_path, LEGACY_FLAT_NOTE)
    ev = _mock_evaluator("news", 5, "timeliness")
    mocker.patch("agent.reclassifier.Evaluator", return_value=ev)
    spy = mocker.patch("agent.reclassifier.Writer")
    # Writer() instance whose regenerate_index we assert was called
    inst = spy.return_value

    r = Reclassifier(vault_path=tmp_path / "vault")
    r.reclassify(all_notes=True)

    assert inst.regenerate_index.call_count == 1


def test_reclassify_date_filter(tmp_path, mocker):
    _write_flat(tmp_path, LEGACY_FLAT_NOTE, name="2026-08-03-a.md")
    _write_flat(tmp_path, LEGACY_FLAT_NOTE, name="2026-08-04-b.md")
    ev = _mock_evaluator("news", 5, "timeliness")
    mocker.patch("agent.reclassifier.Evaluator", return_value=ev)

    r = Reclassifier(vault_path=tmp_path / "vault")
    report = r.reclassify(date="2026-08-03")

    # only the 08-03 note was processed
    assert report["reclassified"] == 1
```

- [ ] **Step 2: Run tests to verify they fail (or pass if Task 1 already covers)**

Run: `uv run pytest tests/test_reclassifier.py -v`
Expected: The three new tests run. `test_reclassify_regenerates_index` mocks `Writer` in the reclassifier module, so it needs `Writer` imported at module scope (it is, from Task 1). If any assertion fails, adjust `agent/reclassifier.py` minimally. Note: because `test_reclassify_regenerates_index` patches `Writer`, `regenerate_index` is a no-op there — that is intended (we assert the call, not its output).

- [ ] **Step 3: Fix implementation if a test surfaced a gap**

Only if a test failed. The Task 1 implementation is expected to satisfy all three. If `test_reclassify_date_filter` sees both notes, verify `_collect_notes` uses `all_notes` correctly and `date` filtering by filename prefix.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_reclassifier.py -v`
Expected: PASS (all reclassifier tests)

- [ ] **Step 5: Commit**

```bash
git add agent/reclassifier.py tests/test_reclassifier.py
git commit -m "test(0005): research category retained, no-move on unchanged type, date filter, index regen"
```

---

## Task 3: CLI wiring — `cmd_reclassify` + parser + dispatch

**Files:**
- Modify: `cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `agent.reclassifier.Reclassifier` from Tasks 1–2.
- Produces:
  - `cli.cmd_reclassify(args, cfg)` — instantiates `Reclassifier`, calls `.reclassify(date=..., all_notes=...)`, prints a one-line summary.
  - `cli._build_reclassify_parser(subparsers)` — adds the `reclassify` subparser with `--date` and `--all`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py  (append)

def test_cmd_reclassify_dispatches(mocker):
    import cli
    from argparse import Namespace

    mock_rec = MagicMock()
    mock_rec.reclassify.return_value = {"reclassified": 3, "moved": 2, "errored": 0}
    mocker.patch("agent.reclassifier.Reclassifier", return_value=mock_rec)

    cfg = {}
    args = Namespace(date="2026-08-03", all=False)
    cli.cmd_reclassify(args=args, cfg=cfg)

    assert mock_rec.reclassify.call_count == 1
    _, kwargs = mock_rec.reclassify.call_args
    assert kwargs["date"] == "2026-08-03"
    assert kwargs["all_notes"] is False


def test_reclassify_parser_accepts_flags():
    import cli
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    cli._build_reclassify_parser(sub)
    args = parser.parse_args(["reclassify", "--date", "2026-08-04", "--all"])
    assert args.date == "2026-08-04"
    assert args.all is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py::test_cmd_reclassify_dispatches tests/test_cli.py::test_reclassify_parser_accepts_flags -v`
Expected: FAIL with `AttributeError: module 'cli' has no attribute 'cmd_reclassify'` / `_build_reclassify_parser`

- [ ] **Step 3: Write minimal implementation**

```python
# cli.py — add after cmd_regenerate / _build_regenerate_parser

def cmd_reclassify(args, cfg):
    from agent.reclassifier import Reclassifier
    api_key = os.getenv("ANTHROPIC_API_KEY")
    rec = Reclassifier(vault_path=VAULT_PATH, api_key=api_key)
    date = getattr(args, "date", None)
    all_notes = getattr(args, "all", False)
    report = rec.reclassify(date=date, all_notes=all_notes)
    print(
        f"Reclassify complete. "
        f"reclassified={report.get('reclassified', 0)} "
        f"moved={report.get('moved', 0)} "
        f"errored={report.get('errored', 0)}"
    )


def _build_reclassify_parser(subparsers):
    p = subparsers.add_parser(
        "reclassify", help="Re-classify existing vault notes"
    )
    p.add_argument("--date", default=None, help="Only notes from this date (YYYY-MM-DD)")
    p.add_argument("--all", action="store_true", help="Re-classify all notes")
    return p
```

Then wire into `main()`:

```python
# in main(), after _build_regenerate_parser(sub):
    _build_reclassify_parser(sub)

# in the if/elif dispatch, after the regenerate branch:
    elif args.command == "reclassify":
        cmd_reclassify(args, cfg)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS (all CLI tests, including the two new ones)

- [ ] **Step 5: Commit**

```bash
git add cli.py tests/test_cli.py
git commit -m "feat(0005): wire cli.py reclassify command + parser + dispatch"
```

---

## Task 4: Full suite green + README doc line

**Files:**
- Modify: `README.md` (add the `reclassify` command to the CLI usage section, if such a section exists)
- Test: whole suite

**Interfaces:**
- Consumes: everything above.
- Produces: no new API.

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -q`
Expected: PASS — all pre-existing tests plus the new reclassifier + CLI tests. If a pre-existing test broke, root-cause and fix minimally (should not happen — no shared modules were modified).

- [ ] **Step 2: Add a README usage line (if README has a commands section)**

Inspect `README.md` for the CLI commands list (near `sweep` / `regenerate`). Add:

```markdown
- `python cli.py reclassify [--date YYYY-MM-DD] [--all]` — re-classify existing vault notes through the evaluator and file them into the correct type subdirectory.
```

If README has no such section, skip this step (do not invent structure).

- [ ] **Step 3: Run the full suite once more**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(0005): document cli.py reclassify command"
```

---

## Self-Review

**Spec coverage:**
- New CLI command `reclassify [--date] [--all]` → Task 3. ✓
- Collect from `vault/strategies/**/*.md`, date-filter → Task 1 `_collect_notes`, Task 2 date-filter test. ✓
- `split_note` reuse → Task 1 `_build_item`. ✓
- Build `RawItem` per note (defensive old+new schema) → Task 1 `_build_item` (`score` falls back to `novelty`). ✓
- Run `Evaluator.score()` (3 passes + tags) → Task 1 `reclassify`. ✓
- Rewrite `type`/`score`/`score_label`/`category`(research)/`tags`, drop `novelty` → Task 1 `_rewrite_and_move`, Task 1+2 asserts. ✓
- Move to `TYPE_DIRS` subdir; `-2` on collision; flat note always moves → Task 1 `_rewrite_and_move`. ✓
- Unchanged-type subdir note stays put → Task 2 `test_reclassify_keeps_research_category`. ✓
- `Writer().regenerate_index()` after processing → Task 1 `reclassify`, Task 2 asserts call. ✓
- Does not touch dedup index → no dedup code referenced. ✓
- Summary print → Task 3 `cmd_reclassify`. ✓
- Tests with mocked evaluator → all reclassifier/CLI tests. ✓
- Live-API deferred → captured in results file (Step 6.5 of the outer flow), not in code. ✓

**Placeholder scan:** No TBD/TODO; every code step has real content. ✓

**Type consistency:** `Reclassifier(vault_path, api_key)`, `.reclassify(date, all_notes)`, report keys `reclassified`/`moved`/`errored` used identically across module, tests, and CLI. `_mock_evaluator` stamps the same fields the real evaluator sets (`content_type`, `score`, `score_label`, `category`, `tags`). ✓

## Notes / risks

- `test_reclassify_regenerates_index` patches `agent.reclassifier.Writer`, so `regenerate_index` is a spy no-op there — intended. The `Reclassifier.__init__` builds `Writer(vault_path=...)`, so the patch must target the reclassifier-module symbol (it does).
- The evaluator's `Evaluator.__init__` constructs an `anthropic.Anthropic(api_key=...)` client but makes no network call until `.score()`. Tests patch `agent.reclassifier.Evaluator` entirely, so no client is built and no live call occurs. The account credit-balance-400 condition therefore never fires in tests; a live reclassify run is deferred to the human at the merge gate (see results file).
