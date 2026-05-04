#!/usr/bin/env python3
"""CEO Agent — entry point."""

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
from data_models import AccountType, AnalystReport, MarketResearchSnapshot, PortfolioState  # noqa: E402
from decisions import run_ceo_cycle  # noqa: E402


def _load_latest_analyst_report() -> AnalystReport | None:
    recs_dir = _storage.DATA_DIR / "research" / "recommendations"
    files = sorted(recs_dir.glob("*.json"), reverse=True)
    if not files:
        logging.error("No analyst report found in %s", recs_dir)
        return None
    return AnalystReport.model_validate(_storage.read_json(files[0]))


def _load_latest_snapshot(sector: str) -> MarketResearchSnapshot | None:
    snapshots_dir = _storage.DATA_DIR / "research" / "market_snapshots"
    files = sorted(snapshots_dir.glob(f"*_{sector}.json"), reverse=True)
    if not files:
        logging.error("No snapshot found for sector '%s'", sector)
        return None
    return MarketResearchSnapshot.model_validate(_storage.read_json(files[0]))


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
    parser = argparse.ArgumentParser(description="CEO Agent")
    parser.add_argument(
        "--sector",
        default=os.getenv("DEFAULT_TARGET_MARKET", "AI"),
        help="Sector for the market snapshot",
    )
    parser.add_argument("--no-claude", action="store_true")
    args = parser.parse_args()

    analyst_report = _load_latest_analyst_report()
    if analyst_report is None:
        sys.exit(1)

    snapshot = _load_latest_snapshot(args.sector)
    if snapshot is None:
        sys.exit(1)

    portfolio = _load_portfolio()
    daily_report, updated_portfolio, trade_log = run_ceo_cycle(
        analyst_report, portfolio, snapshot, use_claude=not args.no_claude
    )

    print(f"\nCEO Daily Report — {daily_report.report_date}")
    print(f"  P&L: ${daily_report.portfolio_performance.day_pnl:+.2f} "
          f"({daily_report.portfolio_performance.day_pnl_pct:+.2f}%)")
    print(f"  Trades executed: {len(trade_log)}")
    print(f"  Holdings: {len(updated_portfolio.holdings)} | "
          f"Cash: ${updated_portfolio.cash_available:,.2f}")
    print(f"\n{daily_report.executive_summary}")
    if trade_log:
        print("\nTrades:")
        for t in trade_log:
            print(f"  {t.action.value:4s} {t.ticker:6s} {t.shares:.3f}sh @ ${t.price:.2f} = ${t.total_value:,.2f}")


if __name__ == "__main__":
    main()
