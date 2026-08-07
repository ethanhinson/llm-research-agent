"""LLM note synthesis.

Calls the configured LLM provider to write the three body sections of a note —
Summary, How It Works, Why It Matters — grounded in the enriched body text.
Mirrors the evaluator's structured-plain-text + regex-tolerant parsing pattern.
Fail-soft: any API error or unparseable output returns {} so the writer falls
back to its template.

Prompt discipline (learnings/live-testing-catches-what-mocks-miss):
LLMs read [bracket] notation as "optional". The section labels below are
explicit and redundant, with a concrete example, so the model cannot treat a
required section as optional.
"""
import re

from agent.llm import get_client, LLMClient

MAX_TOKENS = 900

SYNTHESIS_PROMPT = """\
You are writing a concise research-vault note about an LLM/AI item, grounded \
strictly in the SOURCE TEXT provided. Do not invent facts. If the source text \
is thin, keep the sections brief rather than padding or speculating.

Write exactly three sections. Output them in this exact structured form, each \
header on its own line, followed by the section text:

SUMMARY:
<2-3 sentences: what this is and the key claim or result>

HOW IT WORKS:
<a short grounded explanation of the technique/release/finding — prose or a few \
bullets; state only what the source text supports>

WHY IT MATTERS:
<one short grounded paragraph on why a practitioner should care; fold in the \
engagement/validation signals as reasoning, do not print them as raw numbers>

All three headers (SUMMARY:, HOW IT WORKS:, WHY IT MATTERS:) are REQUIRED and \
must appear exactly as written. Example of the shape (content is illustrative):

SUMMARY:
FlashAttention is an IO-aware exact attention algorithm. It cuts memory reads \
and writes, giving large speedups without approximation.

HOW IT WORKS:
It tiles the attention computation to keep intermediate results in fast SRAM, \
avoiding repeated round-trips to slower HBM.

WHY IT MATTERS:
It became a default building block because it makes long-context training and \
inference practical on existing hardware.

ITEM METADATA:
- Title: {title}
- Type: {content_type}
- {score_label} score: {score}/10
- Cross-source validated: {validated}
- Engagement signals: {engagement}
- Distinct sources: {sources_count}

SOURCE TEXT:
{body}
"""

_SECTION_RE = re.compile(
    r"^\s*(SUMMARY|HOW IT WORKS|WHY IT MATTERS)\s*:\s*$",
    re.IGNORECASE,
)

_KEY_MAP = {
    "summary": "summary",
    "how it works": "how_it_works",
    "why it matters": "why_it_matters",
}


class NoteSynthesizer:
    def __init__(self, api_key: str | None = None, *, client: LLMClient | None = None,
                 llm_cfg: dict | None = None):
        self._client = client if client is not None else get_client({"llm": llm_cfg or {}})

    def _call(self, prompt: str) -> str:
        return self._client.complete(prompt, max_tokens=MAX_TOKENS)

    def synthesize(self, item) -> dict:
        prompt = SYNTHESIS_PROMPT.format(
            title=item.title,
            content_type=item.content_type,
            score_label=item.score_label,
            score=item.score,
            validated=item.validated,
            engagement=item.engagement,
            sources_count=item.sources_count,
            body=item.body,
        )
        try:
            text = self._call(prompt)
        except Exception as exc:  # fail-soft
            print(f"[warn] synthesis failed for {item.url}: {exc}")
            return {}

        return self._parse(text)

    def _parse(self, text: str) -> dict:
        if not text:
            return {}
        sections: dict[str, list[str]] = {}
        current: str | None = None
        for line in text.splitlines():
            m = _SECTION_RE.match(line)
            if m:
                current = _KEY_MAP[m.group(1).lower()]
                sections[current] = []
                continue
            if current is not None:
                sections[current].append(line)
        result = {k: "\n".join(v).strip() for k, v in sections.items()}
        # drop empties so the writer knows to fall back per-section
        return {k: v for k, v in result.items() if v}
