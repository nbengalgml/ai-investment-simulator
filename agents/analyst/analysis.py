"""
Analyst Agent — core analysis pipeline.
Importable by tests and by main.py.
"""

import json
import logging
import os
import sys
from copy import copy
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
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


# ── Per-account-type strategy configuration ────────────────────────────────────

@dataclass
class StrategyConfig:
    max_positions: int = 5
    max_single_pct: float = 35.0
    min_cash_pct: float = 10.0
    stop_loss_pct: float = -20.0
    review_zone_pct: float = -15.0
    rebalance_trigger_pct: float = 40.0
    rebalance_target_pct: float = 30.0
    # Minimum confidence level required to approve a new BUY
    # "HIGH" = all 3 signals required (brokerage: selective, avoid churn)
    # "MEDIUM" = 2 of 3 signals (IRA: more active, tax-deferred so churn is free)
    min_buy_confidence: str = "HIGH"
    # Wash-sale enforcement: only relevant for brokerage (IRA is tax-deferred)
    enforce_wash_sale: bool = False


# Traditional IRA — tax-deferred, trade freely, maximise capital deployment
IRA_STRATEGY = StrategyConfig(
    max_positions=5,
    max_single_pct=40.0,        # concentrate more — no tax drag on future rebalancing
    min_cash_pct=5.0,           # deploy ~95% of capital; re-entry is free inside IRA
    stop_loss_pct=-20.0,
    review_zone_pct=-15.0,
    rebalance_trigger_pct=35.0, # rebalance early and often — no short-term gain penalty
    rebalance_target_pct=25.0,
    min_buy_confidence="LOW",   # accept any positive signal (1-of-3) — aggressive entry
    enforce_wash_sale=False,    # wash-sale doesn't apply inside tax-deferred accounts
)

# Brokerage — post-tax, selective entries, prefer LTCG, enforce wash-sale
BROKERAGE_STRATEGY = StrategyConfig(
    max_positions=5,
    max_single_pct=35.0,
    min_cash_pct=10.0,          # keep more cash; selling to re-enter triggers taxable events
    stop_loss_pct=-20.0,
    review_zone_pct=-15.0,
    rebalance_trigger_pct=45.0, # wait longer before rebalancing to avoid triggering short-term gains
    rebalance_target_pct=30.0,
    min_buy_confidence="MEDIUM", # require 2-of-3 signals: both technical momentum AND analyst consensus
    enforce_wash_sale=True,      # skip re-buys within 30 days of a loss-sale
)


def get_strategy(account_type: str) -> StrategyConfig:
    if str(account_type) == "traditional_ira":
        return IRA_STRATEGY
    return BROKERAGE_STRATEGY


def _apply_regime(cfg: StrategyConfig, regime: str) -> StrategyConfig:
    """
    Tighten or relax strategy parameters based on the detected sector regime.

    bear  → raise confidence bar, shrink max position, hold more cash
    bull  → slight relaxation (allow bigger positions, deploy more capital)
    sideways → base config unchanged
    """
    if regime == "bear":
        adjusted = copy(cfg)
        # Require stronger conviction in a down market
        if adjusted.min_buy_confidence == "LOW":
            adjusted.min_buy_confidence = "MEDIUM"
        elif adjusted.min_buy_confidence == "MEDIUM":
            adjusted.min_buy_confidence = "HIGH"
        # Smaller individual bets
        adjusted.max_single_pct = round(cfg.max_single_pct * 0.80, 1)
        # Keep more dry powder
        adjusted.min_cash_pct = min(cfg.min_cash_pct * 1.5, 25.0)
        # Tighter stop-loss in bear markets to preserve capital
        adjusted.stop_loss_pct = -15.0
        adjusted.review_zone_pct = -10.0
        return adjusted
    if regime == "bull":
        adjusted = copy(cfg)
        # Slightly larger positions when trend is confirmed
        adjusted.max_single_pct = min(cfg.max_single_pct * 1.10, 40.0)
        # Deploy a bit more capital — less need for large cash buffer
        adjusted.min_cash_pct = max(cfg.min_cash_pct * 0.80, 5.0)
        return adjusted
    return cfg  # sideways: unchanged


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
            f"{ticker} allocation exceeded concentration limit — rebalance triggered.",
            "Partial sale reduces concentration risk per position-sizing rules.",
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

