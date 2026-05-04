import pytest
from unittest.mock import patch

from market_data.yfinance_client import fetch_stock_data, fetch_multiple, StockMarketData


def test_fetch_stock_data_nvda(mock_yf_ticker):
    with patch("market_data.yfinance_client.yf.Ticker", side_effect=mock_yf_ticker):
        data = fetch_stock_data("NVDA")

    assert isinstance(data, StockMarketData)
    assert data.ticker == "NVDA"
    assert data.company_name == "NVIDIA Corporation"
    assert data.sector == "Technology"
    assert data.current_price == 920.0
    assert data.week_52_high == 974.0
    assert data.week_52_low == 450.0
    assert data.pe_ratio == pytest.approx(65.2)
    assert data.analyst_consensus == "buy"
    assert data.analyst_price_target == pytest.approx(1050.0)
    assert data.analyst_count == 40


def test_price_change_1d(mock_yf_ticker):
    with patch("market_data.yfinance_client.yf.Ticker", side_effect=mock_yf_ticker):
        data = fetch_stock_data("NVDA")
    # (920 - 900) / 900 * 100 ≈ 2.2222
    assert data.price_change_1d_pct == pytest.approx(2.2222, abs=0.01)


def test_momentum_20d_positive(mock_yf_ticker):
    """With a rising price history (850→909), 20-day momentum should be positive."""
    with patch("market_data.yfinance_client.yf.Ticker", side_effect=mock_yf_ticker):
        data = fetch_stock_data("NVDA")
    assert data.momentum_20d_pct > 0


def test_fetch_multiple(mock_yf_ticker):
    with patch("market_data.yfinance_client.yf.Ticker", side_effect=mock_yf_ticker):
        results = fetch_multiple(["NVDA", "MSFT"])

    assert set(results.keys()) == {"NVDA", "MSFT"}
    assert results["MSFT"].current_price == 440.0
    assert results["MSFT"].analyst_count == 52


def test_missing_optional_fields(mock_yf_ticker, mock_market_data_json):
    """Ticker with stripped info should not raise — optional fields default to None/0."""
    from unittest.mock import MagicMock
    import pandas as pd

    sparse_ticker = MagicMock()
    sparse_ticker.info = {"currentPrice": 100.0}
    sparse_ticker.history.return_value = pd.DataFrame()
    sparse_ticker.calendar = {}

    with patch("market_data.yfinance_client.yf.Ticker", return_value=sparse_ticker):
        data = fetch_stock_data("XYZ")

    assert data.ticker == "XYZ"
    assert data.pe_ratio is None
    assert data.market_cap is None
    assert data.analyst_count == 0
    assert data.momentum_20d_pct == 0.0
