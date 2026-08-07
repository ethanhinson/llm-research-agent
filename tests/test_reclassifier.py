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
