"""
Integration tests for the Market Researcher agent.
All external API calls are mocked — no real network calls.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the agent directory to sys.path so research.py is importable
_AGENT_DIR = Path(__file__).parent.parent.parent / "agents" / "market-researcher"
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

from data_models import MarketResearchSnapshot, StockSignal  # noqa: E402


# ── Algorithmic scoring ───────────────────────────────────────────────────────

def _make_signal(**overrides) -> StockSignal:
    defaults = dict(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        sector="Technology",
        current_price=920.0,
        price_change_1d_pct=2.2,
        momentum_20d_pct=12.5,
        week_52_high=974.0,
        week_52_low=450.0,
        analyst_consensus="buy",
        analyst_price_target=1050.0,
        news_headline_count=5,
        news_sentiment_score=0.6,
        reddit_mention_count=12,
        reddit_sentiment_score=0.5,
    )
    return StockSignal(**{**defaults, **overrides})


def test_score_algorithmic_strong_signals():
    from research import _score_algorithmic

    scored = _score_algorithmic(_make_signal())
    assert scored.momentum_score is not None and scored.momentum_score >= 70
    assert scored.fundamental_score is not None and scored.fundamental_score >= 65
    assert scored.sentiment_score is not None and scored.sentiment_score >= 55
    assert scored.composite_score is not None and scored.composite_score >= 65


def test_score_algorithmic_negative_signals():
    from research import _score_algorithmic

    signal = _make_signal(
        ticker="XYZ",
        momentum_20d_pct=-22.0,
        analyst_consensus="sell",
        analyst_price_target=None,
        news_sentiment_score=-0.8,
        reddit_sentiment_score=-0.6,
        news_headline_count=1,
        reddit_mention_count=1,
    )
    scored = _score_algorithmic(signal)
    assert scored.momentum_score is not None and scored.momentum_score <= 15
    assert scored.fundamental_score is not None and scored.fundamental_score <= 30
    assert scored.composite_score is not None and scored.composite_score <= 35


def test_score_algorithmic_strong_buy_upside():
    from research import _score_algorithmic

    signal = _make_signal(
        analyst_consensus="strong_buy",
        analyst_price_target=1200.0,  # >20% upside from 920
    )
    scored = _score_algorithmic(signal)
    assert scored.fundamental_score is not None and scored.fundamental_score >= 90


def test_composite_formula():
    from research import _score_algorithmic

    signal = _make_signal(
        momentum_20d_pct=12.5,  # → ms=80
        analyst_consensus="buy",  # → fs=75 (no price target adjustment in default)
        analyst_price_target=None,
        news_sentiment_score=0.0,
        reddit_sentiment_score=0.0,
        news_headline_count=0,
        reddit_mention_count=0,
    )
    scored = _score_algorithmic(signal)
    # ss = (50 + 50) / 2 = 50
    expected = round(80 * 0.40 + 75 * 0.35 + 50 * 0.25, 1)
    assert scored.composite_score == pytest.approx(expected, abs=0.5)


# ── Full pipeline (mocked) ────────────────────────────────────────────────────

def _mock_edgar_empty():
    m = MagicMock()
    m.raise_for_status = MagicMock()
    m.json.return_value = {"hits": {"hits": []}}
    return m


def _mock_news_empty():
    m = MagicMock()
    m.get_everything.return_value = {"articles": []}
    return m


@pytest.fixture
def patched_externals(mock_yf_ticker):
    """Patch all external APIs for a clean integration run."""
    with (
        patch("market_data.yfinance_client.yf.Ticker", side_effect=mock_yf_ticker),
        patch("news_feeds.newsapi_client.NewsApiClient", return_value=_mock_news_empty()),
        patch("news_feeds.reddit_client.praw.Reddit") as mock_reddit,
        patch("news_feeds.sec_edgar_client.requests.get", return_value=_mock_edgar_empty()),
    ):
        mock_reddit.return_value.subreddit.return_value.hot.return_value = []
        yield


def test_run_research_cycle_produces_valid_snapshot(patched_externals, tmp_path):
    import storage as _storage
    from research import run_research_cycle

    _storage.DATA_DIR = tmp_path

    snapshot = run_research_cycle(sector="AI", use_claude=False)

    assert isinstance(snapshot, MarketResearchSnapshot)
    assert snapshot.sector == "AI"
    assert len(snapshot.stocks) > 0
    assert "yfinance" in snapshot.data_sources


def test_all_stocks_have_scores(patched_externals, tmp_path):
    import storage as _storage
    from research import run_research_cycle

    _storage.DATA_DIR = tmp_path
    snapshot = run_research_cycle(sector="AI", use_claude=False)

    for stock in snapshot.stocks:
        assert stock.momentum_score is not None, f"{stock.ticker} missing momentum_score"
        assert stock.fundamental_score is not None, f"{stock.ticker} missing fundamental_score"
        assert stock.sentiment_score is not None, f"{stock.ticker} missing sentiment_score"
        assert stock.composite_score is not None, f"{stock.ticker} missing composite_score"
        assert 0 <= stock.composite_score <= 100, f"{stock.ticker} score out of range"


def test_snapshot_persisted_to_disk(patched_externals, tmp_path):
    import storage as _storage
    from research import run_research_cycle

    _storage.DATA_DIR = tmp_path
    snapshot = run_research_cycle(sector="cloud", use_claude=False)

    saved = list((tmp_path / "research" / "market_snapshots").glob("*.json"))
    assert len(saved) == 1

    restored = MarketResearchSnapshot.model_validate(json.loads(saved[0].read_text()))
    assert restored.snapshot_id == snapshot.snapshot_id
    assert restored.sector == "cloud"
    assert len(restored.stocks) == len(snapshot.stocks)


def test_snapshot_schema_roundtrip(patched_externals, tmp_path):
    import storage as _storage
    from research import run_research_cycle

    _storage.DATA_DIR = tmp_path
    snapshot = run_research_cycle(sector="finance", use_claude=False)

    json_data = snapshot.model_dump(mode="json")
    restored = MarketResearchSnapshot.model_validate(json_data)
    assert restored.snapshot_id == snapshot.snapshot_id
    assert all(0 <= s.composite_score <= 100 for s in restored.stocks)


def test_yfinance_failure_skips_ticker(tmp_path):
    """If yfinance fails for a ticker, that ticker is omitted — not a crash."""
    import storage as _storage
    from research import run_research_cycle

    _storage.DATA_DIR = tmp_path

    def failing_ticker(ticker):
        if ticker == "NVDA":
            raise RuntimeError("yfinance timeout")
        m = MagicMock()
        m.info = {"currentPrice": 100.0}
        m.history.return_value = __import__("pandas").DataFrame()
        m.calendar = {}
        return m

    with (
        patch("market_data.yfinance_client.yf.Ticker", side_effect=failing_ticker),
        patch("news_feeds.newsapi_client.NewsApiClient", return_value=_mock_news_empty()),
        patch("news_feeds.reddit_client.praw.Reddit") as mock_reddit,
        patch("news_feeds.sec_edgar_client.requests.get", return_value=_mock_edgar_empty()),
    ):
        mock_reddit.return_value.subreddit.return_value.hot.return_value = []
        snapshot = run_research_cycle(sector="AI", use_claude=False)

    tickers = [s.ticker for s in snapshot.stocks]
    assert "NVDA" not in tickers
    assert len(snapshot.stocks) > 0  # remaining tickers still processed
