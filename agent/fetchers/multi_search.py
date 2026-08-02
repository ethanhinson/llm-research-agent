from concurrent.futures import ThreadPoolExecutor

from agent.fetchers.web_search import SearchClient
from agent.models import RawItem


class MultiSearchFetcher:
    def __init__(
        self,
        clients: list[SearchClient],
        queries: list[str],
        max_results_per_query: int = 10,
    ):
        self.clients = clients
        self.queries = queries
        self.max_results_per_query = max_results_per_query

    def _search(self, client: SearchClient, query: str) -> list[RawItem]:
        try:
            return client.search(query, max_results=self.max_results_per_query)
        except Exception as exc:
            print(f"[warn] search client failed for query {query!r}: {exc}")
            return []

    def fetch(self) -> list[RawItem]:
        if not self.clients or not self.queries:
            return []

        # Submit in (client, query) order; keep futures in that same order so
        # collection is deterministic regardless of completion timing.
        pairs = [
            (client, query) for client in self.clients for query in self.queries
        ]
        with ThreadPoolExecutor(max_workers=len(pairs)) as executor:
            futures = [
                executor.submit(self._search, client, query)
                for client, query in pairs
            ]
            per_pair_results = [future.result() for future in futures]

        seen: set[str] = set()
        deduped: list[RawItem] = []
        for items in per_pair_results:
            for item in items:
                if item.url in seen:
                    continue
                seen.add(item.url)
                deduped.append(item)
        return deduped
