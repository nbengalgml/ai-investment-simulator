"""
/market/price-history — intraday and historical price data for charting.
"""

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

# yfinance period/interval combos per UI range
_RANGE_PARAMS = {
    "1D":  {"period": "1d",  "interval": "5m"},
    "5D":  {"period": "5d",  "interval": "30m"},
    "1M":  {"period": "1mo", "interval": "1d"},
    "1Y":  {"period": "1y",  "interval": "1wk"},
}


def _fetch_price_history(tickers: list[str], range_key: str) -> dict:
    params = _RANGE_PARAMS.get(range_key, _RANGE_PARAMS["1M"])
    try:
        import pandas as pd
        import yfinance as yf

        raw = yf.download(
            tickers,
            period=params["period"],
            interval=params["interval"],
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if raw.empty:
            return {}

        # Normalise to {ticker: [{t, p}, ...]}
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            close = raw[["Close"]].rename(columns={"Close": tickers[0]})

        series: dict[str, list] = {}
        for ticker in tickers:
            if ticker not in close.columns:
                continue
            col = close[ticker].dropna()
            if col.empty:
                continue
            series[ticker] = [
                {"t": str(idx), "p": round(float(val), 4)}
                for idx, val in col.items()
            ]
        return series
    except Exception as exc:
        logger.warning("price_history fetch failed: %s", exc)
        return {}


@router.get("/price-history")
async def price_history(tickers: str, range: str = "1M") -> dict:
    """
    Returns OHLC close price series for comma-separated tickers.
    range: 1D | 5D | 1M | 1Y
    Response: { range, series: { TICKER: [{t, p}, ...] } }
    """
    if range not in _RANGE_PARAMS:
        raise HTTPException(status_code=400, detail=f"Invalid range '{range}'. Use: {list(_RANGE_PARAMS)}")
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="No tickers provided")
    if len(ticker_list) > 10:
        raise HTTPException(status_code=400, detail="Max 10 tickers per request")

    series = await asyncio.to_thread(_fetch_price_history, ticker_list, range)
    return {"range": range, "series": series}
