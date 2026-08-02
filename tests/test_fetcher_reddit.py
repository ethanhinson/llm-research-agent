import pytest
from unittest.mock import MagicMock, patch

from agent.fetchers.reddit import RedditFetcher


def make_submission(title, url, score, selftext=""):
    sub = MagicMock()
    sub.title = title
    sub.url = url
    sub.score = score
    sub.selftext = selftext
    sub.created_utc = 1754000000.0
    return sub


def test_reddit_fetcher_maps_fields():
    fetcher = RedditFetcher(subreddits=["LocalLLaMA"], threshold=100)
    mock_subreddit = MagicMock()
    mock_subreddit.hot.return_value = [
        make_submission("Chain of Draft prompting", "https://arxiv.org/abs/2502.18600", 2300),
    ]
    with patch("praw.Reddit") as mock_praw:
        mock_praw.return_value.subreddit.return_value = mock_subreddit
        fetcher._reddit = mock_praw.return_value
        items = fetcher.fetch()

    assert len(items) == 1
    assert items[0].source == "reddit/LocalLLaMA"
    assert items[0].engagement == 2300
    assert items[0].title == "Chain of Draft prompting"


def test_reddit_fetcher_filters_below_threshold():
    fetcher = RedditFetcher(subreddits=["LocalLLaMA"], threshold=100)
    mock_subreddit = MagicMock()
    mock_subreddit.hot.return_value = [
        make_submission("Low effort post", "https://example.com/low", 5),
    ]
    with patch("praw.Reddit") as mock_praw:
        mock_praw.return_value.subreddit.return_value = mock_subreddit
        fetcher._reddit = mock_praw.return_value
        items = fetcher.fetch()

    assert len(items) == 0
