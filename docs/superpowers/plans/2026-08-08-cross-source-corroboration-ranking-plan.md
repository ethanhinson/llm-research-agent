<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0014 — Cross-source corroboration + citation-velocity signals](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0014-cross-source-corroboration-ranking.md)**
<!-- docket:backlink:end -->

# Cross-Source Corroboration + Citation-Velocity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the agent a canonical item identity and make it the dedup + corroboration key, turning `sources_count` into a real independent-corroboration signal that feeds evaluation and the vault, plus a weekly Semantic Scholar citation-velocity re-poll that re-ranks rising papers.

**Architecture:** Introduce `canonical_id(item)` (arXiv > DOI > normalized-URL > normalized-title). Populate it after fetch, group by it to collapse intra-sweep duplicates (`corroborate()` supersedes `cross_validate()`), persist it in a v2 dedup index so cross-sweep re-surfaces within a 72h window update the existing note instead of being dropped, feed `sources_count` into the evaluator prompts as a soft signal, and add a config-gated weekly citation-velocity re-poll. Everything new is config-gated and fail-soft — with the new config sections absent, behavior is byte-identical to today.

**Tech Stack:** Python 3, dataclasses, `thefuzz` (already a dep), `httpx` (already a dep), `pyyaml`, `pytest` + `pytest-mock`.

## Global Constraints

