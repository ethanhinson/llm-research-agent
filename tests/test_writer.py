import pytest
import yaml
from pathlib import Path

from agent.models import RawItem
from agent.writer import Writer


def make_item(title="Flash Attention 3", novelty=8):
    return RawItem(
        title=title,
        body="A fast attention implementation.",
        url="https://github.com/Dao-AILab/flash-attention",
        source="hackernews",
        engagement=847,
        timestamp="2026-08-01T10:00:00Z",
        novelty=novelty,
        validated=True,
        sources_count=3,
        category="architecture",
        tags=["inference", "speed"],
    )


def test_writer_creates_note(tmp_path):
    vault = tmp_path / "vault"
    (vault / "strategies").mkdir(parents=True)
    (vault / "index.md").write_text("# Index\n")
    (vault / "sources.md").write_text("# Sources\n")

    writer = Writer(vault_path=vault, date="2026-08-01")
    item = make_item()
    path = writer.write_note(item)

    assert path.exists()
    content = path.read_text()
    assert "Flash Attention 3" in content
    assert "novelty: 8" in content


def test_writer_frontmatter_valid_yaml(tmp_path):
    vault = tmp_path / "vault"
    (vault / "strategies").mkdir(parents=True)
    (vault / "index.md").write_text("# Index\n")
    (vault / "sources.md").write_text("# Sources\n")

    writer = Writer(vault_path=vault, date="2026-08-01")
    path = writer.write_note(make_item())

    content = path.read_text()
    # Extract YAML frontmatter between --- delimiters
    parts = content.split("---")
    assert len(parts) >= 3
    fm = yaml.safe_load(parts[1])
    assert fm["novelty"] == 8
    assert fm["validated"] is True


def test_writer_slug_derived_from_title(tmp_path):
    vault = tmp_path / "vault"
    (vault / "strategies").mkdir(parents=True)
    (vault / "index.md").write_text("# Index\n")
    (vault / "sources.md").write_text("# Sources\n")

    writer = Writer(vault_path=vault, date="2026-08-01")
    path = writer.write_note(make_item("Flash Attention 3"))

    assert "flash-attention-3" in path.name


def test_writer_regenerates_index(tmp_path):
    vault = tmp_path / "vault"
    (vault / "strategies").mkdir(parents=True)
    (vault / "index.md").write_text("# Index\n")
    (vault / "sources.md").write_text("# Sources\n")

    writer = Writer(vault_path=vault, date="2026-08-01")
    writer.write_note(make_item("Flash Attention 3", novelty=8))
    writer.write_note(make_item("Chain of Draft", novelty=6))
    writer.regenerate_index()

    index = (vault / "index.md").read_text()
    assert "Flash Attention 3" in index
    assert "Chain of Draft" in index
