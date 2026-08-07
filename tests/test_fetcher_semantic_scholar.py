import datetime

import httpx
import pytest

from agent.fetchers.semantic_scholar import (
    S2_SEARCH_API,
    SemanticScholarAdapter,
)


def _recent_date():
    return (datetime.date.today() - datetime.timedelta(days=1)).isoformat()


def _old_date():
    return (datetime.date.today() - datetime.timedelta(days=365)).isoformat()


def _paper(**over):
    base = {
        "title": "A Survey of LLM Agents",
        "abstract": "Long abstract about agents. " * 200,
        "url": "https://www.semanticscholar.org/paper/abc123",
        "citationCount": 42,
        "tldr": {"text": "LLM agents are surveyed."},
        "publicationDate": _recent_date(),
        "externalIds": {},
    }
    base.update(over)
    return base


def _resp(mocker, payload=None, status_code=200, raise_status=False):
    """Build a MagicMock httpx response."""
    if payload is None:
        payload = {"data": [_paper()]}
    resp = mocker.MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    if raise_status:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "boom", request=mocker.MagicMock(), response=mocker.MagicMock()
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _mock_get(mocker, resp=None, **kw):
    if resp is None:
        resp = _resp(mocker, **kw)
    return mocker.patch("httpx.get", return_value=resp)


@pytest.fixture(autouse=True)
def _no_sleep(mocker):
    # Neutralize backoff/politeness sleeps so the suite stays fast.
    mocker.patch("time.sleep", return_value=None)


@pytest.fixture(autouse=True)
def _clear_key(monkeypatch):
    monkeypatch.delenv("S2_API_KEY", raising=False)


def test_query_construction(mocker):
    mock_get = _mock_get(mocker, payload={"data": []})
    adapter = SemanticScholarAdapter(queries=["LLM agents"], max_per_query=7)
    adapter.fetch()

    assert mock_get.call_count == 1
    call = mock_get.call_args
    assert call.args[0] == S2_SEARCH_API
    params = call.kwargs["params"]
    assert params["query"] == "LLM agents"
    assert params["limit"] == 7
    fields = params["fields"]
    for f in ("title", "abstract", "url", "citationCount", "tldr", "publicationDate", "externalIds"):
        assert f in fields


def test_one_request_per_query(mocker):
    mock_get = _mock_get(mocker, payload={"data": []})
    adapter = SemanticScholarAdapter(queries=["a", "b", "c"])
    adapter.fetch()
    assert mock_get.call_count == 3


def test_mapping_tldr_preferred_over_abstract(mocker):
    _mock_get(mocker, payload={"data": [_paper(tldr={"text": "TLDR wins."}, abstract="abstract loses")]})
    items = SemanticScholarAdapter(queries=["q"]).fetch()
    assert len(items) == 1
    assert items[0].body == "TLDR wins."


def test_mapping_falls_back_to_abstract_when_no_tldr(mocker):
    abstract = "x" * 3000
    _mock_get(mocker, payload={"data": [_paper(tldr=None, abstract=abstract)]})
    items = SemanticScholarAdapter(queries=["q"]).fetch()
    assert len(items) == 1
    assert items[0].body == abstract[:2000]
    assert len(items[0].body) == 2000


def test_mapping_falls_back_when_tldr_has_no_text(mocker):
    _mock_get(mocker, payload={"data": [_paper(tldr={"text": None}, abstract="the abstract")]})
    items = SemanticScholarAdapter(queries=["q"]).fetch()
    assert items[0].body == "the abstract"


def test_arxiv_url_preference(mocker):
    payload = {
        "data": [
            _paper(externalIds={"ArXiv": "2401.01234"}, url="https://www.semanticscholar.org/paper/x"),
            _paper(externalIds={}, url="https://www.semanticscholar.org/paper/y"),
        ]
    }
    _mock_get(mocker, payload=payload)
    items = SemanticScholarAdapter(queries=["q"]).fetch()
    urls = [i.url for i in items]
    assert "https://arxiv.org/abs/2401.01234" in urls
    assert "https://www.semanticscholar.org/paper/y" in urls