- **Test command:** always `uv sync --extra dev` then `uv run python -m pytest` — NEVER a bare `pytest` (a bare `pytest` resolves to a pyenv shim that autoloads a crashing global `deepeval` plugin: `TracerProvider.get_tracer()` TypeError; and the fresh venv lacks project deps → `trafilatura` ImportError). Both are environment pollution, not code failure.
- **Fail-soft + config-gated:** every new stage must no-op (behavior byte-identical to today) when its config section is absent/disabled, and must never abort a sweep on its own error — catch, `print("[warn] ...")`, continue. Match the existing `_write_kept` / `_run_source_discovery` fail-soft style.
- **No new runtime dependencies.** Reuse `thefuzz`, `httpx`, `pyyaml`, `os`, `re`, `datetime`.
- **Semantic Scholar reuse (S5):** honor `S2_API_KEY` as the `x-api-key` header; one backoff-then-retry on HTTP 429 then fail-soft skip; polite inter-request pacing when unkeyed — mirror `agent/fetchers/semantic_scholar.py`. Use the `POST /graph/v1/paper/batch` endpoint (distinct from the adapter's `/paper/search`).
- **Preserve legacy index keys.** `cli.py cmd_status` reads `.index.json["urls"]`; the v2 schema must keep `urls`/`titles` present (readable) so status and v1 migration do not break.
- **Commit frequently** — one commit per task minimum, TDD order (failing test → implement → green → commit).

---

### Task 1: Canonical identity — `agent/canonical.py` + `RawItem.canonical_id`

**Files:**
- Create: `agent/canonical.py`
- Modify: `agent/models.py` (add `canonical_id: str = ""` field to `RawItem`)
- Test: `tests/test_canonical.py`

**Interfaces:**
- Consumes: `RawItem` (`title`, `url`, `source` attrs).
- Produces: `canonical_id(item: RawItem) -> str` — pure, dependency-free. Returns one of `arxiv:<id>`, `doi:<lowercased-doi>`, `url:<host/path>`, `title:<normalized-title>`, with that strict precedence. `RawItem.canonical_id: str = ""` field.

- [ ] **Step 1: Write the failing tests** — `tests/test_canonical.py`

```python
import pytest

from agent.canonical import canonical_id
from agent.models import RawItem


def _item(title="", url="", source="s"):
    return RawItem(title=title, body="", url=url, source=source, engagement=0, timestamp="2026-08-01")


@pytest.mark.parametrize("url", [
    "https://arxiv.org/abs/2410.12345",
    "https://arxiv.org/pdf/2410.12345",
    "https://arxiv.org/pdf/2410.12345v2",
    "https://huggingface.co/papers/2410.12345",
    "http://arxiv.org/abs/2410.12345v1",
])
def test_arxiv_id_from_url_shapes_strips_version(url):
    assert canonical_id(_item(url=url)) == "arxiv:2410.12345"


def test_arxiv_id_from_title_prefix():
    assert canonical_id(_item(title="[2410.12345] A New Attention Kernel", url="https://example.com/x")) == "arxiv:2410.12345"


def test_arxiv_beats_url_precedence():
    # arXiv id present in url -> arxiv scheme, not url scheme
    assert canonical_id(_item(url="https://arxiv.org/abs/2410.12345")).startswith("arxiv:")


def test_doi_from_url():
    assert canonical_id(_item(url="https://doi.org/10.1145/3597503.3639187")) == "doi:10.1145/3597503.3639187"


def test_doi_lowercased():
    assert canonical_id(_item(url="https://doi.org/10.1145/ABC.DEF")) == "doi:10.1145/abc.def"


def test_normalized_url_strips_scheme_www_query_fragment_trailing_slash():
    a = canonical_id(_item(url="https://www.Example.com/Path/?utm_source=x&ref=y#frag"))
    b = canonical_id(_item(url="http://example.com/Path"))
    assert a == b == "url:example.com/Path"


def test_normalized_url_keeps_case_of_path_but_lowercases_host():
    assert canonical_id(_item(url="https://EXAMPLE.com/AbC")) == "url:example.com/AbC"


def test_title_fallback_when_no_stable_url():
    # empty url -> title scheme, lowercased, punctuation stripped, whitespace collapsed
    got = canonical_id(_item(title="Kimi  K3:  A New!! Model", url=""))
    assert got == "title:kimi k3 a new model"


def test_title_fallback_when_url_is_non_http():
    assert canonical_id(_item(title="Some Release", url="mailto:x@y.com")).startswith("title:")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_canonical.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.canonical'` (and `RawItem` has no `canonical_id`, but that surfaces in Task 2 usage; the canonical module itself is the immediate failure).

- [ ] **Step 3: Add the field to `RawItem`** — `agent/models.py`, in the dataclass field block (after `content_source`):

```python
    canonical_id: str = ""           # stable identity: arxiv:/doi:/url:/title: (set post-fetch)
```

- [ ] **Step 4: Implement `agent/canonical.py`**

```python
"""Canonical item identity — the dedup + corroboration key.

Pure and dependency-free. Precedence: arXiv id > DOI > normalized URL >
normalized title. `title:` is the fallback for items with no stable URL
(some releases / news).
"""

import re

from agent.models import RawItem

_ARXIV_URL = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/|huggingface\.co/papers/)(\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)
_ARXIV_TITLE = re.compile(r"^\s*\[(\d{4}\.\d{4,5})(?:v\d+)?\]")
_DOI = re.compile(r"(10\.\d{4,9}/[^\s?#]+)")
_TRACKING = re.compile(r"^(utm_.*|ref)$", re.IGNORECASE)


def _arxiv_id(item: RawItem) -> str:
    m = _ARXIV_URL.search(item.url or "")
    if m:
        return m.group(1)
    m = _ARXIV_TITLE.match(item.title or "")
    if m:
        return m.group(1)
    return ""


def _doi(url: str) -> str:
    m = _DOI.search(url or "")
    return m.group(1).lower() if m else ""


def _normalized_url(url: str) -> str:
    u = (url or "").strip()
    u = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", "", u)  # drop scheme
    u = u.split("#", 1)[0]                               # drop fragment
    path_part, _, query = u.partition("?")
    # drop tracking params but keep meaningful ones
    if query:
        kept = [
            kv for kv in query.split("&")
            if kv and not _TRACKING.match(kv.split("=", 1)[0])
        ]
        if kept:
            path_part = path_part + "?" + "&".join(kept)
    if path_part.lower().startswith("www."):
        path_part = path_part[4:]
    host, sep, rest = path_part.partition("/")
    host = host.lower()
    normalized = host + sep + rest
    normalized = normalized.rstrip("/")
    return normalized


def _normalized_title(title: str) -> str:
    t = (title or "").lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def canonical_id(item: RawItem) -> str:
    arxiv = _arxiv_id(item)
    if arxiv:
        return f"arxiv:{arxiv}"
    doi = _doi(item.url)
    if doi:
        return f"doi:{doi}"
    url = item.url or ""
    if re.match(r"^https?://", url, re.IGNORECASE):
        norm = _normalized_url(url)
        if norm:
            return f"url:{norm}"
    return f"title:{_normalized_title(item.title)}"
```

Note on `test_normalized_url_keeps_case_of_path`: the DOI regex must not fire for a plain `example.com/AbC` (no `10.NNNN/` pattern) — it won't. Verify the `doi.org` cases produce `doi:` and the plain host cases produce `url:`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_canonical.py -v`
Expected: PASS (all parametrized + scalar cases).

- [ ] **Step 6: Commit**

```bash
git add agent/canonical.py agent/models.py tests/test_canonical.py
git commit -m "feat(0014): S1 canonical item identity (arxiv>doi>url>title)"
```

---

### Task 2: Intra-sweep collapse + corroboration — `corroborate()` replaces `cross_validate()`

**Files:**
- Create: `agent/tools/corroborate.py`
- Modify: `agent/scheduler.py` (populate `canonical_id` post-fetch in both sweeps; replace `cross_validate(after_topic)` with `corroborate(after_topic)` in `run_sweep` and `search_sweep`; swap the import)
- Delete: `agent/tools/cross_validate.py` and `tests/test_cross_validate.py` (superseded — `corroborate` subsumes both the identity grouping and the title-fuzzy fallback)
- Test: `tests/test_corroborate.py`

**Interfaces:**
- Consumes: `canonical_id` (Task 1); `RawItem` with `canonical_id` populated.
- Produces: `corroborate(items: list[RawItem]) -> list[RawItem]` — groups by `canonical_id`, returns **one representative RawItem per identity** with `sources_count = number of distinct sources`, `validated = sources_count >= 2`, and `corroboration_sources: list[tuple[str, str, int]]` (source, url, engagement) collected on the representative for the note's `## Sources` block. For the `title:`-bucket only, a secondary `fuzz.ratio >= 85` merge groups near-title items.
- Also produces: a `corroboration_sources: list = field(default_factory=list)` field added to `RawItem` (holds the per-source tuples for the representative).

- [ ] **Step 1: Write the failing tests** — `tests/test_corroborate.py`

```python
from agent.canonical import canonical_id
from agent.corroborate_helpers import _prep  # optional; else set canonical_id inline
from agent.models import RawItem
from agent.tools.corroborate import corroborate


def _item(title, source, url, engagement=100):
    it = RawItem(title=title, body="", url=url, source=source, engagement=engagement, timestamp="2026-08-01")
    it.canonical_id = canonical_id(it)
    return it


def test_same_arxiv_identity_collapses_to_one_item():
    items = [
        _item("Flash Attention 3", "hackernews", "https://arxiv.org/abs/2410.12345"),
        _item("Flash Attention 3 (v2)", "hf-papers", "https://arxiv.org/pdf/2410.12345v2"),
    ]
    result = corroborate(items)
    assert len(result) == 1
    rep = result[0]
    assert rep.validated is True
    assert rep.sources_count == 2
    assert {s[0] for s in rep.corroboration_sources} == {"hackernews", "hf-papers"}


def test_distinct_identities_pass_through():
    items = [
        _item("Paper A", "arxiv", "https://arxiv.org/abs/2410.00001"),
        _item("Paper B", "arxiv", "https://arxiv.org/abs/2410.00002"),
    ]
    result = corroborate(items)
    assert len(result) == 2
    assert all(i.sources_count == 1 and not i.validated for i in result)


def test_single_source_not_validated():
    items = [_item("Solo LoRA paper", "arxiv", "https://arxiv.org/abs/2410.99999")]
    result = corroborate(items)
    assert result[0].validated is False
    assert result[0].sources_count == 1


def test_same_source_twice_counts_one_distinct_source():
    items = [
        _item("Same paper", "arxiv", "https://arxiv.org/abs/2410.12345"),
        _item("Same paper", "arxiv", "https://arxiv.org/pdf/2410.12345"),
    ]
    result = corroborate(items)
    assert len(result) == 1
    assert result[0].sources_count == 1
    assert result[0].validated is False


def test_title_fallback_fuzzy_merge_for_non_paper_items():
    # No stable URL -> title: bucket; near-titles from distinct sources merge at ratio>=85
    items = [
        _item("Kimi K3: A New Model", "news", ""),
        _item("Kimi K3: A New Model!", "blog", ""),
    ]
    result = corroborate(items)
    assert len(result) == 1
    assert result[0].sources_count == 2
    assert result[0].validated is True


def test_representative_prefers_arxiv_url():
    items = [
        _item("Paper X", "blog", "https://blog.example.com/paper-x"),
        _item("Paper X", "arxiv", "https://arxiv.org/abs/2410.55555"),
    ]
    # These are DISTINCT identities (url: vs arxiv:), so they do NOT merge here.
    result = corroborate(items)
    assert len(result) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_corroborate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.tools.corroborate'` (remove the `corroborate_helpers` import line; it is illustrative — set `canonical_id` inline in `_item` as shown).

- [ ] **Step 3: Add `corroboration_sources` to `RawItem`** — `agent/models.py`, after `canonical_id`:

```python
    corroboration_sources: list = field(default_factory=list)  # (source, url, engagement) tuples on the representative
```

- [ ] **Step 4: Implement `agent/tools/corroborate.py`**

```python
"""Intra-sweep collapse + corroboration — supersedes cross_validate.

Group items by canonical_id; return one representative per identity with
sources_count (distinct sources) and validated (>=2). For the title:-fallback
bucket only, a secondary fuzzy merge (ratio>=85) groups near-title non-paper
items so they still corroborate (no regression vs the old cross_validate).
"""

from thefuzz import fuzz

from agent.models import RawItem

TITLE_FUZZY_THRESHOLD = 85


def _pick_representative(group: list[RawItem]) -> RawItem:
    for it in group:
        if (it.canonical_id or "").startswith(("arxiv:", "doi:")):
            return it
    return group[0]


def _finalize(group: list[RawItem]) -> RawItem:
    rep = _pick_representative(group)
    distinct_sources = {it.source for it in group}
    rep.sources_count = len(distinct_sources)
    rep.validated = rep.sources_count >= 2
    seen = set()
    tuples = []
    for it in group:
        key = (it.source, it.url)
        if key in seen:
            continue
        seen.add(key)
        tuples.append((it.source, it.url, it.engagement))
    rep.corroboration_sources = tuples
    return rep


def corroborate(items: list[RawItem]) -> list[RawItem]:
    exact: dict[str, list[RawItem]] = {}
    title_bucket: list[RawItem] = []
    for it in items:
        cid = it.canonical_id or ""
        if cid.startswith("title:"):
            title_bucket.append(it)
        else:
            exact.setdefault(cid, []).append(it)

    # Secondary fuzzy merge inside the title: bucket only.
    title_groups: list[list[RawItem]] = []
    for it in title_bucket:
        placed = False
        for grp in title_groups:
            if fuzz.ratio(it.title.lower(), grp[0].title.lower()) >= TITLE_FUZZY_THRESHOLD:
                grp.append(it)
                placed = True
                break
        if not placed:
            title_groups.append([it])

    result: list[RawItem] = []
    for group in exact.values():
        result.append(_finalize(group))
    for group in title_groups:
        result.append(_finalize(group))
    return result
```

- [ ] **Step 5: Wire into `agent/scheduler.py`**

  - Swap the import: replace `from agent.tools.cross_validate import cross_validate` with:
    ```python
    from agent.canonical import canonical_id
    from agent.tools.corroborate import corroborate
    ```
  - In `run_sweep`, immediately after `raw.extend(_fetch(adapter))` loop completes (before `Deduplicator`), populate identities:
    ```python
    for item in raw:
        item.canonical_id = canonical_id(item)
    ```
  - Replace `after_cv = cross_validate(after_topic)` with `after_cv = corroborate(after_topic)`.
  - In `search_sweep`, after `raw = fetcher.fetch()`, add the same identity-population loop, and replace `after_cv = cross_validate(after_topic)` with `after_cv = corroborate(after_topic)`.

- [ ] **Step 6: Delete the superseded module + its test**

```bash
git rm agent/tools/cross_validate.py tests/test_cross_validate.py
```

- [ ] **Step 7: Run the full suite to verify green**

Run: `uv sync --extra dev && uv run python -m pytest -q`
Expected: PASS. `test_scheduler.py` sweep tests still pass (the pipeline order is unchanged; identity population is additive). If a scheduler test patched `agent.scheduler.cross_validate`, update it to `agent.scheduler.corroborate`.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(0014): S2 corroborate() collapses intra-sweep duplicates by identity"
```

---

### Task 3: Cross-sweep corroboration — `Deduplicator` index schema v2 + `Writer.update_corroboration`

**Files:**
- Modify: `agent/deduplicator.py` (schema v2 `items` map; canonical-id logic; window logic; migration)
- Modify: `agent/writer.py` (add `update_corroboration()`)
- Modify: `agent/scheduler.py` (`_write_kept` uses the new dedup decision: new identity → write note + record; within-window re-surface with a new source → update existing note, no new file)
- Test: `tests/test_deduplicator.py` (extend), `tests/test_writer.py` (extend)

**Interfaces:**
- Consumes: `RawItem.canonical_id`, `RawItem.corroboration_sources`, `RawItem.sources_count`, `RawItem.validated`.
- Produces:
  - `Deduplicator.window_hours: int` (ctor arg, default 72).
  - `Deduplicator.record(item, note_path)` — records a new identity: `items[canonical_id] = {"sources": [...distinct sources...], "first_seen": <ISO8601 now>, "note_path": str, "title": str}`. Still appends to legacy `urls`/`titles` for back-compat.
  - `Deduplicator.corroboration_update(item) -> dict | None` — if `canonical_id` is a known identity, within `window_hours` of `first_seen`, and `item.source` is NOT already in the record's `sources`: append the source, return `{"note_path": <str>, "sources_count": <int>, "validated": <bool>, "new_source_line": <str>}`; else return `None`.
  - `Deduplicator.is_duplicate(item)` — unchanged public behavior for legacy callers, but now also treats a known canonical identity outside the window (or an already-counted source) as duplicate.
  - `Writer.update_corroboration(note_path, sources_count, validated, new_source_line)` — targeted frontmatter rewrite (`sources_count`, `validated`) + `## Sources` append; **no body regeneration**; fail-soft.

- [ ] **Step 1: Write the failing tests** — extend `tests/test_deduplicator.py`

```python
import json
from datetime import datetime, timedelta, timezone

from agent.deduplicator import Deduplicator
from agent.models import RawItem


def _rec_item(cid, source, url="https://arxiv.org/abs/2410.12345", title="Paper"):
    it = RawItem(title=title, body="", url=url, source=source, engagement=10, timestamp="2026-08-01")
    it.canonical_id = cid
    return it


def test_v1_index_migrates_to_empty_items_map(tmp_path):
    p = tmp_path / ".index.json"
    p.write_text(json.dumps({"urls": ["https://x"], "titles": ["Old"]}))
    d = Deduplicator(p)
    # legacy still readable; items map present and empty
    assert d._index.get("items") == {}
    assert "https://x" in d._index["urls"]


def test_record_new_identity_writes_items_entry(tmp_path):
    p = tmp_path / ".index.json"
    d = Deduplicator(p)
    it = _rec_item("arxiv:2410.12345", "hackernews")
    d.record(it, note_path="research/2026-08-08-paper.md")
    d2 = Deduplicator(p)  # reload from disk
    rec = d2._index["items"]["arxiv:2410.12345"]
    assert rec["sources"] == ["hackernews"]
    assert rec["note_path"] == "research/2026-08-08-paper.md"
    assert "first_seen" in rec


def test_within_window_new_source_returns_update(tmp_path):
    p = tmp_path / ".index.json"
    d = Deduplicator(p, window_hours=72)
    it = _rec_item("arxiv:2410.12345", "hackernews")
    d.record(it, note_path="research/n.md")
    resurface = _rec_item("arxiv:2410.12345", "hf-papers")
    upd = d.corroboration_update(resurface)
    assert upd is not None
    assert upd["note_path"] == "research/n.md"
    assert upd["sources_count"] == 2
    assert upd["validated"] is True
    assert "hf-papers" in upd["new_source_line"]


def test_already_counted_source_no_update(tmp_path):
    p = tmp_path / ".index.json"
    d = Deduplicator(p)
    it = _rec_item("arxiv:2410.12345", "hackernews")
    d.record(it, note_path="research/n.md")
    again = _rec_item("arxiv:2410.12345", "hackernews")
    assert d.corroboration_update(again) is None


def test_outside_window_no_update(tmp_path):
    p = tmp_path / ".index.json"
    d = Deduplicator(p, window_hours=72)
    it = _rec_item("arxiv:2410.12345", "hackernews")
    d.record(it, note_path="research/n.md")
    # backdate first_seen beyond the window
    old = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
    d._index["items"]["arxiv:2410.12345"]["first_seen"] = old
    resurface = _rec_item("arxiv:2410.12345", "hf-papers")
    assert d.corroboration_update(resurface) is None
    assert d.is_duplicate(resurface) is True
```

- [ ] **Step 2: Write the failing test** — extend `tests/test_writer.py`

```python
def test_update_corroboration_rewrites_frontmatter_and_appends_source(tmp_path):
    from agent.writer import Writer
    note = tmp_path / "note.md"
    note.write_text(
        "---\ntitle: \"Paper\"\ndate: 2026-08-08\ntype: research\nscore: 7\n"
        "score_label: novelty\ntags: [rag]\nvalidated: false\nsources_count: 1\n"
        "content_source: snippet\nstatus: new\n---\n\n# Paper\n\n## Summary\nx\n\n"
        "## Sources\n- [Paper](https://a) — hackernews · 10\n\n## Related\n"
    )
    w = Writer(vault_path=tmp_path)
    w.update_corroboration(
        str(note), sources_count=2, validated=True,
        new_source_line="- [Paper](https://b) — hf-papers · 5",
    )
    text = note.read_text()
    assert "sources_count: 2" in text
    assert "validated: true" in text
    assert "hf-papers" in text
    # body untouched
    assert "# Paper" in text and "## Summary\nx" in text


def test_update_corroboration_missing_file_is_failsoft(tmp_path):
    from agent.writer import Writer
    w = Writer(vault_path=tmp_path)
    # must not raise
    w.update_corroboration(str(tmp_path / "nope.md"), 2, True, "- [x](y) — z · 0")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_deduplicator.py tests/test_writer.py -v`
Expected: FAIL — `TypeError`/`AttributeError` (`window_hours` kwarg, `record`, `corroboration_update`, `update_corroboration` do not exist yet).

- [ ] **Step 4: Implement `Deduplicator` v2** — `agent/deduplicator.py`

```python
import json
from datetime import datetime, timezone
from pathlib import Path

from thefuzz import fuzz

from agent.models import RawItem

FUZZY_THRESHOLD = 90
DEFAULT_WINDOW_HOURS = 72


class Deduplicator:
    def __init__(self, index_path: Path, window_hours: int = DEFAULT_WINDOW_HOURS):
        self._path = Path(index_path)
        self.window_hours = window_hours
        self._index: dict = self._load()

    def _load(self) -> dict:
        default = {"urls": [], "titles": [], "items": {}}
        if self._path.exists():
            data = json.loads(self._path.read_text())
            merged = {**default, **{k: v for k, v in data.items() if k in default}}
            # a v1 index has no "items" -> stays the default empty map
            if not isinstance(merged.get("items"), dict):
                merged["items"] = {}
            return merged
        return default

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._index, indent=2))

    def _known(self, item: RawItem):
        cid = item.canonical_id or ""
        return self._index["items"].get(cid) if cid else None

    def is_duplicate(self, item: RawItem) -> bool:
        rec = self._known(item)
        if rec is not None:
            # known identity: duplicate unless it is a within-window NEW source
            if self.corroboration_update(item, _peek=True) is not None:
                return False
            return True
        if item.url in self._index["urls"]:
            return True
        for seen_title in self._index["titles"]:
            if fuzz.ratio(item.title.lower(), seen_title.lower()) >= FUZZY_THRESHOLD:
                return True
        return False

    def record(self, item: RawItem, note_path: str):
        cid = item.canonical_id or ""
        if cid:
            self._index["items"][cid] = {
                "sources": sorted({item.source} | {s for (s, _u, _e) in item.corroboration_sources}),
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "note_path": note_path,
                "title": item.title,
            }
        if item.url not in self._index["urls"]:
            self._index["urls"].append(item.url)
        if item.title not in self._index["titles"]:
            self._index["titles"].append(item.title)
        self._save()

    def corroboration_update(self, item: RawItem, _peek: bool = False):
        rec = self._known(item)
        if rec is None:
            return None
        try:
            first_seen = datetime.fromisoformat(rec["first_seen"])
        except Exception:
            return None
        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - first_seen).total_seconds() / 3600.0
        if age_h > self.window_hours:
            return None
        if item.source in rec["sources"]:
            return None
        if not _peek:
            rec["sources"].append(item.source)
            self._save()
        sources_count = len(rec["sources"]) if _peek is False else len(rec["sources"]) + 1
        new_line = f"- [{item.title}]({item.url}) — {item.source} · {item.engagement}"
        return {
            "note_path": rec["note_path"],
            "sources_count": sources_count,
            "validated": sources_count >= 2,
            "new_source_line": new_line,
        }

    def mark_seen(self, item: RawItem):
        # legacy no-op-safe path retained for callers not yet on record();
        # record() is the canonical writer now.
        if item.url not in self._index["urls"]:
            self._index["urls"].append(item.url)
        if item.title not in self._index["titles"]:
            self._index["titles"].append(item.title)
        self._save()
```

Note: verify the `_peek` count arithmetic against the tests — when `_peek=False` the source is appended first, so `len(rec["sources"])` already includes it (`sources_count=2` in the within-window test). When `_peek=True` (the `is_duplicate` probe) nothing is appended, so add 1 to reflect the would-be count. Adjust to make `test_within_window_new_source_returns_update` (expects 2) and the `is_duplicate` path both correct.

- [ ] **Step 5: Implement `Writer.update_corroboration`** — `agent/writer.py`

```python
    def update_corroboration(self, note_path, sources_count, validated, new_source_line):
        """Targeted frontmatter rewrite (sources_count, validated) + ## Sources
        append. No body regeneration. Fail-soft: a bad/missing file logs + skips."""
        try:
            path = Path(note_path)
            text = path.read_text()
        except Exception as exc:
            print(f"[warn] update_corroboration: cannot read {note_path}: {exc}")
            return
        try:
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if line.startswith("sources_count:"):
                    lines[i] = f"sources_count: {sources_count}"
                elif line.startswith("validated:"):
                    lines[i] = f"validated: {str(validated).lower()}"
            # append the new source line into the ## Sources block (before ## Related if present)
            out = []
            inserted = False
            for i, line in enumerate(lines):
                if line.strip() == "## Related" and not inserted:
                    out.append(new_source_line)
                    inserted = True
                out.append(line)
            if not inserted:
                out.append(new_source_line)
            path.write_text("\n".join(out) + ("\n" if text.endswith("\n") else ""))
        except Exception as exc:
            print(f"[warn] update_corroboration: failed on {note_path}: {exc}")
```

- [ ] **Step 6: Wire into `_write_kept`** — `agent/scheduler.py`

Replace the write loop body so that, per item, a within-window re-surface updates the existing note instead of writing a new one:

```python
    for item in kept:
        upd = dedup.corroboration_update(item)
        if upd is not None:
            writer.update_corroboration(
                upd["note_path"], upd["sources_count"], upd["validated"], upd["new_source_line"],
            )
            continue
        sections = None
        if enabled and item.score >= min_score:
            try:
                enricher.enrich(item)
                sections = synthesizer.synthesize(item) or None
            except Exception as exc:
                print(f"[warn] synthesis pipeline failed for {item.url}: {exc}")
                sections = None
        note_path = writer.write_note(item, sections=sections) if sections else writer.write_note(item)
        # record the identity so later sweeps corroborate against it
        try:
            rel = str(note_path.relative_to(writer._vault))
        except Exception:
            rel = str(note_path)
        dedup.record(item, note_path=rel)

    if kept:
        writer.regenerate_index()
```

Keep `dedup.mark_seen` removed from the loop (record() supersedes it). Confirm the `_write_kept` signature is unchanged.

- [ ] **Step 7: Thread `window_hours` from config** — deferred to Task 6 (config threading). For now `Deduplicator(index_path)` uses the 72h default; Task 6 passes `window_hours` from `corroboration.window_hours`.

- [ ] **Step 8: Run the full suite**

Run: `uv sync --extra dev && uv run python -m pytest -q`
Expected: PASS. Update any `test_scheduler.py` assertions that expected `mark_seen` calls to expect `record` instead (grep the scheduler test for `mark_seen`).

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat(0014): S3 index schema v2 + cross-sweep corroboration note updates"
```

---

### Task 4: Corroboration as an eval signal

**Files:**
- Modify: `agent/evaluator.py` (`_score_batch` and `_validate_batch` item lines)
- Test: `tests/test_evaluator.py` (extend)

**Interfaces:**
- Consumes: `RawItem.sources_count`.
- Produces: no new API — the score/validate prompt item lines gain a trailing `[corroborated by N sources]` when `sources_count >= 2`; unchanged when `< 2`.

- [ ] **Step 1: Write the failing tests** — extend `tests/test_evaluator.py`

Use a fake client that captures the prompt (match the existing pattern in that file — reuse its `FakeLLM`/`client=` injection). Sketch:

```python
def test_score_prompt_includes_corroboration_when_multi_source(mocker):
    from agent.evaluator import Evaluator
    captured = {}

    class Cap:
        def complete(self, prompt, max_tokens=512):
            captured.setdefault("prompts", []).append(prompt)
            return "1. 7 agentic"

    it = RawItem(title="Corro Paper", body="b", url="u", source="s", engagement=1, timestamp="t")
    it.content_type = "research"; it.sources_count = 3
    Evaluator(client=Cap())._score_batch([it])
    assert any("[corroborated by 3 sources]" in p for p in captured["prompts"])


def test_score_prompt_omits_corroboration_when_single_source(mocker):
    from agent.evaluator import Evaluator
    captured = {}

    class Cap:
        def complete(self, prompt, max_tokens=512):
            captured.setdefault("prompts", []).append(prompt)
            return "1. 7 agentic"

    it = RawItem(title="Solo", body="b", url="u", source="s", engagement=1, timestamp="t")
    it.content_type = "research"; it.sources_count = 1
    Evaluator(client=Cap())._score_batch([it])
    assert all("corroborated by" not in p for p in captured["prompts"])
```

Confirm the `Evaluator(client=...)` injection seam exists (it does — `__init__(self, api_key=None, *, client=None, llm_cfg=None)`). Mirror the existing evaluator tests' construction style.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_evaluator.py -v -k corroboration`
Expected: FAIL (the marker is not in the prompt yet).

- [ ] **Step 3: Implement** — add a small helper and use it in both batch builders

In `agent/evaluator.py`, add a module-level helper and append it to the item lines in `_score_batch` and `_validate_batch`:

```python
def _corroboration_suffix(item) -> str:
    return f" [corroborated by {item.sources_count} sources]" if item.sources_count >= 2 else ""
```

`_score_batch` item line becomes:
```python
        item_lines = "\n".join(
            f"{i+1}. [{item.content_type}] {item.title}{_corroboration_suffix(item)} — {item.body[:150]}"
            for i, item in enumerate(batch)
        )
```

`_validate_batch` item line becomes:
```python
        item_lines = "\n".join(
            f"{i+1}. [{item.content_type}, {item.score_label}={item.score}]{_corroboration_suffix(item)} {item.title}"
            for i, item in enumerate(batch)
        )
```

Also add one sentence to the `SCORE_PROMPT` and `VALIDATE_PROMPT` framing corroboration as **evidence of relevance/significance, not an automatic keep** (soft signal, no gate). E.g. append to each prompt's preamble:
`"Note: '[corroborated by N sources]' means the item independently surfaced on N sources — treat it as supporting evidence of relevance/significance, NOT an automatic keep."`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_evaluator.py -v`
Expected: PASS, and no regression in existing evaluator tests (the suffix is empty for single-source items, so their captured prompts are unchanged apart from the added static preamble sentence — update any test that asserts on the exact full prompt string).

- [ ] **Step 5: Commit**

```bash
git add agent/evaluator.py tests/test_evaluator.py
git commit -m "feat(0014): S4 corroboration as a soft eval signal in score/validate prompts"
```

---

### Task 5: Weekly citation-velocity re-poll — `agent/tools/citation_velocity.py`

**Files:**
- Create: `agent/tools/citation_velocity.py`
- Modify: `agent/scheduler.py` (`run_sweep`: after the normal sweep, when `deep=True` and config-enabled, run the re-poll — fail-soft)
- Modify: `agent/writer.py` (`regenerate_index`: read `rising`/`citation_count` frontmatter, add a 📈 marker + sort tiebreak that surfaces rising papers)
- Test: `tests/test_citation_velocity.py`, and extend `tests/test_writer.py` for the index marker

**Interfaces:**
- Consumes: vault `research`/`benchmark` notes with a resolvable paper id (arXiv ID / DOI from the note's `## Sources` URL); `S2_API_KEY` env.
- Produces:
  - `paper_ids_from_note(text: str) -> str | None` — extract an S2-batch id (`ARXIV:<id>` or `DOI:<doi>`) from a note's `## Sources` URLs.
  - `fetch_citation_counts(ids: list[str], *, api_key: str | None) -> dict[str, int]` — `POST /graph/v1/paper/batch` with `fields=citationCount`; one 429 backoff-then-skip; fail-soft `{}` on any error.
  - `run_citation_velocity(vault_path, *, min_delta: int, api_key: str | None, today: str | None = None) -> int` — walk notes, query in batch, store `citation_count` + `citation_checked` + compute `citation_delta`, flag `rising: true` when `delta >= min_delta`; returns count of notes flagged rising. Fail-soft throughout; returns 0 on soft failure.

- [ ] **Step 1: Write the failing tests** — `tests/test_citation_velocity.py`

```python
import agent.tools.citation_velocity as cv


def test_paper_id_from_arxiv_source_url():
    text = "## Sources\n- [P](https://arxiv.org/abs/2410.12345) — arxiv · 3\n"
    assert cv.paper_ids_from_note(text) == "ARXIV:2410.12345"


def test_paper_id_from_doi_source_url():
    text = "## Sources\n- [P](https://doi.org/10.1145/abc.def) — s2 · 3\n"
    assert cv.paper_ids_from_note(text) == "DOI:10.1145/abc.def"


def test_paper_id_none_when_no_resolvable_id():
    text = "## Sources\n- [P](https://blog.example.com/x) — blog · 3\n"
    assert cv.paper_ids_from_note(text) is None


def test_fetch_citation_counts_maps_batch_response(mocker):
    class Resp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return [{"paperId": "a", "externalIds": {"ArXiv": "2410.12345"}, "citationCount": 42}]
    mocker.patch("agent.tools.citation_velocity.httpx.post", return_value=Resp())
    out = cv.fetch_citation_counts(["ARXIV:2410.12345"], api_key=None)
    assert out["ARXIV:2410.12345"] == 42


def test_fetch_citation_counts_429_then_skip_failsoft(mocker):
    class Resp429:
        status_code = 429
        def raise_for_status(self): pass
        def json(self): return []
    mocker.patch("agent.tools.citation_velocity.httpx.post", return_value=Resp429())
    mocker.patch("agent.tools.citation_velocity.time.sleep")
    assert cv.fetch_citation_counts(["ARXIV:2410.12345"], api_key=None) == {}


def test_run_flags_rising_and_stores_frontmatter(tmp_path, mocker):
    note = tmp_path / "strategies" / "research" / "n.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\ntitle: \"P\"\ndate: 2026-08-01\ntype: research\nscore: 7\n"
        "score_label: novelty\ntags: [rag]\nvalidated: false\nsources_count: 1\n"
        "content_source: snippet\ncitation_count: 10\nstatus: new\n---\n\n# P\n\n"
        "## Sources\n- [P](https://arxiv.org/abs/2410.12345) — arxiv · 3\n"
    )
    mocker.patch(
        "agent.tools.citation_velocity.fetch_citation_counts",
        return_value={"ARXIV:2410.12345": 40},
    )
    flagged = cv.run_citation_velocity(tmp_path, min_delta=25, api_key=None, today="2026-08-08")
    text = note.read_text()
    assert flagged == 1
    assert "citation_count: 40" in text
    assert "citation_delta: 30" in text
    assert "rising: true" in text
    assert "citation_checked: 2026-08-08" in text


def test_run_disabled_is_noop_via_delta_below_threshold(tmp_path, mocker):
    note = tmp_path / "strategies" / "research" / "n.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\ntitle: \"P\"\ntype: research\ncitation_count: 10\nstatus: new\n---\n\n"
        "## Sources\n- [P](https://arxiv.org/abs/2410.12345) — arxiv · 3\n"
    )
    mocker.patch(
        "agent.tools.citation_velocity.fetch_citation_counts",
        return_value={"ARXIV:2410.12345": 12},
    )
    flagged = cv.run_citation_velocity(tmp_path, min_delta=25, api_key=None, today="2026-08-08")
    assert flagged == 0
    assert "rising: true" not in note.read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_citation_velocity.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `agent/tools/citation_velocity.py`**

```python
"""Weekly citation-velocity re-poll (deep sweep only).

Reuses the change-0012 Semantic Scholar integration patterns (S2_API_KEY,
429 backoff-then-skip, polite pacing) but hits the batch endpoint. Fully
config-gated + fail-soft: disabled => never called; any error => no-op.
"""

import datetime
import os
import re
import time
from pathlib import Path

import httpx
import yaml

S2_BATCH_API = "https://api.semanticscholar.org/graph/v1/paper/batch"
BACKOFF_SECONDS = 2
_ARXIV = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
_DOI = re.compile(r"(10\.\d{4,9}/[^\s?#)]+)")


def paper_ids_from_note(text: str) -> str | None:
    m = _ARXIV.search(text)
    if m:
        return f"ARXIV:{m.group(1)}"
    m = _DOI.search(text)
    if m:
        return f"DOI:{m.group(1).lower()}"
    return None


def fetch_citation_counts(ids: list[str], *, api_key: str | None) -> dict[str, int]:
    if not ids:
        return {}
    headers = {"x-api-key": api_key} if api_key else {}
    for attempt in range(2):
        try:
            resp = httpx.post(
                S2_BATCH_API,
                params={"fields": "citationCount,externalIds"},
                json={"ids": ids},
                headers=headers,
                timeout=15,
            )
        except Exception:
            return {}
        if getattr(resp, "status_code", None) == 429:
            if attempt == 0:
                time.sleep(BACKOFF_SECONDS)
                continue
            return {}
        try:
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return {}
        out: dict[str, int] = {}
        for req_id, paper in zip(ids, data if isinstance(data, list) else []):
            if isinstance(paper, dict) and paper.get("citationCount") is not None:
                out[req_id] = paper["citationCount"]
        return out
    return {}


def _iter_notes(vault_path: Path):
    for sub in ("research", "benchmarks"):
        d = Path(vault_path) / "strategies" / sub
        if d.exists():
            yield from d.glob("*.md")


def run_citation_velocity(vault_path, *, min_delta: int, api_key: str | None, today: str | None = None) -> int:
    today = today or str(datetime.date.today())
    notes: list[tuple[Path, str, str, dict]] = []
    ids: list[str] = []
    for note in _iter_notes(vault_path):
        try:
            text = note.read_text()
            parts = text.split("---")
            fm = yaml.safe_load(parts[1]) if len(parts) >= 3 else {}
        except Exception:
            continue
        pid = paper_ids_from_note(text)
        if not pid:
            continue
        notes.append((note, text, pid, fm or {}))
        ids.append(pid)
    if not ids:
        return 0
    counts = fetch_citation_counts(ids, api_key=api_key)
    if not counts:
        return 0
    flagged = 0
    for note, text, pid, fm in notes:
        new_count = counts.get(pid)
        if new_count is None:
            continue
        prev = fm.get("citation_count")
        delta = new_count - prev if isinstance(prev, int) else 0
        rising = isinstance(prev, int) and delta >= min_delta
        try:
            _rewrite_frontmatter(note, text, {
                "citation_count": new_count,
                "citation_delta": delta,
                "citation_checked": today,
                **({"rising": True} if rising else {}),
            })
        except Exception as exc:
            print(f"[warn] citation_velocity: {note}: {exc}")
            continue
        if rising:
            flagged += 1
    return flagged


def _rewrite_frontmatter(note: Path, text: str, updates: dict):
    lines = text.splitlines()
    # locate the frontmatter block (first two --- fences)
    fences = [i for i, l in enumerate(lines) if l.strip() == "---"]
    if len(fences) < 2:
        return
    start, end = fences[0], fences[1]
    keys_seen = set()
    for i in range(start + 1, end):
        key = lines[i].split(":", 1)[0].strip()
        if key in updates:
            val = updates[key]
            lines[i] = f"{key}: {str(val).lower() if isinstance(val, bool) else val}"
            keys_seen.add(key)
    inserts = [
        f"{k}: {str(v).lower() if isinstance(v, bool) else v}"
        for k, v in updates.items() if k not in keys_seen
    ]
    lines[end:end] = inserts
    note.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""))
