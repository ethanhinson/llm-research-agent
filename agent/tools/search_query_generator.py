import logging

from agent.llm import get_client, provider_key_present, LLMClient

logger = logging.getLogger(__name__)

DYNAMIC_PROMPT = """\
You help a research agent monitor LLM and AI developments via web search.

Recent strategies documented (for context):
{recent_titles}

Suggest 2-3 additional SHORT web-search queries (a few words each) that would surface
new, related developments not already obvious from the titles above. Focus on emerging
LLM/AI topics. Output one query per line, no numbering, no extra prose.
"""


class SearchQueryGenerator:
    def __init__(self, cfg: dict, api_key: str | None = None, *,
                 client: LLMClient | None = None, llm_cfg: dict | None = None):
        self._cfg = cfg or {}
        self._llm_cfg = {"llm": llm_cfg or {}}
        self._client = client

    def queries(self, recent_titles: list[str]) -> list[str]:
        search = self._cfg.get("search", {})
        fixed = list(search.get("fixed_queries", []))
        dynamic_enabled = search.get("dynamic_queries_enabled", True)
        max_queries = search.get("max_queries", 10)

        dynamic: list[str] = []
        if dynamic_enabled and (self._client is not None or provider_key_present(self._llm_cfg)):
            dynamic = self._dynamic_queries(recent_titles)

        merged = fixed + dynamic
        deduped: list[str] = []
        seen: set[str] = set()
        for q in merged:
            if q not in seen:
                seen.add(q)
                deduped.append(q)
        return deduped[:max_queries]

    def _dynamic_queries(self, recent_titles: list[str]) -> list[str]:
        try:
            titles_text = "\n".join(f"- {t}" for t in recent_titles) or "(none yet)"
            prompt = DYNAMIC_PROMPT.format(recent_titles=titles_text)
            client = self._client if self._client is not None else get_client(self._llm_cfg)
            text = client.complete(prompt, max_tokens=256)
            queries = []
            for line in text.splitlines():
                line = line.strip().lstrip("-•* ").strip()
                if line:
                    queries.append(line)
            return queries
        except Exception:  # noqa: BLE001 — dynamic step is non-fatal
            logger.warning("dynamic query generation failed; using fixed anchors only", exc_info=True)
            return []
