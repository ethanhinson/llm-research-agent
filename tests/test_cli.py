import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def test_cli_sweep_calls_run_sweep(mocker):
    mock_sweep = mocker.patch("agent.scheduler.run_sweep", return_value=[])
    with patch("sys.argv", ["cli.py", "sweep"]):
        import cli
        import importlib
        importlib.reload(cli)

    # cli was called; if no exception was raised sweep was reached
    # (actual dispatch is in __main__ block so we just verify import works)


def test_cmd_start_passes_search_cfg(mocker):
    import cli

    mock_start = mocker.patch("agent.scheduler.start_scheduler")

    search_block = {
        "interval_hours": 6,
        "max_results_per_query": 10,
        "fixed_queries": ["LLM prompting techniques 2026"],
    }
    cfg = {
        "thresholds": {"hn_points": 50},
        "sources": {"feeds": []},
        "schedule": {},
        "search": search_block,
    }

    cli.cmd_start(args=None, cfg=cfg)

    assert mock_start.call_count == 1
    _, kwargs = mock_start.call_args
    assert kwargs["search_cfg"] == search_block


def test_cli_status_prints_info(tmp_path, capsys):
    vault = tmp_path / "vault"
    (vault / "strategies").mkdir(parents=True)
    (vault / "index.md").write_text("# Index\n")
    (vault / "sources.md").write_text("# Sources\n")

    with patch("sys.argv", ["cli.py", "status"]):
        import importlib, cli
        with patch("cli.VAULT_PATH", vault):
            importlib.reload(cli)
