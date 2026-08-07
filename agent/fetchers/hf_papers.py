import datetime

import httpx

from agent.models import RawItem

HF_API = "https://huggingface.co/api/daily_papers"
LOOKBACK_DAYS = 7


def _parse_published(value: str) -> datetime.datetime | None:
    """Parse HF's ISO ``publishedAt`` (handles trailing ``Z`` and milliseconds)."""
    if not value:
        return None
    try:
        # Python's fromisoformat handles fractional seconds; normalise the Z.
        dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


class HFPapersAdapter:
    name = "hf-papers"

    def __init__(self, min_upvotes: int = 0, lookback_days: int = LOOKBACK_DAYS):
        self.min_upvotes = min_upvotes
        self.lookback_days = lookback_days

    def fetch(self) -> list[RawItem]:
        try:
            cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
                days=self.lookback_days
            )
            resp = httpx.get(HF_API, timeout=15)
            resp.raise_for_status()
            entries = resp.json()
            if not isinstance(entries, list):
                return []

            items = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                # Entry may be flat or nested under "paper".
                paper = entry.get("paper") if isinstance(entry.get("paper"), dict) else entry

                upvotes = paper.get("upvotes") or 0
                if upvotes < self.min_upvotes:
                    continue

                published = paper.get("publishedAt") or entry.get("publishedAt") or ""
                pub_dt = _parse_published(published)
                if pub_dt is not None and pub_dt < cutoff:
                    continue

                paper_id = paper.get("id") or ""
                if not paper_id:
                    continue

                items.append(
                    RawItem(
                        title=paper.get("title", ""),
                        body=(paper.get("summary") or "")[:2000],
                        url=f"https://huggingface.co/papers/{paper_id}",
                        source="hf-papers",
                        engagement=upvotes,
                        timestamp=published,
                    )
                )
            return items
        except Exception:
            return []
