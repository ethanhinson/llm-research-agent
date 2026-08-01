import httpx

from agent.models import RawItem

HN_API = "https://hn.algolia.com/api/v1/search"


class HNFetcher:
    def __init__(self, threshold: int = 50):
        self.threshold = threshold

    def fetch(self) -> list[RawItem]:
        resp = httpx.get(
            HN_API,
            params={"tags": "story", "hitsPerPage": 100, "numericFilters": f"points>={self.threshold}"},
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
