import yaml
from pathlib import Path

from agent.models import RawItem
from agent.writer import Writer


def make_item(title="Flash Attention 3", content_type="research", score=8):
    return RawItem(
        title=title,
        body="A fast attention implementation.",
        url="https://github.com/Dao-AILab/flash-attention",
        source="hackernews",
        engagement=847,
        timestamp="2026-08-01T10:00:00Z",
        content_type=content_type,
        score=score,
        score_label="novelty" if content_type == "research" else "significance",
        keep=True,
        validated=True,
        sources_count=3,
        category="architecture" if content_type == "research" else "",
        tags=["inference", "speed"],
    )


def _vault(tmp_path):
    vault = tmp_path / "vault"
    (vault / "strategies").mkdir(parents=True)
    (vault / "index.md").write_text("# Index\n")
    return vault


def test_writer_creates_note_in_type_subdir(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    item = make_item(content_type="research")
    path = writer.write_note(item)

    assert path.exists()
    assert "strategies/research/" in str(path)


def test_writer_release_goes_to_releases_dir(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    item = make_item(title="GPT-5 launch", content_type="release", score=9)
    path = writer.write_note(item)

    assert "strategies/releases/" in str(path)


def test_writer_frontmatter_has_score_and_type(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    path = writer.write_note(make_item())

    parts = path.read_text().split("---")
    assert len(parts) >= 3
    fm = yaml.safe_load(parts[1])
    assert fm["score"] == 8
    assert fm["score_label"] == "novelty"
    assert fm["type"] == "research"
    assert fm["category"] == "architecture"
    assert fm["validated"] is True
    assert "novelty" not in fm  # old field must be gone


def test_writer_non_research_omits_category(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    item = make_item(title="GPT-5 launch", content_type="release", score=9)
    path = writer.write_note(item)

    fm = yaml.safe_load(path.read_text().split("---")[1])
    assert "category" not in fm


def test_writer_slug_derived_from_title(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    path = writer.write_note(make_item("Flash Attention 3"))

    assert "flash-attention-3" in path.name


def test_writer_uses_synthesized_sections(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    item = make_item()
    item.content_source = "full"
    sections = {
        "summary": "A synthesized summary sentence.",
        "how_it_works": "A synthesized explanation of the mechanism.",
        "why_it_matters": "A synthesized paragraph on practitioner impact.",
    }
    path = writer.write_note(item, sections=sections)
    content = path.read_text()

    assert "A synthesized summary sentence." in content
    assert "A synthesized explanation of the mechanism." in content
    assert "A synthesized paragraph on practitioner impact." in content
    assert "## Why It Matters" in content
    # legacy hardcoded line must NOT appear when synthesized
    assert "Engagement:" not in content
    assert "Why It's Gaining Traction" not in content


def test_writer_falls_back_to_template_without_sections(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    path = writer.write_note(make_item())  # no sections
    content = path.read_text()
    # legacy path keeps the body-excerpt template behavior
    assert "A fast attention implementation." in content


def test_writer_records_content_source_in_frontmatter(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    item = make_item()
    item.content_source = "full"
    path = writer.write_note(item, sections={"summary": "s", "how_it_works": "h", "why_it_matters": "w"})
    fm = yaml.safe_load(path.read_text().split("---")[1])
    assert fm["content_source"] == "full"


def test_writer_partial_sections_fall_back_per_section(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    item = make_item()
    # only summary synthesized; other two fall back to legacy template text
    path = writer.write_note(item, sections={"summary": "Only a summary here."})
    content = path.read_text()
    assert "Only a summary here." in content
    assert "## Why It Matters" in content


def test_writer_regenerates_index_grouped_by_type(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    writer.write_note(make_item("Flash Attention 3", content_type="research", score=8))
    writer.write_note(make_item("GPT-5 launch", content_type="release", score=9))
    writer.regenerate_index()

    index = (vault / "index.md").read_text()
    assert "## Research" in index
    assert "## Releases" in index
    assert "Flash Attention 3" in index
    assert "GPT-5 launch" in index


def test_regenerate_index_rising_marker_and_sort(tmp_path):
    vault = _vault(tmp_path)
    writer = Writer(vault_path=vault, date="2026-08-01")
    # higher-score non-rising note
    high = make_item("High Score Paper", content_type="research", score=9)
    writer.write_note(high)
    # lower-score rising note -> mark rising in frontmatter after writing
    low_path = writer.write_note(make_item("Rising Paper", content_type="research", score=5))
    low_text = low_path.read_text().replace("status: new", "status: new\nrising: true")
    low_path.write_text(low_text)

    writer.regenerate_index()
    index = (vault / "index.md").read_text()

    # rising note renders the marker
    assert "📈" in index
    rising_line = next(l for l in index.splitlines() if "Rising Paper" in l)
    assert "📈" in rising_line
    high_line = next(l for l in index.splitlines() if "High Score Paper" in l)
    assert "📈" not in high_line
    # rising sorts above the higher-score non-rising note within the section
    assert index.index("Rising Paper") < index.index("High Score Paper")


# --- Task 3: update_corroboration ---


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
