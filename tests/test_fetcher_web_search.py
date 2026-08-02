from unittest.mock import Mock

from agent.fetchers.web_search import (
    TavilySearchClient,
    BingSearchClient,
    SerpAPISearchClient,
)


# --- Tavily ---


def test_tavily_maps_fields(mocker, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    fake_client = Mock()
    fake_client.search.return_value = {
        "results": [
            {
                "title": "Speculative Decoding",
                "url": "https://a.com/spec",
                "content": "A deep dive.",
                "published_date": "2026-08-01",
            }
        ]
    }
    fake_ctor = mocker.patch(
        "agent.fetchers.web_search.TavilyClient", return_value=fake_client, create=True
    )
    items = TavilySearchClient().search("query", max_results=5)

    assert len(items) == 1
    assert items[0].title == "Speculative Decoding"
    assert items[0].url == "https://a.com/spec"
    assert items[0].body == "A deep dive."
    assert items[0].source == "search/tavily"
    assert items[0].engagement == 0
    assert items[0].timestamp == "2026-08-01"
    fake_ctor.assert_called_once()


def test_tavily_missing_key_returns_empty(mocker, monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    fake_ctor = mocker.patch(
        "agent.fetchers.web_search.TavilyClient", create=True
    )
    assert TavilySearchClient().search("q") == []
    fake_ctor.assert_not_called()


def test_tavily_network_error_returns_empty(mocker, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    mocker.patch(
        "agent.fetchers.web_search.TavilyClient",
        side_effect=Exception("boom"),
        create=True,
    )
    assert TavilySearchClient().search("q") == []


# --- Bing ---


def _bing_response():
    resp = Mock()
    resp.json.return_value = {
        "webPages": {
            "value": [
                {
                    "name": "Bing Result",
                    "snippet": "Bing snippet.",
                    "url": "https://b.com/x",
                    "dateLastCrawled": "2026-07-30",
                }
            ]
        }
    }
    return resp


def test_bing_maps_fields(mocker, monkeypatch):
    monkeypatch.setenv("BING_SEARCH_API_KEY", "k")
    get = mocker.patch(
        "agent.fetchers.web_search.httpx.get", return_value=_bing_response()
    )
    items = BingSearchClient().search("query", max_results=5)

    assert len(items) == 1
    assert items[0].title == "Bing Result"
    assert items[0].body == "Bing snippet."
    assert items[0].url == "https://b.com/x"
    assert items[0].source == "search/bing"
    assert items[0].engagement == 0
    assert items[0].timestamp == "2026-07-30"
    get.assert_called_once()


def test_bing_missing_key_returns_empty(mocker, monkeypatch):
    monkeypatch.delenv("BING_SEARCH_API_KEY", raising=False)
    get = mocker.patch("agent.fetchers.web_search.httpx.get")
    assert BingSearchClient().search("q") == []
    get.assert_not_called()


def test_bing_network_error_returns_empty(mocker, monkeypatch):
    monkeypatch.setenv("BING_SEARCH_API_KEY", "k")
    mocker.patch(
        "agent.fetchers.web_search.httpx.get", side_effect=Exception("boom")
    )
    assert BingSearchClient().search("q") == []


# --- SerpAPI ---


def _serp_response():
    resp = Mock()
    resp.json.return_value = {
        "organic_results": [
            {
                "title": "Serp Result",
                "link": "https://s.com/y",
                "snippet": "Serp snippet.",
                "date": "2026-07-29",
            }
        ]
    }
    return resp


def test_serpapi_maps_fields(mocker, monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "k")
    mocker.patch("agent.fetchers.web_search.time.sleep")
    get = mocker.patch(
        "agent.fetchers.web_search.httpx.get", return_value=_serp_response()
    )
    items = SerpAPISearchClient().search("query", max_results=5)

    assert len(items) == 1
    assert items[0].title == "Serp Result"
    assert items[0].url == "https://s.com/y"
    assert items[0].body == "Serp snippet."
    assert items[0].source == "search/serpapi"
    assert items[0].engagement == 0
    assert items[0].timestamp == "2026-07-29"
    get.assert_called_once()


def test_serpapi_missing_key_returns_empty(mocker, monkeypatch):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    mocker.patch("agent.fetchers.web_search.time.sleep")
    get = mocker.patch("agent.fetchers.web_search.httpx.get")
    assert SerpAPISearchClient().search("q") == []
    get.assert_not_called()


def test_serpapi_network_error_returns_empty(mocker, monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "k")
    mocker.patch("agent.fetchers.web_search.time.sleep")
    mocker.patch(
        "agent.fetchers.web_search.httpx.get", side_effect=Exception("boom")
    )
    assert SerpAPISearchClient().search("q") == []
