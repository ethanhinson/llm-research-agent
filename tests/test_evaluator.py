import pytest
from unittest.mock import MagicMock, patch

from agent.models import RawItem
from agent.evaluator import Evaluator


def make_item(title):
    return RawItem(title=title, body="description", url=f"https://example.com/{title}",
                   source="hackernews", engagement=200, timestamp="2026-08-01")


MOCK_SCORE_RESPONSE = """\
1. Flash Attention: 8
2. Chain of Draft: 6
"""


def test_evaluator_sets_novelty_scores(mocker):
    evaluator = Evaluator(api_key="test-key")
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=MOCK_SCORE_RESPONSE)]

    mocker.patch.object(evaluator._client.messages, "create", return_value=mock_message)

    items = [make_item("Flash Attention"), make_item("Chain of Draft")]
    result = evaluator.score(items)

    assert result[0].novelty == 8
    assert result[1].novelty == 6


def test_evaluator_handles_empty_list(mocker):
    evaluator = Evaluator(api_key="test-key")
    result = evaluator.score([])
    assert result == []
