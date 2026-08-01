import re
from agent.models import RawItem

_KEYWORDS = re.compile(
    r"\b("
    r"llm|language model|large model|foundation model|"
    r"transformer|attention mechanism|self.attention|"
    r"embedding|vector|tokeni[sz]|"
    r"neural net|deep learning|machine learning|"
    r"fine.?tun|rlhf|rl\b|reinforcement|reward model|"
    r"prompt|chain.of.thought|few.shot|zero.shot|in.context|"
    r"inference|latency|throughput|quantiz|"
    r"diffusion|generative|multimodal|vision.language|"
    r"gpt|claude|gemini|mistral|llama|deepseek|qwen|kimi|"
    r"anthropic|openai|google deepmind|hugging.?face|"
    r"agent|agentic|tool.use|function.call|rag|retrieval|"
    r"benchmark|eval|evals|alignment|safety|"
    r"moe|mixture.of.experts|speculative.decod|"
    r"lora|qlora|peft|adapter|"
    r"context.window|context.length|long.context|"
    r"hallucin|grounding|reasoning|"
    r"open.?source.model|weights|checkpoint|"
    r"ai\b|a\.i\."
    r")",
    re.IGNORECASE,
)

# Sources that are already topic-filtered at the API level
_TRUSTED_SOURCES = {"arxiv"}


def is_relevant(item: RawItem) -> bool:
    if item.source in _TRUSTED_SOURCES:
        return True
    text = f"{item.title} {item.body[:500]}"
    return bool(_KEYWORDS.search(text))
