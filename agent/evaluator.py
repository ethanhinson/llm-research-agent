import re

import anthropic

from agent.models import RawItem

MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 20

CONTENT_TYPES = {"research", "release", "news", "benchmark", "tutorial"}

SCORE_LABELS = {
    "research": "novelty",
    "release": "significance",
    "news": "timeliness",
    "benchmark": "authority",
    "tutorial": "practicality",
}

RESEARCH_SUBCATEGORIES = {"prompting", "architecture", "agentic", "tooling", "use-case"}

CLASSIFY_PROMPT = """\
You are classifying LLM/AI content items by type.

For each item, output exactly one line:
<n>. <type>

Types:
- research    — novel techniques, papers, arXiv findings, new approaches
- release     — product/model/SDK/framework/tool launches or major updates
- news        — company news, funding, industry trends, adoption stories
- benchmark   — eval results, leaderboards, model comparisons, capability assessments
- tutorial    — how-tos, implementation guides, cookbooks, practical walkthroughs

Items:
{items}"""

SCORE_PROMPT = """\
You are scoring LLM/AI content items. Each item has been pre-classified by type.

Output format — exactly one line per item:
- research items:  <n>. <score> <subcategory>     (subcategory is REQUIRED, not optional)
- all other items: <n>. <score>

Scoring axis per type:
- research:   novelty 1-10  (10=breakthrough new technique, 5=incremental, 1=already well-known)
  subcategory must be one of: prompting | architecture | agentic | tooling | use-case
- release:    significance 1-10  (10=landmark release that changes the field, 1=minor patch)
- news:       timeliness 1-10  (10=major consequential development right now, 1=stale/trivial)
- benchmark:  authority 1-10  (10=rigorous methodology + credible source, 1=cherry-picked/unclear)
- tutorial:   practicality 1-10  (10=immediately actionable with working code/steps, 1=too abstract)

Example output for a mixed batch:
1. 8 architecture
2. 7
3. 4
4. 9 prompting
5. 6

Items (with pre-classified types):
{items}"""

TAG_PROMPT = """\
You are tagging LLM/AI content items with topic tags for an Obsidian research vault.

For each item, output exactly one line:
<n>. tag1 tag2 tag3

Rules:
- 2 to 4 tags per item
- Lowercase, hyphenated (rag, chain-of-thought, fine-tuning)
- Tags describe the topic, NOT the content type (no "research", "news", "release")
- Be specific: prefer "speculative-decoding" over "inference", "rlhf" over "training"
- Non-redundant: don't emit both "reasoning" and "chain-of-thought" for the same item

Common topics (not exhaustive — coin new ones when needed):
rag fine-tuning inference-efficiency chain-of-thought reasoning multimodal
safety-alignment tool-use agent-frameworks context-window embeddings
instruction-following code-generation vision long-context speculative-decoding
memory rlhf synthetic-data evaluation

Items:
{items}"""

VALIDATE_PROMPT = """\
You are reviewing LLM/AI content items for inclusion in a research vault.
Each item has been classified by type and scored on a type-appropriate axis.

For each item, output exactly one line:
<n>. keep|skip

Keep an item if it is genuinely worth a researcher reading and saving.
Skip an item if it is noise, too low-signal, or not relevant to LLM/AI work regardless of type.
Be selective but not overly conservative — a score of 6+ generally warrants keeping.

Items (with type and score):
{items}"""


