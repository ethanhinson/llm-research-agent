import httpx
import feedparser

from agent.models import RawItem


class WebFetcher:
    def __init__(self, feeds: list[dict]):
        self.feeds = feeds

    def fetch(self) -> list[RawItem]:
        items = []
        for feed in self.feeds:
            try:
                resp = httpx.get(feed["url"], timeout=15, follow_redirects=True)
                parsed = feedparser.parse(resp.content)
                for entry in parsed.entries:
                    title = entry.get("title", "")
                    url = entry.get("link", "")
                    body = entry.get("summary", entry.get("description", ""))[:2000]
                    published = entry.get("published", "")
                    if not title or not url:
                        continue
                    items.append(
                        RawItem(
                            title=title,
                            body=body,
                            url=url,
                            source=f"web/{feed['name']}",
                            engagement=0,
                            timestamp=published,
                        )
                    )
            except Exception:
                pass
        return items
