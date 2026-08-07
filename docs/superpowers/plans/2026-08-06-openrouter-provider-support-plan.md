<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0008 — OpenRouter provider support — full-system alternative to the Anthropic API](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0008-openrouter-provider-support.md)**
<!-- docket:backlink:end -->

# OpenRouter Provider Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a config-driven LLM provider abstraction so the whole agent can run against OpenRouter (OpenAI-compatible chat-completions) as an alternative to the direct Anthropic API, with an absent config leaving today's Anthropic behavior byte-identical.

**Architecture:** A new `agent/llm.py` defines an `LLMClient` Protocol (`complete(prompt, max_tokens) -> str`), an `AnthropicClient` (wraps the existing `anthropic.Anthropic`), an `OpenRouterClient` (`httpx` against the REST chat-completions endpoint — no new dependency), and a `get_client(cfg)` factory that reads the `llm:` config section, resolves the provider's API key from the environment, and returns the right backend. All four LLM call sites stop constructing `anthropic.Anthropic` directly and instead accept an injected `LLMClient`; `cli.py` builds one client from config + env and threads it through the existing `api_key` paths.

**Tech Stack:** Python 3.11+, `anthropic` SDK (existing), `httpx>=0.27` (already a dependency), `pytest` + `pytest-mock`, `pyyaml`, `python-dotenv`.

## Global Constraints

- **No new dependencies.** OpenRouter is reached via `httpx>=0.27`, already a direct dependency (`pyproject.toml`). Do NOT add `openai` or `litellm`.
- **Backward compatibility is byte-identical.** An absent `llm:` config section ⇒ `provider: anthropic` + the default model `claude-haiku-4-5-20251001` — the exact model constant used today. Existing deployments with no config change behave identically.
- **Per-provider default models:** `anthropic` → `claude-haiku-4-5-20251001`; `openrouter` → `anthropic/claude-haiku-4.5`. An explicit `llm.model` overrides the default for whichever provider is selected.
- **Preserve every existing fail-soft behavior:** `SearchQueryGenerator._dynamic_queries` returns `[]` on any exception (non-fatal); `NoteSynthesizer.synthesize` returns `{}` on any exception. The `complete()` implementations return `""` on a malformed/empty response, matching today's `_call` behavior.
- **Unknown provider fails LOUD at startup:** `get_client` raises a clear `ValueError` for an unknown `provider:` — never mid-sweep.
- **Test command (CANONICAL — learnings `pytest-shim-and-venv-provisioning`):** provision with `uv sync --extra dev` then run **`uv run python -m pytest`**. A bare `pytest` resolves to a global pyenv shim that autoloads a crashing global `deepeval` plugin (a `TracerProvider.get_tracer()` TypeError), and a fresh venv lacks project deps (`trafilatura`). A `TracerProvider.get_tracer()` TypeError or `ModuleNotFoundError: trafilatura` at pytest **startup** is environment pollution, NOT a red suite — provision and re-run, do not treat it as a code failure.
- **Secret hygiene:** never print or commit `OPENROUTER_API_KEY` (or any key). `.env` is gitignored; only `.env.example` (placeholder) is committed.

---

### Task 1: Provision the venv (setup — no commit of its own)

**Files:** none (environment only).

- [ ] **Step 1: Provision dev deps**

Run: `uv sync --extra dev`
Expected: succeeds; `trafilatura`, `pytest`, `pytest-mock` available in the project venv.

- [ ] **Step 2: Baseline the suite is green before any change**

Run: `uv run python -m pytest -q`
Expected: PASS (all existing tests green). If you see a `TracerProvider.get_tracer()` TypeError or `ModuleNotFoundError: trafilatura` at startup, that is environment pollution — you ran a bare `pytest` or skipped `uv sync`; re-run the canonical command above.

---

### Task 2: `agent/llm.py` — the provider abstraction + factory

