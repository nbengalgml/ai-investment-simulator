"""
Tests for the Analyst agent analysis pipeline.
All inputs are constructed in-memory — no disk I/O except via tmp_path.
"""

import sys
from datetime import datetime, date, timezone
from pathlib import Path

import pytest

_ANALYST = Path(__file__).parent.parent.parent / "agents" / "analyst"
_SHARED = Path(__file__).parent.parent.parent / "shared"
for _p in [str(_ANALYST), str(_SHARED)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from data_models import (
    AccountType, AnalystReport, Confidence, Holding, MarketResearchSnapshot,
    PortfolioState, Recommendation, StockSignal,
)
from analysis import (
    MAX_POSITIONS, MAX_SINGLE_PCT, MIN_CASH_PCT,
    STOP_LOSS_PCT, REVIEW_ZONE_PCT, REBALANCE_TRIGGER_PCT, REBALANCE_TARGET_PCT,
    check_exit_signals, rank_candidates, compute_allocations, run_analysis,
    _confidence, _sector_avg_momentum,
)


# ── Factories ──────────────────────────────────────────────────────────────────

def _holding(ticker="NVDA", avg_cost=850.0, current_price=920.0, allocation_pct=23.0) -> Holding:
    return Holding(
        ticker=ticker,
        shares=2.5,
        avg_cost_basis=avg_cost,
        current_price=current_price,
        market_value=current_price * 2.5,
        unrealized_pnl=(current_price - avg_cost) * 2.5,
        unrealized_pnl_pct=(current_price - avg_cost) / avg_cost * 100,
        allocation_pct=allocation_pct,
        open_date=date(2026, 4, 1),
        analyst_rating="BUY",
        confidence=Confidence.HIGH,
    )


def _signal(ticker="AAPL", score=75.0, momentum=8.0, consensus="buy") -> StockSignal:
    return StockSignal(
        ticker=ticker,
        company_name=f"{ticker} Corp",
        sector="Technology",
        current_price=100.0,
        price_change_1d_pct=1.0,
        momentum_20d_pct=momentum,
        week_52_high=120.0,
        week_52_low=70.0,
        analyst_consensus=consensus,
        analyst_price_target=115.0,
        news_headline_count=3,
        news_sentiment_score=0.4,
        reddit_mention_count=5,
        reddit_sentiment_score=0.3,
        composite_score=score,
        momentum_score=70.0,
        fundamental_score=75.0,
        sentiment_score=65.0,
    )


def _snapshot(stocks=None, snapshot_id="snap-test") -> MarketResearchSnapshot:
    return MarketResearchSnapshot(
        snapshot_id=snapshot_id,
        timestamp=datetime.now(timezone.utc),
        sector="AI",
        target_market="AI",
        stocks=stocks or [_signal(t, 80 - i * 5) for i, t in enumerate(
            ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "AMD", "ORCL", "CRM", "PLTR", "SOUN"]
        )],
        data_sources=["yfinance"],
    )


def _portfolio(holdings=None, budget=10_000.0, cash_pct=100.0) -> PortfolioState:
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


# ── _sector_avg_momentum ──────────────────────────────────────────────────────

def test_sector_avg_momentum_empty():
    assert _sector_avg_momentum([]) == 0.0


def test_sector_avg_momentum():
    sigs = [_signal("A", momentum=10.0), _signal("B", momentum=20.0)]
    assert _sector_avg_momentum(sigs) == pytest.approx(15.0)


# ── _confidence ───────────────────────────────────────────────────────────────

def test_confidence_high_all_signals():
    sig = _signal(consensus="buy", momentum=12.0)
    sig.reddit_sentiment_score = 0.5
    sig.news_sentiment_score = 0.3
    assert _confidence(sig, avg_momentum=8.0) == "HIGH"


def test_confidence_medium_two_signals():
    # fundamental (buy) + sentiment (both positive) = 2; momentum fails (5 < avg 8)
    sig = _signal(consensus="buy", momentum=5.0)
    sig.reddit_sentiment_score = 0.2
    sig.news_sentiment_score = 0.3
    assert _confidence(sig, avg_momentum=8.0) == "MEDIUM"


