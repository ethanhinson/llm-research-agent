"""Bluesky author-feed intake via the public ``getAuthorFeed`` endpoint.

Mirrors the ``SemanticScholarAdapter``/``GitHubTrendingAdapter`` shape: one
unauthenticated ``httpx.get`` per configured handle against the public API,
per-handle fail-soft error handling, and ``RawItem`` mapping. Posts are short —
the payload is the link — so outbound links / arXiv IDs are extracted from post
facets and embeds; reposts, replies, and pure-commentary posts are dropped.
``engagement`` = likeCount + repostCount, thresholded by ``min_engagement``.

Verified 2026-08-07: the public endpoint returns HTTP 200 with no auth. Keyword
search (``searchPosts``) is 403 unauthenticated and is deliberately out of scope.
"""

import datetime
import re

import httpx

from agent.models import RawItem

GET_AUTHOR_FEED_API = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
LOOKBACK_DAYS = 7
FEED_LIMIT = 25

# arxiv.org/abs/<id> or arxiv.org/pdf/<id>; id like 2401.01234 or 2401.01234v2,
# also legacy hep-th/9901001 style. Captured group is the bare id.
_ARXIV_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:v\d+)?(?:\.pdf)?(?:[?#].*)?$",
    re.IGNORECASE,
)


def _parse_ts(value: str) -> datetime.datetime | None:
    """Parse an ISO ``indexedAt`` (handles trailing ``Z`` and fractional secs)."""
    if not value:
        return None
    try:
        dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _within_lookback(ts: str, cutoff: datetime.datetime) -> bool:
    """Keep undated/unparseable posts; drop only posts clearly older than cutoff."""
    parsed = _parse_ts(ts)
    if parsed is None:
        return True
    return parsed >= cutoff


def _normalize_arxiv(url: str) -> str | None:
    """Return ``https://arxiv.org/abs/<id>`` if ``url`` is an arXiv link, else None."""
    if not url:
        return None
    m = _ARXIV_RE.search(url)
    if not m:
        return None
    return f"https://arxiv.org/abs/{m.group(1)}"


def _extract_outbound_urls(post: dict) -> list[str]:
    """Collect candidate outbound URLs from facet links and the external embed.

    Returns a de-duplicated list preserving first-seen order.
    """
    urls: list[str] = []
    record = post.get("record")
    if isinstance(record, dict):
        facets = record.get("facets")
        if isinstance(facets, list):
            for facet in facets:
                if not isinstance(facet, dict):
                    continue
                for feature in facet.get("features") or []:
                    if not isinstance(feature, dict):
                        continue
                    ftype = feature.get("$type") or ""
                    if ftype.endswith("#link"):
                        uri = feature.get("uri")
                        if uri:
                            urls.append(uri)
    embed = post.get("embed")
    if isinstance(embed, dict) and (embed.get("$type") or "").endswith(
        "embed.external#view"
    ):
        external = embed.get("external")
        if isinstance(external, dict):
            uri = external.get("uri")
            if uri:
                urls.append(uri)
    # de-dup, order-preserving
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _external_embed_title(post: dict) -> str:
    embed = post.get("embed")
    if isinstance(embed, dict) and (embed.get("$type") or "").endswith(
        "embed.external#view"
    ):
        external = embed.get("external")
        if isinstance(external, dict):
            return external.get("title") or ""
    return ""


def _post_web_url(handle: str, at_uri: str) -> str:
    """``at://<did>/app.bsky.feed.post/<rkey>`` -> the public bsky.app post URL."""
    rkey = at_uri.rstrip("/").rsplit("/", 1)[-1] if at_uri else ""
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


def _is_reply(post: dict) -> bool:
    record = post.get("record")
    return isinstance(record, dict) and "reply" in record


class BlueskyAdapter:
    name = "bluesky"

    def __init__(
        self,
        authors: list[str],
        min_engagement: int = 5,
        lookback_days: int = LOOKBACK_DAYS,
    ):
        self.authors = authors
        self.min_engagement = min_engagement
        self.lookback_days = lookback_days

    def fetch(self) -> list[RawItem]:
        if not self.authors:
            return []

        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=self.lookback_days
        )
        items: list[RawItem] = []
        for handle in self.authors:
            try:
                resp = httpx.get(
                    GET_AUTHOR_FEED_API,
                    params={"actor": handle, "limit": FEED_LIMIT},
                    timeout=15,
                )
                resp.raise_for_status()
                feed = resp.json().get("feed", [])
            except Exception:
                continue  # fail-soft PER HANDLE: one dead handle never kills the source
            if not isinstance(feed, list):
                continue
            for entry in feed:
                item = self._map(handle, entry, cutoff)
                if item is not None:
                    items.append(item)
        return items

    def _map(self, handle: str, entry: dict, cutoff: datetime.datetime):
        if not isinstance(entry, dict):
            return None
        # SKIP REPOSTS: item has a top-level `reason` key.
        if "reason" in entry:
            return None
        post = entry.get("post")
        if not isinstance(post, dict):
            return None
        # SKIP REPLIES: record contains a `reply` key.
        if _is_reply(post):
            return None

        indexed_at = post.get("indexedAt") or ""
        if not _within_lookback(indexed_at, cutoff):
            return None

        engagement = (post.get("likeCount") or 0) + (post.get("repostCount") or 0)
        if engagement < self.min_engagement:
            return None  # engagement floor

        record = post.get("record") if isinstance(post.get("record"), dict) else {}
        text = record.get("text") or ""

        outbound = _extract_outbound_urls(post)
        arxiv_urls = [a for a in (_normalize_arxiv(u) for u in outbound) if a]

        # DROP PURE COMMENTARY: no outbound link AND no arXiv ID.
        if not outbound and not arxiv_urls:
            return None

        # url: prefer a normalized arXiv url; else the single outbound link when
        # exactly one distinct outbound exists; else the post's own web URL.
        if arxiv_urls:
            url = arxiv_urls[0]
        elif len(outbound) == 1:
            url = outbound[0]
        else:
            url = _post_web_url(handle, post.get("uri") or "")

        title = (text or _external_embed_title(post))[:200]
        body = text[:2000]

        return RawItem(
            title=title,
            body=body,
            url=url,
            source=f"bluesky/{handle}",
            engagement=engagement,
            timestamp=indexed_at,
        )