**Files:**
- Create: `agent/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: environment variables `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`; the `anthropic` SDK; `httpx`.
- Produces (later tasks rely on these EXACT names/signatures):
  - `class LLMClient(Protocol): def complete(self, prompt: str, max_tokens: int) -> str: ...`
  - `class AnthropicClient: def __init__(self, api_key: str | None, model: str); def complete(self, prompt: str, max_tokens: int) -> str`
  - `class OpenRouterClient: def __init__(self, api_key: str | None, model: str); def complete(self, prompt: str, max_tokens: int) -> str`
  - `def get_client(cfg: dict) -> LLMClient` — `cfg` is the full config dict (or any dict); reads `cfg.get("llm", {})`, keys `provider` (default `"anthropic"`) and `model` (optional). Resolves the API key from env per provider. Returns the matching client. Raises `ValueError(f"unknown llm provider: {provider!r}")` for anything other than `anthropic`/`openrouter`.
  - Module constants: `DEFAULT_MODELS = {"anthropic": "claude-haiku-4-5-20251001", "openrouter": "anthropic/claude-haiku-4.5"}`; `OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"`.

- [ ] **Step 1: Write failing tests for the factory**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.llm'`.

- [ ] **Step 3: Write failing tests for the two backends**

```python
# append to tests/test_llm.py

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
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_llm.py -v`
Expected: FAIL (classes not defined / attributes missing).

- [ ] **Step 5: Implement `agent/llm.py`**

```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_llm.py -v`
Expected: PASS (all `agent/llm.py` tests green).

- [ ] **Step 7: Commit**

```bash
git add agent/llm.py tests/test_llm.py
git commit -m "feat(llm): add provider abstraction (Anthropic + OpenRouter) and factory"
```

---

### Task 3: Migrate `agent/evaluator.py` to the LLMClient abstraction

**Files:**
- Modify: `agent/evaluator.py` (remove `MODEL` at line 7; `Evaluator.__init__`; `Evaluator._call`)
- Test: `tests/test_evaluator.py`, `tests/test_reclassifier.py`

**Interfaces:**
- Consumes: `agent.llm.get_client`, `agent.llm.LLMClient`.
- Produces: `Evaluator.__init__(self, api_key=None, *, client=None, llm_cfg=None)` — if `client` is provided, use it; else build via `get_client({"llm": llm_cfg or {}})` (the factory reads the env key itself, so `api_key` is retained only for signature backward-compat and passed through to the factory context is unnecessary — see note). `Evaluator._call(prompt)` delegates to `self._client.complete(prompt, max_tokens=512)`. `_set_tags` unchanged (local, no LLM).

> **Backward-compat note.** Existing callers pass `api_key=...` positionally/by keyword. Keep `api_key` as the first param so no caller breaks. When no explicit `client` is injected, construct `get_client({"llm": llm_cfg or {}})`; the factory resolves the key from env. This means a bare `Evaluator(api_key=key)` now builds an Anthropic client from env — identical model, identical behavior. Tests that need a fake inject `client=FakeLLM()`.

- [ ] **Step 1: Update `tests/test_evaluator.py` to inject a fake client (failing)**

Replace the `mocker.patch.object(evaluator._client.messages, "create", ...)` pattern with a fake `LLMClient`. Example for `test_evaluator_three_passes_sets_fields`:

```python
class FakeLLM:
    def __init__(self, texts):
        self._texts = list(texts)
    def complete(self, prompt, max_tokens):
        return self._texts.pop(0)


def test_evaluator_three_passes_sets_fields():
    fake = FakeLLM([
        "1. research\n2. release\n",
        "1. 8 architecture\n2. 7\n",
        "1. keep\n2. skip\n",
    ])
    evaluator = Evaluator(client=fake)
    items = [make_item("Flash Attention"), make_item("GPT-5 launch")]
    result = evaluator.score(items)
    assert result[0].content_type == "research"
    assert result[0].score == 8
    assert result[1].keep is False
```

