import re

import anthropic

from agent.models import RawItem

MODEL = "claude-haiku-4-5-20251001"

SCORE_PROMPT_TEMPLATE = """\
You are evaluating LLM research items for novelty. For each item below, rate it 1-10:
- 10 = genuinely new breakthrough technique not widely known
- 5 = incremental improvement or moderate novelty
- 1 = well-known, widely discussed, no novelty

Output ONLY in this format (one line per item, no other text):
<n>. <title>: <score>

Items to score:
{items}"""


class Evaluator:
    def __init__(self, api_key: str | None = None):
        self._client = anthropic.Anthropic(api_key=api_key)

    def score(self, items: list[RawItem]) -> list[RawItem]:
        if not items:
            return []

        item_lines = "\n".join(
            f"{i+1}. {item.title} — {item.body[:200]}" for i, item in enumerate(items)
        )
        prompt = SCORE_PROMPT_TEMPLATE.format(items=item_lines)

        message = self._client.messages.create(
            model=MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        if not message.content or not hasattr(message.content[0], "text"):
            return self._parse_scores(items, "")
        response_text = message.content[0].text
        return self._parse_scores(items, response_text)

    def _parse_scores(self, items: list[RawItem], text: str) -> list[RawItem]:
        pattern = re.compile(r"^\s*(\d+)\.\s+.+?:\s*(\d+)", re.MULTILINE)
        scores: dict[int, int] = {}
        for match in pattern.finditer(text):
            idx = int(match.group(1)) - 1
            score = int(match.group(2))
            scores[idx] = max(1, min(10, score))

        for i, item in enumerate(items):
            item.novelty = scores.get(i, 5)

        return items
