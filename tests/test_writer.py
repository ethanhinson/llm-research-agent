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