Apply the same `client=fake` injection to every test in the file that currently patches `_client.messages.create` (the `_mock_message` helper and its `mocker.patch.object` calls are removed in favor of `FakeLLM`). Preserve every assertion.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_evaluator.py -v`
Expected: FAIL (`Evaluator.__init__` has no `client` kwarg yet).

- [ ] **Step 3: Implement the evaluator migration**

In `agent/evaluator.py`: delete `import anthropic` and the `MODEL = "claude-haiku-4-5-20251001"` line. Add `from agent.llm import get_client, LLMClient`. Rewrite:

```python
class Evaluator:
    def __init__(self, api_key: str | None = None, *, client: LLMClient | None = None,
                 llm_cfg: dict | None = None):
        self._client = client if client is not None else get_client({"llm": llm_cfg or {}})

    # ... score(), _set_tags(), _classify_batch() etc. UNCHANGED ...

    def _call(self, prompt: str) -> str:
        return self._client.complete(prompt, max_tokens=512)
```

> The `MODEL` constant is removed. `synthesizer.py` imports it — Task 4 fixes that import. If you migrate evaluator first, `tests/test_synthesizer.py` collection may error on the stale import until Task 4; run evaluator tests in isolation for this task's green check (`-p no:cacheprovider tests/test_evaluator.py tests/test_reclassifier.py`), and rely on the full-suite gate in Task 8.

- [ ] **Step 4: Update `tests/test_reclassifier.py`**

Its tests `mocker.patch(... Evaluator ...)` at lines ~67/131/163 patch the `Evaluator` constructor/class in `agent.reclassifier`. Those keep working because `Reclassifier` still calls `Evaluator(api_key=...)`. Verify no test reaches a live client; if any constructs a real `Evaluator` expecting `_client.messages`, switch it to inject `client=FakeLLM([...])` via the reclassifier path or keep the existing class-level patch. Make the minimal change needed to keep them green.

- [ ] **Step 5: Run the affected tests to verify they pass**

Run: `uv run python -m pytest tests/test_evaluator.py tests/test_reclassifier.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/evaluator.py tests/test_evaluator.py tests/test_reclassifier.py
git commit -m "refactor(evaluator): route LLM calls through the llm.py abstraction"
```

---

### Task 4: Migrate `agent/synthesizer.py` to the LLMClient abstraction

**Files:**
- Modify: `agent/synthesizer.py` (drop `import anthropic`, drop `from agent.evaluator import MODEL`; `NoteSynthesizer.__init__`; `_call`)
- Test: `tests/test_synthesizer.py`, `tests/test_regenerator.py`

**Interfaces:**
- Consumes: `agent.llm.get_client`, `agent.llm.LLMClient`.
- Produces: `NoteSynthesizer.__init__(self, api_key=None, *, client=None, llm_cfg=None)` (same shape as `Evaluator`). `_call(prompt)` → `self._client.complete(prompt, max_tokens=MAX_TOKENS)` where `MAX_TOKENS = 900` stays a local module constant in synthesizer.

- [ ] **Step 1: Update `tests/test_synthesizer.py` to inject a fake client (failing)**

Replace `mocker.patch.object(synth._client.messages, "create", ...)` with a `FakeLLM` whose `complete` returns the canned synthesis text, constructing `NoteSynthesizer(client=fake)`. Preserve all section-parsing assertions.

```python
class FakeLLM:
    def __init__(self, text=""):
        self.text = text
    def complete(self, prompt, max_tokens):
        return self.text

# e.g.
def test_synthesize_parses_three_sections():
    fake = FakeLLM("SUMMARY:\n...\nHOW IT WORKS:\n...\nWHY IT MATTERS:\n...\n")
    synth = NoteSynthesizer(client=fake)
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_synthesizer.py -v`
Expected: FAIL (`client` kwarg not accepted yet / stale `MODEL` import).

- [ ] **Step 3: Implement the synthesizer migration**

In `agent/synthesizer.py`: remove `import anthropic` and `from agent.evaluator import MODEL`. Add `from agent.llm import get_client, LLMClient`. Keep `MAX_TOKENS = 900`. Rewrite:

```python
class NoteSynthesizer:
    def __init__(self, api_key: str | None = None, *, client: LLMClient | None = None,
                 llm_cfg: dict | None = None):
        self._client = client if client is not None else get_client({"llm": llm_cfg or {}})

    def _call(self, prompt: str) -> str:
        return self._client.complete(prompt, max_tokens=MAX_TOKENS)
    # synthesize() UNCHANGED (fail-soft try/except returning {} preserved)
