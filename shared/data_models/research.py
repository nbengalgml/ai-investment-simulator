from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class StockSignal(BaseModel):
    ticker: str
    company_name: str
    sector: str

    # Price
    current_price: float
    price_change_1d_pct: float
    momentum_20d_pct: float
    week_52_high: float
    week_52_low: float

    # Fundamentals
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    earnings_surprise_pct: Optional[float] = None

    # Analyst consensus from yfinance
    analyst_consensus: str = "none"
    analyst_price_target: Optional[float] = None
    analyst_count: int = 0

    # Sentiment (populated by Market Researcher in M3)
    reddit_mention_count: int = 0
    reddit_sentiment_score: float = 0.0   # -1 to 1
    news_headline_count: int = 0
    news_sentiment_score: float = 0.0     # -1 to 1

    # SEC
    recent_8k_summary: Optional[str] = None
    next_earnings_date: Optional[date] = None

    # Scores (0–100), computed by Analyst in M4
    momentum_score: Optional[float] = None
    fundamental_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    composite_score: Optional[float] = None


class MarketResearchSnapshot(BaseModel):
    snapshot_id: str
    timestamp: datetime
    sector: str
    target_market: str
    stocks: list[StockSignal]
    data_sources: list[str] = Field(default_factory=list)
    # "bull" | "bear" | "sideways" — computed from sector-wide momentum
    sector_regime: str = "sideways"


class Recommendation(BaseModel):
    ticker: str
    action: str           # BUY | SELL | HOLD
    confidence: str       # HIGH | MEDIUM | LOW
    allocation_pct: float
    composite_score: float
    rationale: list[str]  # 3-bullet rationale
    data_sources: list[str]
    generated_at: datetime


class AnalystReport(BaseModel):
    report_id: str
    generated_at: datetime
    based_on_snapshot_id: str
    recommendations: list[Recommendation]
    total_invested_pct: float
    cash_reserve_pct: float
    strategy_notes: str = ""
