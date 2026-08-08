import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from agent.models import RawItem
from agent import scheduler as sched_module


def make_item(title, engagement=200):
    return RawItem(title=title, body="body", url=f"https://example.com/{title}",
                   source="hackernews", engagement=engagement, timestamp="2026-08-01")


@pytest.fixture
def config(tmp_path):
    vault = tmp_path / "vault"
    (vault / "strategies").mkdir(parents=True)
    (vault / "index.md").write_text("# Index\n")
    (vault / "sources.md").write_text("# Sources\n")
    index = tmp_path / ".index.json"
    return {
        "vault_path": vault,
        "index_path": index,
        "thresholds": {"reddit_upvotes": 100, "hn_points": 50},
    }


def _hn_hit(title, points):
    return {
        "title": title,
        "story_text": "body",
        "url": f"https://example.com/{title}",
        "objectID": title,
        "points": points,
        "created_at": "2026-08-01",
    }


def test_run_sweep_filters_and_writes(config, mocker):
    # Engagement policy now lives in the HN *adapter* (its points>=threshold
    # post-filter), not in a sweep-level allowlist. Mock the HN API so the real
    # HNFetcher.fetch runs and drops the below-threshold hit; the above-threshold
    # one flows through the funnel to the writer.
    hn_resp = MagicMock()
    hn_resp.json.return_value = {
        "hits": [
            _hn_hit("Flash Attention 3: faster LLM inference", 200),
            _hn_hit("Low quality post about elevators", 10),
        ]
    }
    hn_resp.raise_for_status.return_value = None
    mocker.patch("agent.fetchers.hackernews.httpx.get", return_value=hn_resp)
    mocker.patch("agent.scheduler.ArxivFetcher.fetch", return_value=[])

    def mock_score(items):
        for item in items:
            item.keep = True
        return items

    mocker.patch("agent.scheduler.Evaluator.score", side_effect=mock_score)

    written = []
    mocker.patch("agent.scheduler.Writer.write_note", side_effect=lambda i: written.append(i) or Path("/tmp/x.md"))
    mocker.patch("agent.scheduler.Writer.regenerate_index")

    sched_module.run_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        thresholds=config["thresholds"],
        api_key="test",
        feeds=[],
    )

    assert len(written) == 1
    assert written[0].title == "Flash Attention 3: faster LLM inference"


def test_run_sweep_threads_llm_cfg_to_evaluator(config, mocker):
    """When cfg selects openrouter, run_sweep builds the evaluator via get_client
    with that llm cfg (proving the provider/model is threaded, not hard-coded)."""
    item = make_item("Flash Attention 3: faster LLM inference", engagement=200)
    mocker.patch("agent.scheduler.HNFetcher.fetch", return_value=[item])
    mocker.patch("agent.scheduler.ArxivFetcher.fetch", return_value=[])
    mocker.patch("agent.scheduler.WebFetcher.fetch", return_value=[])

    fake_client = MagicMock()
    spy = mocker.patch("agent.evaluator.get_client", return_value=fake_client)

    mocker.patch("agent.scheduler.Evaluator.score", side_effect=lambda items: items)
    mocker.patch("agent.scheduler.Writer.write_note", return_value=Path("/tmp/x.md"))
    mocker.patch("agent.scheduler.Writer.regenerate_index")

    sched_module.run_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        thresholds=config["thresholds"],
        api_key="test",
        feeds=[],
        llm_cfg={"provider": "openrouter"},
    )

    assert spy.call_args_list, "get_client was never called for the evaluator"
    assert spy.call_args_list[0].args[0] == {"llm": {"provider": "openrouter"}}


