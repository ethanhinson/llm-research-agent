<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0013 — Bluesky author-feed adapter with researcher registry](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0013-bluesky-author-feeds.md)**
<!-- docket:backlink:end -->

# Bluesky Author-Feed Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `BlueskyAdapter` on the landed 0009 source-adapter layer that ingests posts from a curated registry of AI researchers' Bluesky author feeds as candidate research items.

**Architecture:** A new `agent/fetchers/bluesky.py` module mirrors the sibling adapters (`semantic_scholar.py`, `github_trending.py`, `hf_papers.py`): one `httpx.get` per configured handle against the unauthenticated public `getAuthorFeed` endpoint, per-handle fail-soft error handling, `RawItem` mapping, and `lookback_days` threading. Reposts/replies/pure-commentary are dropped; outbound links and arXiv IDs are extracted from post facets and embeds. The adapter is config-gated and wired into `build_adapters(kind="sweep")` alongside the other `sources:` adapters.

**Tech Stack:** Python 3, `httpx` (sync `httpx.get`), `datetime`, `re`. Tests use `pytest` + `pytest-mock` (`mocker`). No new dependencies.

## Global Constraints

- Endpoint: `GET https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed` — **no auth header**, params `actor=<handle>`, `limit=25`. One request per handle. (Verified live 2026-08-07: HTTP 200 unauthenticated.)
- `httpx.get(..., timeout=15)` — matches every sibling adapter.
- **Fail-soft PER HANDLE**: wrap each handle's request+parse in `try/except Exception: continue` so one dead/400 handle never kills the source (mirrors `semantic_scholar`'s per-query fail-soft). Empty `authors` returns `[]` with **no HTTP call**.
- Module constant `LOOKBACK_DAYS = 7` is the default lookback window.
- Adapter `name` class attr = `"bluesky"` (the source *family* id). Per-item `RawItem.source` = `f"bluesky/{handle}"` (finer per-item source, matching the `base.py` protocol doc's `"web/<feed>"` precedent).
- Must satisfy `runtime_checkable` protocol conformance: `isinstance(adapter, SourceAdapter)` is `True`.
- `keyword search (searchPosts)` is **out of scope** — author feeds only, no account needed.

---

## File Structure

- **Create** `agent/fetchers/bluesky.py` — the `BlueskyAdapter` class + module-level helpers (`_parse_ts`, `_within_lookback`, `_extract_outbound_urls`, `_normalize_arxiv`, `_post_web_url`). One clear responsibility: turn one author's feed into `RawItem`s.
- **Modify** `agent/fetchers/base.py` — add a config-gated `bluesky` block to `build_adapters(kind="sweep")` and import `BlueskyAdapter` in the local-import block.
- **Modify** `config.yml` — add a `bluesky:` entry under `sources:` (enabled, `min_engagement`, `authors` list of 27 verified handles).
- **Create** `tests/test_fetcher_bluesky.py` — mocked-httpx unit tests, mirroring `tests/test_fetcher_semantic_scholar.py` structure.
- **Modify** `tests/test_build_adapters.py` — factory-gating tests for the bluesky block.

---

## Task 1: `BlueskyAdapter` core — fetch, per-handle fail-soft, mapping, filters

**Files:**
- Create: `agent/fetchers/bluesky.py`
- Test: `tests/test_fetcher_bluesky.py`

**Interfaces:**
- Consumes: `from agent.models import RawItem` (fields: `title`, `body`, `url`, `source`, `engagement: int`, `timestamp: str`); `from agent.fetchers.base import SourceAdapter` (protocol, for the conformance test only).
- Produces: module constant `LOOKBACK_DAYS = 7`; class `BlueskyAdapter` with class attr `name = "bluesky"`, constructor `BlueskyAdapter(authors: list[str], min_engagement: int = 5, lookback_days: int = LOOKBACK_DAYS)` setting `self.authors`, `self.min_engagement`, `self.lookback_days`; method `fetch(self) -> list[RawItem]`. Module constant `GET_AUTHOR_FEED_API = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"`. Helper functions `_parse_ts(value: str) -> datetime.datetime | None`, `_within_lookback(ts, cutoff) -> bool`, `_normalize_arxiv(url: str) -> str | None`, `_extract_outbound_urls(post: dict) -> list[str]`, `_post_web_url(handle: str, at_uri: str) -> str`.

### Step-by-step

- [ ] **Step 1: Write the failing test file scaffold + first behaviors**

Create `tests/test_fetcher_bluesky.py` with the shared fixtures/builders and the first batch of behavior tests. Use `pytest-mock`'s `mocker` (already used by `test_fetcher_semantic_scholar.py`). Build feed payloads with a `_post(...)` factory and a `_feed(*items)` wrapper, and a `_mock_get` that patches `httpx.get`.

```python
import datetime

import httpx
import pytest

from agent.fetchers.bluesky import (
    GET_AUTHOR_FEED_API,
    BlueskyAdapter,
)


def _recent_iso():
    return (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    ).isoformat().replace("+00:00", "Z")


def _old_iso():
    return (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)
    ).isoformat().replace("+00:00", "Z")


def _facet_link(uri):
    return {
        "features": [
            {"$type": "app.bsky.richtext.facet#link", "uri": uri}
        ]
    }


def _external_embed(uri, title="Embed Title"):
    return {
        "$type": "app.bsky.embed.external#view",
        "external": {"uri": uri, "title": title},
    }


def _post(
    *,
    text="A short post with a link",
    like_count=10,
    repost_count=5,
    indexed_at=None,
    uri="at://did:plc:abc123/app.bsky.feed.post/rkey123",
    facets=None,
    embed=None,
    reply=False,
):
    record = {"text": text}
    if facets is not None:
        record["facets"] = facets
    if reply:
        record["reply"] = {"parent": {"uri": "at://x/y/z"}, "root": {"uri": "at://x/y/z"}}
    post = {
        "uri": uri,
        "likeCount": like_count,
        "repostCount": repost_count,
        "indexedAt": indexed_at or _recent_iso(),
        "record": record,
    }
    if embed is not None:
        post["embed"] = embed
    return post


def _item(post=None, *, reason=False):
    """One feed item. reason=True marks a repost (top-level `reason` key)."""
    item = {"post": post or _post()}
    if reason:
        item["reason"] = {"$type": "app.bsky.feed.defs#reasonRepost"}
    return item


def _feed(*items):
    return {"feed": list(items)}


def _resp(mocker, payload=None, status_code=200, raise_status=False):
    if payload is None:
        payload = _feed(_item())
    resp = mocker.MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    if raise_status:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "boom", request=mocker.MagicMock(), response=mocker.MagicMock()
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _mock_get(mocker, resp=None, **kw):
    if resp is None:
        resp = _resp(mocker, **kw)
    return mocker.patch("httpx.get", return_value=resp)


def test_request_shape_one_per_handle(mocker):
    mock_get = _mock_get(mocker, payload=_feed())
    BlueskyAdapter(authors=["a.bsky.social", "b.bsky.social"]).fetch()
    assert mock_get.call_count == 2
    call = mock_get.call_args_list[0]
    assert call.args[0] == GET_AUTHOR_FEED_API
    params = call.kwargs["params"]
    assert params["actor"] == "a.bsky.social"
    assert params["limit"] == 25
    # unauthenticated: no auth header sent
    headers = call.kwargs.get("headers") or {}
    assert not any(k.lower() == "authorization" for k in headers)


def test_empty_authors_returns_empty_no_http(mocker):
    mock_get = mocker.patch("httpx.get")
    assert BlueskyAdapter(authors=[]).fetch() == []
    assert mock_get.call_count == 0


def test_maps_post_with_facet_link_to_rawitem(mocker):
    post = _post(
        text="Great new paper",
        like_count=8,
        repost_count=4,
        facets=[_facet_link("https://example.com/thing")],
    )
    _mock_get(mocker, payload=_feed(_item(post)))
    items = BlueskyAdapter(authors=["a.bsky.social"]).fetch()
    assert len(items) == 1
    it = items[0]
    assert it.title == "Great new paper"
    assert it.body == "Great new paper"
    assert it.url == "https://example.com/thing"
    assert it.source == "bluesky/a.bsky.social"
    assert it.engagement == 12  # 8 + 4
    assert it.timestamp == post["indexedAt"]


def test_source_is_per_handle(mocker):
    _mock_get(
        mocker,
        payload=_feed(_item(_post(facets=[_facet_link("https://ex.com/x")]))),
    )
    items = BlueskyAdapter(authors=["simonwillison.net"]).fetch()
    assert items[0].source == "bluesky/simonwillison.net"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_fetcher_bluesky.py -v`
Expected: FAIL — `ImportError` / `ModuleNotFoundError: No module named 'agent.fetchers.bluesky'`.

- [ ] **Step 3: Write the minimal implementation**

Create `agent/fetchers/bluesky.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run python -m pytest tests/test_fetcher_bluesky.py -v`
Expected: PASS (all four Step-1 tests green).

- [ ] **Step 5: Commit**

```bash
git add agent/fetchers/bluesky.py tests/test_fetcher_bluesky.py
git commit -m "feat(0013): BlueskyAdapter core — fetch, per-handle fail-soft, RawItem mapping"
```

---

## Task 2: Extraction & filter coverage — facets, embeds, arXiv, skips, floor, lookback, fail-soft, conformance

**Files:**
- Modify: `agent/fetchers/bluesky.py` (only if a test surfaces a gap — the Task-1 implementation should already satisfy these)
- Test: `tests/test_fetcher_bluesky.py`

**Interfaces:**
- Consumes: everything Produced by Task 1 (`BlueskyAdapter`, `GET_AUTHOR_FEED_API`, `LOOKBACK_DAYS`, helpers). Uses the `_post/_item/_feed/_facet_link/_external_embed/_mock_get/_resp` builders defined in the Task-1 test scaffold.
- Produces: full behavioral coverage. No new production symbols.

### Step-by-step

- [ ] **Step 1: Write the remaining failing tests**

Append to `tests/test_fetcher_bluesky.py`:

```python
def test_external_embed_link_and_title_extraction(mocker):
    # text present -> title is the text; url is the embed uri (single outbound)
    post = _post(
        text="Check this out",
        embed=_external_embed("https://blog.example/post", title="Embed Title"),
        facets=None,
    )
    _mock_get(mocker, payload=_feed(_item(post)))
    items = BlueskyAdapter(authors=["a.bsky.social"]).fetch()
    assert items[0].url == "https://blog.example/post"
    assert items[0].title == "Check this out"


def test_embed_title_used_when_text_empty(mocker):
    post = _post(
        text="",
        embed=_external_embed("https://blog.example/post", title="The Embed Title"),
    )
    _mock_get(mocker, payload=_feed(_item(post)))
    items = BlueskyAdapter(authors=["a.bsky.social"]).fetch()
    assert items[0].title == "The Embed Title"
    assert items[0].body == ""


def test_arxiv_id_detected_and_normalized_from_facet(mocker):
    post = _post(facets=[_facet_link("https://arxiv.org/pdf/2401.01234v2")])
    _mock_get(mocker, payload=_feed(_item(post)))
    items = BlueskyAdapter(authors=["a.bsky.social"]).fetch()
    assert items[0].url == "https://arxiv.org/abs/2401.01234"


def test_arxiv_id_detected_from_embed(mocker):
    post = _post(text="paper", embed=_external_embed("https://arxiv.org/abs/2405.09999"))
    _mock_get(mocker, payload=_feed(_item(post)))
    items = BlueskyAdapter(authors=["a.bsky.social"]).fetch()
    assert items[0].url == "https://arxiv.org/abs/2405.09999"


def test_arxiv_preferred_when_also_other_links(mocker):
    post = _post(
        facets=[
            _facet_link("https://twitter.com/x/status/1"),
            _facet_link("https://arxiv.org/abs/2401.05555"),
        ]
    )
    _mock_get(mocker, payload=_feed(_item(post)))
    items = BlueskyAdapter(authors=["a.bsky.social"]).fetch()
    assert items[0].url == "https://arxiv.org/abs/2401.05555"


def test_repost_skipped(mocker):
    # top-level `reason` marks a repost
    _mock_get(
        mocker,
        payload=_feed(_item(_post(facets=[_facet_link("https://ex.com/x")]), reason=True)),
    )
    assert BlueskyAdapter(authors=["a.bsky.social"]).fetch() == []


def test_reply_skipped(mocker):
    post = _post(facets=[_facet_link("https://ex.com/x")], reply=True)
    _mock_get(mocker, payload=_feed(_item(post)))
    assert BlueskyAdapter(authors=["a.bsky.social"]).fetch() == []


def test_pure_commentary_dropped(mocker):
    # no facets, no embed -> no outbound link, no arxiv -> dropped
    post = _post(text="just my thoughts, no link", facets=None, embed=None)
    _mock_get(mocker, payload=_feed(_item(post)))
    assert BlueskyAdapter(authors=["a.bsky.social"]).fetch() == []


def test_engagement_floor_drops_below_min(mocker):
    low = _post(like_count=2, repost_count=1, facets=[_facet_link("https://ex.com/x")])
    high = _post(like_count=4, repost_count=4, facets=[_facet_link("https://ex.com/y")])
    _mock_get(mocker, payload=_feed(_item(low), _item(high)))
    items = BlueskyAdapter(authors=["a.bsky.social"], min_engagement=5).fetch()
    urls = [i.url for i in items]
    assert "https://ex.com/x" not in urls  # engagement 3 < 5
    assert "https://ex.com/y" in urls      # engagement 8 >= 5


def test_engagement_is_like_plus_repost_sum(mocker):
    post = _post(like_count=7, repost_count=6, facets=[_facet_link("https://ex.com/x")])
    _mock_get(mocker, payload=_feed(_item(post)))
    items = BlueskyAdapter(authors=["a.bsky.social"], min_engagement=0).fetch()
    assert items[0].engagement == 13


def test_per_handle_fail_soft_one_bad_does_not_sink_others(mocker):
    good = _resp(
        mocker,
        payload=_feed(_item(_post(text="good", facets=[_facet_link("https://ex.com/g")]))),
    )
    mocker.patch("httpx.get", side_effect=[httpx.ConnectError("dead"), good])
    items = BlueskyAdapter(authors=["bad.bsky.social", "good.bsky.social"]).fetch()
    assert [i.body for i in items] == ["good"]


def test_fail_soft_on_status_error(mocker):
    _mock_get(mocker, raise_status=True)
    assert BlueskyAdapter(authors=["a.bsky.social"]).fetch() == []


def test_lookback_bounding_drops_old_keeps_recent_and_undated(mocker):
    payload = _feed(
        _item(_post(text="old", indexed_at=_old_iso(), facets=[_facet_link("https://ex.com/o")])),
        _item(_post(text="recent", indexed_at=_recent_iso(), facets=[_facet_link("https://ex.com/r")])),
        _item(_post(text="undated", indexed_at="", facets=[_facet_link("https://ex.com/u")])),
    )
    _mock_get(mocker, payload=payload)
    items = BlueskyAdapter(authors=["a.bsky.social"], lookback_days=7).fetch()
    bodies = [i.body for i in items]
    assert "old" not in bodies
    assert "recent" in bodies
    assert "undated" in bodies


def test_post_own_url_fallback_when_multiple_outbound(mocker):
    post = _post(
        uri="at://did:plc:xyz/app.bsky.feed.post/rkeyABC",
        facets=[
            _facet_link("https://ex.com/one"),
            _facet_link("https://ex.com/two"),
        ],
    )
    _mock_get(mocker, payload=_feed(_item(post)))
    items = BlueskyAdapter(authors=["someone.bsky.social"]).fetch()
    assert items[0].url == "https://bsky.app/profile/someone.bsky.social/post/rkeyABC"


def test_is_source_adapter():
    from agent.fetchers.base import SourceAdapter

    adapter = BlueskyAdapter(authors=["a.bsky.social"])
    assert isinstance(adapter, SourceAdapter)
    assert adapter.name == "bluesky"
```

- [ ] **Step 2: Run tests to verify they fail (or reveal gaps)**

Run: `uv run python -m pytest tests/test_fetcher_bluesky.py -v`
Expected: The new tests run against the Task-1 implementation. Most should PASS immediately; any FAIL points to a real gap in `agent/fetchers/bluesky.py`.

- [ ] **Step 3: Fix any gap surfaced by a failing test**

If (and only if) a test above fails, adjust `agent/fetchers/bluesky.py` minimally to satisfy it — e.g. tighten `_ARXIV_RE`, correct the `#link`/`embed.external#view` `$type` suffix checks, or the `url` selection order (arXiv → single-outbound → post-own-url). Do not add behavior not exercised by a test.

- [ ] **Step 4: Run the full new test module to verify all pass**

Run: `uv run python -m pytest tests/test_fetcher_bluesky.py -v`
Expected: PASS (all tests green).

- [ ] **Step 5: Commit**

```bash
git add agent/fetchers/bluesky.py tests/test_fetcher_bluesky.py
git commit -m "test(0013): full extraction/filter coverage for BlueskyAdapter"
```

---

## Task 3: Factory wiring in `build_adapters`

**Files:**
- Modify: `agent/fetchers/base.py:60-116` (local-import block + the `kind=="sweep"` body, after the `semantic_scholar` block)
- Test: `tests/test_build_adapters.py`

**Interfaces:**
- Consumes: `BlueskyAdapter(authors: list[str], min_engagement: int = 5, lookback_days: int = LOOKBACK_DAYS)` from Task 1; `build_adapters(cfg, *, kind, feeds=None, lookback_days=None, ...)` from `base.py`. The `lb` dict local (`{} if lookback_days is None else {"lookback_days": lookback_days}`) already exists in the `sweep` branch.
- Produces: `build_adapters(cfg, kind="sweep")` appends a `BlueskyAdapter` **after** the `SemanticScholarAdapter` block when `cfg["sources"]["bluesky"]["enabled"]` is truthy, threading `authors`, `min_engagement`, and `lb`.

### Step-by-step

- [ ] **Step 1: Write the failing factory tests**

Append to `tests/test_build_adapters.py`. Add the import at the top of the file alongside the other fetcher imports:

```python
from agent.fetchers.bluesky import BlueskyAdapter
```

Then add these tests:

```python
# --- Bluesky (change 0013) --------------------------------------------------


def test_sweep_adds_bluesky_when_enabled():
    cfg = {
        "sources": {
            "bluesky": {
                "enabled": True,
                "min_engagement": 8,
                "authors": ["simonwillison.net", "karpathy.bsky.social"],
            }
        }
    }
    adapters = build_adapters(cfg, kind="sweep", feeds=[])
    bsky = [a for a in adapters if isinstance(a, BlueskyAdapter)]
    assert len(bsky) == 1
    assert bsky[0].authors == ["simonwillison.net", "karpathy.bsky.social"]
    assert bsky[0].min_engagement == 8
    assert all(isinstance(a, SourceAdapter) for a in adapters)


def test_sweep_bluesky_defaults_min_engagement():
    cfg = {"sources": {"bluesky": {"enabled": True, "authors": ["a.bsky.social"]}}}
    adapters = build_adapters(cfg, kind="sweep", feeds=[])
    bsky = [a for a in adapters if isinstance(a, BlueskyAdapter)][0]
    assert bsky.min_engagement == 5
    assert bsky.authors == ["a.bsky.social"]


def test_sweep_omits_bluesky_when_disabled():
    cfg = {"sources": {"bluesky": {"enabled": False, "authors": ["a.bsky.social"]}}}
    assert BlueskyAdapter not in _sweep_types(cfg)


def test_sweep_omits_bluesky_when_absent():
    assert BlueskyAdapter not in _sweep_types({"sources": {"arxiv_queries": ["q"]}})
    assert BlueskyAdapter not in _sweep_types({"sources": {}})


def test_sweep_bluesky_empty_authors_when_missing():
    cfg = {"sources": {"bluesky": {"enabled": True}}}
    adapters = build_adapters(cfg, kind="sweep", feeds=[])
    bsky = [a for a in adapters if isinstance(a, BlueskyAdapter)][0]
    assert bsky.authors == []


def test_sweep_threads_lookback_into_bluesky():
    cfg = {"sources": {"bluesky": {"enabled": True, "authors": ["a.bsky.social"]}}}
    adapters = build_adapters(cfg, kind="sweep", feeds=[], lookback_days=30)
    bsky = [a for a in adapters if isinstance(a, BlueskyAdapter)][0]
    assert bsky.lookback_days == 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_build_adapters.py -v -k bluesky`
Expected: FAIL — `BlueskyAdapter` is never appended (the enabled cases find 0 adapters), and the enabled tests raise on `bsky[0]` / `[...][0]` index errors.

- [ ] **Step 3: Wire the factory**

In `agent/fetchers/base.py`, add the import to the local-import block (after the `SemanticScholarAdapter` import):

```python
    from agent.fetchers.bluesky import BlueskyAdapter
```

Then, in the `kind == "sweep"` branch, **after** the `semantic_scholar` block (right before `return adapters`), add:

```python
        # Change 0013: Bluesky author feeds. `authors` is a config registry of
        # researcher handles; each is polled fail-soft at fetch time.
        bsky_cfg = sources.get("bluesky") or {}
        if bsky_cfg.get("enabled"):
            adapters.append(
                BlueskyAdapter(
                    authors=list(bsky_cfg.get("authors") or []),
                    min_engagement=bsky_cfg.get("min_engagement", 5),
                    **lb,
                )
            )
```

- [ ] **Step 4: Run the factory tests to verify they pass**

Run: `uv run python -m pytest tests/test_build_adapters.py -v`
Expected: PASS (all bluesky tests + the existing factory tests still green).

- [ ] **Step 5: Commit**

```bash
git add agent/fetchers/base.py tests/test_build_adapters.py
git commit -m "feat(0013): wire BlueskyAdapter into build_adapters sweep factory"
```

---

## Task 4: Config registry — `sources.bluesky` with 27 verified handles

**Files:**
- Modify: `config.yml` (the `sources:` block, after the `semantic_scholar` / `s2_queries` entries and before `feeds:`)

**Interfaces:**
- Consumes: the factory block from Task 3, which reads `sources.bluesky.enabled`, `sources.bluesky.min_engagement`, `sources.bluesky.authors`.
- Produces: a `sources.bluesky` config entry. No code; no unit test (config parse-load smoke is covered by the existing suite).

### Step-by-step

- [ ] **Step 1: Add the `bluesky:` entry under `sources:`**

In `config.yml`, insert this block inside `sources:`, immediately after the `semantic_scholar` block's `s2_queries` comment lines and before `feeds:`. All 27 handles were build-verified HTTP 200 from `getProfile` on 2026-08-07:

```yaml
  bluesky:              # Change 0013: curated AI-researcher author feeds
    enabled: true       # public getAuthorFeed, no auth; posts as candidate items
    min_engagement: 5   # likes+reposts floor; posts below are noise-prone
    authors:            # human-curated registry of active AI researchers
      - simonwillison.net
      - karpathy.bsky.social
      - soumith.bsky.social
      - emollick.bsky.social
      - jeremyphoward.bsky.social
      - rasbt.bsky.social
      - giffmana.ai
      - natolambert.bsky.social
      - tomgoldstein.bsky.social
      - jbhuang0604.bsky.social
      - sedielem.bsky.social
      - chelseafinn.bsky.social
      - merve.bsky.social
      - andrewwhite.bsky.social
      - gm8xx8.bsky.social
      - hardmaru.bsky.social
      - tunguz.bsky.social
      - osanseviero.bsky.social
      - danielvanstrien.bsky.social
      - arankomatsuzaki.bsky.social
      - johnowhitaker.bsky.social
      - lateinteraction.bsky.social
      - neelnanda.bsky.social
      - jxmnop.bsky.social
      - srush.bsky.social
      - yoavgo.bsky.social
      - vikhyat.bsky.social
```

- [ ] **Step 2: Verify the config still parses**

Run: `uv run python -c "import yaml; c = yaml.safe_load(open('config.yml')); b = c['sources']['bluesky']; assert b['enabled'] is True; assert b['min_engagement'] == 5; assert len(b['authors']) == 27; assert 'simonwillison.net' in b['authors']; print('config OK', len(b['authors']), 'handles')"`
Expected: prints `config OK 27 handles`.

- [ ] **Step 3: Commit**

```bash
git add config.yml
git commit -m "feat(0013): register 27 verified AI-researcher handles under sources.bluesky"
```

---

## Task 5: Full-suite gate

**Files:** none (verification only)

- [ ] **Step 1: Sync dev extras**

Run: `uv sync --extra dev`
Expected: environment resolved (a bare `pytest` hits a polluting global deepeval plugin — always use `uv run python -m pytest`).

- [ ] **Step 2: Run the full suite**

Run: `uv run python -m pytest`
Expected: PASS. Baseline was ~209 tests; this change adds ~19 new bluesky adapter tests + 6 factory-gating tests, so expect ~234 passing and 0 failures.

- [ ] **Step 3: Commit only if anything was adjusted to make the gate green**

If the gate revealed nothing to fix, no commit is needed. Otherwise:

```bash
git add -A
git commit -m "fix(0013): resolve full-suite gate"
```

---

## Post-Build Verification (handled by parent, NOT part of the plan's code work)

After the build lands, the parent performs a live (un-mocked) verification — **not** a unit test and **not** committed as a test:

- Fetch 2-3 real handles from the registry against the live `getAuthorFeed` endpoint (e.g. `simonwillison.net`, `karpathy.bsky.social`, `rasbt.bsky.social`) and record the resulting `RawItem` counts to confirm the adapter returns plausible non-empty results end-to-end.

This is a smoke check on live data; the plan's own code work is entirely mocked-tests + implementation.

---

## Self-Review

**1. Spec coverage:**
- "Poll `getAuthorFeed` per handle (limit ~25, lookback-filtered via `indexedAt`; skip reposts/replies)" → Task 1 (request shape, lookback, reply skip) + Task 2 (repost skip, lookback bounding).
- "Extract outbound links / arXiv IDs from post facets+embeds" → Task 2 (`_extract_outbound_urls`, `_normalize_arxiv`, facet + embed tests).
- "title = post text (truncated) or embed title when present" → Task 1/2 (`test_embed_title_used_when_text_empty`).
- "url = the outbound link when exactly one exists, else the post's own URL" + arXiv preference → Task 1 impl + Task 2 (`test_arxiv_preferred_when_also_other_links`, `test_post_own_url_fallback_when_multiple_outbound`).
- "engagement = likeCount + repostCount, thresholded by min_engagement" → Task 2 (sum + floor tests).
- "Posts with no outbound link and no arXiv ID are dropped (pure commentary)" → Task 2 (`test_pure_commentary_dropped`).
- "Fail-soft per handle" → Task 1 + Task 2 (`test_per_handle_fail_soft_...`, `test_fail_soft_on_status_error`).
- "config-gated; registered in build_adapters" → Task 3 (factory tests + wiring).
- "source: bluesky/<handle>" → Task 1 (`test_source_is_per_handle`).
- Researcher registry config with ~20-30 handles → Task 4 (27 handles).
- "Live check at build time: fetch 2-3 real handles, record counts" → Post-Build Verification section (parent-owned).
- Out-of-scope (`searchPosts`, custom feeds, Mastodon) → honored: only `getAuthorFeed` is called.

**2. Placeholder scan:** No TBD/TODO/"add error handling"/"similar to Task N" — all steps carry real code, real commands, and expected outcomes.

**3. Type consistency:** `BlueskyAdapter(authors, min_engagement, lookback_days)` is identical across Task 1 (definition), Task 3 (factory call), and Task 4 (config keys). `name = "bluesky"`, per-item `source = "bluesky/<handle>"`, `GET_AUTHOR_FEED_API`, `LOOKBACK_DAYS = 7`, and helper names (`_parse_ts`, `_within_lookback`, `_normalize_arxiv`, `_extract_outbound_urls`, `_post_web_url`) are consistent between the implementation and the tests that reference them.