def _wash_sale_tickers(sim_dir: Optional[Path]) -> set[str]:
    """
    Return tickers sold at a loss within the last 30 days (wash-sale window).
    Only called for brokerage accounts. Returns empty set if trade log not found.
    """
    if sim_dir is None:
        return set()
    log_path = sim_dir / "trades" / "log.json"
    if not log_path.exists():
        return set()
    try:
        entries = _storage.read_json(log_path)
        cutoff = date.today() - timedelta(days=30)
        blocked = set()
        for e in entries:
            if e.get("action") != "SELL":
                continue
            ts = e.get("timestamp", "")[:10]
            try:
                trade_date = date.fromisoformat(ts)
            except ValueError:
                continue
            if trade_date >= cutoff and e.get("simulated_tax_impact", {}).get("gain_loss", 0) < 0:
                blocked.add(e["ticker"])
        return blocked
    except Exception:
        return set()


_LTCG_PROTECTION_DAYS = 300  # don't sell brokerage positions within 65 days of 1-year LTCG threshold


def check_exit_signals(
    holdings: list[Holding],
    cfg: Optional[StrategyConfig] = None,
    account_type: str = "brokerage",
) -> list[dict]:
    """
    Evaluate current holdings against exit rules.
    Returns list of raw exit dicts with keys: ticker, action, trigger, [loss_pct|allocation_pct].

    LTCG protection (brokerage only): skip rebalance sells when a position is within
    65 days of the 1-year long-term capital gains threshold — hold until LTCG qualifies
    unless the stop-loss is triggered.
    """
    if cfg is None:
        cfg = BROKERAGE_STRATEGY
    today = date.today()
    exits = []
    for h in holdings:
        if h.avg_cost_basis == 0:
            continue
        loss_pct = (h.current_price - h.avg_cost_basis) / h.avg_cost_basis * 100
        days_held = (today - h.open_date).days

        if loss_pct <= cfg.stop_loss_pct:
            # Stop-loss always fires — capital preservation overrides tax optimisation
            exits.append({"ticker": h.ticker, "action": "SELL", "trigger": "stop_loss",
                          "loss_pct": round(loss_pct, 2)})

        elif h.allocation_pct > cfg.rebalance_trigger_pct:
            # LTCG protection: if brokerage and approaching 1-year mark, hold for LTCG
            if account_type == "brokerage" and _LTCG_PROTECTION_DAYS <= days_held < 365:
                exits.append({"ticker": h.ticker, "action": "HOLD",
                               "trigger": "ltcg_protection",
                               "days_to_ltcg": 365 - days_held})
            else:
                exits.append({"ticker": h.ticker, "action": "SELL", "trigger": "rebalance",
                               "allocation_pct": h.allocation_pct})

        elif loss_pct <= cfg.review_zone_pct:
            exits.append({"ticker": h.ticker, "action": "HOLD", "trigger": "review_zone",
                          "loss_pct": round(loss_pct, 2)})
    return exits


def rank_candidates(
    signals: list[StockSignal],
    held_tickers: set[str],
    blocked_tickers: Optional[set[str]] = None,
) -> list[StockSignal]:
    """Return new candidates sorted by composite_score descending."""
    skip = held_tickers | (blocked_tickers or set())
    eligible = [
        s for s in signals
        if s.ticker not in skip and (s.composite_score or 0) > 0
    ]
    return sorted(eligible, key=lambda s: s.composite_score or 0, reverse=True)


MAX_NEW_POSITIONS_PER_CYCLE = 2  # prevent excessive churn in a single run


