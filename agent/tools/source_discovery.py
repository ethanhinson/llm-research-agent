import datetime
import re
from pathlib import Path

from agent.llm import get_client, LLMClient

SUGGESTED_HEADING = "## Suggested (pending review)"

_URL_RE = re.compile(r"https?://[^\s|)>\]]+")


def _urls_in(text: str) -> set[str]:
    return {u.rstrip("/.,") for u in _URL_RE.findall(text)}


def append_suggestions(
    sources_path: Path,
    suggestions: list[str],
    *,
    date: str | None = None,
) -> int:
    """Append genuinely-new suggestions to ``sources.md`` under a dated
    ``## Suggested (pending review)`` section, deduped against everything
    already in the file (existing feeds AND prior suggestions).

    Returns the number of suggestions actually appended. The LLM never edits
    config — a human promotes reviewed suggestions into ``config.yml``.
    Idempotent: re-running with the same suggestions appends nothing.
    """
    if not suggestions:
        return 0

    sources_path = Path(sources_path)
    existing = sources_path.read_text() if sources_path.exists() else ""
    existing_urls = _urls_in(existing)
    # Whole-line dedup for non-URL suggestions: compare against the set of
    # existing stripped lines (list-item bullets normalized), NOT a substring
    # scan of the whole file — a substring test would over-drop a short
    # suggestion that merely appears inside a longer existing line.
    existing_lines = {
        ln.strip().lstrip("-•* ").strip().lower()
        for ln in existing.splitlines()
        if ln.strip()
    }

    date = date or datetime.date.today().isoformat()

    fresh: list[str] = []
    seen_this_call_urls: set[str] = set()
    seen_this_call_text: set[str] = set()
    for raw in suggestions:
        line = raw.strip().lstrip("-•* ").strip()
        if not line:
            continue
        urls = _urls_in(line)
        # Dedup by URL when present, else by the normalized whole-line text.
        if urls:
            if urls & existing_urls or urls & seen_this_call_urls:
                continue
            seen_this_call_urls |= urls
        else:
            key = line.lower()
            if key in existing_lines or key in seen_this_call_text:
                continue
            seen_this_call_text.add(key)
        fresh.append(line)

    if not fresh:
        return 0

    text = existing
    if text and not text.endswith("\n"):
        text += "\n"
    if SUGGESTED_HEADING in text:
        # Section already exists — append a fresh dated subsection under it.
        block = [f"\n### {date}\n"] + [f"- {s}\n" for s in fresh]
    else:
        block = [f"\n{SUGGESTED_HEADING}\n", f"### {date}\n"]
        block += [f"- {s}\n" for s in fresh]
    text += "".join(block)
    sources_path.write_text(text)
    return len(fresh)

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
