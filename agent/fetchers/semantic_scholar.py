"""Semantic Scholar keyword-search intake via the Graph API.

Mirrors the ``GitHubTrendingAdapter``/``HFPapersAdapter`` shape: an ``httpx.get``
call per configured query, fail-soft error handling, and ``RawItem`` mapping.
Body text prefers the tldr summary over the abstract; ``engagement`` is the
citation count; the arXiv link (from ``externalIds``) is preferred as the item
URL to aid cross-source dedup.

Rate handling: the unkeyed shared pool is aggressively throttled (429s expected).
A single query gets one backoff-then-retry on 429, then fails soft (that query is
skipped — the sweep never aborts). An optional ``S2_API_KEY`` env var is sent as
the ``x-api-key`` header for the dedicated tier. A small inter-request sleep keeps
this a polite citizen of the shared pool when unkeyed.
"""

import datetime
import os
import time

import httpx

from agent.models import RawItem

S2_SEARCH_API = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,abstract,url,citationCount,tldr,publicationDate,externalIds"
LOOKBACK_DAYS = 7
BACKOFF_SECONDS = 2
POLITE_SLEEP_SECONDS = 1


def _tldr_text(paper: dict) -> str:
    tldr = paper.get("tldr")
    if isinstance(tldr, dict):
        return tldr.get("text") or ""
    return ""


def _prefer_arxiv_url(paper: dict) -> str:
    external = paper.get("externalIds")
    if isinstance(external, dict):
        arxiv_id = external.get("ArXiv")
        if arxiv_id:
            return f"https://arxiv.org/abs/{arxiv_id}"
    return paper.get("url") or ""


def _within_lookback(pub_date: str, cutoff: datetime.date) -> bool:
    """Keep undated / unparseable papers; drop only papers clearly older than cutoff."""
    if not pub_date:
        return True
    try:
        parsed = datetime.date.fromisoformat(pub_date[:10])
    except (ValueError, TypeError):
        return True
    return parsed >= cutoff


class SemanticScholarAdapter:
    name = "s2"

    def __init__(
        self,
        queries: list[str],
        max_per_query: int = 10,
        lookback_days: int = LOOKBACK_DAYS,
    ):
        self.queries = queries
        self.max_per_query = max_per_query
        self.lookback_days = lookback_days

    def _get(self, query: str, headers: dict):
        """One GET with a single 429 backoff-then-retry. Returns the parsed
        ``data`` list, or ``None`` on any failure (caller fails soft)."""
        for attempt in range(2):
            resp = httpx.get(
                S2_SEARCH_API,
                params={
                    "query": query,
                    "fields": S2_FIELDS,
                    "limit": self.max_per_query,
                },
                headers=headers,
                timeout=15,
            )
            if getattr(resp, "status_code", None) == 429:
                if attempt == 0:
                    time.sleep(BACKOFF_SECONDS)
                    continue
                return None  # retry also throttled — skip this query
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return data if isinstance(data, list) else []
        return None

    def fetch(self) -> list[RawItem]:
        if not self.queries:
            return []

        cutoff = datetime.date.today() - datetime.timedelta(days=self.lookback_days)
        headers: dict = {}
        api_key = os.getenv("S2_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key
        unkeyed = not api_key

        items: list[RawItem] = []
        for idx, query in enumerate(self.queries):
            if idx > 0 and unkeyed:
                time.sleep(POLITE_SLEEP_SECONDS)
            try:
                papers = self._get(query, headers)
            except Exception:
                continue  # fail-soft: skip this query on any error
            if not papers:
                continue
            for paper in papers:
                if not isinstance(paper, dict):
                    continue
                pub_date = paper.get("publicationDate") or ""
                if not _within_lookback(pub_date, cutoff):
                    continue
                body = (_tldr_text(paper) or paper.get("abstract") or "")[:2000]
                items.append(
                    RawItem(
                        title=paper.get("title") or "",
                        body=body,
                        url=_prefer_arxiv_url(paper),
                        source="s2",
                        engagement=paper.get("citationCount") or 0,
                        timestamp=pub_date,
                    )
                )
        return items
