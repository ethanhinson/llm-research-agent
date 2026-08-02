"""Full pipeline smoke test: 2 items in, 1 above threshold, 1 below, 1 note written."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from agent.models import RawItem
from agent import scheduler as sched_module


@pytest.fixture
def vault(tmp_path):
    v = tmp_path / "vault"
    (v / "strategies").mkdir(parents=True)
    (v / "index.md").write_text("# Index\n")
    (v / "sources.md").write_text("# Sources\n")
    return v


def test_smoke_one_note_written(vault, mocker):
    above = RawItem(
        title="Mixture of Experts explained",
        body="MoE routes tokens to specialist sub-networks.",
        url="https://example.com/moe",
        source="hackernews",
        engagement=300,
        timestamp="2026-08-01",
    )
    below = RawItem(
        title="Random low-quality post",
        body="Not useful.",
        url="https://example.com/low",
        source="hackernews",
        engagement=5,
        timestamp="2026-08-01",
    )

    mocker.patch("agent.scheduler.HNFetcher.fetch", return_value=[above, below])
    mocker.patch("agent.scheduler.ArxivFetcher.fetch", return_value=[])
    mocker.patch("agent.scheduler.WebFetcher.fetch", return_value=[])

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="1. 8 architecture")]
    mocker.patch("anthropic.Anthropic.messages", new_callable=lambda: type(
        "M", (), {"create": staticmethod(lambda **kw: mock_message)}
    ))

    index_path = vault.parent / ".index.json"
    sched_module.run_sweep(
        vault_path=vault,
        index_path=index_path,
        thresholds={"hn_points": 50, "novelty_min": 0},
        api_key="test",
        feeds=[],
    )

    notes = list((vault / "strategies").glob("*.md"))
    assert len(notes) == 1
    content = notes[0].read_text()
    assert "Mixture of Experts" in content
