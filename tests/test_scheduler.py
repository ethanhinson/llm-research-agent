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