def test_engagement_is_citation_count(mocker):
    _mock_get(mocker, payload={"data": [_paper(citationCount=99)]})
    items = SemanticScholarAdapter(queries=["q"]).fetch()
    assert items[0].engagement == 99


def test_engagement_defaults_to_zero_when_missing(mocker):
    p = _paper()
    del p["citationCount"]
    _mock_get(mocker, payload={"data": [p]})
    items = SemanticScholarAdapter(queries=["q"]).fetch()
    assert items[0].engagement == 0


def test_timestamp_and_source(mocker):
    d = _recent_date()
    _mock_get(mocker, payload={"data": [_paper(publicationDate=d)]})
    items = SemanticScholarAdapter(queries=["q"]).fetch()
    assert items[0].timestamp == d
    assert items[0].source == "s2"


def test_lookback_bounding_drops_old_keeps_recent_and_undated(mocker):
    payload = {
        "data": [
            _paper(title="old", publicationDate=_old_date()),
            _paper(title="recent", publicationDate=_recent_date()),
            _paper(title="undated", publicationDate=""),
        ]
    }
    _mock_get(mocker, payload=payload)
    items = SemanticScholarAdapter(queries=["q"], lookback_days=7).fetch()
    titles = [i.title for i in items]
    assert "old" not in titles
    assert "recent" in titles
    assert "undated" in titles


def test_api_key_sends_header(mocker, monkeypatch):
    monkeypatch.setenv("S2_API_KEY", "secret-key")
    mock_get = _mock_get(mocker, payload={"data": []})
    SemanticScholarAdapter(queries=["q"]).fetch()
    headers = mock_get.call_args.kwargs.get("headers") or {}
    assert headers.get("x-api-key") == "secret-key"


def test_no_key_no_header(mocker):
    mock_get = _mock_get(mocker, payload={"data": []})
    SemanticScholarAdapter(queries=["q"]).fetch()
    headers = mock_get.call_args.kwargs.get("headers") or {}
    assert "x-api-key" not in headers


def test_429_retry_then_skip(mocker):
    r429 = _resp(mocker, status_code=429, payload={"code": "429"})
    mock_get = mocker.patch("httpx.get", return_value=r429)
    items = SemanticScholarAdapter(queries=["q"]).fetch()
    assert items == []
    # one retry => two calls for the single query
    assert mock_get.call_count == 2


def test_429_retry_then_success(mocker):
    r429 = _resp(mocker, status_code=429, payload={"code": "429"})
    r200 = _resp(mocker, status_code=200, payload={"data": [_paper(title="after retry")]})
    mock_get = mocker.patch("httpx.get", side_effect=[r429, r200])
    items = SemanticScholarAdapter(queries=["q"]).fetch()
    assert [i.title for i in items] == ["after retry"]
    assert mock_get.call_count == 2


def test_fail_soft_on_httpx_error(mocker):
    mocker.patch("httpx.get", side_effect=httpx.ConnectError("no network"))
    assert SemanticScholarAdapter(queries=["q"]).fetch() == []


def test_fail_soft_on_status_error(mocker):
    _mock_get(mocker, raise_status=True)
    assert SemanticScholarAdapter(queries=["q"]).fetch() == []


def test_fail_soft_on_malformed_payload(mocker):
    _mock_get(mocker, payload={"unexpected": "shape"})
    assert SemanticScholarAdapter(queries=["q"]).fetch() == []


def test_one_bad_query_does_not_sink_others(mocker):
    good = _resp(mocker, status_code=200, payload={"data": [_paper(title="good")]})
    mocker.patch("httpx.get", side_effect=[httpx.ConnectError("x"), good])
    items = SemanticScholarAdapter(queries=["bad", "good"]).fetch()
    assert [i.title for i in items] == ["good"]


def test_empty_queries_returns_empty_no_http(mocker):
    mock_get = mocker.patch("httpx.get")
    assert SemanticScholarAdapter(queries=[]).fetch() == []
    assert mock_get.call_count == 0


def test_is_source_adapter():
    from agent.fetchers.base import SourceAdapter

    adapter = SemanticScholarAdapter(queries=["q"])
    assert isinstance(adapter, SourceAdapter)
    assert adapter.name == "s2"