```

Also update the module docstring line that references importing `MODEL` from the evaluator (remove the stale "single source of the Haiku model id" note).

- [ ] **Step 4: Update `tests/test_regenerator.py`**

It patches `agent.regenerator.NoteSynthesizer.synthesize` (line ~72) — a method-level patch that keeps working since `Regenerator` still calls `NoteSynthesizer(api_key=...)`. Verify green; make the minimal change if any test constructs a live synthesizer expecting `_client.messages`.

- [ ] **Step 5: Run the affected tests to verify they pass**

Run: `uv run python -m pytest tests/test_synthesizer.py tests/test_regenerator.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/synthesizer.py tests/test_synthesizer.py tests/test_regenerator.py
git commit -m "refactor(synthesizer): route LLM calls through the llm.py abstraction"
```

---

### Task 5: Migrate `agent/tools/source_discovery.py`

**Files:**
- Modify: `agent/tools/source_discovery.py` (drop `import anthropic`, drop `MODEL` line 6; `SourceDiscovery.__init__`; `suggest`)
- Test: `tests/test_source_discovery.py`

**Interfaces:**
- Produces: `SourceDiscovery.__init__(self, sources_path, api_key=None, *, client=None, llm_cfg=None)`. `suggest()` calls `self._client.complete(prompt, max_tokens=512)` and keeps the existing text-parsing / "no new sources" logic.

- [ ] **Step 1: Update `tests/test_source_discovery.py` (failing)**

Replace `mocker.patch.object(sd._client.messages, "create", ...)` with a `FakeLLM` whose `complete` returns the canned suggestions text, constructing `SourceDiscovery(sources_path=sources_file, client=fake)`. Preserve both tests' assertions.

- [ ] **Step 2: Run to verify fail**

Run: `uv run python -m pytest tests/test_source_discovery.py -v`
Expected: FAIL (`client` kwarg not accepted).

- [ ] **Step 3: Implement**

Remove `import anthropic` and `MODEL`. Add `from agent.llm import get_client, LLMClient`.

```python
class SourceDiscovery:
    def __init__(self, sources_path: Path, api_key: str | None = None, *,
                 client: LLMClient | None = None, llm_cfg: dict | None = None):
        self._sources_path = Path(sources_path)
        self._client = client if client is not None else get_client({"llm": llm_cfg or {}})

    def suggest(self, recent_titles: list[str]) -> list[str]:
        current = self._sources_path.read_text() if self._sources_path.exists() else ""
        titles_text = "\n".join(f"- {t}" for t in recent_titles) or "(none yet)"
        prompt = SUGGEST_PROMPT.format(current_sources=current or "(none)", recent_titles=titles_text)
        text = self._client.complete(prompt, max_tokens=512)
        if "no new sources" in text.lower():
            return []
        suggestions = []
        for line in text.splitlines():
            line = line.strip().lstrip("-•* ")
            if line and ("r/" in line or "http" in line or "|" in line):
                suggestions.append(line)
        return suggestions
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run python -m pytest tests/test_source_discovery.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/tools/source_discovery.py tests/test_source_discovery.py
git commit -m "refactor(source-discovery): route LLM calls through the llm.py abstraction"
```

---

### Task 6: Migrate `agent/tools/search_query_generator.py` (and generalize the key guard)

**Files:**
- Modify: `agent/tools/search_query_generator.py` (drop `import anthropic`, drop `MODEL` line 5; `__init__`; `queries` guard; `_dynamic_queries`)
- Test: `tests/test_search_query_generator.py`

**Interfaces:**
- Produces: `SearchQueryGenerator.__init__(self, cfg, api_key=None, *, client=None)`. The client is built lazily from the merged config so the "provider key present" guard can be evaluated. The guard in `queries()` generalizes from `self._api_key` to "the configured provider's key is present" — computed via `agent.llm` env-key lookup for the configured provider.

> **Design.** `cfg` here is the `{"search": {...}}` shape (built by `scheduler.search_sweep`). To evaluate the provider-key guard and to build a client, the generator also needs the `llm:` config. Thread it: `SearchQueryGenerator.__init__(self, cfg, api_key=None, *, client=None, llm_cfg=None)`. The guard becomes: dynamic queries run only when `dynamic_enabled` AND the configured provider's key is present in the environment. Add a small helper in `agent/llm.py` — `def provider_key_present(cfg: dict) -> bool` — that returns whether `os.getenv(_ENV_KEYS[provider])` is truthy for the configured provider (default anthropic). Add a unit test for it in `tests/test_llm.py`.

- [ ] **Step 1: Add `provider_key_present` test + `search_query_generator` tests (failing)**

In `tests/test_llm.py`:
```python
def test_provider_key_present(monkeypatch):
    from agent.llm import provider_key_present
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert provider_key_present({"llm": {"provider": "openrouter"}}) is False
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    assert provider_key_present({"llm": {"provider": "openrouter"}}) is True
```

In `tests/test_search_query_generator.py`, replace the `mocker.patch("...anthropic.Anthropic")` pattern with injecting a fake client and setting the provider key. Example:
```python
class FakeLLM:
    def __init__(self, text=""):
        self.text = text
    def complete(self, prompt, max_tokens):
        return self.text

