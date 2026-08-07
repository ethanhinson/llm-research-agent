"""RawItem model tests."""
from agent.models import RawItem


def _item(**kw):
    base = dict(
        title="t",
        body="b",
        url="https://example.com",
        source="hackernews",
        engagement=0,
        timestamp="2026-08-01",
    )
    base.update(kw)
    return RawItem(**base)


def test_content_source_defaults_to_snippet():
    item = _item()
    assert item.content_source == "snippet"


def test_content_source_can_be_set_full():
    item = _item(content_source="full")
    assert item.content_source == "full"