def compute_allocations(
    candidates: list[StockSignal],
    portfolio: PortfolioState,
    freed_slots: int = 0,
    cfg: Optional[StrategyConfig] = None,
) -> list[tuple[StockSignal, float]]:
    """
    Allocate capital to top N new positions.
    freed_slots: slots opened by pending SELL recommendations.
    Capped at MAX_NEW_POSITIONS_PER_CYCLE to avoid excessive turnover.
    """
    if cfg is None:
        cfg = BROKERAGE_STRATEGY
    used_slots = len(portfolio.holdings) - freed_slots
    open_slots = min(cfg.max_positions - used_slots, MAX_NEW_POSITIONS_PER_CYCLE)
    if open_slots <= 0 or not candidates:
        return []

    top = candidates[:open_slots]
    invested_pct = sum(h.allocation_pct for h in portfolio.holdings)
    if freed_slots > 0 and portfolio.holdings:
        avg_alloc = invested_pct / len(portfolio.holdings)
        invested_pct -= freed_slots * avg_alloc

    available = 100.0 - invested_pct - cfg.min_cash_pct
    if available <= 0:
        return []

    total_score = sum(s.composite_score or 50.0 for s in top) or 1.0
    result = []
    for s in top:
        raw = (s.composite_score or 50.0) / total_score * available
        pct = round(min(raw, cfg.max_single_pct), 1)
        if pct > 0:
            result.append((s, pct))
    return result


_CONFIDENCE_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def run_analysis(
    snapshot: MarketResearchSnapshot,
    portfolio: PortfolioState,
    use_claude: bool = True,
    out_dir: Optional[Path] = None,
    sim_dir: Optional[Path] = None,
) -> AnalystReport:
    cfg = get_strategy(portfolio.account_type.value)

    # Adjust strategy based on detected sector regime (bull/bear/sideways)
    regime = getattr(snapshot, "sector_regime", "sideways")
    cfg = _apply_regime(cfg, regime)
    logger.info(
        "Strategy for %s/%s in '%s' regime: confidence=%s max_pos=%.0f%% min_cash=%.0f%%",
        portfolio.account_type.value, portfolio.target_market, regime,
        cfg.min_buy_confidence, cfg.max_single_pct, cfg.min_cash_pct,
    )

    avg_momentum = _sector_avg_momentum(snapshot.stocks)
    signal_map = {s.ticker: s for s in snapshot.stocks}
    held_tickers = {h.ticker for h in portfolio.holdings}

    # ── 1. Exit checks on current holdings ───────────────────────────────────
    exit_signals = check_exit_signals(portfolio.holdings, cfg, account_type=portfolio.account_type.value)
    exit_map = {e["ticker"]: e for e in exit_signals}
    freed = sum(1 for e in exit_signals if e["action"] == "SELL")

    # ── 2. HOLD for stable existing positions ────────────────────────────────
    stable_holds = [
        h for h in portfolio.holdings
        if h.ticker not in exit_map
    ]

    # ── 3. Rank new BUY candidates ────────────────────────────────────────────
    # Brokerage: enforce wash-sale rule (no re-buy within 30 days of a loss-sale)
    blocked: set[str] = set()
    if cfg.enforce_wash_sale:
        blocked = _wash_sale_tickers(sim_dir)
        if blocked:
            logger.info("Wash-sale block (brokerage): %s", ", ".join(sorted(blocked)))

    all_candidates = rank_candidates(snapshot.stocks, held_tickers, blocked_tickers=blocked)

    # Filter by account-type confidence threshold before allocating
    min_rank = _CONFIDENCE_RANK.get(cfg.min_buy_confidence, 3)
    qualified = [
        s for s in all_candidates
        if _CONFIDENCE_RANK.get(_confidence(s, avg_momentum), 1) >= min_rank
    ]
    logger.info(
        "BUY candidates: %d total → %d pass %s confidence threshold (%s)",
        len(all_candidates), len(qualified), cfg.min_buy_confidence, portfolio.account_type.value,
    )

    allocations = compute_allocations(qualified, portfolio, freed_slots=freed, cfg=cfg)

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
            allocation_pct=cfg.rebalance_target_pct if e["trigger"] == "rebalance" else 0.0,
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
            f"regime: {regime} | BUY={n_buy} SELL={n_sell} HOLD={n_hold}"
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
