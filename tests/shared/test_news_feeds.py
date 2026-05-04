import pytest
from unittest.mock import patch, MagicMock

from news_feeds.sentiment import score_text
from news_feeds.newsapi_client import NewsArticle, fetch_sector_news, get_ticker_news_score
from news_feeds.reddit_client import fetch_ticker_mentions
from news_feeds.sec_edgar_client import fetch_recent_8k


# ── Sentiment ──────────────────────────────────────────────────────────────────

def test_sentiment_positive():
    assert score_text("NVDA surges on strong earnings beat record profits") > 0


def test_sentiment_negative():
    assert score_text("Stock falls on earnings miss weak guidance cut layoffs") < 0


def test_sentiment_neutral():
    assert score_text("NVIDIA announces Q2 earnings date for investors") == 0.0


def test_sentiment_empty():
    assert score_text("") == 0.0


def test_sentiment_mixed_leans_positive():
    # 3 positive words, 1 negative → positive result
    score = score_text("strong record beat but disappointing")
    assert score > 0


# ── NewsAPI ───────────────────────────────────────────────────────────────────

def test_newsapi_returns_articles(monkeypatch):
    monkeypatch.setenv("NEWSAPI_KEY", "test_key")
    mock_client = MagicMock()
    mock_client.get_everything.return_value = {
        "articles": [
            {
                "title": "NVDA surges on AI demand",
                "description": "Beat estimates by 15%",
                "source": {"name": "Reuters"},
                "publishedAt": "2026-05-03T10:00:00Z",
                "url": "https://example.com/1",
            }
        ]
    }
    with patch("news_feeds.newsapi_client.NewsApiClient", return_value=mock_client):
        articles = fetch_sector_news("AI", ["NVDA", "MSFT"])

    assert len(articles) == 1
    assert articles[0].title == "NVDA surges on AI demand"
    assert articles[0].sentiment > 0


def test_newsapi_no_key_returns_empty(monkeypatch):
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    assert fetch_sector_news("AI", ["NVDA"]) == []


def test_newsapi_exception_returns_empty(monkeypatch):
    monkeypatch.setenv("NEWSAPI_KEY", "test_key")
    mock_client = MagicMock()
    mock_client.get_everything.side_effect = Exception("Rate limited")
    with patch("news_feeds.newsapi_client.NewsApiClient", return_value=mock_client):
        assert fetch_sector_news("AI", ["NVDA"]) == []


def test_get_ticker_news_score_counts_and_averages():
    articles = [
        NewsArticle("NVDA beats estimates", "Record revenue", "Reuters", "2026-05-03", "http://x", 0.8),
        NewsArticle("MSFT quarterly results", "In line", "Bloomberg", "2026-05-03", "http://y", 0.1),
        NewsArticle("NVDA AI chip demand surges", "Strong growth", "CNBC", "2026-05-03", "http://z", 0.6),
    ]
    count, sentiment = get_ticker_news_score("NVDA", articles)
    assert count == 2
    assert sentiment == pytest.approx(0.7, abs=0.01)


def test_get_ticker_news_score_no_match():
    articles = [NewsArticle("AAPL revenue", "", "Reuters", "", "", 0.5)]
    count, sentiment = get_ticker_news_score("NVDA", articles)
    assert count == 0
    assert sentiment == 0.0


# ── Reddit ────────────────────────────────────────────────────────────────────

def test_reddit_no_credentials_returns_zeros(monkeypatch):
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    result = fetch_ticker_mentions(["NVDA", "MSFT"])
    assert result["NVDA"].mention_count == 0
    assert result["MSFT"].mention_count == 0


def test_reddit_mention_counting(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "fake_id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "fake_secret")

    post1 = MagicMock(title="NVDA is the future of AI computing", selftext="Bought more NVDA")
    post2 = MagicMock(title="MSFT Azure winning cloud wars", selftext="")
    post3 = MagicMock(title="General market discussion", selftext="No specific tickers")

    mock_reddit = MagicMock()
    mock_reddit.subreddit.return_value.hot.return_value = [post1, post2, post3]

    with patch("news_feeds.reddit_client.praw.Reddit", return_value=mock_reddit):
        result = fetch_ticker_mentions(["NVDA", "MSFT"])

    assert result["NVDA"].mention_count >= 1
    assert result["MSFT"].mention_count >= 1


# ── SEC EDGAR ─────────────────────────────────────────────────────────────────

def test_sec_edgar_no_filings():
    with patch("news_feeds.sec_edgar_client.requests.get") as mock_get:
        mock_get.return_value.raise_for_status = MagicMock()
        mock_get.return_value.json.return_value = {"hits": {"hits": []}}
        assert fetch_recent_8k("NVDA") is None


def test_sec_edgar_returns_filing():
    with patch("news_feeds.sec_edgar_client.requests.get") as mock_get:
        mock_get.return_value.raise_for_status = MagicMock()
        mock_get.return_value.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "form_type": "8-K",
                            "file_date": "2026-04-29",
                            "entity_name": "NVIDIA CORP",
                        }
                    }
                ]
            }
        }
        result = fetch_recent_8k("NVDA")

    assert result is not None
    assert result.ticker == "NVDA"
    assert result.form_type == "8-K"
    assert result.filed_date == "2026-04-29"
    assert result.entity_name == "NVIDIA CORP"


def test_sec_edgar_network_error_returns_none():
    with patch("news_feeds.sec_edgar_client.requests.get", side_effect=Exception("timeout")):
        assert fetch_recent_8k("NVDA") is None
