import time
import calendar

import httpx
import feedparser

from agent.models import RawItem

LOOKBACK_DAYS = 7


class WebFetcher:
    def __init__(self, feeds: list[dict], lookback_days: int = LOOKBACK_DAYS):
        self.feeds = feeds
        self.lookback_days = lookback_days

    def fetch(self) -> list[RawItem]:
        cutoff = time.time() - self.lookback_days * 86400
        items = []
        for feed in self.feeds:
            try:
                resp = httpx.get(feed["url"], timeout=15, follow_redirects=True)
                parsed = feedparser.parse(resp.content)
                for entry in parsed.entries:
                    title = entry.get("title", "")
                    url = entry.get("link", "")
                    if not title or not url:
                        continue
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    if pub:
                        ts = calendar.timegm(pub)
                        if ts < cutoff:
                            continue
                    body = entry.get("summary", entry.get("description", ""))[:2000]
                    published = entry.get("published", "")
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
