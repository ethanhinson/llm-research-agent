import pytest
from unittest.mock import patch, MagicMock

from agent.fetchers.web import WebFetcher

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Blog</title>
    <item>
      <title>Speculative Decoding walkthrough</title>
      <link>https://blog.example.com/speculative-decoding</link>
      <description>A deep dive into speculative decoding.</description>
      <pubDate>Sat, 01 Aug 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


def test_web_fetcher_maps_fields():
    feeds = [{"name": "Test Blog", "url": "https://blog.example.com/feed.xml", "type": "blog"}]
    fetcher = WebFetcher(feeds=feeds)
    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_RSS
        mock_resp.content = SAMPLE_RSS.encode()
        mock_get.return_value = mock_resp
        items = fetcher.fetch()

    assert len(items) == 1
    assert items[0].title == "Speculative Decoding walkthrough"
    assert items[0].url == "https://blog.example.com/speculative-decoding"
    assert items[0].source == "web/Test Blog"
    assert items[0].engagement == 0


def test_web_fetcher_filters_old_entries():
    old_rss = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>T</title>
<item><title>Old post</title><link>https://a.com/old</link>
<description>Old content.</description>
<pubDate>Mon, 01 Jan 2024 10:00:00 +0000</pubDate>
</item></channel></rss>"""
    feeds = [{"name": "T", "url": "https://t.com/feed", "type": "blog"}]
    fetcher = WebFetcher(feeds=feeds, lookback_days=7)
    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.content = old_rss.encode()
        mock_get.return_value = mock_resp
        items = fetcher.fetch()

    assert items == []


def test_web_fetcher_truncates_body():
    long_desc = "x" * 3000
    rss = f"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>T</title>
<item><title>T</title><link>https://a.com</link>
<description>{long_desc}</description>
<pubDate>Sat, 01 Aug 2026 10:00:00 +0000</pubDate>
</item></channel></rss>"""
    feeds = [{"name": "T", "url": "https://t.com/feed", "type": "blog"}]
    fetcher = WebFetcher(feeds=feeds)
    with patch("httpx.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = rss
        mock_resp.content = rss.encode()
        mock_get.return_value = mock_resp
        items = fetcher.fetch()

    assert len(items[0].body) <= 2000
