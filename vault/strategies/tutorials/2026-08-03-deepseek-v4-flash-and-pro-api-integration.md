---
date: 2026-08-03
score: 9
score_label: practicality
sources_count: 4
status: new
tags:
- tutorial
title: "DeepSeek V4 Flash + Pro: API Integration and Model IDs"
type: tutorial
validated: true
---

# DeepSeek V4 Flash + Pro: API Integration and Model IDs

## Summary
DeepSeek V4 exposes two tiers via an OpenAI-compatible API: `deepseek-v4-flash` (304B params, July 31 2026 checkpoint, $0.14/1M input) and `deepseek-v4-pro` (1M-token context, $0.435/1M input on OpenRouter). Both share the same native base URL and Bearer token auth.

## How It Works

**Model IDs:**
- `deepseek-v4-flash` — points to the DeepSeek-V4-Flash-0731 checkpoint; ID is stable across checkpoint updates
- `deepseek-v4-pro` — released April 24, 2026; 1M-token context window

**Native API (OpenAI-compatible):**
```
Base URL:  https://api.deepseek.com
Path:      /chat/completions
Auth:      Authorization: Bearer $DEEPSEEK_API_KEY
Key from:  platform.deepseek.com
```

**Anthropic-format endpoint (alternative):**
```
Base URL:  https://api.deepseek.com/anthropic
```

**OpenAI SDK usage:**
```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)
response = client.chat.completions.create(
    model="deepseek-v4-flash",   # or "deepseek-v4-pro"
    messages=[{"role": "user", "content": "Hello"}],
)
```

**OpenRouter (if using unified key):**
- Flash: `deepseek/deepseek-v4-flash-0731` (verify slug at openrouter.ai)
- Pro: `deepseek/deepseek-v4-pro` — $0.435/1M input · $0.87/1M output

**Pricing (native, verified 2026-08-03):**
- V4 Flash: $0.14/1M input (per artificialanalysis.ai)
- V4 Pro on OpenRouter: $0.435 input / $0.87 output per 1M tokens

## Why It's Gaining Traction
Engagement: 4 sources. Cross-source validated: true. DeepSeek V4 Flash ranked ahead of MiniMax M3 (428B) on Artificial Analysis despite being 304B — strong price-to-performance ratio and agentic capability improvements make it a practical Claude alternative for high-volume workloads.

## Sources
- [DeepSeek API Docs](https://api-docs.deepseek.com/) — official · n/a
- [DeepSeek Pricing](https://api-docs.deepseek.com/quick_start/pricing/) — official · n/a
- [DeepSeek Anthropic API Guide](https://api-docs.deepseek.com/guides/anthropic_api/) — official · n/a
- [deepseek/deepseek-v4-pro on OpenRouter](https://openrouter.ai/deepseek/deepseek-v4-pro) — openrouter · n/a

## Related
- [[strategies/releases/2026-08-02-deepseek-aideepseek-v4-flash-0731|DeepSeek-V4-Flash-0731 (release)]]
- [[strategies/releases/2026-08-02-deepseek-v4-flash-update|DeepSeek V4 Flash update]]
- [[strategies/tutorials/2026-08-03-unified-llm-access-openrouter-litellm-claude|Unified LLM API Access: OpenRouter + LiteLLM]]