```

- [ ] **Step 4: Wire into `run_sweep`** — `agent/scheduler.py`

After the existing `if deep: _run_source_discovery(...)` block, add (config-gated, fail-soft):

```python
    if deep and (citation_velocity_cfg or {}).get("enabled"):
        try:
            from agent.tools.citation_velocity import run_citation_velocity
            run_citation_velocity(
                vault_path,
                min_delta=citation_velocity_cfg.get("min_delta", 25),
                api_key=None,  # S2_API_KEY read from env inside
                today=date,
            )
        except Exception as exc:
            print(f"[warn] citation-velocity re-poll failed, skipping: {exc}")
```

Add `citation_velocity_cfg: dict | None = None` to the `run_sweep` signature (Task 6 threads it from cli).

- [ ] **Step 5: Add the 📈 rising marker to `regenerate_index`** — `agent/writer.py`

In `regenerate_index`, read `rising = fm.get("rising", False)` per note; when building the research/benchmark row title, prefix `📈 ` when rising, and add `rising` to the sort key so rising papers sort first within their score tier:

```python
                rising = fm.get("rising", False)
                ...
                groups[content_type].append((score, title, link, validated, category, rising))
```
and in the row emit + sort, use `rows.sort(key=lambda r: (not r[5], -r[0]))` (rising first, then score desc) and prefix the link/title cell with `"📈 "` when `r[5]`. Adjust the tuple unpacking in the emit loop accordingly (now 6-tuples). Add a `test_writer.py` case asserting a note with `rising: true` renders a `📈` and sorts above a higher-score non-rising note in the same section.

- [ ] **Step 6: Run the full suite**

Run: `uv sync --extra dev && uv run python -m pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(0014): S5 weekly citation-velocity re-poll + rising marker in index"
```

---

### Task 6: Config threading + defaults (corroboration + citation_velocity)

**Files:**
- Modify: `config.yml` (add the two new sections, both enabled with defaults)
- Modify: `cli.py` (`cmd_sweep`, `cmd_start`: read `corroboration`/`citation_velocity`, pass through)
- Modify: `agent/scheduler.py` (`run_sweep`/`search_sweep`/`start_scheduler` accept `corroboration_cfg`/`citation_velocity_cfg`; construct `Deduplicator(index_path, window_hours=...)` when corroboration enabled)
- Test: `tests/test_scheduler.py` (extend), optionally a `tests/test_cli.py` if one exists

**Interfaces:**
- Consumes: config dict.
- Produces: `run_sweep(..., corroboration_cfg=None, citation_velocity_cfg=None)`; `search_sweep(..., corroboration_cfg=None)`; both construct `Deduplicator(index_path, window_hours=corroboration_cfg.get("window_hours", 72))` when `corroboration_cfg` is enabled, else `Deduplicator(index_path)` (72 default — byte-identical).

- [ ] **Step 1: Write the failing test** — extend `tests/test_scheduler.py`

```python
def test_run_sweep_threads_window_hours_into_deduplicator(config, mocker):
    # patch Deduplicator to capture ctor kwargs; assert window_hours passed
    captured = {}
    real_init = ...
    # Follow the file's existing mocker.patch style for agent.scheduler.Deduplicator
    # and assert window_hours=48 when corroboration_cfg={"enabled": True, "window_hours": 48}
