"""Trending Hugging Face models + datasets intake.

Surfaces release-type artifacts (open models and datasets) that never appear as
papers — 0010's daily-papers adapter misses them. Mirrors the ``HFPapersAdapter``
/ ``GitHubTrendingAdapter`` shape: an ``httpx.get`` call, fail-soft error
handling, and ``RawItem`` mapping.

Two endpoints are queried by a single ``fetch()`` — models and datasets — each
independently fail-soft, so a failure of one still returns the other's items.
The HF hub API sorts by ``trendingScore`` (``sort=trending`` returns HTTP 400 —
the param must be ``trendingScore``) and requires no auth.
"""

import httpx

from agent.models import RawItem

HF_MODELS_API = "https://huggingface.co/api/models"
HF_DATASETS_API = "https://huggingface.co/api/datasets"

# Interface parity only: build_adapters threads a widened crawl window into every
# source via **lb, and the factory tests assert each adapter exposes
# .lookback_days. The trending endpoints have no recency parameter (trendingScore
# already encodes recency), so lookback_days is stored but never used to filter
# or as an API param.
LOOKBACK_DAYS = 7


class HFTrendingAdapter:
    name = "hf-trending"

    def __init__(
        self,
        limit: int = 20,
        min_likes: int = 0,
        lookback_days: int = LOOKBACK_DAYS,
    ):
        self.limit = limit
        self.min_likes = min_likes
        self.lookback_days = lookback_days

    def _fetch_endpoint(self, url: str, *, is_dataset: bool) -> list[RawItem]:
        """Fetch one endpoint, fail-soft: any error yields an empty list."""
        try:
            resp = httpx.get(
                url,
                params={"sort": "trendingScore", "limit": self.limit},
                timeout=15,
            )
            resp.raise_for_status()
            entries = resp.json()
        except Exception:
            return []

        if not isinstance(entries, list):
            return []

        items: list[RawItem] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue

            artifact_id = entry.get("id") or ""
            if not artifact_id:
                continue

            likes = entry.get("likes") or 0
            if likes < self.min_likes:
                continue

            if is_dataset:
                item_url = f"https://huggingface.co/datasets/{artifact_id}"
            else:
                item_url = f"https://huggingface.co/{artifact_id}"

            # Models list payloads carry no description; datasets do.
            body = entry.get("description") or ""
            timestamp = entry.get("lastModified") or entry.get("createdAt") or ""

            items.append(
                RawItem(
                    title=artifact_id,
                    body=body[:2000],
                    url=item_url,
                    source="hf-trending",
                    engagement=likes,  # likes is the engagement signal, not downloads
                    timestamp=timestamp,
                )
            )
        return items

    def fetch(self) -> list[RawItem]:
        items: list[RawItem] = []
        items.extend(self._fetch_endpoint(HF_MODELS_API, is_dataset=False))
        items.extend(self._fetch_endpoint(HF_DATASETS_API, is_dataset=True))
        return items
