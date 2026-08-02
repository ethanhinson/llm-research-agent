from unittest.mock import MagicMock

from agent.tools.search_query_generator import SearchQueryGenerator


FIXED = [
    "LLM prompting techniques 2026",
    "agentic AI patterns",
    "multimodal language models",
]


def _cfg(**overrides):
    search = {
        "fixed_queries": list(FIXED),
        "dynamic_queries_enabled": True,
        "max_queries": 10,
    }
    search.update(overrides)
    return {"search": search}


def test_dynamic_disabled_returns_fixed_anchors():
    gen = SearchQueryGenerator(_cfg(dynamic_queries_enabled=False), api_key="test-key")
    assert gen.queries(["some title"]) == FIXED


def test_dynamic_enabled_merges_dedupes_and_truncates(mocker):
    # Dynamic response: one duplicate of a fixed anchor (dedup proof) + two new.
    canned = (
        "- agentic AI patterns\n"
        "- retrieval augmented generation benchmarks\n"
        "* LLM eval harnesses 2026\n"
    )
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=canned)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    ctor = mocker.patch(
        "agent.tools.search_query_generator.anthropic.Anthropic",
        return_value=mock_client,
    )

    # max_queries=4 forces truncation: 3 fixed + 2 unique dynamic = 5, capped to 4.
    gen = SearchQueryGenerator(_cfg(max_queries=4), api_key="test-key")
    result = gen.queries(["Flash Attention 3", "Chain of Draft"])

    ctor.assert_called_once_with(api_key="test-key")
    expected = FIXED + [
        "retrieval augmented generation benchmarks",
        "LLM eval harnesses 2026",
    ]
    # deduped (dup fixed dropped), preserving first-seen order, truncated to 4.
    assert result == expected[:4]
    assert len(result) == 4


def test_anthropic_error_is_nonfatal(mocker):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("boom")
    mocker.patch(
        "agent.tools.search_query_generator.anthropic.Anthropic",
        return_value=mock_client,
    )

    gen = SearchQueryGenerator(_cfg(), api_key="test-key")
    assert gen.queries(["title a", "title b"]) == FIXED


def test_no_api_key_skips_dynamic(mocker):
    ctor = mocker.patch("agent.tools.search_query_generator.anthropic.Anthropic")

    gen = SearchQueryGenerator(_cfg(), api_key=None)
    assert gen.queries(["title"]) == FIXED
    ctor.assert_not_called()
