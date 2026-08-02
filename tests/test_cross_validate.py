import pytest

from agent.models import RawItem
from agent.tools.cross_validate import cross_validate


def item(title, source):
    return RawItem(title=title, body="", url=f"https://example.com/{title}", source=source, engagement=100, timestamp="2026-08-01")


def test_matching_titles_across_sources_validated():
    items = [
        item("Flash Attention 3: faster inference", "hackernews"),
        item("Flash Attention 3: faster inference!", "reddit/LocalLLaMA"),
    ]
    result = cross_validate(items)
    assert all(i.validated for i in result)
    assert all(i.sources_count == 2 for i in result)


def test_dissimilar_titles_not_validated():
    items = [
        item("Flash Attention 3", "hackernews"),
        item("Chain of Thought survey 2026", "reddit/MachineLearning"),
    ]
    result = cross_validate(items)
    assert not any(i.validated for i in result)


def test_single_item_not_validated():
    items = [item("Solo paper about LoRA", "arxiv")]
    result = cross_validate(items)
    assert result[0].validated is False
    assert result[0].sources_count == 1
