from agent.fetchers.multi_search import MultiSearchFetcher
from agent.models import RawItem


def _item(url, title="t"):
    return RawItem(
        title=title,
        body="b",
        url=url,
        source="search/fake",
        engagement=0,
        timestamp="",
    )


class FakeClient:
    def __init__(self, items_by_query):
        # items_by_query: dict[query -> list[RawItem]]
        self.items_by_query = items_by_query
        self.calls = []

    def search(self, query, max_results=10):
        self.calls.append((query, max_results))
        return list(self.items_by_query.get(query, []))


class RaisingClient:
    def search(self, query, max_results=10):
        raise RuntimeError("boom")


def test_dedup_first_seen_and_stable_order():
    # clientA returns for two queries; clientB returns an overlapping url.
    a1 = _item("http://a/1")
    a2 = _item("http://a/2")
    b_overlap = _item("http://a/1", title="dup")  # same url as a1
    b_new = _item("http://b/1")

    client_a = FakeClient({"q1": [a1], "q2": [a2]})
    client_b = FakeClient({"q1": [b_overlap], "q2": [b_new]})

    fetcher = MultiSearchFetcher(
        clients=[client_a, client_b],
        queries=["q1", "q2"],
    )
    result = fetcher.fetch()

    # order: clientA q1, clientA q2, then clientB q1 (dup dropped), clientB q2
    urls = [r.url for r in result]
    assert urls == ["http://a/1", "http://a/2", "http://b/1"]
    # first-seen wins: the http://a/1 kept is clientA's, not clientB's "dup"
    assert result[0].title == "t"


def test_empty_clients_returns_empty():
    fetcher = MultiSearchFetcher(clients=[], queries=["q1"])
    assert fetcher.fetch() == []


def test_empty_queries_returns_empty():
    client = FakeClient({"q1": [_item("http://a/1")]})
    fetcher = MultiSearchFetcher(clients=[client], queries=[])
    assert fetcher.fetch() == []


def test_client_failure_is_isolated():
    healthy = FakeClient({"q1": [_item("http://ok/1")]})
    fetcher = MultiSearchFetcher(
        clients=[RaisingClient(), healthy],
        queries=["q1"],
    )
    result = fetcher.fetch()
    urls = [r.url for r in result]
    assert urls == ["http://ok/1"]


def test_max_results_per_query_passed_through():
    client = FakeClient({"q1": [_item("http://a/1")]})
    fetcher = MultiSearchFetcher(
        clients=[client],
        queries=["q1", "q2"],
        max_results_per_query=3,
    )
    fetcher.fetch()
    assert client.calls == [("q1", 3), ("q2", 3)]
