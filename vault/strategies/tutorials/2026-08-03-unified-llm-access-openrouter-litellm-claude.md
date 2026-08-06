---
date: 2026-08-03
score: 9
score_label: practicality
sources_count: 5
status: new
tags:
- tutorial
title: "Unified LLM API Access: OpenRouter + LiteLLM for DeepSeek, GLM, Kimi, Qwen, and Claude"
type: tutorial
validated: true
---

# Unified LLM API Access: OpenRouter + LiteLLM for DeepSeek, GLM, Kimi, Qwen, and Claude

## Summary
All four open-weight frontier models (DeepSeek V4, GLM 5.2, Kimi K3, Qwen3-8B) are accessible alongside Claude via two strategies: OpenRouter (one key, one base URL, zero infra) or a self-hosted LiteLLM proxy (YAML config, load balancing, custom aliases). OpenRouter is the fastest path to get running; LiteLLM is better for production routing control.

## How It Works

### Strategy A: OpenRouter (Recommended for simplicity)

Single base URL, single API key. All models use the OpenAI SDK with only the model ID changing.

**Environment variable:**
```bash
export OPENROUTER_API_KEY="sk-or-..."
```

**Model slugs on OpenRouter:**
| Model | OpenRouter ID | Input $/1M | Output $/1M |
|---|---|---|---|
| DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` | $0.435 | $0.87 |
| DeepSeek V4 Flash | `deepseek/deepseek-v4-flash-0731` | ~$0.14* | — |
| GLM 5.2 (Z.ai) | `z-ai/glm-5.2` | verify† | verify† |
| Qwen3-8B | `qwen/qwen3-8b` | $0.117 | $0.455 |
| Kimi K3 | check openrouter.ai‡ | — | — |

*Flash pricing via Artificial Analysis. †GLM 5.2 pricing not verified — check openrouter.ai/z-ai/glm-5.2. ‡Kimi K3 OpenRouter availability unconfirmed; use native Moonshot API as fallback.

**Python usage (OpenAI SDK):**
```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)

# Swap model string — everything else stays the same
response = client.chat.completions.create(
    model="deepseek/deepseek-v4-pro",   # or any slug above
    messages=[{"role": "user", "content": "Hello"}],
)
```

**Claude via Anthropic SDK (separate key):**
```python
import anthropic
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
```

---

### Strategy B: LiteLLM Proxy (Recommended for production routing)

Self-hosted proxy with a YAML config. Expose one local endpoint and route by custom model name to any provider.

**Install:**
```bash
pip install litellm[proxy]
```

**`litellm_config.yaml`:**
```yaml
model_list:
  - model_name: deepseek-v4-flash
    litellm_params:
      model: deepseek/deepseek-v4-flash
      api_key: os.environ/DEEPSEEK_API_KEY
      api_base: https://api.deepseek.com

  - model_name: deepseek-v4-pro
    litellm_params:
      model: deepseek/deepseek-v4-pro
      api_key: os.environ/DEEPSEEK_API_KEY
      api_base: https://api.deepseek.com

  - model_name: glm-5.2
    litellm_params:
      model: openrouter/z-ai/glm-5.2
      api_key: os.environ/OPENROUTER_API_KEY

  - model_name: kimi-k3
    litellm_params:
      model: openai/kimi-k3
      api_base: https://api.moonshot.ai/v1
      api_key: os.environ/MOONSHOT_API_KEY

  - model_name: qwen3-8b
    litellm_params:
      model: openrouter/qwen/qwen3-8b
      api_key: os.environ/OPENROUTER_API_KEY

  - model_name: claude-sonnet-4-6
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      api_key: os.environ/ANTHROPIC_API_KEY
```

**Start proxy:**
```bash
litellm --config litellm_config.yaml --port 4000
```

**Call any model through one endpoint:**
```python
client = OpenAI(api_key="any-string", base_url="http://localhost:4000")
response = client.chat.completions.create(model="kimi-k3", messages=[...])
```

---

### Required environment variables

```bash
# Core
export ANTHROPIC_API_KEY="sk-ant-..."      # Claude models
export OPENROUTER_API_KEY="sk-or-..."      # OpenRouter (GLM, Qwen, DeepSeek via OR)

# Native APIs (optional, lower latency than OpenRouter)
export DEEPSEEK_API_KEY="..."              # platform.deepseek.com
export MOONSHOT_API_KEY="..."              # platform.kimi.ai  (Kimi K3)
export ZAI_API_KEY="..."                   # Z.ai (GLM 5.2 new SDK)
# export ZHIPUAI_API_KEY="..."            # Legacy ZhipuAI SDK — prefer ZAI_API_KEY
```

---

### Decision guide

| Criterion | OpenRouter | LiteLLM Proxy |
|---|---|---|
| Setup time | Minutes | ~30 min |
| Infra required | None | Local or cloud server |
| Load balancing | No | Yes |
| Custom aliases | No | Yes (YAML) |
| Cost visibility | Per-call | YAML + logs |
| Best for | Prototyping, low volume | Production, multi-model routing |

## Why It's Gaining Traction
Engagement: 5 sources. Cross-source validated: true. All four models expose OpenAI-compatible APIs, making unified access via base URL substitution the path of least resistance. LiteLLM's model_list YAML pattern decouples caller code from provider details entirely.

## Sources
- [OpenRouter API Docs](https://openrouter.ai/deepseek/deepseek-v4-pro) — openrouter · n/a
- [LiteLLM Proxy Config Docs](https://docs.litellm.ai/docs/proxy/configs) — docs · n/a
- [DeepSeek API Docs](https://api-docs.deepseek.com/) — official · n/a
- [Moonshot API Overview](https://platform.kimi.ai/docs/api/overview) — official · n/a
- [LiteLLM Moonshot Provider](https://docs.litellm.ai/docs/providers/moonshot) — docs · n/a

## Related
- [[strategies/tutorials/2026-08-03-deepseek-v4-flash-and-pro-api-integration|DeepSeek V4 Flash + Pro: API Integration]]
- [[strategies/tutorials/2026-08-03-kimi-k3-cloud-api-access-moonshot-openai-compatible|Kimi K3 Cloud API Access]]
- [[strategies/tutorials/2026-08-03-qwen3-8b-api-access-via-openrouter|Qwen3-8B API Access via OpenRouter]]
- [[strategies/releases/2026-08-03-glm-5-2-z-ai-rebranded-zhipuai-753b-moe|GLM 5.2 (Z.ai) release]]
- [[strategies/releases/2026-08-02-deepseek-aideepseek-v4-flash-0731|DeepSeek-V4-Flash-0731 (release)]]
- [[strategies/releases/2026-08-02-moonshotaikimi-k3|moonshotai/Kimi-K3 (release)]]
- [[strategies/releases/2026-08-03-qwen38-max-a-new-bar-for-coding-and-cowork|Qwen3.8-Max release]]
