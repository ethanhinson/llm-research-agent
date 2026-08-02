"""Verify the top-level `search:` block in the repo-root config.yml."""
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
CONFIG_FILE = REPO_ROOT / "config.yml"


def test_search_block_present_and_valid():
    cfg = yaml.safe_load(CONFIG_FILE.read_text())

    assert cfg["search"]["interval_hours"] == 6
    assert cfg["search"]["dynamic_queries_enabled"] is True

    fixed = cfg["search"]["fixed_queries"]
    assert isinstance(fixed, list)
    assert len(fixed) > 0
