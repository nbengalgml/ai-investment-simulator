"""
Tests for the CEO agent decision pipeline.
All inputs are constructed in-memory — no disk I/O except via tmp_path.
"""

import sys
from datetime import datetime, date, timezone
from pathlib import Path

import pytest

_CEO = Path(__file__).parent.parent.parent / "agents" / "ceo"
_SHARED = Path(__file__).parent.parent.parent / "shared"
for _p in [str(_CEO), str(_SHARED)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from data_models import (
    AccountType, AnalystReport, Confidence, DailyReport, Holding,
    MarketResearchSnapshot, PortfolioState, Recommendation, TradeLogEntry,
)
from decisions import (
    MAX_POSITIONS, MAX_SINGLE_PCT, MIN_CASH_PCT, MIN_DATA_SOURCES_FOR_BUY,
    approve_recommendations, apply_trades, compute_day_pnl,
    generate_daily_report, run_ceo_cycle, update_memory,
)


# ── Factories ──────────────────────────────────────────────────────────────────

def _rec(ticker="NVDA", action="BUY", allocation_pct=20.0, score=80.0, sources=None) -> Recommendation:
    return Recommendation(
        ticker=ticker,
        action=action,
        confidence="HIGH",
        allocation_pct=allocation_pct,
        composite_score=score,
        rationale=["r1", "r2", "r3"],
        data_sources=sources or ["yfinance", "newsapi"],
        generated_at=datetime.now(timezone.utc),
    )


def _holding(ticker="NVDA", avg_cost=850.0, current_price=920.0, allocation_pct=20.0, open_date=None) -> Holding:
    od = open_date or date(2026, 1, 1)
    return Holding(
        ticker=ticker,
        shares=2.5,
        avg_cost_basis=avg_cost,
        current_price=current_price,
        market_value=current_price * 2.5,
        unrealized_pnl=(current_price - avg_cost) * 2.5,
        unrealized_pnl_pct=(current_price - avg_cost) / avg_cost * 100,
        allocation_pct=allocation_pct,
        open_date=od,
        analyst_rating="BUY",
        confidence=Confidence.HIGH,
    )


def _signal_dict(ticker="NVDA", price=100.0, change_1d=1.5, momentum=8.0, score=75.0):
    from data_models import StockSignal
    return StockSignal(
        ticker=ticker, company_name=f"{ticker} Corp", sector="Technology",
        current_price=price, price_change_1d_pct=change_1d,
        momentum_20d_pct=momentum, week_52_high=120.0, week_52_low=60.0,
        analyst_consensus="buy", news_headline_count=3, news_sentiment_score=0.4,
        reddit_mention_count=5, reddit_sentiment_score=0.3,
        composite_score=score, momentum_score=70.0, fundamental_score=75.0, sentiment_score=65.0,
    )


def _snapshot(tickers=None) -> MarketResearchSnapshot:
    tickers = tickers or ["NVDA", "MSFT", "GOOGL", "META", "AMZN"]
    return MarketResearchSnapshot(
        snapshot_id="snap-ceo-test",
        timestamp=datetime.now(timezone.utc),
        sector="AI",
        target_market="AI",
        stocks=[_signal_dict(t, price=100 + i * 10) for i, t in enumerate(tickers)],
        data_sources=["yfinance", "newsapi"],
    )


def _portfolio(holdings=None, budget=10_000.0) -> PortfolioState:
    h = holdings or []
    invested = sum(x.allocation_pct for x in h)
    return PortfolioState(
        account_type=AccountType.brokerage,
        target_market="AI",
        budget_total=budget,
        cash_available=budget * (100 - invested) / 100,
        last_updated=datetime.now(timezone.utc),
        holdings=h,
        total_market_value=budget * invested / 100,
        total_unrealized_pnl=0.0,
        total_unrealized_pnl_pct=0.0,
    )


def _report(recs=None) -> AnalystReport:
    return AnalystReport(
        report_id="rpt-test",
        generated_at=datetime.now(timezone.utc),
        based_on_snapshot_id="snap-ceo-test",
        recommendations=recs or [_rec()],
        total_invested_pct=20.0,
        cash_reserve_pct=80.0,
    )


# ── approve_recommendations ────────────────────────────────────────────────────

def test_approve_sell_always_passes():
    recs = [_rec("NVDA", action="SELL", sources=["yfinance"])]
    approved, rejected = approve_recommendations(_report(recs), _portfolio())
    assert len(approved) == 1 and approved[0].ticker == "NVDA"
    assert rejected == []


def test_approve_hold_always_passes():
    recs = [_rec("NVDA", action="HOLD", sources=["yfinance"])]
    approved, rejected = approve_recommendations(_report(recs), _portfolio())
    assert len(approved) == 1
    assert rejected == []


def test_approve_buy_requires_min_sources():
    recs = [_rec("NVDA", action="BUY", sources=["yfinance"])]  # only 1 source
    approved, rejected = approve_recommendations(_report(recs), _portfolio())
    assert any(r.ticker == "NVDA" for r in rejected)
    assert not any(r.ticker == "NVDA" and r.action == "BUY" for r in approved)


def test_approve_buy_rejected_when_exceeds_max_pct():
    recs = [_rec("NVDA", action="BUY", allocation_pct=MAX_SINGLE_PCT + 1)]
    approved, rejected = approve_recommendations(_report(recs), _portfolio())
    assert any(r.ticker == "NVDA" for r in rejected)


def test_approve_buy_rejected_when_portfolio_full():
    holdings = [_holding(f"T{i}", allocation_pct=15.0) for i in range(MAX_POSITIONS)]
    recs = [_rec("NEW", action="BUY")]
    approved, rejected = approve_recommendations(_report(recs), _portfolio(holdings=holdings))
    assert any(r.ticker == "NEW" for r in rejected)


def test_approve_buy_counts_pending_buys():
    recs = [
        _rec(f"T{i}", action="BUY") for i in range(MAX_POSITIONS + 1)
    ]
    portfolio = _portfolio()
    approved, rejected = approve_recommendations(_report(recs), portfolio)
    buy_approved = [r for r in approved if r.action == "BUY"]
    assert len(buy_approved) == MAX_POSITIONS


def test_approve_sell_frees_slot_for_buy():
    holdings = [_holding(f"T{i}", allocation_pct=15.0) for i in range(MAX_POSITIONS)]
    recs = [
        _rec("T0", action="SELL"),
        _rec("NEW", action="BUY"),
    ]
    approved, rejected = approve_recommendations(_report(recs), _portfolio(holdings=holdings))
    buy_approved = [r for r in approved if r.action == "BUY"]
    assert any(r.ticker == "NEW" for r in buy_approved)


# ── apply_trades ───────────────────────────────────────────────────────────────

def test_apply_buy_creates_holding():
    recs = [_rec("NVDA", action="BUY", allocation_pct=20.0)]
    portfolio = _portfolio()
    signal_map = {"NVDA": _signal_dict("NVDA", price=100.0)}
    updated, trades = apply_trades(recs, portfolio, signal_map, date.today())
    assert any(h.ticker == "NVDA" for h in updated.holdings)
    assert len(trades) == 1
    assert trades[0].action.value == "BUY"


def test_apply_buy_computes_shares_correctly():
    recs = [_rec("NVDA", action="BUY", allocation_pct=10.0)]
    portfolio = _portfolio(budget=10_000.0)
    signal_map = {"NVDA": _signal_dict("NVDA", price=100.0)}
    updated, trades = apply_trades(recs, portfolio, signal_map, date.today())
    # 10% of $10,000 = $1,000 / $100 = 10 shares
    assert trades[0].shares == pytest.approx(10.0, rel=0.01)


def test_apply_sell_removes_holding():
    holdings = [_holding("NVDA", avg_cost=80.0, current_price=100.0, allocation_pct=20.0)]
    recs = [_rec("NVDA", action="SELL")]
    portfolio = _portfolio(holdings=holdings)
    signal_map = {"NVDA": _signal_dict("NVDA", price=100.0)}
    updated, trades = apply_trades(recs, portfolio, signal_map, date.today())
    assert all(h.ticker != "NVDA" for h in updated.holdings)
    assert trades[0].action.value == "SELL"


def test_apply_sell_records_gain_loss():
    holdings = [_holding("NVDA", avg_cost=80.0, current_price=100.0, allocation_pct=20.0)]
    recs = [_rec("NVDA", action="SELL")]
    portfolio = _portfolio(holdings=holdings)
    signal_map = {"NVDA": _signal_dict("NVDA", price=100.0)}
    _, trades = apply_trades(recs, portfolio, signal_map, date.today())
    # gain = (100 - 80) * 2.5 = 50
    assert trades[0].simulated_tax_impact.gain_loss == pytest.approx(50.0, rel=0.01)


def test_apply_sell_tax_short_term():
    od = date(2026, 4, 1)  # opened recently — short-term
    holdings = [_holding("NVDA", open_date=od)]
    recs = [_rec("NVDA", action="SELL")]
    portfolio = _portfolio(holdings=holdings)
    signal_map = {"NVDA": _signal_dict("NVDA", price=100.0)}
    _, trades = apply_trades(recs, portfolio, signal_map, date(2026, 5, 1))
    assert "short-term" in trades[0].simulated_tax_impact.tax_treatment


def test_apply_sell_tax_long_term():
    od = date(2024, 1, 1)  # > 365 days ago
    holdings = [_holding("NVDA", open_date=od)]
    recs = [_rec("NVDA", action="SELL")]
    portfolio = _portfolio(holdings=holdings)
    signal_map = {"NVDA": _signal_dict("NVDA", price=100.0)}
    _, trades = apply_trades(recs, portfolio, signal_map, date(2026, 5, 1))
    assert "LTCG" in trades[0].simulated_tax_impact.tax_treatment


def test_apply_sell_tax_ira():
    portfolio = _portfolio(holdings=[_holding("NVDA")])
    portfolio = portfolio.model_copy(update={"account_type": AccountType.traditional_ira})
    recs = [_rec("NVDA", action="SELL")]
    signal_map = {"NVDA": _signal_dict("NVDA", price=100.0)}
    _, trades = apply_trades(recs, portfolio, signal_map, date.today())
    assert "IRA" in trades[0].simulated_tax_impact.tax_treatment


def test_apply_hold_produces_no_trade():
    holdings = [_holding("NVDA")]
    recs = [_rec("NVDA", action="HOLD")]
    portfolio = _portfolio(holdings=holdings)
    _, trades = apply_trades(recs, portfolio, {}, date.today())
    assert trades == []


def test_apply_sell_then_buy_order():
    """SELLs should be processed before BUYs to free cash."""
    holdings = [_holding("NVDA", avg_cost=80.0, current_price=100.0, allocation_pct=80.0)]
    recs = [
        _rec("NVDA", action="SELL"),
        _rec("MSFT", action="BUY", allocation_pct=15.0),
    ]
    portfolio = _portfolio(holdings=holdings)
    signal_map = {
        "NVDA": _signal_dict("NVDA", price=100.0),
        "MSFT": _signal_dict("MSFT", price=200.0),
    }
    updated, trades = apply_trades(recs, portfolio, signal_map, date.today())
    actions = [t.action.value for t in trades]
    assert actions.index("SELL") < actions.index("BUY")
    assert any(h.ticker == "MSFT" for h in updated.holdings)


# ── compute_day_pnl ────────────────────────────────────────────────────────────

def test_compute_day_pnl_zero_when_no_holdings():
    portfolio = _portfolio()
    signal_map = {"NVDA": _signal_dict("NVDA")}
    pnl, pct = compute_day_pnl(portfolio, signal_map)
    assert pnl == 0.0


def test_compute_day_pnl_positive():
    holdings = [_holding("NVDA", current_price=100.0, allocation_pct=20.0)]
    portfolio = _portfolio(holdings=holdings)
    portfolio = portfolio.model_copy(update={
        "total_market_value": 100.0 * 2.5,
        "holdings": holdings,
    })
    signal_map = {"NVDA": _signal_dict("NVDA", change_1d=2.0)}
    pnl, pct = compute_day_pnl(portfolio, signal_map)
    assert pnl > 0


def test_compute_day_pnl_missing_signal():
    holdings = [_holding("NVDA")]
    portfolio = _portfolio(holdings=holdings)
    pnl, pct = compute_day_pnl(portfolio, {})  # no signal_map entry
    assert pnl == 0.0


# ── generate_daily_report ──────────────────────────────────────────────────────

def test_generate_report_structure():
    snapshot = _snapshot()
    portfolio = _portfolio()
    report = generate_daily_report(
        approved=[_rec("NVDA", action="BUY")],
        rejected=[],
        portfolio=portfolio,
        snapshot=snapshot,
        trade_log=[],
        day_pnl=50.0,
        day_pnl_pct=0.5,
        use_claude=False,
    )
    assert isinstance(report, DailyReport)
    assert len(report.executive_summary) > 0
    assert len(report.market_conditions) > 0
    assert report.portfolio_performance.day_pnl == 50.0


def test_generate_report_top_signals_sorted():
    snapshot = _snapshot(tickers=["NVDA", "MSFT", "GOOGL", "META", "AMZN"])
    report = generate_daily_report(
        approved=[], rejected=[], portfolio=_portfolio(),
        snapshot=snapshot, trade_log=[],
        day_pnl=0.0, day_pnl_pct=0.0, use_claude=False,
    )
    scores = [s["composite_score"] for s in report.top_signals]
    assert scores == sorted(scores, reverse=True)


def test_generate_report_watchlist_excludes_held():
    holdings = [_holding("NVDA")]
    portfolio = _portfolio(holdings=holdings)
    snapshot = _snapshot(tickers=["NVDA", "MSFT", "GOOGL"])
    report = generate_daily_report(
        approved=[], rejected=[], portfolio=portfolio,
        snapshot=snapshot, trade_log=[],
        day_pnl=0.0, day_pnl_pct=0.0, use_claude=False,
    )
    assert "NVDA" not in report.next_day_watchlist


def test_generate_report_includes_rejected():
    rejected = [_rec("AMD", action="BUY")]
    report = generate_daily_report(
        approved=[], rejected=rejected, portfolio=_portfolio(),
        snapshot=_snapshot(), trade_log=[],
        day_pnl=0.0, day_pnl_pct=0.0, use_claude=False,
    )
    assert any(r["ticker"] == "AMD" for r in report.recommendations_pending)


# ── update_memory ──────────────────────────────────────────────────────────────

def test_update_memory_creates_file(tmp_path):
    memory_path = tmp_path / "MEMORY.md"
    update_memory(memory_path, date(2026, 5, 3), [], [], _portfolio(), 100.0)
    assert memory_path.exists()
    content = memory_path.read_text()
    assert "2026-05-03" in content


def test_update_memory_appends_entries(tmp_path):
    memory_path = tmp_path / "MEMORY.md"
    update_memory(memory_path, date(2026, 5, 3), [], [], _portfolio(), 50.0)
    update_memory(memory_path, date(2026, 5, 4), [], [], _portfolio(), 75.0)
    content = memory_path.read_text()
    assert "2026-05-03" in content
    assert "2026-05-04" in content


def test_update_memory_records_buys_and_sells(tmp_path):
    memory_path = tmp_path / "MEMORY.md"
    approved = [_rec("NVDA", action="BUY"), _rec("MSFT", action="SELL")]
    update_memory(memory_path, date(2026, 5, 3), approved, [], _portfolio(), 0.0)
    content = memory_path.read_text()
    assert "NVDA" in content
    assert "MSFT" in content


# ── run_ceo_cycle (full pipeline) ──────────────────────────────────────────────

def test_run_ceo_cycle_produces_all_outputs(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    portfolio = _portfolio()
    report_in = _report(recs=[_rec("NVDA", action="BUY", allocation_pct=20.0)])
    daily_report, updated_portfolio, trade_log = run_ceo_cycle(
        report_in, portfolio, snapshot, use_claude=False
    )

    assert isinstance(daily_report, DailyReport)
    assert isinstance(updated_portfolio, PortfolioState)
    assert isinstance(trade_log, list)


def test_run_ceo_cycle_persists_portfolio(tmp_path):
    import json, storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    portfolio = _portfolio()
    report_in = _report(recs=[_rec("NVDA", action="BUY", allocation_pct=20.0)])
    run_ceo_cycle(report_in, portfolio, snapshot, use_claude=False)

    state_file = tmp_path / "portfolio" / "state.json"
    assert state_file.exists()
    loaded = json.loads(state_file.read_text())
    ps = PortfolioState.model_validate(loaded)
    assert isinstance(ps, PortfolioState)


def test_run_ceo_cycle_persists_daily_report(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    portfolio = _portfolio()
    report_in = _report(recs=[_rec("NVDA", action="BUY", allocation_pct=20.0)])
    run_ceo_cycle(report_in, portfolio, snapshot, use_claude=False)

    reports = list((tmp_path / "reports" / "daily").glob("*.json"))
    assert len(reports) == 1


def test_run_ceo_cycle_persists_history(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    run_ceo_cycle(_report(), _portfolio(), snapshot, use_claude=False)

    history = list((tmp_path / "portfolio" / "history").glob("*.json"))
    assert len(history) == 1


def test_run_ceo_cycle_persists_trade_log(tmp_path):
    import json, storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    portfolio = _portfolio()
    report_in = _report(recs=[_rec("NVDA", action="BUY", allocation_pct=20.0)])
    run_ceo_cycle(report_in, portfolio, snapshot, use_claude=False)

    log_file = tmp_path / "trades" / "log.json"
    assert log_file.exists()
    entries = json.loads(log_file.read_text())
    assert len(entries) >= 1


def test_run_ceo_cycle_rejects_underfunded_buy(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    # Only 1 data source — should be rejected
    recs = [_rec("NVDA", action="BUY", sources=["yfinance"])]
    report_in = _report(recs=recs)
    snapshot = _snapshot()
    daily_report, updated_portfolio, trade_log = run_ceo_cycle(
        report_in, _portfolio(), snapshot, use_claude=False
    )

    assert trade_log == []  # rejected, so no trades
    assert any(r["ticker"] == "NVDA" for r in daily_report.recommendations_pending)


def test_run_ceo_cycle_stop_loss_sell(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    holdings = [_holding("NVDA", avg_cost=1000.0, current_price=780.0, allocation_pct=20.0)]
    recs = [_rec("NVDA", action="SELL")]  # from analyst stop-loss
    report_in = _report(recs=recs)
    snapshot = _snapshot()
    portfolio = _portfolio(holdings=holdings)

    _, updated_portfolio, trade_log = run_ceo_cycle(
        report_in, portfolio, snapshot, use_claude=False
    )

    assert all(h.ticker != "NVDA" for h in updated_portfolio.holdings)
    assert any(t.action.value == "SELL" and t.ticker == "NVDA" for t in trade_log)


def test_run_ceo_cycle_no_buys_when_full(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    holdings = [_holding(f"T{i}", allocation_pct=15.0) for i in range(MAX_POSITIONS)]
    recs = [_rec("NEW", action="BUY")]
    report_in = _report(recs=recs)
    snapshot = _snapshot()
    portfolio = _portfolio(holdings=holdings)

    _, updated_portfolio, trade_log = run_ceo_cycle(
        report_in, portfolio, snapshot, use_claude=False
    )

    buys = [t for t in trade_log if t.action.value == "BUY"]
    assert len(buys) == 0
