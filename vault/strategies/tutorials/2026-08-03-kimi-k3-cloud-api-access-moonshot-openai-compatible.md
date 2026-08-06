---
date: 2026-08-03
score: 8
score_label: practicality
sources_count: 3
status: new
tags:
- tutorial
title: "Kimi K3 Cloud API Access: Moonshot AI OpenAI-Compatible Endpoint"
type: tutorial
validated: true
---

# Kimi K3 Cloud API Access: Moonshot AI OpenAI-Compatible Endpoint

## Summary
Kimi K3 (2.8T parameter model, released July 27 2026) is accessible via Moonshot AI's OpenAI-compatible API at `https://api.moonshot.ai/v1` using model ID `kimi-k3` and a Bearer token from `MOONSHOT_API_KEY`. No SDK changes needed beyond base URL and key swap.

## How It Works

**Model ID:** `kimi-k3`

**Endpoints:**
```
Global:  https://api.moonshot.ai/v1
China:   https://api.moonshot.cn/v1
Path:    /chat/completions
Auth:    Authorization: Bearer $MOONSHOT_API_KEY
Key:     platform.kimi.ai
```

**OpenAI SDK usage:**
```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["MOONSHOT_API_KEY"],
    base_url="https://api.moonshot.ai/v1",
)
response = client.chat.completions.create(
    model="kimi-k3",
    messages=[{"role": "user", "content": "Hello"}],
)
```

**LiteLLM config:**
```yaml
- model_name: kimi-k3
  litellm_params:
    model: openai/kimi-k3
    api_base: https://api.moonshot.ai/v1
    api_key: os.environ/MOONSHOT_API_KEY
```

LiteLLM also supports overriding the base URL via `MOONSHOT_API_BASE` env var.

**Note on OpenRouter:** OpenRouter availability of `kimi-k3` was not confirmed by adversarial verification — check openrouter.ai directly. The native Moonshot endpoint above is verified.

## Why It's Gaining Traction
Engagement: 3 sources. Cross-source validated: true. Kimi K3 weights released July 27 2026 (1.56TB on HuggingFace); the cloud API provides access without local infrastructure. Complements the local-run guide already in vault (`run-kimi-k3-using-29-gb-of-ram`).

## Sources
- [Kimi K3 Quickstart](https://platform.kimi.ai/docs/guide/kimi-k3-quickstart) — official · n/a
- [Moonshot API Overview](https://platform.kimi.ai/docs/api/overview) — official · n/a
- [LiteLLM Moonshot Provider](https://docs.litellm.ai/docs/providers/moonshot) — docs · n/a

## Related
- [[strategies/releases/2026-08-02-moonshotaikimi-k3|moonshotai/Kimi-K3 (weights release)]]
- [[strategies/releases/2026-08-02-kimi-k3-256k|Kimi K3 256k (release)]]
- [[strategies/tutorials/2026-08-02-run-kimi-k3-using-29-gb-of-ram-at-050-toks|Run Kimi K3 locally at 0.50 tok/s]]
- [[strategies/tutorials/2026-08-03-unified-llm-access-openrouter-litellm-claude|Unified LLM API Access: OpenRouter + LiteLLM]]
