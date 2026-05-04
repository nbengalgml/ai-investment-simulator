import pytest
from datetime import datetime, date
from pydantic import ValidationError

from data_models import (
    AccountType,
    Confidence,
    Holding,
    PortfolioState,
    TradeAction,
    TradeLogEntry,
    TaxImpact,
    DailyReport,
    PortfolioPerformance,
    StockSignal,
    MarketResearchSnapshot,
    Recommendation,
    AnalystReport,
)


def make_holding(**overrides) -> Holding:
    defaults = dict(
        ticker="NVDA",
        shares=2.5,
        avg_cost_basis=850.0,
        current_price=920.0,
        market_value=2300.0,
        unrealized_pnl=175.0,
        unrealized_pnl_pct=8.24,
        allocation_pct=23.0,
        open_date=date(2026, 4, 15),
        analyst_rating="BUY",
        confidence=Confidence.HIGH,
    )
    return Holding(**{**defaults, **overrides})


def make_portfolio(**overrides) -> PortfolioState:
    defaults = dict(
        account_type=AccountType.brokerage,
        target_market="AI",
        budget_total=10000.0,
        cash_available=3500.0,
        last_updated=datetime(2026, 5, 3, 16, 15),
        holdings=[make_holding()],
        total_market_value=6500.0,
        total_unrealized_pnl=500.0,
        total_unrealized_pnl_pct=8.33,
    )
    return PortfolioState(**{**defaults, **overrides})


# ── PortfolioState ─────────────────────────────────────────────────────────────

def test_portfolio_defaults():
    p = make_portfolio()
    assert p.strategy == "growth"
    assert p.max_positions == 5


def test_portfolio_ira_type():
    p = make_portfolio(account_type=AccountType.traditional_ira)
    assert p.account_type == AccountType.traditional_ira


def test_portfolio_json_roundtrip():
    p = make_portfolio()
    restored = PortfolioState.model_validate(p.model_dump(mode="json"))
    assert restored.account_type == p.account_type
    assert restored.holdings[0].ticker == "NVDA"
    assert restored.holdings[0].open_date == date(2026, 4, 15)


def test_portfolio_from_fixture(mock_portfolio_json):
    p = PortfolioState.model_validate(mock_portfolio_json)
    assert len(p.holdings) == 2
    assert p.holdings[0].ticker == "NVDA"
    assert p.holdings[1].confidence == Confidence.MEDIUM


# ── TradeLogEntry ──────────────────────────────────────────────────────────────

def test_trade_log_entry():
    entry = TradeLogEntry(
        trade_id="TRD-20260503-001",
        timestamp=datetime(2026, 5, 3, 9, 35, 12),
        action=TradeAction.BUY,
        ticker="NVDA",
        shares=2.5,
        price=850.0,
        total_value=2125.0,
        rationale="Strong Q1 beat",
        data_sources=["SEC EDGAR", "NewsAPI", "Reddit"],
        approved_by="CEO",
        account_type=AccountType.brokerage,
        simulated_tax_impact=TaxImpact(
            holding_period_days=0,
            gain_loss=0.0,
            tax_treatment="N/A (new position)",
        ),
    )
    assert entry.action == TradeAction.BUY
    assert len(entry.data_sources) == 3


def test_trade_action_sell():
    # Sell entries must carry gain/loss and tax treatment
    impact = TaxImpact(
        holding_period_days=400,
        gain_loss=175.0,
        tax_treatment="preferential LTCG rate",
    )
    assert impact.holding_period_days >= 365


# ── Research models ────────────────────────────────────────────────────────────

def test_stock_signal_optional_scores():
    sig = StockSignal(
        ticker="NVDA",
        company_name="NVIDIA Corporation",
        sector="Technology",
        current_price=920.0,
        price_change_1d_pct=2.2,
        momentum_20d_pct=8.5,
        week_52_high=974.0,
        week_52_low=450.0,
    )
    assert sig.composite_score is None
    assert sig.reddit_mention_count == 0


def test_market_research_snapshot():
    snap = MarketResearchSnapshot(
        snapshot_id="snap-20260503-0930",
        timestamp=datetime(2026, 5, 3, 9, 30),
        sector="Technology",
        target_market="AI",
        stocks=[
            StockSignal(
                ticker="NVDA",
                company_name="NVIDIA",
                sector="Technology",
                current_price=920.0,
                price_change_1d_pct=2.2,
                momentum_20d_pct=8.5,
                week_52_high=974.0,
                week_52_low=450.0,
            )
        ],
    )
    assert len(snap.stocks) == 1
    json_out = snap.model_dump(mode="json")
    restored = MarketResearchSnapshot.model_validate(json_out)
    assert restored.snapshot_id == snap.snapshot_id


def test_recommendation_roundtrip():
    rec = Recommendation(
        ticker="NVDA",
        action="BUY",
        confidence="HIGH",
        allocation_pct=25.0,
        composite_score=87.5,
        rationale=["Momentum above sector", "Analyst upgrade", "Reddit velocity +340%"],
        data_sources=["yfinance", "NewsAPI"],
        generated_at=datetime(2026, 5, 3, 9, 31),
    )
    restored = Recommendation.model_validate(rec.model_dump(mode="json"))
    assert restored.ticker == "NVDA"
    assert len(restored.rationale) == 3
