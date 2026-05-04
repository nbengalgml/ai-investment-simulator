import json
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_portfolio_json() -> dict:
    return json.loads((FIXTURES_DIR / "mock_portfolio.json").read_text())


@pytest.fixture
def mock_market_data_json() -> dict:
    return json.loads((FIXTURES_DIR / "mock_market_data.json").read_text())


@pytest.fixture
def mock_price_history() -> pd.DataFrame:
    dates = pd.date_range(end="2026-05-03", periods=60, freq="B")
    n = len(dates)
    prices = [float(850 + i) for i in range(n)]
    return pd.DataFrame(
        {
            "Open": prices,
            "High": [p + 5 for p in prices],
            "Low": [p - 5 for p in prices],
            "Close": prices,
            "Volume": [1_000_000] * n,
        },
        index=dates,
    )


@pytest.fixture
def mock_yf_ticker(mock_market_data_json, mock_price_history):
    """Factory: returns a mock yfinance Ticker configured for a given ticker symbol."""
    from unittest.mock import MagicMock

    def _make(ticker: str):
        m = MagicMock()
        m.info = mock_market_data_json.get(ticker, {})
        m.history.return_value = mock_price_history
        m.calendar = {}
        return m

    return _make
