import re
from pathlib import Path

from agent.llm import get_client, LLMClient

SUGGEST_PROMPT = """\
You are a research assistant helping find new sources about LLM strategies and AI research.

Current sources already monitored:
{current_sources}

Recent strategies documented (for context):
{recent_titles}

Suggest up to 5 NEW sources not already in the list above. Focus on:
- Subreddits (format: r/SubredditName — brief description)
- Blogs/newsletters (format: URL | Name | type)

Only suggest sources with consistent, high-quality LLM/AI content.
If no good new sources come to mind, say "No new sources to suggest at this time."
"""


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
