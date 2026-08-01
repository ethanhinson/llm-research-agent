import re

import anthropic

from agent.models import RawItem

MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 20

SCORE_PROMPT_TEMPLATE = """\
You are evaluating LLM/AI research items for novelty and relevance.

For each item, output exactly one line:
<n>. <score> <category>

Where:
- score = 1-10 novelty (10=breakthrough new technique, 5=incremental, 1=well-known or off-topic)
- category = one of: prompting | architecture | agentic | tooling | use-case
- Score off-topic items (news, politics, products unrelated to LLM strategies) as 1

Items:
{items}"""


class Evaluator:
    def __init__(self, api_key: str | None = None):
        self._client = anthropic.Anthropic(api_key=api_key)

    def score(self, items: list[RawItem]) -> list[RawItem]:
        if not items:
            return []
        for batch_start in range(0, len(items), BATCH_SIZE):
            batch = items[batch_start: batch_start + BATCH_SIZE]
            self._score_batch(batch, offset=batch_start)
        return items

    def _score_batch(self, batch: list[RawItem], offset: int):
        item_lines = "\n".join(
            f"{i+1}. {item.title} — {item.body[:200]}" for i, item in enumerate(batch)
        )
        prompt = SCORE_PROMPT_TEMPLATE.format(items=item_lines)

        message = self._client.messages.create(
            model=MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        if not message.content or not hasattr(message.content[0], "text"):
            return
        self._parse_batch(batch, message.content[0].text)

    def _parse_batch(self, batch: list[RawItem], text: str):
        # Match lines like: "1. 7 architecture" or "1. 7"
        pattern = re.compile(
            r"^\s*(\d+)\.\s+(\d+)\s*(prompting|architecture|agentic|tooling|use-case)?",
            re.MULTILINE | re.IGNORECASE,
        )
        parsed: dict[int, tuple[int, str]] = {}
        for match in pattern.finditer(text):
            idx = int(match.group(1)) - 1
            score = max(1, min(10, int(match.group(2))))
            category = (match.group(3) or "architecture").lower()
            parsed[idx] = (score, category)

        for i, item in enumerate(batch):
            if i in parsed:
                item.novelty, item.category = parsed[i]
            else:
                item.novelty = 5
