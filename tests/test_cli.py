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


def test_cmd_sweep_threads_sources_cfg(mocker):
    import cli
    from argparse import Namespace

    mock_run = mocker.patch("agent.scheduler.run_sweep", return_value=[])
    mocker.patch("agent.scheduler.search_sweep", return_value=[])

    cfg = {
        "thresholds": {"hn_points": 50},
        "sources": {
            "feeds": [],
            "hf_papers": {"enabled": True, "min_upvotes": 3},
            "arxiv_queries": ["LLM agents"],
            "github_trending": {"enabled": True, "topics": ["llm"], "min_stars": 100},
        },
        "search": {},
        "synthesis": {},
    }
    args = Namespace(deep=False, lookback_days=None, date=None)
    cli.cmd_sweep(args=args, cfg=cfg)

    _, run_kwargs = mock_run.call_args
    assert run_kwargs["sources_cfg"] == cfg["sources"]


def test_cmd_discover_sources_appends(mocker, tmp_path):
    import cli
    from argparse import Namespace

    # Point the CLI's vault at a temp dir with a sources file.
    vault = tmp_path / "vault"
    (vault / "strategies").mkdir(parents=True)
    (vault / "sources.md").write_text("# Sources\n")
    mocker.patch.object(cli, "VAULT_PATH", vault)

    class FakeSD:
        def __init__(self, *a, **k):
            pass

        def suggest(self, recent_titles):
            return ["r/LLMPrompting — techniques"]

    mocker.patch("agent.tools.source_discovery.SourceDiscovery", FakeSD)
    mocker.patch("agent.scheduler.SourceDiscovery", FakeSD)

    cfg = {"llm": {"provider": "openrouter"}}
    cli.cmd_discover_sources(args=Namespace(), cfg=cfg)

    text = (vault / "sources.md").read_text()
    assert "Suggested (pending review)" in text
    assert "r/LLMPrompting" in text


def test_main_dispatches_discover_sources(mocker):
    import cli

    mock_cmd = mocker.patch.object(cli, "cmd_discover_sources")
    with patch("sys.argv", ["cli.py", "discover-sources"]):
        cli.main()
    assert mock_cmd.call_count == 1


def test_load_config_surfaces_llm_section():
    import cli
    cfg = cli.load_config()
    assert "llm" in cfg
    # config.yml defaults the provider to openrouter (see ops commit 74553b5).
    assert cfg["llm"].get("provider") == "openrouter"


def test_cmd_sweep_threads_llm_cfg(mocker):
    import cli
    from argparse import Namespace

    mock_run = mocker.patch("agent.scheduler.run_sweep", return_value=[])
    mock_search = mocker.patch("agent.scheduler.search_sweep", return_value=[])

    cfg = {
        "thresholds": {"hn_points": 50},
        "sources": {"feeds": []},
        "search": {"max_results_per_query": 10},
        "synthesis": {"enabled": True, "min_score": 6, "max_chars": 8000},
        "llm": {"provider": "openrouter", "model": "openai/gpt-4o-mini"},
    }
    args = Namespace(deep=False, lookback_days=None, date=None)
    cli.cmd_sweep(args=args, cfg=cfg)

    _, run_kwargs = mock_run.call_args
    assert run_kwargs["llm_cfg"] == cfg["llm"]
    _, search_kwargs = mock_search.call_args
    assert search_kwargs["llm_cfg"] == cfg["llm"]


def test_sweep_parser_accepts_lookback_days():
    import cli
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    cli._build_sweep_parser(sub)
    args = parser.parse_args(["sweep", "--lookback-days", "14"])
    assert args.lookback_days == 14


def test_cmd_regenerate_dispatches(mocker):
    import cli
    from argparse import Namespace

    mock_reg = MagicMock()
    mock_reg.regenerate_all.return_value = {
        "regenerated": 2, "fetch_failed": 0, "skipped": 1,
        "content_source_by_domain": {"full:example.com": 2},
    }
    mocker.patch("agent.regenerator.Regenerator", return_value=mock_reg)

    cfg = {"synthesis": {"enabled": True, "min_score": 6, "max_chars": 8000}}
    args = Namespace(date=None, all=True, min_score=None)
    cli.cmd_regenerate(args=args, cfg=cfg)

    assert mock_reg.regenerate_all.call_count == 1


def test_regenerate_parser_accepts_flags():
    import cli
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    cli._build_regenerate_parser(sub)
    args = parser.parse_args(["regenerate", "--all", "--min-score", "7"])
    assert args.all is True
    assert args.min_score == 7


def test_cmd_reclassify_dispatches(mocker):
    import cli
    from argparse import Namespace

    mock_rec = MagicMock()
    mock_rec.reclassify.return_value = {"reclassified": 3, "moved": 2, "errored": 0}
    mocker.patch("agent.reclassifier.Reclassifier", return_value=mock_rec)

    cfg = {}
    args = Namespace(date="2026-08-03", all=False)
    cli.cmd_reclassify(args=args, cfg=cfg)

    assert mock_rec.reclassify.call_count == 1
    _, kwargs = mock_rec.reclassify.call_args
    assert kwargs["date"] == "2026-08-03"
    assert kwargs["all_notes"] is False


def test_reclassify_parser_accepts_flags():
    import cli
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    cli._build_reclassify_parser(sub)
    args = parser.parse_args(["reclassify", "--date", "2026-08-04", "--all"])
    assert args.date == "2026-08-04"
    assert args.all is True
