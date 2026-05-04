import os
from dataclasses import dataclass
from datetime import datetime, timedelta

from newsapi import NewsApiClient

from .sentiment import score_text


@dataclass
class NewsArticle:
    title: str
    description: str
    source: str
    published_at: str
    url: str
    sentiment: float  # -1 to 1


def fetch_sector_news(
    sector: str,
    tickers: list[str],
    days_back: int = 3,
) -> list[NewsArticle]:
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return []

    client = NewsApiClient(api_key=api_key)
    query_terms = [sector] + tickers[:5]
    query = " OR ".join(f'"{t}"' for t in query_terms)
    from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    try:
        response = client.get_everything(
            q=query,
            language="en",
            sort_by="publishedAt",
            page_size=20,
            from_param=from_date,
        )
    except Exception:
        return []

    articles = []
    for art in response.get("articles", []):
        text = f"{art.get('title', '')} {art.get('description', '') or ''}"
        articles.append(
            NewsArticle(
                title=art.get("title", ""),
                description=art.get("description", "") or "",
                source=art.get("source", {}).get("name", ""),
                published_at=art.get("publishedAt", ""),
                url=art.get("url", ""),
                sentiment=score_text(text),
            )
        )
    return articles


def get_ticker_news_score(ticker: str, articles: list[NewsArticle]) -> tuple[int, float]:
    """Count articles mentioning ticker and return (count, avg_sentiment)."""
    relevant = [
        a for a in articles
        if ticker.upper() in (a.title + " " + a.description).upper()
    ]
    if not relevant:
        return 0, 0.0
    avg = sum(a.sentiment for a in relevant) / len(relevant)
    return len(relevant), round(avg, 4)
