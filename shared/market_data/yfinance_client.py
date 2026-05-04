import yfinance as yf
import pandas as pd
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class StockMarketData:
    ticker: str
    company_name: str
    sector: str
    current_price: float
    price_change_1d_pct: float
    momentum_20d_pct: float
    week_52_high: float
    week_52_low: float
    pe_ratio: Optional[float]
    market_cap: Optional[float]
    analyst_consensus: str  # "buy", "strong buy", "hold", "sell", "none"
    analyst_price_target: Optional[float]
    analyst_count: int
    next_earnings_date: Optional[date] = None
    price_history: pd.DataFrame = field(default_factory=pd.DataFrame)


def fetch_stock_data(ticker: str) -> StockMarketData:
    t = yf.Ticker(ticker)
    info = t.info
    hist = t.history(period="3mo")

    current_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)
    prev_close = float(info.get("previousClose") or current_price)
    price_change_1d_pct = ((current_price - prev_close) / prev_close * 100) if prev_close else 0.0

    momentum_20d_pct = 0.0
    if len(hist) >= 20:
        price_20d_ago = float(hist["Close"].iloc[-20])
        if price_20d_ago:
            momentum_20d_pct = (current_price - price_20d_ago) / price_20d_ago * 100

    next_earnings: Optional[date] = None
    try:
        cal = t.calendar
        if isinstance(cal, dict) and "Earnings Date" in cal:
            dates = cal["Earnings Date"]
            if dates:
                d = dates[0]
                next_earnings = d.date() if hasattr(d, "date") else d
    except Exception:
        pass

    target_price = info.get("targetMeanPrice")
    analyst_count = info.get("numberOfAnalystOpinions", 0)

    return StockMarketData(
        ticker=ticker.upper(),
        company_name=info.get("longName", ticker),
        sector=info.get("sector", "Unknown"),
        current_price=current_price,
        price_change_1d_pct=round(price_change_1d_pct, 4),
        momentum_20d_pct=round(momentum_20d_pct, 4),
        week_52_high=float(info.get("fiftyTwoWeekHigh") or 0.0),
        week_52_low=float(info.get("fiftyTwoWeekLow") or 0.0),
        pe_ratio=float(info["trailingPE"]) if info.get("trailingPE") else None,
        market_cap=float(info["marketCap"]) if info.get("marketCap") else None,
        analyst_consensus=info.get("recommendationKey", "none"),
        analyst_price_target=float(target_price) if target_price else None,
        analyst_count=int(analyst_count) if analyst_count else 0,
        next_earnings_date=next_earnings,
        price_history=hist,
    )


def fetch_price_history(ticker: str, period: str = "3mo") -> pd.DataFrame:
    return yf.Ticker(ticker).history(period=period)


def fetch_multiple(tickers: list[str]) -> dict[str, StockMarketData]:
    return {t: fetch_stock_data(t) for t in tickers}
