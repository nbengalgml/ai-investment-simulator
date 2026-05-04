import os
import re
from collections import Counter
from dataclasses import dataclass, field

import praw

from .sentiment import score_text

_SUBREDDITS = ["wallstreetbets", "investing", "stocks"]


@dataclass
class RedditMentionData:
    mention_count: int
    sentiment_score: float
    recent_titles: list[str] = field(default_factory=list)


def fetch_ticker_mentions(
    tickers: list[str],
    post_limit: int = 50,
) -> dict[str, RedditMentionData]:
    """Scan hot posts in finance subreddits for ticker mentions."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {t.upper(): RedditMentionData(0, 0.0) for t in tickers}

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=os.getenv("REDDIT_USER_AGENT", "ai-investment-simulator/1.0"),
        )
    except Exception:
        return {t.upper(): RedditMentionData(0, 0.0) for t in tickers}

    ticker_set = {t.upper() for t in tickers}
    counts: Counter = Counter()
    sentiments: dict[str, list[float]] = {t: [] for t in ticker_set}
    titles: dict[str, list[str]] = {t: [] for t in ticker_set}

    for sub_name in _SUBREDDITS:
        try:
            posts = list(reddit.subreddit(sub_name).hot(limit=post_limit))
        except Exception:
            continue
        for post in posts:
            text = (post.title or "") + " " + (post.selftext or "")
            for ticker in ticker_set:
                if re.search(rf"\b{re.escape(ticker)}\b", text, re.IGNORECASE):
                    counts[ticker] += 1
                    sentiments[ticker].append(score_text(post.title or ""))
                    if len(titles[ticker]) < 3:
                        titles[ticker].append(post.title or "")

    return {
        t: RedditMentionData(
            mention_count=counts[t],
            sentiment_score=round(sum(sentiments[t]) / len(sentiments[t]), 4) if sentiments[t] else 0.0,
            recent_titles=titles[t],
        )
        for t in ticker_set
    }