def test_confidence_low_one_signal():
    sig = _signal(consensus="hold", momentum=2.0)
    sig.reddit_sentiment_score = -0.2
    sig.news_sentiment_score = -0.1
    assert _confidence(sig, avg_momentum=8.0) == "LOW"


# ── check_exit_signals ────────────────────────────────────────────────────────

def test_exit_stop_loss():
    h = _holding(avg_cost=1000.0, current_price=790.0)  # -21%
    exits = check_exit_signals([h])
    assert len(exits) == 1
    assert exits[0]["action"] == "SELL"
    assert exits[0]["trigger"] == "stop_loss"
    assert exits[0]["loss_pct"] <= STOP_LOSS_PCT


def test_exit_rebalance():
    h = _holding(avg_cost=800.0, current_price=900.0, allocation_pct=42.0)  # >40%
    exits = check_exit_signals([h])
    assert len(exits) == 1
    assert exits[0]["action"] == "SELL"
    assert exits[0]["trigger"] == "rebalance"


def test_exit_review_zone():
    h = _holding(avg_cost=1000.0, current_price=840.0)  # -16%, between -20 and -15
    exits = check_exit_signals([h])
    assert len(exits) == 1
    assert exits[0]["action"] == "HOLD"
    assert exits[0]["trigger"] == "review_zone"


def test_no_exit_healthy_position():
    h = _holding(avg_cost=800.0, current_price=920.0, allocation_pct=23.0)  # +15%, fine
    assert check_exit_signals([h]) == []


def test_exit_exactly_at_stop_loss():
    h = _holding(avg_cost=1000.0, current_price=800.0)  # exactly -20%
    exits = check_exit_signals([h])
    assert exits[0]["trigger"] == "stop_loss"


def test_multiple_holdings_mixed_exits():
    holdings = [
        _holding("AAA", avg_cost=1000.0, current_price=790.0),   # stop-loss
        _holding("BBB", avg_cost=800.0, current_price=920.0),    # healthy
        _holding("CCC", avg_cost=1000.0, current_price=840.0),   # review zone
    ]
    exits = check_exit_signals(holdings)
    tickers = {e["ticker"] for e in exits}
    assert "AAA" in tickers
    assert "CCC" in tickers
    assert "BBB" not in tickers


# ── rank_candidates ───────────────────────────────────────────────────────────

def test_rank_excludes_held_tickers():
    signals = [_signal("NVDA", 90), _signal("MSFT", 80), _signal("GOOGL", 70)]
    ranked = rank_candidates(signals, held_tickers={"NVDA"})
    assert all(s.ticker != "NVDA" for s in ranked)
    assert ranked[0].ticker == "MSFT"


