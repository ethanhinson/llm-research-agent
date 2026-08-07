"""Provider abstraction for LLM completions.

A minimal single-shot completion interface with two backends selected by
config: the direct Anthropic SDK, and OpenRouter's OpenAI-compatible REST API
(reached via httpx — no new dependency). An absent `llm:` config section leaves
today's Anthropic behavior byte-identical.
"""
import os
from typing import Protocol

import anthropic
import httpx

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openrouter": "anthropic/claude-haiku-4.5",
}

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_ATTRIBUTION_HEADERS = {
    "HTTP-Referer": "https://github.com/ethanhinson/llm-research-agent",
    "X-Title": "llm-research-agent",
}


class LLMClient(Protocol):
    def complete(self, prompt: str, max_tokens: int) -> str: ...


class AnthropicClient:
    def __init__(self, api_key: str | None, model: str):
        self._api_key = api_key
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, prompt: str, max_tokens: int) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if not message.content or not hasattr(message.content[0], "text"):
            return ""
        return message.content[0].text


class OpenRouterClient:
    def __init__(self, api_key: str | None, model: str):
        self._api_key = api_key
        self._model = model

    def complete(self, prompt: str, max_tokens: int) -> str:
        headers = {"Authorization": f"Bearer {self._api_key}", **_ATTRIBUTION_HEADERS}
        body = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = httpx.post(OPENROUTER_URL, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        content = choices[0].get("message", {}).get("content")
        return content or ""


def get_client(cfg: dict) -> LLMClient:
    llm_cfg = (cfg or {}).get("llm", {}) or {}
    provider = llm_cfg.get("provider", "anthropic")
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"unknown llm provider: {provider!r}")
    model = llm_cfg.get("model") or DEFAULT_MODELS[provider]
    api_key = os.getenv(_ENV_KEYS[provider])
    if provider == "anthropic":
        return AnthropicClient(api_key=api_key, model=model)
    return OpenRouterClient(api_key=api_key, model=model)
