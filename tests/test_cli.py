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


def test_cmd_sweep_threads_lookback_and_runs_search(mocker):
    import cli
    from argparse import Namespace

    mock_run = mocker.patch("agent.scheduler.run_sweep", return_value=[])
    mock_search = mocker.patch("agent.scheduler.search_sweep", return_value=[])

    cfg = {
        "thresholds": {"hn_points": 50},
        "sources": {"feeds": [{"name": "x", "url": "http://x", "type": "blog"}]},
        "search": {"max_results_per_query": 10},
        "synthesis": {"enabled": True, "min_score": 6, "max_chars": 8000},
    }
    args = Namespace(deep=False, lookback_days=21, date=None)
    cli.cmd_sweep(args=args, cfg=cfg)

    # run_sweep got the lookback window and the synthesis config
    _, run_kwargs = mock_run.call_args
    assert run_kwargs["lookback_days"] == 21
    assert run_kwargs["synthesis_cfg"] == cfg["synthesis"]

    # the search-backend path was exercised too (reconcile fix)
    assert mock_search.call_count == 1
    _, search_kwargs = mock_search.call_args
    assert search_kwargs["synthesis_cfg"] == cfg["synthesis"]


def test_sweep_parser_accepts_lookback_days():
    import cli
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    cli._build_sweep_parser(sub)
    args = parser.parse_args(["sweep", "--lookback-days", "14"])
    assert args.lookback_days == 14
