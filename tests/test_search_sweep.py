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


def _search_item(title="Agentic RAG patterns for LLMs", url="https://ex.com/a"):
    return RawItem(
        title=title,
        body="A new LLM inference technique using retrieval augmented generation.",
        url=url,
        source="search/tavily",
        engagement=0,
        timestamp="2026-08-01",
    )


def test_search_sweep_drives_pipeline_and_writes(vault, mocker):
    item = _search_item()

    mocker.patch(
        "agent.scheduler.MultiSearchFetcher.fetch", return_value=[item]
    )
    mocker.patch(
        "agent.scheduler.SearchQueryGenerator.queries",
        return_value=["LLM prompting techniques 2026"],
    )

    def mock_score(items):
        for it in items:
            it.novelty = 9
        return items

    mocker.patch("agent.scheduler.Evaluator.score", side_effect=mock_score)

    written = []
    mocker.patch(
        "agent.scheduler.Writer.write_note",
        side_effect=lambda i: written.append(i) or Path("/tmp/x.md"),
    )
    mocker.patch("agent.scheduler.Writer.regenerate_index")

    index_path = vault.parent / ".index.json"
    result = sched_module.search_sweep(
        vault_path=vault,
        index_path=index_path,
        search_cfg={"max_results_per_query": 10, "novelty_min": 6},
        api_key="test",
    )

    # The search/* item survived the engagement filter and reached Writer.
    assert len(written) == 1
    assert written[0].source == "search/tavily"
    assert result == written


def test_search_sweep_engagement_filter_admits_search_source(vault, mocker):
    # engagement=0 must not disqualify a search/* item (unconditional pass).
    item = _search_item(url="https://ex.com/zero-engagement")

    mocker.patch(
        "agent.scheduler.MultiSearchFetcher.fetch", return_value=[item]
    )
    mocker.patch(
        "agent.scheduler.SearchQueryGenerator.queries", return_value=["q"]
    )

    def mock_score(items):
        for it in items:
            it.novelty = 8
        return items

    mocker.patch("agent.scheduler.Evaluator.score", side_effect=mock_score)

    written = []
    mocker.patch(
        "agent.scheduler.Writer.write_note",
        side_effect=lambda i: written.append(i) or Path("/tmp/x.md"),
    )
    mocker.patch("agent.scheduler.Writer.regenerate_index")

    index_path = vault.parent / ".index.json"
    sched_module.search_sweep(
        vault_path=vault,
        index_path=index_path,
        search_cfg={},
        api_key=None,
    )

    assert len(written) == 1
    assert written[0].source == "search/tavily"


def test_start_scheduler_registers_search_job_when_cfg_present(mocker, tmp_path):
    mock_scheduler = MagicMock()
    mock_scheduler.start.side_effect = KeyboardInterrupt
    mocker.patch("agent.scheduler.BlockingScheduler", return_value=mock_scheduler)

    try:
        sched_module.start_scheduler(
            vault_path=tmp_path / "vault",
            index_path=tmp_path / ".index.json",
            thresholds={"hn_points": 50},
            api_key="test",
            feeds=[],
            daily_time="08:00",
            weekly_day="sunday",
            search_cfg={"interval_hours": 6},
        )
    except KeyboardInterrupt:
        pass

    job_ids = [
        kw.get("id")
        for _, kw in mock_scheduler.add_job.call_args_list
    ]
    assert "search_sweep" in job_ids
    assert "daily_sweep" in job_ids
    assert "weekly_deep_sweep" in job_ids
    assert mock_scheduler.add_job.call_count == 3


def test_start_scheduler_no_search_job_when_cfg_empty(mocker, tmp_path):
    mock_scheduler = MagicMock()
    mock_scheduler.start.side_effect = KeyboardInterrupt
    mocker.patch("agent.scheduler.BlockingScheduler", return_value=mock_scheduler)

    try:
        sched_module.start_scheduler(
            vault_path=tmp_path / "vault",
            index_path=tmp_path / ".index.json",
            thresholds={"hn_points": 50},
            api_key="test",
            feeds=[],
            daily_time="08:00",
            weekly_day="sunday",
            search_cfg={},
        )
    except KeyboardInterrupt:
        pass

    job_ids = [
        kw.get("id")
        for _, kw in mock_scheduler.add_job.call_args_list
    ]
    assert "search_sweep" not in job_ids
    assert mock_scheduler.add_job.call_count == 2


def test_start_scheduler_no_search_job_when_cfg_none(mocker, tmp_path):
    mock_scheduler = MagicMock()
    mock_scheduler.start.side_effect = KeyboardInterrupt
    mocker.patch("agent.scheduler.BlockingScheduler", return_value=mock_scheduler)

    try:
        sched_module.start_scheduler(
            vault_path=tmp_path / "vault",
            index_path=tmp_path / ".index.json",
            thresholds={"hn_points": 50},
            api_key="test",
            feeds=[],
            daily_time="08:00",
            weekly_day="sunday",
        )
    except KeyboardInterrupt:
        pass

    job_ids = [
        kw.get("id")
        for _, kw in mock_scheduler.add_job.call_args_list
    ]
    assert "search_sweep" not in job_ids
    assert mock_scheduler.add_job.call_count == 2