```

Match the existing scheduler test fixtures/patch seams (`config` fixture, `mocker.patch("agent.scheduler.Deduplicator")`).

- [ ] **Step 2: Run to verify fail**

Run: `uv run python -m pytest tests/test_scheduler.py -v -k window_hours`
Expected: FAIL (kwarg not threaded).

- [ ] **Step 3: Implement config threading**

  - `agent/scheduler.py`: add `corroboration_cfg`/`citation_velocity_cfg` params; construct the `Deduplicator` with `window_hours` when corroboration is enabled; pass `citation_velocity_cfg` into the Task-5 deep block. When `corroboration_cfg` is `None`/absent, keep today's construction and the corroborate() path is still active (identity dedup is the new baseline — confirm the grooming intent: corroboration.enabled default true; when the section is entirely absent, use defaults so behavior is the improved-but-safe path — verify against spec "with the new config sections absent, behavior is byte-identical to today"; if strict byte-identity is required when absent, gate the corroborate()/record() path behind `corroboration_cfg.get("enabled", True)` and fall back to the legacy write+mark_seen when explicitly disabled — implement the enabled-default-true gate).
  - `cli.py`: in `cmd_sweep` and `cmd_start`, read `cfg.get("corroboration", {})` and `cfg.get("citation_velocity", {})` and pass them into `run_sweep`/`search_sweep`/`start_scheduler`.

- [ ] **Step 4: Add config sections** — `config.yml`

```yaml
corroboration:
  enabled: true
  window_hours: 72

