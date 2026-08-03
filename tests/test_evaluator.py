from unittest.mock import MagicMock, call

from agent.models import RawItem
from agent.evaluator import Evaluator


def make_item(title):
    return RawItem(title=title, body="description", url=f"https://example.com/{title}",
                   source="hackernews", engagement=200, timestamp="2026-08-01")


def _mock_message(text):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


def test_evaluator_three_passes_sets_fields(mocker):
    evaluator = Evaluator(api_key="test-key")

    responses = [
        _mock_message("1. research\n2. release\n"),
        _mock_message("1. 8 architecture\n2. 7\n"),
        _mock_message("1. keep\n2. skip\n"),
    ]
    mocker.patch.object(
        evaluator._client.messages, "create", side_effect=responses
    )

    items = [make_item("Flash Attention"), make_item("GPT-5 launch")]
    result = evaluator.score(items)

    assert result[0].content_type == "research"
    assert result[0].score == 8
    assert result[0].score_label == "novelty"
    assert result[0].category == "architecture"
    assert result[0].keep is True

    assert result[1].content_type == "release"
    assert result[1].score == 7
    assert result[1].score_label == "significance"
    assert result[1].keep is False


def test_evaluator_handles_empty_list(mocker):
    evaluator = Evaluator(api_key="test-key")
    result = evaluator.score([])
    assert result == []


def test_evaluator_missing_classify_line_keeps_default(mocker):
    evaluator = Evaluator(api_key="test-key")

    responses = [
        _mock_message(""),           # classify returns nothing → default "research"
        _mock_message("1. 6\n"),
        _mock_message("1. keep\n"),
    ]
    mocker.patch.object(
        evaluator._client.messages, "create", side_effect=responses
    )

    items = [make_item("Some item")]
    result = evaluator.score(items)

    assert result[0].content_type == "research"
    assert result[0].score == 6
    assert result[0].keep is True


def test_evaluator_subcategory_only_set_for_research(mocker):
    evaluator = Evaluator(api_key="test-key")

    responses = [
        _mock_message("1. tutorial\n"),
        _mock_message("1. 9\n"),
        _mock_message("1. keep\n"),
    ]
    mocker.patch.object(
        evaluator._client.messages, "create", side_effect=responses
    )

    items = [make_item("How to fine-tune LLMs")]
    result = evaluator.score(items)

    assert result[0].content_type == "tutorial"
    assert result[0].score_label == "practicality"
    assert result[0].category == ""   # no sub-category for tutorials
    assert result[0].keep is True
