"""
CEO Agent — core decision pipeline.
Importable by tests and by main.py.
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional

_SHARED = Path(__file__).parent.parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import storage as _storage
from data_models import (
    AccountType,
    AnalystReport,
    Confidence,
    DailyReport,
    Holding,
    MarketResearchSnapshot,
    PortfolioPerformance,
    PortfolioState,
    Recommendation,
    TaxImpact,
    TradeAction,
    TradeLogEntry,
)

logger = logging.getLogger(__name__)

# ── Approval rules ─────────────────────────────────────────────────────────────
MIN_DATA_SOURCES_FOR_BUY = 2
MAX_POSITIONS = 5
MAX_SINGLE_PCT = 35.0
MIN_CASH_PCT = 10.0

_MEMORY_HEADER = "# CEO MEMORY.md\n\nAutomatic daily log. Most recent entry at bottom.\n\n"


# ── Approval ───────────────────────────────────────────────────────────────────

def approve_recommendations(
    report: AnalystReport,
    portfolio: PortfolioState,
) -> tuple[list[Recommendation], list[Recommendation]]:
    """
    Split analyst recommendations into (approved, rejected).

    Rules:
    - SELL / HOLD: always approved
    - BUY: requires >= MIN_DATA_SOURCES_FOR_BUY data sources, allocation <= MAX_SINGLE_PCT,
           and portfolio must have an open slot
    """
    approved: list[Recommendation] = []
    rejected: list[Recommendation] = []

    pending_buys = 0
    sell_tickers = {r.ticker for r in report.recommendations if r.action == "SELL"}

    for rec in report.recommendations:
        if rec.action in ("SELL", "HOLD"):
            approved.append(rec)
            continue

        # BUY checks
        reasons = []
        if len(rec.data_sources) < MIN_DATA_SOURCES_FOR_BUY:
            reasons.append(f"insufficient data sources ({len(rec.data_sources)} < {MIN_DATA_SOURCES_FOR_BUY})")
        if rec.allocation_pct > MAX_SINGLE_PCT:
            reasons.append(f"allocation {rec.allocation_pct:.1f}% exceeds max {MAX_SINGLE_PCT:.0f}%")

        current_positions = len(portfolio.holdings) - len(sell_tickers) + pending_buys
        if current_positions >= MAX_POSITIONS:
            reasons.append(f"portfolio already at max {MAX_POSITIONS} positions")

        if reasons:
            rec_copy = rec.model_copy(update={"action": "HOLD"})
            rejected.append(rec)
            logger.info("CEO rejected BUY %s: %s", rec.ticker, "; ".join(reasons))
        else:
            approved.append(rec)
            pending_buys += 1

    return approved, rejected


# ── Trade execution ────────────────────────────────────────────────────────────

def _tax_impact(
    holding: Optional[Holding],
    action: str,
    gain_loss: float,
    account_type: AccountType,
    today: date,
) -> TaxImpact:
    if action == "BUY" or holding is None:
        return TaxImpact(holding_period_days=0, gain_loss=0.0, tax_treatment="n/a")

    holding_days = (today - holding.open_date).days if holding else 0

    if account_type == AccountType.traditional_ira:
        treatment = "tax-deferred (IRA)"
    elif holding_days >= 365:
        treatment = "long-term capital gain (LTCG)"
    else:
        treatment = "short-term gain, taxed as ordinary income"

    return TaxImpact(
        holding_period_days=holding_days,
        gain_loss=round(gain_loss, 2),
        tax_treatment=treatment,
    )


def apply_trades(
    approved: list[Recommendation],
    portfolio: PortfolioState,
    signal_map: dict,
    today: date,
) -> tuple[PortfolioState, list[TradeLogEntry]]:
    """
    Simulate approved trades.  Returns updated portfolio + trade log entries.
    Prices come from signal_map[ticker].current_price when available,
    otherwise from the existing holding.
    """
    holdings_by_ticker: dict[str, Holding] = {h.ticker: h for h in portfolio.holdings}
    trade_log: list[TradeLogEntry] = []
    now = datetime.now(timezone.utc)
    budget = portfolio.budget_total

    # Process SELLs first so cash becomes available for BUYs
    for rec in sorted(approved, key=lambda r: (0 if r.action == "SELL" else 1)):
        ticker = rec.ticker
        sig = signal_map.get(ticker)
        current_price = sig.current_price if sig else (
            holdings_by_ticker[ticker].current_price if ticker in holdings_by_ticker else 0.0
        )

        if rec.action == "BUY":
            if current_price <= 0:
                logger.warning("Skipping BUY %s — no price available", ticker)
                continue
            dollar_amount = budget * rec.allocation_pct / 100.0
            shares = round(dollar_amount / current_price, 4)
            tax = _tax_impact(None, "BUY", 0.0, portfolio.account_type, today)
            holdings_by_ticker[ticker] = Holding(
                ticker=ticker,
                shares=shares,
                avg_cost_basis=current_price,
                current_price=current_price,
                market_value=dollar_amount,
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0,
                allocation_pct=rec.allocation_pct,
                open_date=today,
                analyst_rating=rec.action,
                confidence=Confidence(rec.confidence),
            )
            trade_log.append(TradeLogEntry(
                trade_id=str(uuid.uuid4()),
                timestamp=now,
                action=TradeAction.BUY,
                ticker=ticker,
                shares=shares,
                price=current_price,
                total_value=round(dollar_amount, 2),
                rationale=rec.rationale[0] if rec.rationale else "",
                data_sources=rec.data_sources,
                approved_by="CEO",
                account_type=portfolio.account_type,
                simulated_tax_impact=tax,
            ))

        elif rec.action == "SELL":
            h = holdings_by_ticker.pop(ticker, None)
            if h is None:
                continue
            gain_loss = (current_price - h.avg_cost_basis) * h.shares
            tax = _tax_impact(h, "SELL", gain_loss, portfolio.account_type, today)
            trade_log.append(TradeLogEntry(
                trade_id=str(uuid.uuid4()),
                timestamp=now,
                action=TradeAction.SELL,
                ticker=ticker,
                shares=h.shares,
                price=current_price,
                total_value=round(current_price * h.shares, 2),
                rationale=rec.rationale[0] if rec.rationale else "",
                data_sources=rec.data_sources,
                approved_by="CEO",
                account_type=portfolio.account_type,
                simulated_tax_impact=tax,
            ))

    # Recompute portfolio totals
    new_holdings = list(holdings_by_ticker.values())
    total_market_value = sum(h.allocation_pct / 100.0 * budget for h in new_holdings)
    total_invested_pct = sum(h.allocation_pct for h in new_holdings)
    cash_available = budget * (1.0 - total_invested_pct / 100.0)
    total_unrealized_pnl = sum(
        (h.current_price - h.avg_cost_basis) * h.shares for h in new_holdings
    )
    total_unrealized_pnl_pct = (
        total_unrealized_pnl / total_market_value * 100.0 if total_market_value > 0 else 0.0
    )

    updated_portfolio = portfolio.model_copy(update={
        "holdings": new_holdings,
        "total_market_value": round(total_market_value, 2),
        "cash_available": round(cash_available, 2),
        "total_unrealized_pnl": round(total_unrealized_pnl, 2),
        "total_unrealized_pnl_pct": round(total_unrealized_pnl_pct, 2),
        "last_updated": datetime.now(timezone.utc),
    })
    return updated_portfolio, trade_log


# ── Day P&L ────────────────────────────────────────────────────────────────────

def compute_day_pnl(
    portfolio: PortfolioState,
    signal_map: dict,
) -> tuple[float, float]:
    """Estimate today's P&L using price_change_1d_pct from each holding's signal."""
    day_pnl = 0.0
    total_invested = portfolio.total_market_value
    for h in portfolio.holdings:
        sig = signal_map.get(h.ticker)
        if sig is None:
            continue
        day_pnl += h.market_value * sig.price_change_1d_pct / 100.0
    day_pnl_pct = day_pnl / total_invested * 100.0 if total_invested > 0 else 0.0
    return round(day_pnl, 2), round(day_pnl_pct, 4)


# ── Daily report ───────────────────────────────────────────────────────────────

def _algo_narrative(
    approved: list[Recommendation],
    rejected: list[Recommendation],
    portfolio: PortfolioState,
    day_pnl: float,
    day_pnl_pct: float,
    snapshot: MarketResearchSnapshot,
) -> tuple[str, str]:
    """Return (executive_summary, market_conditions) strings."""
    buys = [r for r in approved if r.action == "BUY"]
    sells = [r for r in approved if r.action == "SELL"]

    summary_parts = [
        f"Simulation cycle completed for {date.today().isoformat()}.",
        f"Portfolio day P&L: ${day_pnl:+.2f} ({day_pnl_pct:+.2f}%).",
    ]
    if buys:
        tickers = ", ".join(r.ticker for r in buys)
        summary_parts.append(f"Initiated {len(buys)} new position(s): {tickers}.")
    if sells:
        tickers = ", ".join(r.ticker for r in sells)
        summary_parts.append(f"Exited {len(sells)} position(s): {tickers}.")
    if rejected:
        summary_parts.append(f"{len(rejected)} recommendation(s) held pending additional data.")
    summary_parts.append("SIMULATION ONLY — not financial advice.")

    avg_momentum = (
        sum(s.momentum_20d_pct for s in snapshot.stocks) / len(snapshot.stocks)
        if snapshot.stocks else 0.0
    )
    conditions = (
        f"Sector '{snapshot.sector}' avg 20-day momentum: {avg_momentum:+.1f}%. "
        f"{len(snapshot.stocks)} stocks tracked. "
        f"Data sources: {', '.join(snapshot.data_sources)}."
    )
    return " ".join(summary_parts), conditions


def _claude_narrative(
    approved: list[Recommendation],
    rejected: list[Recommendation],
    portfolio: PortfolioState,
    day_pnl: float,
    day_pnl_pct: float,
    snapshot: MarketResearchSnapshot,
) -> tuple[str, str]:
    SYSTEM = (
        "You are the CEO Agent of an investment simulation "
        "(SIMULATION ONLY — not financial advice).\n\n"
        "Write a concise executive summary (2-3 sentences) and a brief market conditions "
        "paragraph (1-2 sentences) for the daily report. "
        "Reference specific tickers, percentages, and data points.\n\n"
        'Respond ONLY with JSON: {"executive_summary": "...", "market_conditions": "..."}'
    )
    buys = [{"ticker": r.ticker, "allocation_pct": r.allocation_pct} for r in approved if r.action == "BUY"]
    sells = [{"ticker": r.ticker} for r in approved if r.action == "SELL"]
    user_msg = json.dumps({
        "date": date.today().isoformat(),
        "day_pnl": day_pnl,
        "day_pnl_pct": day_pnl_pct,
        "buys": buys,
        "sells": sells,
        "rejected_count": len(rejected),
        "portfolio_holdings": len(portfolio.holdings),
        "sector": snapshot.sector,
        "avg_momentum": round(
            sum(s.momentum_20d_pct for s in snapshot.stocks) / max(len(snapshot.stocks), 1), 2
        ),
    })
    try:
        from claude_client import ClaudeClient
        raw = ClaudeClient().analyze(system=SYSTEM, user_message=user_msg)
        parsed = json.loads(raw)
        return parsed["executive_summary"], parsed["market_conditions"]
    except Exception as exc:
        logger.warning("Claude narrative failed (%s) — using algorithmic fallback", exc)
        return _algo_narrative(approved, rejected, portfolio, day_pnl, day_pnl_pct, snapshot)


def generate_daily_report(
    approved: list[Recommendation],
    rejected: list[Recommendation],
    portfolio: PortfolioState,
    snapshot: MarketResearchSnapshot,
    trade_log: list[TradeLogEntry],
    day_pnl: float,
    day_pnl_pct: float,
    use_claude: bool = True,
) -> DailyReport:
    today = date.today()

    if use_claude and os.getenv("ANTHROPIC_API_KEY"):
        executive_summary, market_conditions = _claude_narrative(
            approved, rejected, portfolio, day_pnl, day_pnl_pct, snapshot
        )
    else:
        executive_summary, market_conditions = _algo_narrative(
            approved, rejected, portfolio, day_pnl, day_pnl_pct, snapshot
        )

    actions_taken = [
        {
            "action": t.action.value,
            "ticker": t.ticker,
            "shares": t.shares,
            "price": t.price,
            "total_value": t.total_value,
        }
        for t in trade_log
    ]

    top_signals = sorted(
        [{"ticker": s.ticker, "composite_score": s.composite_score, "momentum_20d_pct": s.momentum_20d_pct}
         for s in snapshot.stocks if s.composite_score is not None],
        key=lambda x: x["composite_score"],
        reverse=True,
    )[:5]

    next_day_watchlist = [
        s.ticker for s in sorted(
            [s for s in snapshot.stocks if s.ticker not in {h.ticker for h in portfolio.holdings}],
            key=lambda x: x.composite_score or 0,
            reverse=True,
        )[:5]
    ]

    return DailyReport(
        report_date=today,
        generated_at=datetime.now(timezone.utc),
        executive_summary=executive_summary,
        market_conditions=market_conditions,
        portfolio_performance=PortfolioPerformance(
            day_pnl=day_pnl,
            day_pnl_pct=day_pnl_pct,
            total_unrealized_pnl=portfolio.total_unrealized_pnl,
        ),
        actions_taken=actions_taken,
        top_signals=top_signals,
        recommendations_pending=[
            {"ticker": r.ticker, "action": r.action, "composite_score": r.composite_score}
            for r in rejected
        ],
        next_day_watchlist=next_day_watchlist,
    )


# ── Memory update ──────────────────────────────────────────────────────────────

def update_memory(
    memory_path: Path,
    today: date,
    approved: list[Recommendation],
    rejected: list[Recommendation],
    portfolio: PortfolioState,
    day_pnl: float,
) -> None:
    buys = [r.ticker for r in approved if r.action == "BUY"]
    sells = [r.ticker for r in approved if r.action == "SELL"]
    entry_lines = [
        f"\n## {today.isoformat()}",
        f"- P&L: ${day_pnl:+.2f}",
        f"- Holdings: {len(portfolio.holdings)} | Cash: ${portfolio.cash_available:,.2f}",
    ]
    if buys:
        entry_lines.append(f"- Bought: {', '.join(buys)}")
    if sells:
        entry_lines.append(f"- Sold: {', '.join(sells)}")
    if rejected:
        entry_lines.append(f"- Rejected: {len(rejected)} recommendation(s)")

    memory_path.parent.mkdir(parents=True, exist_ok=True)
    if not memory_path.exists():
        memory_path.write_text(_MEMORY_HEADER)
    with memory_path.open("a") as f:
        f.write("\n".join(entry_lines) + "\n")


# ── Full CEO cycle ─────────────────────────────────────────────────────────────

def run_ceo_cycle(
    analyst_report: AnalystReport,
    portfolio: PortfolioState,
    snapshot: MarketResearchSnapshot,
    use_claude: bool = True,
) -> tuple[DailyReport, PortfolioState, list[TradeLogEntry]]:
    today = date.today()
    signal_map = {s.ticker: s for s in snapshot.stocks}

    # 1. Approve / reject
    approved, rejected = approve_recommendations(analyst_report, portfolio)

    # 2. Execute trades
    updated_portfolio, trade_log = apply_trades(approved, portfolio, signal_map, today)

    # 3. Day P&L (pre-trade portfolio price change)
    day_pnl, day_pnl_pct = compute_day_pnl(portfolio, signal_map)

    # 4. Daily report
    daily_report = generate_daily_report(
        approved, rejected, updated_portfolio, snapshot,
        trade_log, day_pnl, day_pnl_pct, use_claude,
    )

    # 5. Persist portfolio state
    _storage.write_json(
        _storage.DATA_DIR / "portfolio" / "state.json",
        updated_portfolio.model_dump(mode="json"),
    )

    # 6. Persist portfolio history snapshot
    _storage.write_json(
        _storage.DATA_DIR / "portfolio" / "history" / f"{today.isoformat()}.json",
        updated_portfolio.model_dump(mode="json"),
    )

    # 7. Append to trade log
    for entry in trade_log:
        _storage.append_json_list(
            _storage.DATA_DIR / "trades" / "log.json",
            entry.model_dump(mode="json"),
        )

    # 8. Persist daily report
    ts = today.isoformat()
    _storage.write_json(
        _storage.DATA_DIR / "reports" / "daily" / f"{ts}_executive_summary.json",
        daily_report.model_dump(mode="json"),
    )

    # 9. Update agent memory — writes to DATA_DIR so tests stay isolated
    memory_path = _storage.DATA_DIR / "agent_memory" / "ceo.md"
    update_memory(memory_path, today, approved, rejected, updated_portfolio, day_pnl)

    n_buy = sum(1 for r in approved if r.action == "BUY")
    n_sell = sum(1 for r in approved if r.action == "SELL")
    logger.info(
        "CEO cycle complete | BUY=%d SELL=%d rejected=%d | day_pnl=$%+.2f",
        n_buy, n_sell, len(rejected), day_pnl,
    )
    return daily_report, updated_portfolio, trade_log
