import os
import datetime

import praw
from dotenv import load_dotenv

from agent.models import RawItem

load_dotenv()


class RedditFetcher:
    def __init__(self, subreddits: list[str], threshold: int = 100):
        self.subreddits = subreddits
        self.threshold = threshold
        self._reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            user_agent=os.getenv("REDDIT_USER_AGENT", "llm-research-agent/0.1"),
        )

    def fetch(self) -> list[RawItem]:
        items = []
        for sub_name in self.subreddits:
            subreddit = self._reddit.subreddit(sub_name)
            for post in subreddit.hot(limit=100):
                if post.score < self.threshold:
                    continue
                ts = datetime.datetime.fromtimestamp(post.created_utc, tz=datetime.timezone.utc).isoformat()
                items.append(
                    RawItem(
                        title=post.title,
                        body=post.selftext[:2000] if post.selftext else "",
                        url=post.url,
                        source=f"reddit/{sub_name}",
                        engagement=post.score,
                        timestamp=ts,
                    )
                )
        return items
