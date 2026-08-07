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
