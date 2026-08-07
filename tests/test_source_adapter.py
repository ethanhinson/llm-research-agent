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