citation_velocity:
  enabled: true
  min_delta: 25
```

- [ ] **Step 5: Run the full suite**

Run: `uv sync --extra dev && uv run python -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(0014): S6 thread corroboration + citation_velocity config end-to-end"
```

---

### Task 7: Live check + verification

**Files:**
- No production code; this task produces the evidence for the results doc (authored by the implementer, not this task).

- [ ] **Step 1: Full suite green**

Run: `uv sync --extra dev && uv run python -m pytest -q`
Expected: all pass, no `deepeval`/`TracerProvider` crash, no `trafilatura` ImportError. Record the pass count.

- [ ] **Step 2: One real Semantic Scholar `/paper/batch` call**

Run a minimal Python snippet (or a throwaway `uv run python -c`) that calls `fetch_citation_counts(["ARXIV:1706.03762"], api_key=os.getenv("S2_API_KEY"))` for a known paper (Attention Is All You Need). Record the outcome:
- A 200 with a citation count → happy-path verified.
- A 429 from the unkeyed shared pool → **valid fail-soft verification** (per the live-testing learning: for a fail-soft adapter, hitting the throttle response live is the acceptance criterion firing, not a deferral). Record it as such and leave the happy-path on the human verify-checklist.

- [ ] **Step 3: (Optional, if API budget allows) one live deep sweep smoke**

`uv run python cli.py sweep --deep --lookback-days 2` with `llm.provider: openrouter` (repo default — needs no Anthropic credit). Confirm: exit 0, plausible item count, at least one corroborated note if any identity double-surfaced, citation-velocity block ran fail-soft. Non-fatal enrich/search self-skips are expected. If no live LLM budget, defer this to the human at the merge gate and note it in the results doc.

---

## Self-Review

**Spec coverage:** S1 (canonical.py + field) → Task 1; S2 (corroborate replacing cross_validate, wired both sweeps) → Task 2; S3 (index v2 + window + Writer.update_corroboration) → Task 3; S4 (eval signal) → Task 4; S5 (citation_velocity + rising marker, deep-only) → Task 5; config-gating/fail-soft/threading → Task 6; live check → Task 7. All spec sections mapped.

**Type consistency:** `canonical_id(item)->str` (Task 1) consumed by `corroborate` (Task 2) and `Deduplicator` (Task 3). `corroboration_sources` field added in Task 2, read in Task 3's `record`. `Deduplicator.corroboration_update`/`record` (Task 3) consumed by `_write_kept` (Task 3) and constructed with `window_hours` (Task 6). `fetch_citation_counts`/`run_citation_velocity` (Task 5) consumed by scheduler (Task 5) + threaded (Task 6). Consistent.

**Fail-soft/gating:** every new stage catches + warns + continues; citation-velocity + corroboration are config-gated; legacy `urls`/`titles` index keys preserved so `cmd_status` and v1 migration hold.

**Open verification note for the implementer:** the exact byte-identity-when-absent requirement (Task 6, Step 3) — decide during build whether "sections absent" means "corroboration on with defaults" (grooming intent: the fix is the new baseline) or "legacy path". The spec says "with the new config sections absent, behavior is byte-identical to today"; the safest reading is to gate the corroborate/record path behind `enabled` defaulting **true**, and keep a legacy `cross_validate`-equivalent fallback only if a test proves byte-identity is required when explicitly `enabled: false`. Resolve this with a test either way; do not leave it ambiguous.
