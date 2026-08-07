from agent.models import RawItem
from agent.evaluator import Evaluator


def make_item(title):
    return RawItem(title=title, body="description", url=f"https://example.com/{title}",
                   source="hackernews", engagement=200, timestamp="2026-08-01")


class FakeLLM:
    def __init__(self, texts):
        self._texts = list(texts)

    def complete(self, prompt, max_tokens):
        return self._texts.pop(0)


def test_evaluator_three_passes_sets_fields():
    fake = FakeLLM([
        "1. research\n2. release\n",
        "1. 8 architecture\n2. 7\n",
        "1. keep\n2. skip\n",
        "1. flash-attention\n2. gpt\n",
    ])
    evaluator = Evaluator(client=fake)

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


def test_evaluator_handles_empty_list():
    evaluator = Evaluator(client=FakeLLM([]))
    result = evaluator.score([])
    assert result == []


def test_evaluator_missing_classify_line_keeps_default():
    fake = FakeLLM([
        "",           # classify returns nothing → default "research"
        "1. 6\n",
        "1. keep\n",
        "1. reasoning\n",
    ])
    evaluator = Evaluator(client=fake)

    items = [make_item("Some item")]
    result = evaluator.score(items)

    assert result[0].content_type == "research"
    assert result[0].score == 6
    assert result[0].keep is True


def test_evaluator_subcategory_only_set_for_research():
    fake = FakeLLM([
        "1. tutorial\n",
        "1. 9\n",
        "1. keep\n",
        "1. fine-tuning\n",
    ])
    evaluator = Evaluator(client=fake)

    items = [make_item("How to fine-tune LLMs")]
    result = evaluator.score(items)

    assert result[0].content_type == "tutorial"
    assert result[0].score_label == "practicality"
    assert result[0].category == ""   # no sub-category for tutorials
    assert result[0].keep is True


def test_tag_batch_appends_to_structural_tags():
    fake = FakeLLM(["1. rag chain-of-thought\n2. fine-tuning rlhf\n"])
    evaluator = Evaluator(client=fake)
    a, b = make_item("A"), make_item("B")
    a.tags = ["research", "agentic"]
    b.tags = ["release"]
    evaluator._tag_batch([a, b])
    assert a.tags == ["research", "agentic", "rag", "chain-of-thought"]
    assert b.tags == ["release", "fine-tuning", "rlhf"]


def test_tag_batch_caps_at_4_tags():
    fake = FakeLLM(["1. a b c d e f\n"])
    evaluator = Evaluator(client=fake)
    item = make_item("A")
    item.tags = ["research"]
    evaluator._tag_batch([item])
    # cap is on topic tags appended (topic_tags[:4]); structural tag preserved leading
    assert item.tags == ["research", "a", "b", "c", "d"]


def test_tag_batch_normalizes_commas_and_case():
    fake = FakeLLM(["1. RAG, Fine Tuning, reasoning\n"])
    evaluator = Evaluator(client=fake)
    item = make_item("A")
    item.tags = ["research"]
    evaluator._tag_batch([item])
    assert item.tags == ["research", "rag", "fine-tuning", "reasoning"]


def test_score_includes_topic_tags():
    fake = FakeLLM([
        "1. research\n",
        "1. 8 architecture\n",
        "1. keep\n",
        "1. rag reasoning\n",
    ])
    evaluator = Evaluator(client=fake)
    items = [make_item("Flash Attention")]
    result = evaluator.score(items)
    assert result[0].tags[0] == "research"          # structural first
    assert "rag" in result[0].tags and "reasoning" in result[0].tags
