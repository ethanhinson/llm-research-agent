import os
import time
from typing import Protocol

import httpx

from agent.models import RawItem


class SearchClient(Protocol):
    def search(self, query: str, max_results: int = 10) -> list[RawItem]: ...


class TavilySearchClient:
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")

    def search(self, query: str, max_results: int = 10) -> list[RawItem]:
        if not self.api_key:
            print("[warn] TAVILY_API_KEY not set, skipping Tavily search")
            return []
        try:
            import agent.fetchers.web_search as _self

            if not hasattr(_self, "TavilyClient"):
                from tavily import TavilyClient as _TavilyClient

                _self.TavilyClient = _TavilyClient
            client = _self.TavilyClient(api_key=self.api_key)
            resp = client.search(
                query,
                search_depth="basic",
                include_answer=False,
                max_results=max_results,
            )
            items = []
            for item in resp.get("results", []):
                items.append(
                    RawItem(
                        title=item.get("title", ""),
                        body=item.get("content", ""),
                        url=item.get("url", ""),
                        source="search/tavily",
                        engagement=0,
                        timestamp=item.get("published_date", ""),
                    )
                )
            return items
        except Exception as exc:
            print(f"[warn] Tavily search failed: {exc}")
            return []


class BingSearchClient:
    def __init__(self):
        self.api_key = os.getenv("BING_SEARCH_API_KEY")

    def search(self, query: str, max_results: int = 10) -> list[RawItem]:
        if not self.api_key:
            print("[warn] BING_SEARCH_API_KEY not set, skipping Bing search")
            return []
        try:
            resp = httpx.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers={"Ocp-Apim-Subscription-Key": self.api_key},
                params={"q": query, "count": max_results, "freshness": "Week"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            items = []
            for item in data.get("webPages", {}).get("value", []):
                items.append(
                    RawItem(
                        title=item.get("name", ""),
                        body=item.get("snippet", ""),
                        url=item.get("url", ""),
                        source="search/bing",
                        engagement=0,
                        timestamp=item.get("dateLastCrawled", ""),
                    )
                )
            return items
        except Exception as exc:
            print(f"[warn] Bing search failed: {exc}")
            return []


class SerpAPISearchClient:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")

    def search(self, query: str, max_results: int = 10) -> list[RawItem]:
        if not self.api_key:
            print("[warn] SERPAPI_KEY not set, skipping SerpAPI search")
            return []
        try:
            resp = httpx.get(
                "https://serpapi.com/search.json",
                params={
                    "q": query,
                    "engine": "google",
                    "api_key": self.api_key,
                    "num": max_results,
                },
                timeout=15,
            )
            time.sleep(0.5)
            resp.raise_for_status()
            data = resp.json()
            items = []
            for item in data.get("organic_results", []):
                items.append(
                    RawItem(
                        title=item.get("title", ""),
                        body=item.get("snippet", ""),
                        url=item.get("link", ""),
                        source="search/serpapi",
                        engagement=0,
                        timestamp=item.get("date", ""),
                    )
                )
            return items
        except Exception as exc:
            print(f"[warn] SerpAPI search failed: {exc}")
            return []
