import arxiv

from agent.models import RawItem

CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]
MAX_RESULTS = 200


class ArxivFetcher:
    def __init__(self, max_results: int = MAX_RESULTS):
        self.max_results = max_results

    def fetch(self) -> list[RawItem]:
        query = " OR ".join(f"cat:{cat}" for cat in CATEGORIES)
        search = arxiv.Search(
            query=query,
            max_results=self.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        )
        client = arxiv.Client()
        items = []
        for result in client.results(search):
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