def test_run_sweep_unknown_source_flows_through_no_silent_drop(config, mocker):
    """The trap this refactor removes: an item whose source matched no old
    engagement-allowlist substring (e.g. "reddit") must flow all the way through
    the funnel — no NameError, no silent drop. Previously "reddit" hit an
    undefined reddit_threshold (NameError) and any other unknown source was
    silently dropped by the allowlist."""
    unknown = RawItem(
        title="A relevant LLM inference agent framework post",
        body="A new LLM agent framework for inference.",
        url="https://example.com/unknown-source",
        source="reddit",  # the exact string that used to raise NameError
        engagement=0,
        timestamp="2026-08-01",
    )
    # An adapter (arbitrary) yields the unknown-source item.
    mocker.patch("agent.scheduler.HNFetcher.fetch", return_value=[unknown])
    mocker.patch("agent.scheduler.ArxivFetcher.fetch", return_value=[])

    def mock_score(items):
        for item in items:
            item.keep = True
        return items

    mocker.patch("agent.scheduler.Evaluator.score", side_effect=mock_score)

    written = []
    mocker.patch(
        "agent.scheduler.Writer.write_note",
        side_effect=lambda i: written.append(i) or Path("/tmp/x.md"),
    )
    mocker.patch("agent.scheduler.Writer.regenerate_index")

    sched_module.run_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        thresholds=config["thresholds"],
        api_key="test",
        feeds=[],
    )

    assert len(written) == 1
    assert written[0].source == "reddit"


def test_run_sweep_threads_sources_cfg_into_build_adapters(config, mocker):
    """run_sweep passes its sources_cfg through to build_adapters as cfg['sources']
    so the new config-gated adapters (change 0010) are constructed."""
    captured = {}

    def fake_build_adapters(cfg, *, kind, **kw):
        captured["cfg"] = cfg
        captured["kind"] = kind
        return []  # no adapters -> empty sweep, exercised purely for the cfg

    mocker.patch("agent.scheduler.build_adapters", side_effect=fake_build_adapters)
    mocker.patch("agent.scheduler.Evaluator.score", side_effect=lambda items: items)

    sources_cfg = {
        "hf_papers": {"enabled": True},
        "arxiv_queries": ["LLM agents"],
        "github_trending": {"enabled": True, "topics": ["llm"]},
    }
    sched_module.run_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        thresholds=config["thresholds"],
        api_key="test",
        feeds=[],
        sources_cfg=sources_cfg,
    )

    assert captured["kind"] == "sweep"
    assert captured["cfg"]["sources"] == sources_cfg
    assert captured["cfg"]["thresholds"] == config["thresholds"]


def test_run_sweep_deep_triggers_source_discovery(config, mocker):
    """A deep sweep runs SourceDiscovery and appends suggestions to sources.md;
    a shallow sweep does not."""
    mocker.patch("agent.scheduler.build_adapters", return_value=[])
    mocker.patch("agent.scheduler.Evaluator.score", side_effect=lambda items: items)

    called = {"suggest": 0}

    class FakeSD:
        def __init__(self, *a, **k):
            pass

        def suggest(self, recent_titles):
            called["suggest"] += 1
            return ["r/LocalLLaMA — new subreddit"]

    mocker.patch("agent.scheduler.SourceDiscovery", FakeSD)

    # Shallow: no discovery.
    sched_module.run_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        thresholds=config["thresholds"],
        api_key="test",
        feeds=[],
        deep=False,
    )
    assert called["suggest"] == 0

    # Deep: discovery runs and appends the section.
    sched_module.run_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        thresholds=config["thresholds"],
        api_key="test",
        feeds=[],
        deep=True,
    )
    assert called["suggest"] == 1
    sources_text = (config["vault_path"] / "sources.md").read_text()
    assert "Suggested (pending review)" in sources_text
    assert "r/LocalLLaMA" in sources_text


def test_run_sweep_threads_window_hours_into_deduplicator(config, mocker):
    """corroboration_cfg.window_hours must reach the Deduplicator ctor; absent
    it defaults to 72 (today's construction)."""
    mocker.patch("agent.scheduler.build_adapters", return_value=[])
    mocker.patch("agent.scheduler.Evaluator.score", side_effect=lambda items: items)

    fake_dedup = MagicMock()
    fake_dedup.is_duplicate.return_value = False
    fake_dedup.corroboration_update.return_value = None
    dedup_ctor = mocker.patch(
        "agent.scheduler.Deduplicator", return_value=fake_dedup
    )

    sched_module.run_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        thresholds=config["thresholds"],
        api_key="test",
        feeds=[],
        corroboration_cfg={"enabled": True, "window_hours": 48},
    )
    assert dedup_ctor.call_args.kwargs.get("window_hours") == 48


