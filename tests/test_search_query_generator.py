from agent.tools.search_query_generator import SearchQueryGenerator


FIXED = [
    "LLM prompting techniques 2026",
    "agentic AI patterns",
    "multimodal language models",
]


class FakeLLM:
    def __init__(self, text="", *, error=None):
        self.text = text
        self.error = error

    def complete(self, prompt, max_tokens):
        if self.error is not None:
            raise self.error
        return self.text


def _cfg(**overrides):
    search = {
        "fixed_queries": list(FIXED),
        "dynamic_queries_enabled": True,
        "max_queries": 10,
    }
    search.update(overrides)
    return {"search": search}


def test_dynamic_disabled_returns_fixed_anchors():
    gen = SearchQueryGenerator(
        _cfg(dynamic_queries_enabled=False), client=FakeLLM("ignored")
    )
    assert gen.queries(["some title"]) == FIXED


def test_dynamic_enabled_merges_dedupes_and_truncates():
    # Dynamic response: one duplicate of a fixed anchor (dedup proof) + two new.
    canned = (
        "- agentic AI patterns\n"
        "- retrieval augmented generation benchmarks\n"
        "* LLM eval harnesses 2026\n"
    )
    fake = FakeLLM(canned)

    # max_queries=4 forces truncation: 3 fixed + 2 unique dynamic = 5, capped to 4.
    gen = SearchQueryGenerator(_cfg(max_queries=4), client=fake)
    result = gen.queries(["Flash Attention 3", "Chain of Draft"])

    expected = FIXED + [
        "retrieval augmented generation benchmarks",
        "LLM eval harnesses 2026",
    ]
    # deduped (dup fixed dropped), preserving first-seen order, truncated to 4.
    assert result == expected[:4]
    assert len(result) == 4


def test_llm_error_is_nonfatal():
    fake = FakeLLM(error=Exception("boom"))
    gen = SearchQueryGenerator(_cfg(), client=fake)
    assert gen.queries(["title a", "title b"]) == FIXED


def test_no_provider_key_skips_dynamic(monkeypatch):
    # No injected client and no provider key present -> dynamic step is skipped.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    gen = SearchQueryGenerator(_cfg())
    assert gen.queries(["title"]) == FIXED


def test_provider_key_present_enables_dynamic(monkeypatch, mocker):
    # No injected client, but the configured provider's key is present -> the
    # generator builds a client via the factory and merges dynamic queries.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    fake = FakeLLM("agentic eval harnesses\nlong context retrieval\n")
    mocker.patch(
        "agent.tools.search_query_generator.get_client", return_value=fake
    )

    gen = SearchQueryGenerator(_cfg())
    out = gen.queries(recent_titles=["X"])
    assert "agentic eval harnesses" in out
    assert "long context retrieval" in out
