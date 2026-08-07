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