def test_run_sweep_deduplicator_defaults_window_hours_when_absent(config, mocker):
    mocker.patch("agent.scheduler.build_adapters", return_value=[])
    mocker.patch("agent.scheduler.Evaluator.score", side_effect=lambda items: items)

    fake_dedup = MagicMock()
    fake_dedup.is_duplicate.return_value = False
    fake_dedup.corroboration_update.return_value = None
    dedup_ctor = mocker.patch(
        "agent.scheduler.Deduplicator", return_value=fake_dedup
    )

    sched_module.run_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        thresholds=config["thresholds"],
        api_key="test",
        feeds=[],
    )
    # absent -> positional index_path only, no window_hours kwarg (72 default)
    assert dedup_ctor.call_args.kwargs.get("window_hours") is None


def test_search_sweep_threads_window_hours_into_deduplicator(config, mocker):
    mocker.patch("agent.scheduler.build_adapters", return_value=[MagicMock(fetch=lambda: [])])
    mocker.patch(
        "agent.scheduler.SearchQueryGenerator.queries", return_value=["q"]
    )
    mocker.patch("agent.scheduler.Evaluator.score", side_effect=lambda items: items)

    fake_dedup = MagicMock()
    fake_dedup.is_duplicate.return_value = False
    fake_dedup.corroboration_update.return_value = None
    dedup_ctor = mocker.patch(
        "agent.scheduler.Deduplicator", return_value=fake_dedup
    )

    sched_module.search_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        search_cfg={"enabled": True},
        api_key="test",
        corroboration_cfg={"enabled": True, "window_hours": 12},
    )
    assert dedup_ctor.call_args.kwargs.get("window_hours") == 12


def test_run_sweep_corroboration_disabled_skips_update(config, mocker):
    """With corroboration_cfg={"enabled": False}, a within-window re-surface of a
    known identity must NOT take the corroboration_update path — it falls through
    to the normal write+record path. We assert via a mocked Deduplicator whose
    corroboration_update would otherwise fire, and confirm the writer never gets
    update_corroboration and does get write_note instead."""
    mocker.patch("agent.scheduler.build_adapters", return_value=[
        MagicMock(fetch=lambda: [make_item("Flash Attention 3", engagement=200)])
    ])
    mocker.patch("agent.scheduler.is_relevant", return_value=True)
    mocker.patch("agent.scheduler.corroborate", side_effect=lambda items: items)

    def mock_score(items):
        for item in items:
            item.keep = True
        return items

    mocker.patch("agent.scheduler.Evaluator.score", side_effect=mock_score)

    fake_dedup = MagicMock()
    fake_dedup.is_duplicate.return_value = False
    # If this were consulted, it would trigger the corroboration_update path.
    fake_dedup.corroboration_update.return_value = {
        "note_path": "n.md",
        "sources_count": 2,
        "validated": True,
        "new_source_line": "- line",
    }
    mocker.patch("agent.scheduler.Deduplicator", return_value=fake_dedup)

    updated = []
    written = []
    mocker.patch(
        "agent.scheduler.Writer.update_corroboration",
        side_effect=lambda *a, **k: updated.append(a),
    )
    mocker.patch(
        "agent.scheduler.Writer.write_note",
        side_effect=lambda i, **k: written.append(i) or Path("/tmp/x.md"),
    )
    mocker.patch("agent.scheduler.Writer.regenerate_index")

    sched_module.run_sweep(
        vault_path=config["vault_path"],
        index_path=config["index_path"],
        thresholds=config["thresholds"],
        api_key="test",
        feeds=[],
        corroboration_cfg={"enabled": False},
    )

    # disabled: corroboration_update must not be honored; normal write path taken.
    assert updated == []
    assert len(written) == 1
    fake_dedup.record.assert_called_once()


def test_start_scheduler_registers_two_jobs(config, mocker):
    mock_scheduler = MagicMock()
    mock_scheduler.start.side_effect = KeyboardInterrupt
    mocker.patch("agent.scheduler.BlockingScheduler", return_value=mock_scheduler)

    try:
        sched_module.start_scheduler(
            vault_path=config["vault_path"],
            index_path=config["index_path"],
            thresholds=config["thresholds"],
            api_key="test",
            feeds=[],
            daily_time="08:00",
            weekly_day="sunday",
        )
    except KeyboardInterrupt:
        pass

    assert mock_scheduler.add_job.call_count == 2
