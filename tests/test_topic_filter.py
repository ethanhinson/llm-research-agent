from agent.models import RawItem
from agent.topic_filter import is_relevant


def item(title, body="", source="hackernews"):
    return RawItem(title=title, body=body, url="https://x.com", source=source,
                   engagement=200, timestamp="2026-08-01")


def test_llm_keyword_in_title_passes():
    assert is_relevant(item("Speculative decoding for faster LLM inference"))


def test_model_name_passes():
    assert is_relevant(item("DeepSeek-R2 technical report released"))


def test_off_topic_rejected():
    assert not is_relevant(item("7.1 Earthquake in Japan"))
    assert not is_relevant(item("UEFA drops out of FIFA competition"))
    assert not is_relevant(item("Elevators: a history"))


def test_arxiv_always_passes():
    assert is_relevant(item("Seismic activity in the Pacific", source="arxiv"))


def test_keyword_in_body_passes():
    assert is_relevant(item("New paper out", body="We evaluate our approach using chain-of-thought prompting"))


def test_openai_mention_passes():
    assert is_relevant(item("Our position on open-weights models", body="OpenAI released a statement"))
