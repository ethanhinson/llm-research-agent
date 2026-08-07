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
            it.keep = True
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
        search_cfg={"max_results_per_query": 10},
        api_key="test",
    )

    # The search/* item flows through the funnel to the Writer (no sweep-level
    # engagement allowlist; the search adapter owns its own policy).
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
            it.keep = True
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


def test_search_sweep_threads_llm_cfg_to_query_generator(vault, mocker):
    """search_sweep passes llm_cfg into SearchQueryGenerator so dynamic queries
    use the configured provider."""
    item = _search_item()
    mocker.patch("agent.scheduler.MultiSearchFetcher.fetch", return_value=[item])

    gen_instance = MagicMock()
    gen_instance.queries.return_value = ["q"]
    gen_cls = mocker.patch(
        "agent.scheduler.SearchQueryGenerator", return_value=gen_instance
    )

    mocker.patch("agent.scheduler.Evaluator.score", side_effect=lambda items: items)
    mocker.patch("agent.scheduler.Writer.write_note", return_value=Path("/tmp/x.md"))
    mocker.patch("agent.scheduler.Writer.regenerate_index")

    sched_module.search_sweep(
        vault_path=vault,
        index_path=vault.parent / ".index.json",
        search_cfg={},
        api_key="test",
        llm_cfg={"provider": "openrouter"},
    )

    _, kwargs = gen_cls.call_args
    assert kwargs["llm_cfg"] == {"provider": "openrouter"}


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


def test_search_sweep_synthesizes_above_threshold(vault, mocker):
    """A kept item at/above min_score is enriched + synthesized; below is not."""
    above = _search_item(title="Above threshold item", url="https://ex.com/above")
    below = _search_item(title="Below threshold item", url="https://ex.com/below")

    mocker.patch(
        "agent.scheduler.MultiSearchFetcher.fetch", return_value=[above, below]
    )
    mocker.patch(
        "agent.scheduler.SearchQueryGenerator.queries", return_value=["q"]
    )

    def mock_score(items):
        for it in items:
            it.keep = True
            it.score = 8 if it.title.startswith("Above") else 3
        return items

    mocker.patch("agent.scheduler.Evaluator.score", side_effect=mock_score)

    enrich_calls = []
    mocker.patch(
        "agent.scheduler.ContentEnricher.enrich",
        side_effect=lambda item: enrich_calls.append(item) or item,
    )
    synth_calls = []

    def fake_synth(item):
        synth_calls.append(item)
        return {"summary": "s", "how_it_works": "h", "why_it_matters": "w"}

    mocker.patch(
        "agent.scheduler.NoteSynthesizer.synthesize", side_effect=fake_synth
    )

    write_calls = []
    mocker.patch(
        "agent.scheduler.Writer.write_note",
        side_effect=lambda i, sections=None: write_calls.append((i.title, sections)) or Path("/tmp/x.md"),
    )
    mocker.patch("agent.scheduler.Writer.regenerate_index")

    index_path = vault.parent / ".index.json"
    sched_module.search_sweep(
        vault_path=vault,
        index_path=index_path,
        search_cfg={},
        api_key="test",
        synthesis_cfg={"enabled": True, "min_score": 6, "max_chars": 8000},
    )

    # only the above-threshold item was enriched + synthesized
    assert [i.title for i in enrich_calls] == ["Above threshold item"]
    assert [i.title for i in synth_calls] == ["Above threshold item"]
    # above got sections; below got the legacy path (sections is None)
    calls = dict(write_calls)
    assert calls["Above threshold item"] is not None
    assert calls["Below threshold item"] is None


def test_search_sweep_synthesis_disabled_uses_legacy(vault, mocker):
    item = _search_item(title="Any item", url="https://ex.com/any")
    mocker.patch("agent.scheduler.MultiSearchFetcher.fetch", return_value=[item])
    mocker.patch("agent.scheduler.SearchQueryGenerator.queries", return_value=["q"])

    def mock_score(items):
        for it in items:
            it.keep = True
            it.score = 9
        return items

    mocker.patch("agent.scheduler.Evaluator.score", side_effect=mock_score)
    spy_enrich = mocker.patch("agent.scheduler.ContentEnricher.enrich")

    write_calls = []
    mocker.patch(
        "agent.scheduler.Writer.write_note",
        side_effect=lambda i, sections=None: write_calls.append(sections) or Path("/tmp/x.md"),
    )
    mocker.patch("agent.scheduler.Writer.regenerate_index")

    sched_module.search_sweep(
        vault_path=vault,
        index_path=vault.parent / ".index.json",
        search_cfg={},
        api_key="test",
        synthesis_cfg={"enabled": False, "min_score": 6, "max_chars": 8000},
    )

    spy_enrich.assert_not_called()
    assert write_calls == [None]
