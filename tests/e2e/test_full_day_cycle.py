"""
End-to-end test: full trading day cycle.
Simulates: Market Researcher → Analyst → CEO
No real network calls — all external APIs are mocked with fixture data.
Asserts all output files exist, validate against schemas, and have expected content.
"""

import json
import sys
from datetime import datetime, date, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent.parent
_SHARED = _ROOT / "shared"
_RESEARCHER = _ROOT / "agents" / "market-researcher"
_ANALYST = _ROOT / "agents" / "analyst"
_CEO = _ROOT / "agents" / "ceo"
_FIXTURES = Path(__file__).parent.parent / "fixtures"

for _p in [str(_SHARED), str(_RESEARCHER), str(_ANALYST), str(_CEO)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import storage as _storage
from data_models import (
    AnalystReport, DailyReport, MarketResearchSnapshot,
    PortfolioState, AccountType,
)


# ── Fixture helpers ────────────────────────────────────────────────────────────

def _make_price_history() -> pd.DataFrame:
    dates = pd.date_range(end="2026-05-03", periods=60, freq="B")
    n = len(dates)
    prices = [float(850 + i) for i in range(n)]
    return pd.DataFrame(
        {"Open": prices, "High": [p + 5 for p in prices],
         "Low": [p - 5 for p in prices], "Close": prices, "Volume": [1_000_000] * n},
        index=dates,
    )


def _mock_yf_ticker(ticker: str, market_data: dict) -> MagicMock:
    m = MagicMock()
    m.info = market_data.get(ticker, {
        "currentPrice": 100.0, "previousClose": 98.0,
        "longName": f"{ticker} Corp", "sector": "Technology",
        "fiftyTwoWeekHigh": 120.0, "fiftyTwoWeekLow": 60.0,
        "trailingPE": 30.0, "marketCap": 1_000_000_000,
        "recommendationKey": "buy", "targetMeanPrice": 115.0,
        "numberOfAnalystOpinions": 20,
    })
    m.history.return_value = _make_price_history()
    m.calendar = {}
    return m


# ── Full-cycle E2E ────────────────────────────────────────────────────────────

@pytest.fixture
def market_data() -> dict:
    return json.loads((_FIXTURES / "mock_market_data.json").read_text())


@pytest.fixture
def news_data() -> dict:
    return json.loads((_FIXTURES / "mock_news.json").read_text())


@pytest.fixture
def reddit_data() -> dict:
    return json.loads((_FIXTURES / "mock_reddit.json").read_text())


@pytest.fixture
def empty_portfolio() -> PortfolioState:
    return PortfolioState(
        account_type=AccountType.brokerage,
        target_market="AI",
        budget_total=10_000.0,
        cash_available=10_000.0,
        last_updated=datetime.now(timezone.utc),
        holdings=[],
        total_market_value=0.0,
        total_unrealized_pnl=0.0,
        total_unrealized_pnl_pct=0.0,
    )


def _mock_newsapi(news_data: dict):
    m = MagicMock()
    m.get_everything.return_value = news_data
    return m


def _mock_praw(reddit_data: dict, tickers: list[str]):
    mock_reddit = MagicMock()
    subreddit = MagicMock()

    def search_side_effect(query, limit=50, sort="relevance"):
        for ticker in tickers:
            if ticker.lower() in query.lower() or ticker in query:
                posts = reddit_data.get(ticker, {}).get("posts", [])
                return [
                    MagicMock(title=p["title"], score=p["score"], upvote_ratio=p["upvote_ratio"])
                    for p in posts
                ]
        return []

    subreddit.search = search_side_effect
    mock_reddit.subreddit.return_value = subreddit
    return mock_reddit


class TestFullDayCycle:
    """Single-class E2E test to reuse the tmp_path fixture across steps."""

    def test_market_researcher_produces_snapshot(self, tmp_path, market_data, news_data, reddit_data):
        _storage.DATA_DIR = tmp_path
        from research import run_research_cycle

        tickers = ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AMD", "ORCL", "CRM", "PLTR", "SOUN"]

        with patch("yfinance.Ticker", side_effect=lambda t: _mock_yf_ticker(t, market_data)), \
             patch("newsapi.NewsApiClient", return_value=_mock_newsapi(news_data)), \
             patch("praw.Reddit", return_value=_mock_praw(reddit_data, tickers)), \
             patch("requests.get") as mock_req:
            mock_req.return_value = MagicMock(status_code=404)
            snapshot = run_research_cycle("AI", use_claude=False)

        assert isinstance(snapshot, MarketResearchSnapshot)
        assert len(snapshot.stocks) > 0
        assert all(s.composite_score is not None for s in snapshot.stocks)

        saved = list((tmp_path / "research" / "market_snapshots").glob("*.json"))
        assert len(saved) == 1
        loaded = MarketResearchSnapshot.model_validate(json.loads(saved[0].read_text()))
        assert loaded.snapshot_id == snapshot.snapshot_id

    def test_analyst_produces_report(self, tmp_path, market_data, news_data, reddit_data, empty_portfolio):
        _storage.DATA_DIR = tmp_path
        from research import run_research_cycle
        from analysis import run_analysis

        tickers = ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AMD", "ORCL", "CRM", "PLTR", "SOUN"]

        with patch("yfinance.Ticker", side_effect=lambda t: _mock_yf_ticker(t, market_data)), \
             patch("newsapi.NewsApiClient", return_value=_mock_newsapi(news_data)), \
             patch("praw.Reddit", return_value=_mock_praw(reddit_data, tickers)), \
             patch("requests.get") as mock_req:
            mock_req.return_value = MagicMock(status_code=404)
            snapshot = run_research_cycle("AI", use_claude=False)

        report = run_analysis(snapshot, empty_portfolio, use_claude=False)

        assert isinstance(report, AnalystReport)
        assert len(report.recommendations) > 0
        buys = [r for r in report.recommendations if r.action == "BUY"]
        assert len(buys) > 0

        saved = list((tmp_path / "research" / "recommendations").glob("*.json"))
        assert len(saved) == 1
        loaded = AnalystReport.model_validate(json.loads(saved[0].read_text()))
        assert loaded.report_id == report.report_id

    def test_ceo_produces_daily_report(self, tmp_path, market_data, news_data, reddit_data, empty_portfolio):
        _storage.DATA_DIR = tmp_path
        from research import run_research_cycle
        from analysis import run_analysis
        from decisions import run_ceo_cycle

        tickers = ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AMD", "ORCL", "CRM", "PLTR", "SOUN"]

        with patch("yfinance.Ticker", side_effect=lambda t: _mock_yf_ticker(t, market_data)), \
             patch("newsapi.NewsApiClient", return_value=_mock_newsapi(news_data)), \
             patch("praw.Reddit", return_value=_mock_praw(reddit_data, tickers)), \
             patch("requests.get") as mock_req:
            mock_req.return_value = MagicMock(status_code=404)
            snapshot = run_research_cycle("AI", use_claude=False)

        analyst_report = run_analysis(snapshot, empty_portfolio, use_claude=False)
        daily_report, updated_portfolio, trade_log = run_ceo_cycle(
            analyst_report, empty_portfolio, snapshot, use_claude=False
        )

        assert isinstance(daily_report, DailyReport)
        assert len(daily_report.executive_summary) > 0
        assert isinstance(updated_portfolio, PortfolioState)

        # Daily report persisted
        report_files = list((tmp_path / "reports" / "daily").glob("*.json"))
        assert len(report_files) == 1
        loaded = DailyReport.model_validate(json.loads(report_files[0].read_text()))
        assert loaded.report_date == date.today()

        # Portfolio state persisted
        state_file = tmp_path / "portfolio" / "state.json"
        assert state_file.exists()
        ps = PortfolioState.model_validate(json.loads(state_file.read_text()))
        assert isinstance(ps, PortfolioState)

        # Trade log persisted
        log_file = tmp_path / "trades" / "log.json"
        assert log_file.exists()

    def test_full_cycle_all_outputs_exist(self, tmp_path, market_data, news_data, reddit_data, empty_portfolio):
        _storage.DATA_DIR = tmp_path
        from research import run_research_cycle
        from analysis import run_analysis
        from decisions import run_ceo_cycle

        tickers = ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AMD", "ORCL", "CRM", "PLTR", "SOUN"]

        with patch("yfinance.Ticker", side_effect=lambda t: _mock_yf_ticker(t, market_data)), \
             patch("newsapi.NewsApiClient", return_value=_mock_newsapi(news_data)), \
             patch("praw.Reddit", return_value=_mock_praw(reddit_data, tickers)), \
             patch("requests.get") as mock_req:
            mock_req.return_value = MagicMock(status_code=404)
            snapshot = run_research_cycle("AI", use_claude=False)

        analyst_report = run_analysis(snapshot, empty_portfolio, use_claude=False)
        daily_report, updated_portfolio, trade_log = run_ceo_cycle(
            analyst_report, empty_portfolio, snapshot, use_claude=False
        )

        expected_paths = [
            tmp_path / "research" / "market_snapshots",
            tmp_path / "research" / "recommendations",
            tmp_path / "reports" / "daily",
            tmp_path / "portfolio" / "state.json",
            tmp_path / "portfolio" / "history",
            tmp_path / "trades" / "log.json",
        ]
        for p in expected_paths:
            assert p.exists(), f"Expected path missing: {p}"

    def test_full_cycle_report_validation(self, tmp_path, market_data, news_data, reddit_data, empty_portfolio):
        _storage.DATA_DIR = tmp_path
        from research import run_research_cycle
        from analysis import run_analysis
        from decisions import run_ceo_cycle

        tickers = ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AMD", "ORCL", "CRM", "PLTR", "SOUN"]

        with patch("yfinance.Ticker", side_effect=lambda t: _mock_yf_ticker(t, market_data)), \
             patch("newsapi.NewsApiClient", return_value=_mock_newsapi(news_data)), \
             patch("praw.Reddit", return_value=_mock_praw(reddit_data, tickers)), \
             patch("requests.get") as mock_req:
            mock_req.return_value = MagicMock(status_code=404)
            snapshot = run_research_cycle("AI", use_claude=False)

        analyst_report = run_analysis(snapshot, empty_portfolio, use_claude=False)
        daily_report, _, _ = run_ceo_cycle(
            analyst_report, empty_portfolio, snapshot, use_claude=False
        )

        # All recommendation rationales have exactly 3 bullets
        for rec in analyst_report.recommendations:
            assert len(rec.rationale) == 3, f"{rec.ticker} has {len(rec.rationale)} bullets"

        # Daily report has non-empty summary + conditions
        assert len(daily_report.executive_summary) > 0
        assert len(daily_report.market_conditions) > 0

        # Snapshot has all required tickers scored
        ticker_set = {s.ticker for s in snapshot.stocks}
        assert "NVDA" in ticker_set
        assert all(s.composite_score is not None for s in snapshot.stocks)

    def test_portfolio_with_existing_holdings_triggers_exit_check(
        self, tmp_path, market_data, news_data, reddit_data
    ):
        """Verifies stop-loss logic fires in a full cycle when a holding is underwater."""
        _storage.DATA_DIR = tmp_path
        from datetime import date as _date
        from data_models import Holding, Confidence
        from research import run_research_cycle
        from analysis import run_analysis
        from decisions import run_ceo_cycle

        # Build a portfolio with a losing position
        losing_holding = Holding(
            ticker="NVDA",
            shares=2.5,
            avg_cost_basis=1200.0,  # bought high
            current_price=920.0,    # now -23.3% → triggers stop-loss
            market_value=2300.0,
            unrealized_pnl=-700.0,
            unrealized_pnl_pct=-23.3,
            allocation_pct=23.0,
            open_date=_date(2026, 3, 1),
            analyst_rating="HOLD",
            confidence=Confidence.LOW,
        )
        portfolio = PortfolioState(
            account_type=AccountType.brokerage,
            target_market="AI",
            budget_total=10_000.0,
            cash_available=7_700.0,
            last_updated=datetime.now(timezone.utc),
            holdings=[losing_holding],
            total_market_value=2300.0,
            total_unrealized_pnl=-700.0,
            total_unrealized_pnl_pct=-23.3,
        )

        tickers = ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AMD", "ORCL", "CRM", "PLTR", "SOUN"]

        with patch("yfinance.Ticker", side_effect=lambda t: _mock_yf_ticker(t, market_data)), \
             patch("newsapi.NewsApiClient", return_value=_mock_newsapi(news_data)), \
             patch("praw.Reddit", return_value=_mock_praw(reddit_data, tickers)), \
             patch("requests.get") as mock_req:
            mock_req.return_value = MagicMock(status_code=404)
            snapshot = run_research_cycle("AI", use_claude=False)

        analyst_report = run_analysis(snapshot, portfolio, use_claude=False)
        _, updated_portfolio, trade_log = run_ceo_cycle(
            analyst_report, portfolio, snapshot, use_claude=False
        )

        # NVDA should have been sold
        held_tickers = {h.ticker for h in updated_portfolio.holdings}
        assert "NVDA" not in held_tickers
        sell_trades = [t for t in trade_log if t.action.value == "SELL" and t.ticker == "NVDA"]
        assert len(sell_trades) == 1
