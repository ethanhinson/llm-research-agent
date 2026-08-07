"""Trending-repository intake via the GitHub search API.

Mirrors the ``HNFetcher`` shape: an ``httpx.get`` call, fail-soft error handling,
and ``RawItem`` mapping. A single combined request is issued — all configured
topics are joined as ``topic:<t>`` qualifiers (AND) alongside a
``pushed:>=<cutoff>`` recency qualifier, sorted by stars descending.
"""

import datetime
import os

import httpx

from agent.models import RawItem

GITHUB_SEARCH_API = "https://api.github.com/search/repositories"
LOOKBACK_DAYS = 7


class GitHubTrendingAdapter:
    name = "github"

    def __init__(
        self,
        topics: list[str],
        min_stars: int = 100,
        lookback_days: int = LOOKBACK_DAYS,
    ):
        self.topics = topics
        self.min_stars = min_stars
        self.lookback_days = lookback_days

    def fetch(self) -> list[RawItem]:
        cutoff = datetime.date.today() - datetime.timedelta(days=self.lookback_days)
        qualifiers = [f"topic:{t}" for t in self.topics]
        qualifiers.append(f"pushed:>={cutoff.isoformat()}")
        query = " ".join(qualifiers)

        headers = {"Accept": "application/vnd.github+json"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            resp = httpx.get(
                GITHUB_SEARCH_API,
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 100,
                },
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            repos = resp.json().get("items", [])
        except Exception:
            return []

        items = []
        for repo in repos:
            stars = repo.get("stargazers_count") or 0
            if stars < self.min_stars:
                continue
            full_name = repo.get("full_name", "")
            description = repo.get("description") or ""
            items.append(
                RawItem(
                    title=full_name,
                    body=description,
                    url=repo.get("html_url", ""),
                    source="github",
                    engagement=stars,
                    timestamp=repo.get("pushed_at", ""),
                )
            )
        return items
