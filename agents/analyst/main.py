#!/usr/bin/env python3
"""Analyst Agent — entry point."""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)

for _candidate in [Path("/app/shared"), Path(__file__).parent.parent.parent / "shared"]:
    if _candidate.is_dir() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))
        break

import storage as _storage  # noqa: E402
from data_models import AccountType, PortfolioState, MarketResearchSnapshot  # noqa: E402
from analysis import run_analysis  # noqa: E402


def _load_latest_snapshot(sector: str) -> MarketResearchSnapshot | None:
    snapshots_dir = _storage.DATA_DIR / "research" / "market_snapshots"
    files = sorted(snapshots_dir.glob(f"*_{sector}.json"), reverse=True)
    if not files:
        logging.error("No snapshot found for sector '%s' in %s", sector, snapshots_dir)
        return None
    data = _storage.read_json(files[0])
    return MarketResearchSnapshot.model_validate(data)


def _load_portfolio() -> PortfolioState:
    state_path = _storage.DATA_DIR / "portfolio" / "state.json"
    if not state_path.exists():
        budget = float(os.getenv("DEFAULT_BUDGET", "10000"))
        return PortfolioState(
            account_type=AccountType(os.getenv("DEFAULT_ACCOUNT_TYPE", "brokerage")),
            target_market=os.getenv("DEFAULT_TARGET_MARKET", "AI"),
            budget_total=budget,
            cash_available=budget,
            last_updated=datetime.now(timezone.utc),
            holdings=[],
            total_market_value=0.0,
            total_unrealized_pnl=0.0,
            total_unrealized_pnl_pct=0.0,
        )
    return PortfolioState.model_validate(_storage.read_json(state_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyst Agent")
    parser.add_argument(
        "--sector",
        default=os.getenv("DEFAULT_TARGET_MARKET", "AI"),
        help="Sector matching the latest Market Researcher snapshot",
    )
    parser.add_argument("--no-claude", action="store_true")
    args = parser.parse_args()

    snapshot = _load_latest_snapshot(args.sector)
    if snapshot is None:
        sys.exit(1)

    portfolio = _load_portfolio()
    report = run_analysis(snapshot, portfolio, use_claude=not args.no_claude)

    buys = [r for r in report.recommendations if r.action == "BUY"]
    sells = [r for r in report.recommendations if r.action == "SELL"]
    holds = [r for r in report.recommendations if r.action == "HOLD"]
    print(
        f"Report: {report.report_id} | "
        f"BUY={len(buys)} SELL={len(sells)} HOLD={len(holds)} | "
        f"invested={report.total_invested_pct:.1f}% cash={report.cash_reserve_pct:.1f}%"
    )
    for r in buys:
        print(f"  BUY  {r.ticker:6s} {r.allocation_pct:.1f}% [{r.confidence}]  score={r.composite_score:.0f}")


if __name__ == "__main__":
    main()
