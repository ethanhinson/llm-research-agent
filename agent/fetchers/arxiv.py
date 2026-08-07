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


class ArxivSearchAdapter:
    """Keyword-search arXiv adapter alongside the category firehose.

    Runs one ``arxiv.Search`` per configured query string (sorted newest-first),
    then post-filters by ``published`` against a UTC lookback cutoff in Python —
    arXiv 500s on ``submittedDate:[X TO *]`` Lucene ranges, so the date window is
    never put in the query. ``name`` is the source *family* id (``"arxiv"``);
    individual items carry the finer per-item source ``"arxiv/search"``.
    """

    name = "arxiv"

    def __init__(
        self,
        queries: list[str],
        max_results_per_query: int = 10,
        lookback_days: int = LOOKBACK_DAYS,
    ):
        self.queries = queries
        self.max_results_per_query = max_results_per_query
        self.lookback_days = lookback_days

    def fetch(self) -> list[RawItem]:
        if not self.queries:
            return []
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=self.lookback_days
        )
        client = arxiv.Client()
        items: list[RawItem] = []
        for query in self.queries:
            try:
                search = arxiv.Search(
                    query=query,
                    max_results=self.max_results_per_query,
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                )
                for result in client.results(search):
                    if result.published and result.published < since:
                        break  # sorted newest-first; stop once past the window
                    ts = result.published.isoformat() if result.published else ""
                    items.append(
                        RawItem(
                            title=result.title,
                            body=result.summary[:2000],
                            url=result.entry_id,
                            source="arxiv/search",
                            engagement=0,
                            timestamp=ts,
                        )
                    )
            except Exception:
                continue  # fail-soft: skip this query on any error
        return items