def test_dynamic_queries_merged(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    fake = FakeLLM("agentic eval harnesses\nlong context retrieval\n")
    gen = SearchQueryGenerator(
        cfg={"search": {"fixed_queries": ["a"], "dynamic_queries_enabled": True}},
        client=fake,
    )
    out = gen.queries(recent_titles=["X"])
    assert "agentic eval harnesses" in out
```
Preserve the existing tests covering: fixed-only when dynamic disabled, dedupe, max_queries cap, and the guard when no provider key is present (dynamic skipped → fixed only).

- [ ] **Step 2: Run to verify fail**

Run: `uv run python -m pytest tests/test_search_query_generator.py tests/test_llm.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

In `agent/llm.py` add:
```python
def provider_key_present(cfg: dict) -> bool:
    llm_cfg = (cfg or {}).get("llm", {}) or {}
    provider = llm_cfg.get("provider", "anthropic")
    if provider not in _ENV_KEYS:
        return False
    return bool(os.getenv(_ENV_KEYS[provider]))
```

In `agent/tools/search_query_generator.py`: remove `import anthropic` and `MODEL`. Add `from agent.llm import get_client, provider_key_present, LLMClient`.
```python
class SearchQueryGenerator:
    def __init__(self, cfg: dict, api_key: str | None = None, *,
                 client: LLMClient | None = None, llm_cfg: dict | None = None):
        self._cfg = cfg or {}
        self._llm_cfg = {"llm": llm_cfg or {}}
        self._client = client

    def queries(self, recent_titles: list[str]) -> list[str]:
        search = self._cfg.get("search", {})
        fixed = list(search.get("fixed_queries", []))
        dynamic_enabled = search.get("dynamic_queries_enabled", True)
        max_queries = search.get("max_queries", 10)
        dynamic: list[str] = []
        if dynamic_enabled and (self._client is not None or provider_key_present(self._llm_cfg)):
            dynamic = self._dynamic_queries(recent_titles)
        # ... existing merge/dedupe/cap unchanged ...

    def _dynamic_queries(self, recent_titles: list[str]) -> list[str]:
        try:
            titles_text = "\n".join(f"- {t}" for t in recent_titles) or "(none yet)"
            prompt = DYNAMIC_PROMPT.format(recent_titles=titles_text)
            client = self._client if self._client is not None else get_client(self._llm_cfg)
            text = client.complete(prompt, max_tokens=256)
            queries = []
            for line in text.splitlines():
                line = line.strip().lstrip("-•* ").strip()
                if line:
                    queries.append(line)
            return queries
        except Exception:  # noqa: BLE001 — dynamic step is non-fatal
            logger.warning("dynamic query generation failed; using fixed anchors only", exc_info=True)
            return []
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run python -m pytest tests/test_search_query_generator.py tests/test_llm.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/tools/search_query_generator.py tests/test_search_query_generator.py tests/test_llm.py
git commit -m "refactor(search-query-generator): route LLM calls through llm.py; generalize key guard"
```

---

### Task 7: Wire `llm:` config through cli.py + scheduler + config.yml + .env.example

**Files:**
- Modify: `cli.py` (`load_config` already exists; `cmd_sweep`, `cmd_regenerate`, `cmd_reclassify`, `cmd_start`)
- Modify: `agent/scheduler.py` (`run_sweep`, `search_sweep`, `start_scheduler`, `_write_kept`)
- Modify: `agent/regenerator.py` (`Regenerator.__init__`), `agent/reclassifier.py` (`Reclassifier.__init__`)
- Modify: `config.yml` (add `llm:` section), `.env.example` (add `OPENROUTER_API_KEY`)
- Test: `tests/test_scheduler.py`, `tests/test_search_sweep.py`, `tests/test_cli.py` (verify green; extend if needed)

**Interfaces:**
- Consumes: `agent.llm.get_client`.
- Produces: an `llm_cfg` dict (`cfg.get("llm", {})`) threaded from `cli.py` into `scheduler.run_sweep`/`search_sweep`/`start_scheduler`, `Regenerator`, and `Reclassifier`, which pass `llm_cfg=` into `Evaluator`, `NoteSynthesizer`, `SearchQueryGenerator`. The `api_key` params remain for backward-compat but the model+provider now come from `llm_cfg`.

> **Threading rule.** Add an `llm_cfg: dict | None = None` kwarg to `run_sweep`, `search_sweep`, `start_scheduler`, `_write_kept`, `Regenerator.__init__`, `Reclassifier.__init__`. In each, pass `llm_cfg=llm_cfg` into the `Evaluator(...)`, `NoteSynthesizer(...)`, and `SearchQueryGenerator(...)` constructors alongside the existing `api_key=api_key`. In `cli.py`, compute `llm_cfg = cfg.get("llm", {})` in each of the four commands and pass it through. Absent `llm:` ⇒ `{}` ⇒ anthropic default — byte-identical to today. Keep `os.getenv("ANTHROPIC_API_KEY")` as-is for backward-compat, but note the factory resolves the provider key itself, so an openrouter run needs no ANTHROPIC key.

- [ ] **Step 1: Add/adjust tests (failing where new behavior is asserted)**

In `tests/test_scheduler.py` / `tests/test_search_sweep.py`, confirm the existing patches still hold (they patch `Evaluator.score` / construct with fakes). Add one test asserting that when `config.yml`/passed cfg selects `provider: openrouter`, `scheduler.run_sweep` constructs an `OpenRouterClient`-backed evaluator — e.g. spy on `agent.llm.get_client` and assert it was called with the openrouter cfg. In `tests/test_cli.py`, add a test that `load_config()` surfaces an `llm:` section and that `cmd_sweep` threads `llm_cfg` into `scheduler.run_sweep` (patch `scheduler.run_sweep` and assert the kwarg).

- [ ] **Step 2: Run to verify the new tests fail**

Run: `uv run python -m pytest tests/test_scheduler.py tests/test_search_sweep.py tests/test_cli.py -v`
Expected: the newly-added assertions FAIL (kwarg not threaded yet).

- [ ] **Step 3: Implement the wiring**

- `agent/scheduler.py`: add `llm_cfg: dict | None = None` to `run_sweep`, `search_sweep`, `start_scheduler`, and `_write_kept`. Pass `llm_cfg=llm_cfg` to `Evaluator(api_key=api_key, llm_cfg=llm_cfg)`, `NoteSynthesizer(api_key=api_key, llm_cfg=llm_cfg)` (inside `_write_kept`), and `SearchQueryGenerator(cfg={"search": search_cfg}, api_key=api_key, llm_cfg=llm_cfg)`. In `start_scheduler`, add `llm_cfg` into each job's `kwargs`.
- `agent/regenerator.py`: add `llm_cfg: dict | None = None` to `Regenerator.__init__`; pass `llm_cfg=llm_cfg` to `NoteSynthesizer(...)`.
- `agent/reclassifier.py`: add `llm_cfg: dict | None = None` to `Reclassifier.__init__`; pass `llm_cfg=llm_cfg` to `Evaluator(...)`.
- `cli.py`: in `cmd_sweep`, `cmd_regenerate`, `cmd_reclassify`, `cmd_start`, compute `llm_cfg = cfg.get("llm", {})` and pass it into the respective calls (`scheduler.run_sweep(..., llm_cfg=llm_cfg)`, `scheduler.search_sweep(..., llm_cfg=llm_cfg)`, `Regenerator(..., llm_cfg=llm_cfg)`, `Reclassifier(..., llm_cfg=llm_cfg)`, `start_scheduler(..., llm_cfg=llm_cfg)`).

- `config.yml`: add near the top:
```yaml
llm:
  provider: anthropic        # anthropic (default) | openrouter
  model:                     # optional; per-provider default when unset
```
- `.env.example`: add a line:
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

- [ ] **Step 4: Run the affected tests, then the FULL suite**

Run: `uv run python -m pytest tests/test_scheduler.py tests/test_search_sweep.py tests/test_cli.py tests/test_regenerator.py tests/test_reclassifier.py -v`
Then: `uv run python -m pytest -q`
Expected: PASS (whole suite green).

- [ ] **Step 5: Commit**

```bash
git add cli.py agent/scheduler.py agent/regenerator.py agent/reclassifier.py config.yml .env.example tests/
git commit -m "feat(llm): thread llm config from cli through scheduler/regenerator/reclassifier"
```

---

### Task 8: Full-suite gate + static sanity

**Files:** none (verification).

- [ ] **Step 1: Run the full suite**

Run: `uv run python -m pytest -q`
Expected: ALL tests PASS. No remaining references to a removed `MODEL` constant or `import anthropic` outside `agent/llm.py`.

- [ ] **Step 2: Grep for leftover direct provider coupling**

Run: `grep -rn "anthropic.Anthropic\|from agent.evaluator import MODEL\|^MODEL = " agent/ | grep -v "agent/llm.py"`
Expected: NO matches (all direct Anthropic construction and MODEL constants are gone except inside `agent/llm.py`).

- [ ] **Step 3: Commit only if any fixups were needed**

```bash
git add -A
git commit -m "chore(llm): remove residual direct-provider coupling" || echo "nothing to commit"
```

---

### Task 9: LIVE end-to-end verification on OpenRouter (REQUIRED — run for real, record results)

**Files:**
- Create (results file, committed on the feature branch): `docs/results/2026-08-07-openrouter-provider-support-results.md`
- May temporarily create a local `config.yml` override or a throwaway config for the run — do NOT commit a config that flips the default provider to openrouter (the committed default stays `anthropic`).

**Interfaces:** none (integration verification against the real OpenRouter API).

> **Secret hygiene:** `OPENROUTER_API_KEY` is already in `.env` (loaded by `python-dotenv` via `cli.py`'s `load_dotenv()`). NEVER echo, print, or commit it. Do NOT export it inline in a way that lands in shell history output.

- [ ] **Step 1: Confirm the key loads and is not printed**

Run: `uv run python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OPENROUTER key present:', bool(os.getenv('OPENROUTER_API_KEY')))"`
Expected: `OPENROUTER key present: True`. (Prints only the boolean, never the key.)

- [ ] **Step 2: Select openrouter for the run WITHOUT changing the committed default**

Point the run at an openrouter provider via a local, uncommitted config. Two acceptable ways:
- Temporarily edit `config.yml` to `llm.provider: openrouter` for the run, then `git checkout config.yml` afterward so the committed default stays anthropic; OR
- Use a throwaway config file and confirm `cli.py` reads `config.yml` from the repo root (it does), so the temporary edit is the simplest path.

Make the edit:
```yaml
llm:
  provider: openrouter
  model:                 # uses the anthropic/claude-haiku-4.5 default via OpenRouter
```

- [ ] **Step 3: Run a full sweep end to end on OpenRouter**

Run (Anthropic key not required for this run):
`uv run python cli.py sweep --lookback-days 3`
Expected: the command completes and prints `Sweep complete. <N> new strategies documented.` Capture stdout (counts, any `[warn]` lines). The sweep exercises: fetch → topic filter → cross-validate → **Evaluator (classify/score/validate)** → **NoteSynthesizer** for above-threshold kept items. The search path additionally exercises **SearchQueryGenerator dynamic queries** — if search backends are unconfigured, run the search path check in Step 4 instead.

- [ ] **Step 4: Verify each LLM path actually ran via OpenRouter**

- Evaluation: kept items have a `content_type`, a numeric `score`, `score_label`, and `tags` — inspect a couple of the newly written vault notes' frontmatter.
- Synthesis: above-threshold notes have populated `## Summary` / `## How It Works` / `## Why It Matters` sections (not the template fallback).
- Dynamic queries (optional if search unconfigured): run a tiny direct check that does NOT need Anthropic:
  `uv run python -c "from dotenv import load_dotenv; load_dotenv(); from agent.tools.search_query_generator import SearchQueryGenerator as G; g=G(cfg={'search':{'fixed_queries':['x'],'dynamic_queries_enabled':True}}, llm_cfg={'provider':'openrouter'}); print(g.queries(['Flash Attention 3','Chain of Draft']))"`
  Expected: a list including >1 dynamically generated query (proves an OpenRouter call succeeded). Do not print keys.
- Confirm NO Anthropic key was needed: optionally `unset ANTHROPIC_API_KEY` for the run (or confirm it is empty/no-credit) and see the sweep still succeed.

- [ ] **Step 5: Inspect written notes for sane content**

Run: `ls -t vault/strategies/**/*.md | head` and open 1-2 newly written notes; confirm sane content types, scores in 1-10, and tags. Note any anomalies.

- [ ] **Step 6: Record the run outcome in the results file**

Author `docs/results/2026-08-07-openrouter-provider-support-results.md` from the results template with: the exact command(s) run, the provider/model used (`openrouter` / `anthropic/claude-haiku-4.5`), the sweep counts, evidence that classify/score/validate + synthesis (+ dynamic queries) completed via OpenRouter, a couple of sample note excerpts (content_type/score/tags), any provider errors or `[warn]` lines, and an explicit note that the run required NO Anthropic credit. Do NOT include the key.

- [ ] **Step 7: Restore the committed config default and stamp the results back-link**

Run: `git checkout config.yml` (revert the temporary openrouter flip; committed default stays `anthropic`).
Then stamp the results back-link (done by the driver, not this task) and commit the results file:
```bash
git add docs/results/2026-08-07-openrouter-provider-support-results.md
git commit -m "docs(results): live OpenRouter end-to-end sweep verification"
```

- [ ] **Step 8: Final full-suite gate**

Run: `uv run python -m pytest -q`
Expected: PASS (confirm the temporary config edit was reverted and nothing regressed).

---

## Out of scope (explicit non-goals)

- Streaming, tool use, or multi-turn conversations — every call site is single-shot prompt → text.
- Per-call-site model overrides — one global `llm.model` knob only.
- Cross-provider retry/fallback (e.g. OpenRouter down → Anthropic) — existing per-site fail-soft is preserved as-is.
- Adopting the `openai` SDK or `litellm` — `httpx` keeps the dependency surface unchanged.

## Self-Review notes

- **Spec coverage:** `agent/llm.py` + factory (Task 2); all four call sites migrated (Tasks 3-6, matching the spec's four); `llm:` config + `.env.example` + backward compat (Task 7); mocked unit tests for factory + both backends + call sites (Tasks 2-7); live e2e on OpenRouter recorded in results (Task 9). Every spec section maps to a task.
- **Type consistency:** `get_client(cfg) -> LLMClient`, `complete(prompt, max_tokens) -> str`, and `provider_key_present(cfg) -> bool` are used identically across tasks. Call-site constructors uniformly gain `*, client=None, llm_cfg=None`.
- **PR #7 reconcile:** change 0006's `_tag_batch` (unmerged) routes through the same `Evaluator._call` this plan abstracts, so its rebase picks up the abstraction automatically — no coordination task needed here.