class Evaluator:
    def __init__(self, api_key: str | None = None):
        self._client = anthropic.Anthropic(api_key=api_key)

    def score(self, items: list[RawItem]) -> list[RawItem]:
        if not items:
            return []
        for batch_start in range(0, len(items), BATCH_SIZE):
            batch = items[batch_start: batch_start + BATCH_SIZE]
            self._classify_batch(batch)
            self._score_batch(batch)
            self._validate_batch(batch)
            self._set_tags(batch)    # structural tags first
            self._tag_batch(batch)   # topic tags appended
        return items

    def _set_tags(self, batch: list[RawItem]):
        for item in batch:
            tags = [item.content_type]
            if item.content_type == "research" and item.category:
                tags.append(item.category)
            item.tags = tags

    def _tag_batch(self, batch: list[RawItem]):
        item_lines = "\n".join(
            f"{i+1}. [{item.content_type}] {item.title} — {item.body[:150]}"
            for i, item in enumerate(batch)
        )
        text = self._call(TAG_PROMPT.format(items=item_lines))
        pattern = re.compile(r"^\s*(\d+)\.\s+(.+)$", re.MULTILINE)
        for match in pattern.finditer(text):
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(batch):
                raw_tags = match.group(2).strip()
                # Split on commas first so a comma-delimited multi-word tag
                # ("Fine Tuning") hyphenates rather than fragmenting; when no
                # commas are present, fall back to whitespace-delimited tokens.
                if "," in raw_tags:
                    parts = [p for p in raw_tags.split(",")]
                else:
                    parts = re.split(r"\s+", raw_tags)
                topic_tags = [
                    p.strip().lower().replace(" ", "-")
                    for p in parts
                    if p.strip()
                ]
                batch[idx].tags = batch[idx].tags + topic_tags[:4]

    def _call(self, prompt: str) -> str:
        message = self._client.messages.create(
            model=MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        if not message.content or not hasattr(message.content[0], "text"):
            return ""
        return message.content[0].text

    def _classify_batch(self, batch: list[RawItem]):
        item_lines = "\n".join(
            f"{i+1}. {item.title} — {item.body[:200]}" for i, item in enumerate(batch)
        )
        text = self._call(CLASSIFY_PROMPT.format(items=item_lines))
        pattern = re.compile(
            r"^\s*(\d+)\.\s+(research|release|news|benchmark|tutorial)",
            re.MULTILINE | re.IGNORECASE,
        )
        parsed: dict[int, str] = {}
        for match in pattern.finditer(text):
            idx = int(match.group(1)) - 1
            parsed[idx] = match.group(2).lower()
        for i, item in enumerate(batch):
            if i in parsed:
                item.content_type = parsed[i]
                item.score_label = SCORE_LABELS[item.content_type]

    def _score_batch(self, batch: list[RawItem]):
        item_lines = "\n".join(
            f"{i+1}. [{item.content_type}] {item.title} — {item.body[:150]}"
            for i, item in enumerate(batch)
        )
        text = self._call(SCORE_PROMPT.format(items=item_lines))
        pattern = re.compile(
            r"^\s*(\d+)\.\s+(\d+)\s*(prompting|architecture|agentic|tooling|use-case)?",
            re.MULTILINE | re.IGNORECASE,
        )
        parsed: dict[int, tuple[int, str]] = {}
        for match in pattern.finditer(text):
            idx = int(match.group(1)) - 1
            score = max(1, min(10, int(match.group(2))))
            subcategory = (match.group(3) or "").lower()
            parsed[idx] = (score, subcategory)
        for i, item in enumerate(batch):
            if i in parsed:
                item.score, subcategory = parsed[i]
                if item.content_type == "research" and subcategory:
                    item.category = subcategory
            else:
                item.score = 5

    def _validate_batch(self, batch: list[RawItem]):
        item_lines = "\n".join(
            f"{i+1}. [{item.content_type}, {item.score_label}={item.score}] {item.title}"
            for i, item in enumerate(batch)
        )
        text = self._call(VALIDATE_PROMPT.format(items=item_lines))
        pattern = re.compile(
            r"^\s*(\d+)\.\s+(keep|skip)",
            re.MULTILINE | re.IGNORECASE,
        )
        parsed: dict[int, bool] = {}
        for match in pattern.finditer(text):
            idx = int(match.group(1)) - 1
            parsed[idx] = match.group(2).lower() == "keep"
        for i, item in enumerate(batch):
            item.keep = parsed.get(i, False)
