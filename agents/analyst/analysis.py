"""
Analyst Agent — core analysis pipeline.
Importable by tests and by main.py.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_SHARED = Path(__file__).parent.parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

import storage as _storage
from data_models import (
    AnalystReport,
    Holding,
    MarketResearchSnapshot,
    PortfolioState,
    Recommendation,
    StockSignal,
)

logger = logging.getLogger(__name__)

# ── Strategy constants ─────────────────────────────────────────────────────────
MAX_POSITIONS = 5
MAX_SINGLE_PCT = 35.0      # max % of portfolio for any single position
MIN_CASH_PCT = 10.0        # minimum cash reserve always maintained
STOP_LOSS_PCT = -20.0      # triggers SELL
REVIEW_ZONE_PCT = -15.0    # triggers HOLD with review flag
REBALANCE_TRIGGER_PCT = 40.0  # position above this → partial SELL
REBALANCE_TARGET_PCT = 30.0


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sector_avg_momentum(signals: list[StockSignal]) -> float:
    if not signals:
        return 0.0
    return sum(s.momentum_20d_pct for s in signals) / len(signals)


def _confidence(signal: StockSignal, avg_momentum: float) -> str:
    """HIGH requires all 3 entry signals; MEDIUM = 2; LOW = 1."""
    met = 0
    if signal.momentum_20d_pct > avg_momentum:
        met += 1
    if (signal.analyst_consensus or "none").lower() in ("buy", "strong_buy", "strongbuy"):
        met += 1
    if signal.reddit_sentiment_score > 0 and signal.news_sentiment_score > 0:
        met += 1
    return "HIGH" if met >= 3 else ("MEDIUM" if met == 2 else "LOW")


def _algo_rationale(
    ticker: str,
    action: str,
    signal: Optional[StockSignal],
    trigger: str = "",
) -> list[str]:
    """Template-based 3-bullet rationale — used when Claude is unavailable."""
    if action == "SELL" and trigger == "stop_loss":
        return [
            f"{ticker} breached the -20% stop-loss threshold — capital preservation required.",
            "Continued negative momentum with no recovery signal detected.",
            "Position liquidated per growth strategy risk management rules.",
        ]
    if action == "SELL" and trigger == "rebalance":
        return [
            f"{ticker} allocation exceeded {REBALANCE_TRIGGER_PCT:.0f}% — concentration risk above limit.",
            f"Partial sale targets {REBALANCE_TARGET_PCT:.0f}% allocation per position-sizing rules.",
            "Freed capital improves cash reserve for new opportunities.",
        ]
    if action == "BUY" and signal:
        bullets: list[str] = []
        if signal.momentum_20d_pct > 5:
            bullets.append(
                f"20-day momentum of +{signal.momentum_20d_pct:.1f}% outperforms sector average."
            )
        if (signal.analyst_consensus or "").lower() in ("buy", "strong_buy", "strongbuy"):
            target = (
                f" — consensus target ${signal.analyst_price_target:.0f}"
                if signal.analyst_price_target
                else ""
            )
            bullets.append(f"Analyst consensus: {signal.analyst_consensus}{target}.")
        if signal.recent_8k_summary:
            bullets.append(f"Recent SEC filing: {signal.recent_8k_summary}.")
        if signal.news_headline_count > 0:
            bullets.append(
                f"{signal.news_headline_count} news headlines with "
                f"{signal.news_sentiment_score:+.2f} sentiment score."
            )
        if signal.reddit_mention_count > 0:
            bullets.append(
                f"Reddit: {signal.reddit_mention_count} mentions, "
                f"{signal.reddit_sentiment_score:+.2f} sentiment."
            )
        while len(bullets) < 3:
            score = signal.composite_score or 0
            bullets.append(f"Composite score {score:.0f}/100 supports position entry.")
        return bullets[:3]
    # HOLD / review-zone
    return [
        f"{ticker} maintains position within acceptable range.",
        "No exit signals triggered; monitoring for momentum changes.",
        "Current allocation remains within target bounds.",
    ]


def _claude_rationale(
    recs_payload: list[dict],
    portfolio: PortfolioState,
) -> dict[str, list[str]]:
    """Ask Claude for rationale. Returns {ticker: [bullet, bullet, bullet]}."""
    SYSTEM = (
        "You are an Analyst Agent for an investment simulation "
        "(SIMULATION ONLY — not financial advice).\n\n"
        "Write exactly 3 concise, data-driven rationale bullets per recommendation. "
        "Reference specific numbers (scores, %, counts) from the provided data. "
        f"Account type: {portfolio.account_type.value}. "
        "For brokerage accounts, flag holding-period tax implications. "
        "For IRA accounts, note tax-deferred flexibility.\n\n"
        "Respond ONLY with a JSON array — no markdown.\n"
        'Format: [{"ticker": "NVDA", "rationale": ["bullet 1", "bullet 2", "bullet 3"]}]'
    )
    user_msg = (
        "Generate 3-bullet rationale for each recommendation.\n\n"
        f"Recommendations:\n{json.dumps(recs_payload, indent=2)}"
    )
    try:
        from claude_client import ClaudeClient
        raw = ClaudeClient().analyze(system=SYSTEM, user_message=user_msg)
        items = json.loads(raw)
        return {item["ticker"]: item["rationale"][:3] for item in items}
    except Exception as exc:
        logger.warning("Claude rationale failed (%s) — using algorithmic fallback", exc)
        return {}


# ── Public analysis functions ──────────────────────────────────────────────────

def check_exit_signals(holdings: list[Holding]) -> list[dict]:
    """
    Evaluate current holdings against exit rules.
    Returns list of raw exit dicts with keys: ticker, action, trigger, [loss_pct|allocation_pct].
    """
    exits = []
    for h in holdings:
        if h.avg_cost_basis == 0:
            continue
        loss_pct = (h.current_price - h.avg_cost_basis) / h.avg_cost_basis * 100
        if loss_pct <= STOP_LOSS_PCT:
            exits.append({"ticker": h.ticker, "action": "SELL", "trigger": "stop_loss", "loss_pct": round(loss_pct, 2)})
        elif h.allocation_pct > REBALANCE_TRIGGER_PCT:
            exits.append({"ticker": h.ticker, "action": "SELL", "trigger": "rebalance", "allocation_pct": h.allocation_pct})
        elif loss_pct <= REVIEW_ZONE_PCT:
            exits.append({"ticker": h.ticker, "action": "HOLD", "trigger": "review_zone", "loss_pct": round(loss_pct, 2)})
    return exits


def rank_candidates(signals: list[StockSignal], held_tickers: set[str]) -> list[StockSignal]:
    """Return new candidates sorted by composite_score descending."""
    eligible = [
        s for s in signals
        if s.ticker not in held_tickers and (s.composite_score or 0) > 0
    ]
    return sorted(eligible, key=lambda s: s.composite_score or 0, reverse=True)


def compute_allocations(
    candidates: list[StockSignal],
    portfolio: PortfolioState,
    freed_slots: int = 0,
) -> list[tuple[StockSignal, float]]:
    """
    Allocate capital to top N new positions.
    freed_slots: slots opened by pending SELL recommendations.
    """
    used_slots = len(portfolio.holdings) - freed_slots
    open_slots = MAX_POSITIONS - used_slots
    if open_slots <= 0 or not candidates:
        return []

    top = candidates[:open_slots]
    invested_pct = sum(h.allocation_pct for h in portfolio.holdings)
    # Reduce invested_pct by freed_slots worth of allocation (approximate as average)
    if freed_slots > 0 and portfolio.holdings:
        avg_alloc = invested_pct / len(portfolio.holdings)
        invested_pct -= freed_slots * avg_alloc

    available = 100.0 - invested_pct - MIN_CASH_PCT
    if available <= 0:
        return []

    total_score = sum(s.composite_score or 50.0 for s in top) or 1.0
    result = []
    for s in top:
        raw = (s.composite_score or 50.0) / total_score * available
        pct = round(min(raw, MAX_SINGLE_PCT), 1)
        if pct > 0:
            result.append((s, pct))
    return result


def run_analysis(
    snapshot: MarketResearchSnapshot,
    portfolio: PortfolioState,
    use_claude: bool = True,
    out_dir: Optional[Path] = None,
) -> AnalystReport:
    avg_momentum = _sector_avg_momentum(snapshot.stocks)
    signal_map = {s.ticker: s for s in snapshot.stocks}
    held_tickers = {h.ticker for h in portfolio.holdings}

    # ── 1. Exit checks on current holdings ───────────────────────────────────
    exit_signals = check_exit_signals(portfolio.holdings)
    exit_map = {e["ticker"]: e for e in exit_signals}
    # Count full-sell exits to open slots
    freed = sum(1 for e in exit_signals if e["action"] == "SELL")

    # ── 2. HOLD for stable existing positions ────────────────────────────────
    stable_holds = [
        h for h in portfolio.holdings
        if h.ticker not in exit_map
    ]

    # ── 3. Rank new BUY candidates ────────────────────────────────────────────
    ranked = rank_candidates(snapshot.stocks, held_tickers)
    allocations = compute_allocations(ranked, portfolio, freed_slots=freed)

    # ── 4. Build payload for Claude rationale ────────────────────────────────
    claude_payload: list[dict] = []
    for e in exit_signals:
        row: dict = {"ticker": e["ticker"], "action": e["action"], "trigger": e["trigger"]}
        if "loss_pct" in e:
            row["loss_pct"] = e["loss_pct"]
        if "allocation_pct" in e:
            row["allocation_pct"] = e["allocation_pct"]
        claude_payload.append(row)
    for h in stable_holds:
        sig = signal_map.get(h.ticker)
        claude_payload.append({
            "ticker": h.ticker,
            "action": "HOLD",
            "current_allocation_pct": h.allocation_pct,
            "unrealized_pnl_pct": h.unrealized_pnl_pct,
            "composite_score": sig.composite_score if sig else None,
            "momentum_20d_pct": sig.momentum_20d_pct if sig else None,
        })
    for sig, pct in allocations:
        claude_payload.append({
            "ticker": sig.ticker,
            "action": "BUY",
            "allocation_pct": pct,
            "composite_score": sig.composite_score,
            "momentum_20d_pct": sig.momentum_20d_pct,
            "analyst_consensus": sig.analyst_consensus,
            "analyst_price_target": sig.analyst_price_target,
            "news_headline_count": sig.news_headline_count,
            "news_sentiment_score": sig.news_sentiment_score,
            "reddit_mention_count": sig.reddit_mention_count,
            "reddit_sentiment_score": sig.reddit_sentiment_score,
            "recent_8k": sig.recent_8k_summary,
        })

    # ── 5. Rationale ─────────────────────────────────────────────────────────
    rationale_map: dict[str, list[str]] = {}
    if use_claude and os.getenv("ANTHROPIC_API_KEY"):
        rationale_map = _claude_rationale(claude_payload, portfolio)

    def get_rationale(ticker: str, action: str, trigger: str = "") -> list[str]:
        return rationale_map.get(ticker) or _algo_rationale(
            ticker, action, signal_map.get(ticker), trigger
        )

    # ── 6. Assemble Recommendation objects ───────────────────────────────────
    now = datetime.now(timezone.utc)
    recommendations: list[Recommendation] = []

    for e in exit_signals:
        ticker = e["ticker"]
        sig = signal_map.get(ticker)
        recommendations.append(Recommendation(
            ticker=ticker,
            action=e["action"],
            confidence="HIGH",
            allocation_pct=REBALANCE_TARGET_PCT if e["trigger"] == "rebalance" else 0.0,
            composite_score=sig.composite_score or 0.0 if sig else 0.0,
            rationale=get_rationale(ticker, e["action"], e["trigger"]),
            data_sources=snapshot.data_sources,
            generated_at=now,
        ))

    for h in stable_holds:
        sig = signal_map.get(h.ticker)
        recommendations.append(Recommendation(
            ticker=h.ticker,
            action="HOLD",
            confidence="MEDIUM",
            allocation_pct=h.allocation_pct,
            composite_score=sig.composite_score or 50.0 if sig else 50.0,
            rationale=get_rationale(h.ticker, "HOLD"),
            data_sources=snapshot.data_sources,
            generated_at=now,
        ))

    for sig, pct in allocations:
        conf = _confidence(sig, avg_momentum)
        recommendations.append(Recommendation(
            ticker=sig.ticker,
            action="BUY",
            confidence=conf,
            allocation_pct=pct,
            composite_score=sig.composite_score or 0.0,
            rationale=get_rationale(sig.ticker, "BUY"),
            data_sources=snapshot.data_sources,
            generated_at=now,
        ))

    # ── 7. Compute projected totals ───────────────────────────────────────────
    hold_pct = sum(h.allocation_pct for h in stable_holds)
    buy_pct = sum(pct for _, pct in allocations)
    total_invested = round(hold_pct + buy_pct, 1)
    cash_reserve = round(100.0 - total_invested, 1)

    n_buy = sum(1 for r in recommendations if r.action == "BUY")
    n_sell = sum(1 for r in recommendations if r.action == "SELL")
    n_hold = sum(1 for r in recommendations if r.action == "HOLD")

    report = AnalystReport(
        report_id=f"rpt-{now.strftime('%Y%m%d-%H%M')}",
        generated_at=now,
        based_on_snapshot_id=snapshot.snapshot_id,
        recommendations=recommendations,
        total_invested_pct=total_invested,
        cash_reserve_pct=cash_reserve,
        strategy_notes=(
            f"Growth | {portfolio.account_type.value} | sector: {portfolio.target_market} | "
            f"BUY={n_buy} SELL={n_sell} HOLD={n_hold}"
        ),
    )

    # ── 8. Persist ────────────────────────────────────────────────────────────
    ts = now.strftime("%Y-%m-%d_%H")
    base = out_dir if out_dir is not None else _storage.DATA_DIR / "research" / "recommendations"
    out_path = base / f"{ts}_recommendations.json"
    _storage.write_json(out_path, report.model_dump(mode="json"))
    logger.info(
        "Analyst report saved → %s | BUY=%d SELL=%d HOLD=%d",
        out_path.name, n_buy, n_sell, n_hold,
    )
    return report
