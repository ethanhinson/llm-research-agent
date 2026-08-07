import time
import httpx

from agent.models import RawItem

HN_API = "https://hn.algolia.com/api/v1/search"
LOOKBACK_DAYS = 7


class HNFetcher:
    name = "hackernews"

    def __init__(self, threshold: int = 50, lookback_days: int = LOOKBACK_DAYS):
        self.threshold = threshold
        self.lookback_days = lookback_days

    def fetch(self) -> list[RawItem]:
        since = int(time.time()) - self.lookback_days * 86400
        resp = httpx.get(
            HN_API,
            params={
                "tags": "story",
                "hitsPerPage": 100,
                "numericFilters": f"points>={self.threshold},created_at_i>={since}",
            },
            timeout=15,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        items = []
        for hit in hits:
            points = hit.get("points") or 0
            if points < self.threshold:
                continue
            body = hit.get("story_text") or ""
            items.append(
                RawItem(
                    title=hit.get("title", ""),
                    body=body,
                    url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                    source="hackernews",
                    engagement=points,
                    timestamp=hit.get("created_at", ""),
                )
            )
        return items
