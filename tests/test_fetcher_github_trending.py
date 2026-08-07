import datetime

import httpx
import pytest

from agent.fetchers.github_trending import GitHubTrendingAdapter

GH_API = "https://api.github.com/search/repositories"

MOCK_GH_RESPONSE = {
    "items": [
        {
            "full_name": "acme/llm-agent",
            "description": "An autonomous LLM agent framework",
            "html_url": "https://github.com/acme/llm-agent",
            "stargazers_count": 1234,
            "pushed_at": "2026-08-05T12:00:00Z",
        },
        {
            "full_name": "small/obscure",
            "description": "barely any stars",
            "html_url": "https://github.com/small/obscure",
            "stargazers_count": 12,
            "pushed_at": "2026-08-04T09:00:00Z",
        },
    ]
}


def _mock_get(mocker, payload=MOCK_GH_RESPONSE, status_ok=True):
    resp = mocker.MagicMock()
    resp.json.return_value = payload
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "boom", request=mocker.MagicMock(), response=mocker.MagicMock()
        )
    return mocker.patch("httpx.get", return_value=resp)


def test_query_construction(mocker, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    mock_get = _mock_get(mocker)
    adapter = GitHubTrendingAdapter(
        topics=["llm", "ai-agents", "rag"], min_stars=100, lookback_days=7
    )
    adapter.fetch()

    assert mock_get.call_count == 1
    call = mock_get.call_args
    assert call.args[0] == GH_API
    params = call.kwargs["params"]

    q = params["q"]
    assert "topic:llm" in q
    assert "topic:ai-agents" in q
    assert "topic:rag" in q

    cutoff = (
        datetime.date(2026, 8, 7) - datetime.timedelta(days=7)
    )  # informational; real check below on format
    assert "pushed:>=" in q
    # pushed qualifier uses a YYYY-MM-DD date within the lookback window
    pushed_frag = [tok for tok in q.split() if tok.startswith("pushed:>=")][0]
    date_str = pushed_frag.split("pushed:>=")[1]
    parsed = datetime.date.fromisoformat(date_str)
    today = datetime.date.today()
    assert parsed <= today
    assert (today - parsed).days == 7

    assert params["sort"] == "stars"
    assert params["order"] == "desc"


def test_min_stars_threshold_drops_low(mocker, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    _mock_get(mocker)
    adapter = GitHubTrendingAdapter(topics=["llm"], min_stars=100)
    items = adapter.fetch()

    urls = [i.url for i in items]
    assert "https://github.com/acme/llm-agent" in urls
    assert "https://github.com/small/obscure" not in urls
    assert len(items) == 1


def test_mapping_to_rawitem(mocker, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    _mock_get(mocker)
    adapter = GitHubTrendingAdapter(topics=["llm"], min_stars=100)
    items = adapter.fetch()

    item = items[0]
    assert item.title == "acme/llm-agent"
    assert "autonomous LLM agent framework" in item.body
    assert item.url == "https://github.com/acme/llm-agent"
    assert item.engagement == 1234
    assert item.timestamp == "2026-08-05T12:00:00Z"
    assert item.source == "github"


def test_github_token_sends_auth_header(mocker, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    mock_get = _mock_get(mocker)
    adapter = GitHubTrendingAdapter(topics=["llm"], min_stars=100)
    adapter.fetch()

    headers = mock_get.call_args.kwargs.get("headers") or {}
    assert headers.get("Authorization") == "Bearer secret-token"


def test_no_token_no_auth_header(mocker, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    mock_get = _mock_get(mocker)
    adapter = GitHubTrendingAdapter(topics=["llm"], min_stars=100)
    adapter.fetch()

    headers = mock_get.call_args.kwargs.get("headers") or {}
    assert "Authorization" not in headers


def test_fail_soft_on_httpx_error(mocker, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    mocker.patch("httpx.get", side_effect=httpx.ConnectError("no network"))
    adapter = GitHubTrendingAdapter(topics=["llm"], min_stars=100)
    assert adapter.fetch() == []


def test_fail_soft_on_status_error(mocker, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    _mock_get(mocker, status_ok=False)
    adapter = GitHubTrendingAdapter(topics=["llm"], min_stars=100)
    assert adapter.fetch() == []


def test_fail_soft_on_malformed_payload(mocker, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    _mock_get(mocker, payload={"unexpected": "shape"})
    adapter = GitHubTrendingAdapter(topics=["llm"], min_stars=100)
    assert adapter.fetch() == []


def test_fail_soft_on_empty_payload(mocker, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    _mock_get(mocker, payload={"items": []})
    adapter = GitHubTrendingAdapter(topics=["llm"], min_stars=100)
    assert adapter.fetch() == []
