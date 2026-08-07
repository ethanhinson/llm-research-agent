import datetime
import arxiv

from agent.models import RawItem

CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]
MAX_RESULTS = 50
LOOKBACK_DAYS = 7


class ArxivFetcher:
    name = "arxiv"

    def __init__(self, max_results: int = MAX_RESULTS, lookback_days: int = LOOKBACK_DAYS):
        self.max_results = max_results
        self.lookback_days = lookback_days

    def fetch(self) -> list[RawItem]:
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=self.lookback_days)
        query = " OR ".join(f"cat:{cat}" for cat in CATEGORIES)
        search = arxiv.Search(
            query=query,
            max_results=self.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )
        client = arxiv.Client()
        items = []
        for result in client.results(search):
            if result.published and result.published < since:
                break  # results are sorted newest-first; stop once past the window
            ts = result.published.isoformat() if result.published else ""
            items.append(
                RawItem(
                    title=result.title,
                    body=result.summary[:2000],
                    url=result.entry_id,
                    source="arxiv",
                    engagement=0,
                    timestamp=ts,
                )
            )
        return items
