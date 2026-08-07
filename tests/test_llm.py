# tests/test_llm.py
import httpx
import pytest
from unittest.mock import MagicMock

from agent.llm import (
    AnthropicClient,
    OpenRouterClient,
    get_client,
    DEFAULT_MODELS,
)


def test_get_client_defaults_to_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    client = get_client({})  # no llm section
    assert isinstance(client, AnthropicClient)
    assert client._model == DEFAULT_MODELS["anthropic"]


def test_get_client_openrouter_default_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    client = get_client({"llm": {"provider": "openrouter"}})
    assert isinstance(client, OpenRouterClient)
    assert client._model == DEFAULT_MODELS["openrouter"]


def test_get_client_explicit_model_override(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    client = get_client({"llm": {"provider": "openrouter", "model": "openai/gpt-4o-mini"}})
    assert client._model == "openai/gpt-4o-mini"


def test_get_client_unknown_provider_raises():
    with pytest.raises(ValueError, match="unknown llm provider"):
        get_client({"llm": {"provider": "bogus"}})


def test_get_client_missing_key_is_tolerated(monkeypatch):
    # Missing key must not crash construction — key-presence gating lives at the
    # call sites (e.g. dynamic queries). Construction returns a client whose key is None.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = get_client({"llm": {"provider": "anthropic"}})
    assert isinstance(client, AnthropicClient)
    assert client._api_key is None


def _anthropic_message(text):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


def test_anthropic_client_extracts_text(mocker):
    client = AnthropicClient(api_key="sk-ant", model="claude-haiku-4-5-20251001")
    mocker.patch.object(
        client._client.messages, "create",
        return_value=_anthropic_message("hello"),
    )
    assert client.complete("prompt", max_tokens=64) == "hello"


def test_anthropic_client_empty_on_malformed(mocker):
    client = AnthropicClient(api_key="sk-ant", model="claude-haiku-4-5-20251001")
    empty = MagicMock()
    empty.content = []
    mocker.patch.object(client._client.messages, "create", return_value=empty)
    assert client.complete("prompt", max_tokens=64) == ""


def test_openrouter_client_request_shape_and_extraction(mocker):
    client = OpenRouterClient(api_key="sk-or", model="anthropic/claude-haiku-4.5")
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"choices": [{"message": {"content": "hi there"}}]}
    post = mocker.patch("agent.llm.httpx.post", return_value=resp)

    out = client.complete("my prompt", max_tokens=128)
    assert out == "hi there"

    args, kwargs = post.call_args
    assert args[0] == "https://openrouter.ai/api/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer sk-or"
    assert "HTTP-Referer" in kwargs["headers"]
    assert "X-Title" in kwargs["headers"]
    body = kwargs["json"]
    assert body["model"] == "anthropic/claude-haiku-4.5"
    assert body["max_tokens"] == 128
    assert body["messages"] == [{"role": "user", "content": "my prompt"}]
    assert kwargs["timeout"] == 30


def test_openrouter_client_empty_on_malformed(mocker):
    client = OpenRouterClient(api_key="sk-or", model="anthropic/claude-haiku-4.5")
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"choices": []}
    mocker.patch("agent.llm.httpx.post", return_value=resp)
    assert client.complete("p", max_tokens=8) == ""


def test_openrouter_client_http_error_propagates(mocker):
    client = OpenRouterClient(api_key="sk-or", model="anthropic/claude-haiku-4.5")
    resp = MagicMock()
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "boom", request=MagicMock(), response=MagicMock()
    )
    mocker.patch("agent.llm.httpx.post", return_value=resp)
    with pytest.raises(httpx.HTTPStatusError):
        client.complete("p", max_tokens=8)


def test_provider_key_present(monkeypatch):
    from agent.llm import provider_key_present
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert provider_key_present({"llm": {"provider": "openrouter"}}) is False
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    assert provider_key_present({"llm": {"provider": "openrouter"}}) is True
