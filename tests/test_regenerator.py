"""Backfill regenerator tests — in-place note rewrite preserving frontmatter."""
import yaml

from agent.regenerator import Regenerator, extract_first_source_url, split_note


LEGACY_NOTE = """\
---
category: architecture
date: 2026-08-01
score: 8
score_label: novelty
sources_count: 1
status: new
tags:
- research
- architecture
title: Mixture of Experts explained
type: research
validated: false
---

# Mixture of Experts explained

## Summary
Jul 8, 2026 — garbled snippet ...Read more

## How It Works
Jul 8, 2026 — garbled snippet ...Read more

## Why It's Gaining Traction
Engagement: 0 signals. Cross-source validated: false.

## Sources
- [Mixture of Experts explained](https://example.com/moe) — search/tavily · 0

## Related
"""

LOW_SCORE_NOTE = LEGACY_NOTE.replace("score: 8", "score: 3")


def _write(tmp_path, content, name="2026-08-01-moe.md", subdir="research"):
    d = tmp_path / "vault" / "strategies" / subdir
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(content)
    (tmp_path / "vault" / "index.md").write_text("# Index\n")
    return p


def test_split_note_separates_frontmatter_and_body():
    fm, body = split_note(LEGACY_NOTE)
    assert fm["score"] == 8
    assert fm["type"] == "research"
    assert "## Sources" in body


def test_extract_first_source_url():
    _, body = split_note(LEGACY_NOTE)
    assert extract_first_source_url(body) == "https://example.com/moe"


def test_regenerate_preserves_frontmatter_and_adds_content_source(tmp_path, mocker):
    p = _write(tmp_path, LEGACY_NOTE)

    mocker.patch(
        "agent.regenerator.ContentEnricher.enrich",
        side_effect=lambda item: setattr(item, "content_source", "full") or item,
    )
    mocker.patch(
        "agent.regenerator.NoteSynthesizer.synthesize",
        return_value={"summary": "New summary.", "how_it_works": "New mechanism.", "why_it_matters": "New impact."},
    )

    reg = Regenerator(vault_path=tmp_path / "vault", api_key="test", min_score=6)
    report = reg.regenerate_all()

    content = p.read_text()
    fm = yaml.safe_load(content.split("---")[1])
    # frontmatter preserved
    assert fm["score"] == 8
    assert fm["type"] == "research"
    assert fm["category"] == "architecture"
    assert fm["validated"] is False
    assert fm["tags"] == ["research", "architecture"]
    # content_source added
    assert fm["content_source"] == "full"
    # body sections rewritten
    assert "New summary." in content
    assert "New mechanism." in content
    assert "New impact." in content
    assert "## Why It Matters" in content
    # legacy junk gone
    assert "Read more" not in content
    assert "Why It's Gaining Traction" not in content
    assert "Engagement: 0 signals" not in content
    # Sources/Related preserved
    assert "https://example.com/moe" in content
    assert "## Related" in content
    assert report["regenerated"] == 1


def test_below_threshold_is_skipped(tmp_path, mocker):
    p = _write(tmp_path, LOW_SCORE_NOTE)
    spy_enrich = mocker.patch("agent.regenerator.ContentEnricher.enrich")

    reg = Regenerator(vault_path=tmp_path / "vault", api_key="test", min_score=6)
    report = reg.regenerate_all()

    spy_enrich.assert_not_called()
    assert report["skipped"] == 1
    # body untouched
    assert "Read more" in p.read_text()


def test_regenerate_by_date_filters(tmp_path, mocker):
    _write(tmp_path, LEGACY_NOTE, name="2026-08-01-a.md")
    _write(tmp_path, LEGACY_NOTE.replace("2026-08-01", "2026-07-15"), name="2026-07-15-b.md")

    mocker.patch(
        "agent.regenerator.ContentEnricher.enrich",
        side_effect=lambda item: item,
    )
    mocker.patch(
        "agent.regenerator.NoteSynthesizer.synthesize",
        return_value={"summary": "s", "how_it_works": "h", "why_it_matters": "w"},
    )

    reg = Regenerator(vault_path=tmp_path / "vault", api_key="test", min_score=6)
    report = reg.regenerate(date="2026-08-01")
    assert report["regenerated"] == 1


def test_index_regenerated(tmp_path, mocker):
    _write(tmp_path, LEGACY_NOTE)
    mocker.patch("agent.regenerator.ContentEnricher.enrich", side_effect=lambda i: i)
    mocker.patch(
        "agent.regenerator.NoteSynthesizer.synthesize",
        return_value={"summary": "s", "how_it_works": "h", "why_it_matters": "w"},
    )
    reg = Regenerator(vault_path=tmp_path / "vault", api_key="test", min_score=6)
    reg.regenerate_all()
    index = (tmp_path / "vault" / "index.md").read_text()
    assert "## Research" in index
    assert "Mixture of Experts explained" in index


def test_malformed_note_does_not_abort_batch(tmp_path, mocker):
    # A note that raises during rewrite must not stop the rest of the batch.
    good = _write(tmp_path, LEGACY_NOTE, name="2026-08-01-good.md")
    bad = _write(tmp_path, LEGACY_NOTE, name="2026-08-01-bad.md")

    mocker.patch("agent.regenerator.ContentEnricher.enrich", side_effect=lambda i: i)
    mocker.patch(
        "agent.regenerator.NoteSynthesizer.synthesize",
        return_value={"summary": "s", "how_it_works": "h", "why_it_matters": "w"},
    )

    real_read = type(bad).read_text

    def flaky_read(self, *a, **k):
        if self.name == "2026-08-01-bad.md":
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "boom")
        return real_read(self, *a, **k)

    mocker.patch.object(type(bad), "read_text", flaky_read)

    reg = Regenerator(vault_path=tmp_path / "vault", api_key="test", min_score=6)
    report = reg.regenerate_all()

    # the good note was still regenerated; the bad one tallied as a failure
    assert report["regenerated"] == 1
    assert report.get("fetch_failed", 0) + report.get("errored", 0) >= 1


def test_total_synthesis_failure_preserves_note(tmp_path, mocker):
    # enrich yields no full text AND synthesize returns {} -> do not clobber the
    # note with a title-only body; keep the original content.
    p = _write(tmp_path, LEGACY_NOTE)
    original = p.read_text()

    mocker.patch("agent.regenerator.ContentEnricher.enrich", side_effect=lambda i: i)
    mocker.patch("agent.regenerator.NoteSynthesizer.synthesize", return_value={})

    reg = Regenerator(vault_path=tmp_path / "vault", api_key="test", min_score=6)
    report = reg.regenerate_all()

    assert p.read_text() == original  # untouched
    assert report.get("regenerated", 0) == 0