def test_rank_sorts_by_score_descending():
    signals = [_signal("A", 60), _signal("B", 90), _signal("C", 75)]
    ranked = rank_candidates(signals, held_tickers=set())
    scores = [s.composite_score for s in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_excludes_zero_score():
    signals = [_signal("A", 0), _signal("B", 80)]
    ranked = rank_candidates(signals, held_tickers=set())
    assert all(s.ticker != "A" for s in ranked)


# ── compute_allocations ───────────────────────────────────────────────────────

def test_compute_allocations_empty_portfolio():
    candidates = [_signal(t, 80 - i * 5) for i, t in enumerate(["A", "B", "C", "D", "E"])]
    portfolio = _portfolio()
    allocs = compute_allocations(candidates, portfolio)
    assert len(allocs) <= MAX_POSITIONS
    for _, pct in allocs:
        assert pct <= MAX_SINGLE_PCT


def test_compute_respects_min_cash():
    candidates = [_signal("A", 90)]
    portfolio = _portfolio()
    allocs = compute_allocations(candidates, portfolio)
    total_pct = sum(pct for _, pct in allocs)
    assert total_pct <= 100 - MIN_CASH_PCT


def test_compute_no_slots_when_full():
    holdings = [_holding(f"T{i}", allocation_pct=18.0) for i in range(MAX_POSITIONS)]
    portfolio = _portfolio(holdings=holdings)
    candidates = [_signal("NEW", 95)]
    assert compute_allocations(candidates, portfolio) == []


def test_compute_freed_slots_open_space():
    # 5 holdings but 1 is going to be sold → 1 slot free
    holdings = [_holding(f"T{i}", allocation_pct=15.0) for i in range(MAX_POSITIONS)]
    portfolio = _portfolio(holdings=holdings)
    candidates = [_signal("NEW", 95)]
    allocs = compute_allocations(candidates, portfolio, freed_slots=1)
    assert len(allocs) == 1


# ── run_analysis (full pipeline) ─────────────────────────────────────────────

def test_run_analysis_empty_portfolio(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    portfolio = _portfolio()
    report = run_analysis(snapshot, portfolio, use_claude=False)

    assert isinstance(report, AnalystReport)
    assert len([r for r in report.recommendations if r.action == "BUY"]) > 0
    assert report.cash_reserve_pct >= MIN_CASH_PCT
    assert report.total_invested_pct + report.cash_reserve_pct == pytest.approx(100.0, abs=0.5)


def test_run_analysis_all_recs_have_rationale(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    portfolio = _portfolio()
    report = run_analysis(snapshot, portfolio, use_claude=False)

    for rec in report.recommendations:
        assert len(rec.rationale) == 3, f"{rec.ticker} has {len(rec.rationale)} rationale bullets"
        assert all(isinstance(b, str) and len(b) > 0 for b in rec.rationale)


def test_run_analysis_triggers_stop_loss(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    holdings = [_holding("NVDA", avg_cost=1000.0, current_price=780.0)]  # -22%
    snapshot = _snapshot()
    portfolio = _portfolio(holdings=holdings)
    report = run_analysis(snapshot, portfolio, use_claude=False)

    sells = [r for r in report.recommendations if r.action == "SELL"]
    assert any(r.ticker == "NVDA" for r in sells)


def test_run_analysis_triggers_rebalance(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    holdings = [_holding("NVDA", avg_cost=700.0, current_price=900.0, allocation_pct=42.0)]
    snapshot = _snapshot()
    portfolio = _portfolio(holdings=holdings)
    report = run_analysis(snapshot, portfolio, use_claude=False)

    sells = [r for r in report.recommendations if r.action == "SELL" and r.ticker == "NVDA"]
    assert len(sells) == 1
    assert sells[0].allocation_pct == REBALANCE_TARGET_PCT


def test_run_analysis_max_positions_enforced(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    # Full portfolio with 5 healthy holdings
    holdings = [_holding(f"T{i}", avg_cost=100.0, current_price=110.0, allocation_pct=16.0) for i in range(5)]
    snapshot = _snapshot()
    portfolio = _portfolio(holdings=holdings)
    report = run_analysis(snapshot, portfolio, use_claude=False)

    buys = [r for r in report.recommendations if r.action == "BUY"]
    # No new buys — all slots are taken
    assert len(buys) == 0


def test_run_analysis_persists_to_disk(tmp_path):
    import json, storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    portfolio = _portfolio()
    report = run_analysis(snapshot, portfolio, use_claude=False)

    saved = list((tmp_path / "research" / "recommendations").glob("*.json"))
    assert len(saved) == 1
    restored = AnalystReport.model_validate(json.loads(saved[0].read_text()))
    assert restored.report_id == report.report_id


def test_run_analysis_ira_account(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    portfolio = _portfolio()
    portfolio = portfolio.model_copy(update={"account_type": AccountType.traditional_ira})
    report = run_analysis(snapshot, portfolio, use_claude=False)

    assert isinstance(report, AnalystReport)
    assert len(report.recommendations) > 0


def test_buy_allocation_within_bounds(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot()
    portfolio = _portfolio()
    report = run_analysis(snapshot, portfolio, use_claude=False)

    for rec in report.recommendations:
        if rec.action == "BUY":
            assert 0 < rec.allocation_pct <= MAX_SINGLE_PCT


def test_snapshot_id_referenced_in_report(tmp_path):
    import storage as _storage
    _storage.DATA_DIR = tmp_path

    snapshot = _snapshot(snapshot_id="snap-abc-123")
    report = run_analysis(snapshot, _portfolio(), use_claude=False)
    assert report.based_on_snapshot_id == "snap-abc-123"
