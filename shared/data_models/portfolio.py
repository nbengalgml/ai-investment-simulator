from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Any
from enum import Enum


class AccountType(str, Enum):
    brokerage = "brokerage"
    traditional_ira = "traditional_ira"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Holding(BaseModel):
    ticker: str
    shares: float
    avg_cost_basis: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    allocation_pct: float
    open_date: date
    analyst_rating: str
    confidence: Confidence


class PortfolioState(BaseModel):
    account_type: AccountType
    target_market: str
    budget_total: float
    cash_available: float
    last_updated: datetime
    holdings: list[Holding] = Field(default_factory=list)
    total_market_value: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    strategy: str = "growth"
    max_positions: int = 5


class TaxImpact(BaseModel):
    holding_period_days: int
    gain_loss: float
    tax_treatment: str


class TradeLogEntry(BaseModel):
    trade_id: str
    timestamp: datetime
    action: TradeAction
    ticker: str
    shares: float
    price: float
    total_value: float
    rationale: str
    data_sources: list[str]
    approved_by: str
    account_type: AccountType
    simulated_tax_impact: TaxImpact


class PortfolioPerformance(BaseModel):
    day_pnl: float
    day_pnl_pct: float
    total_unrealized_pnl: float


class DailyReport(BaseModel):
    report_date: date
    generated_at: datetime
    executive_summary: str
    market_conditions: str
    portfolio_performance: PortfolioPerformance
    actions_taken: list[dict[str, Any]] = Field(default_factory=list)
    top_signals: list[dict[str, Any]] = Field(default_factory=list)
    recommendations_pending: list[dict[str, Any]] = Field(default_factory=list)
    next_day_watchlist: list[str] = Field(default_factory=list)
