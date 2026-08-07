import pytest

from agent.fetchers.base import SourceAdapter
from agent.models import RawItem


class _Conforms:
    name = "x"

    def fetch(self) -> list[RawItem]:
        return []


class _MissingName:
    def fetch(self) -> list[RawItem]:
        return []


class _MissingFetch:
    name = "x"


def test_conforming_object_is_source_adapter():
    assert isinstance(_Conforms(), SourceAdapter)


def test_missing_fetch_is_not_source_adapter():
    assert not isinstance(_MissingFetch(), SourceAdapter)


# --- shipped fetchers conform to the protocol (Task 3) ---

from agent.fetchers.arxiv import ArxivFetcher
from agent.fetchers.hackernews import HNFetcher
from agent.fetchers.multi_search import MultiSearchFetcher
from agent.fetchers.web import WebFetcher


@pytest.mark.parametrize(
    "adapter, expected_name",
    [
        (HNFetcher(), "hackernews"),
        (ArxivFetcher(), "arxiv"),
        (WebFetcher(feeds=[]), "web"),
        (MultiSearchFetcher(clients=[], queries=[]), "search"),
    ],
)
def test_shipped_fetchers_conform(adapter, expected_name):
    assert isinstance(adapter, SourceAdapter)
    assert adapter.name == expected_name
