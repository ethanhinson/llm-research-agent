---
date: 2026-08-03
score: 8
score_label: significance
sources_count: 2
status: new
tags:
- release
title: "GLM 5.2 (Z.ai): 753B MoE Model with 1M Context Window on OpenRouter"
type: release
validated: true
---

# GLM 5.2 (Z.ai): 753B MoE Model with 1M Context Window on OpenRouter

## Summary
Z.ai (the rebranded ZhipuAI) released GLM 5.2 on OpenRouter on June 16, 2026 — a 753B-parameter Mixture-of-Experts model with a 1M-token context window, accessible via OpenAI-compatible APIs under the model ID `z-ai/glm-5.2`.

## How It Works
GLM 5.2 is a 753B MoE model from Z.ai (formerly ZhipuAI, rebranded mid-2025). It is available on OpenRouter under the slug `z-ai/glm-5.2` with a 1M-token context window. The API is fully OpenAI-compatible — only a base URL swap is needed in existing SDK code.

**Authentication note:** The rebrand introduced a new environment variable. The legacy ZhipuAI Python SDK (`zhipuai-sdk-python-v4`) uses `ZHIPUAI_API_KEY` with base URL `https://open.bigmodel.cn/api/paas/v4/`. The new Z.ai SDK and LiteLLM's Z.AI provider use `ZAI_API_KEY` instead. Prefer the new key to avoid future deprecation.

**Pricing:** Not confirmed by adversarial verification as of 2026-08-03 — verify directly at openrouter.ai/z-ai/glm-5.2 before production use.

## Why It's Gaining Traction
Engagement: 2 sources. Cross-source validated: true. One of the largest openly accessible MoE models; the 1M context window and OpenRouter availability make it a practical drop-in for long-context tasks without running local infrastructure.

## Sources
- [z-ai/glm-5.2 on OpenRouter](https://openrouter.ai/z-ai/glm-5.2) — openrouter · n/a
- [zhipuai-sdk-python-v4](https://github.com/MetaGLM/zhipuai-sdk-python-v4) — github · n/a

## Related
- [[strategies/tutorials/2026-08-03-unified-llm-access-openrouter-litellm-claude|Unified LLM API Access: OpenRouter + LiteLLM]]
