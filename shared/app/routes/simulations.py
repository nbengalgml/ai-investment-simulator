"""
/simulations — list and read data for all parallel simulation tracks.

Each sim_id = "{sector}-{account_type}", e.g. "AI-brokerage", "AI-traditional_ira".
Data lives under data/simulations/{sim_id}/.
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

import storage as _storage

router = APIRouter(prefix="/simulations", tags=["simulations"])


def _list_sim_ids() -> list[str]:
    sims_root = _storage.DATA_DIR / "simulations"
    if not sims_root.exists():
        return []
    return sorted(d.name for d in sims_root.iterdir() if d.is_dir())


def _read_sim_portfolio(sim_id: str) -> dict | None:
    path = _storage.sim_dir(sim_id) / "portfolio" / "state.json"
    if not path.exists():
        return None
    return _storage.read_json(path)


@router.get("")
async def list_simulations() -> list[dict]:
    """Return summary card for every known simulation."""
    result = []
    for sim_id in _list_sim_ids():
        portfolio = _read_sim_portfolio(sim_id)
        parts = sim_id.rsplit("-", 1)
        sector = parts[0] if len(parts) == 2 else sim_id
        account_type = parts[1] if len(parts) == 2 else "unknown"
        card: dict = {
            "sim_id": sim_id,
            "sector": sector,
            "account_type": account_type,
            "has_data": portfolio is not None,
        }
        if portfolio:
            card["total_market_value"] = portfolio.get("total_market_value", 0)
            card["budget_total"] = portfolio.get("budget_total", 0)
            card["total_unrealized_pnl"] = portfolio.get("total_unrealized_pnl", 0)
            card["total_unrealized_pnl_pct"] = portfolio.get("total_unrealized_pnl_pct", 0)
            card["cash_available"] = portfolio.get("cash_available", 0)
            card["holdings_count"] = len(portfolio.get("holdings", []))
            card["last_updated"] = portfolio.get("last_updated")
        result.append(card)
    return result


@router.get("/{sim_id}/portfolio")
async def get_portfolio(sim_id: str) -> dict:
    portfolio = _read_sim_portfolio(sim_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"No portfolio data for sim '{sim_id}'")
    return portfolio


@router.get("/{sim_id}/portfolio/history")
async def get_portfolio_history(sim_id: str) -> list[dict]:
    hist_dir = _storage.sim_dir(sim_id) / "portfolio" / "history"
    if not hist_dir.exists():
        return []
    files = sorted(hist_dir.glob("*.json"))
    return [_storage.read_json(f) for f in files]


@router.get("/{sim_id}/trades")
async def get_trades(sim_id: str) -> list[dict]:
    path = _storage.sim_dir(sim_id) / "trades" / "log.json"
    if not path.exists():
        return []
    entries = _storage.read_json(path)
    return sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)


@router.get("/{sim_id}/reports/daily")
async def list_daily_reports(sim_id: str) -> list[dict]:
    reports_dir = _storage.sim_dir(sim_id) / "reports" / "daily"
    if not reports_dir.exists():
        return []
    files = sorted(reports_dir.glob("*.json"), reverse=True)
    return [_storage.read_json(f) for f in files]


@router.get("/{sim_id}/reports/daily/{report_date}")
async def get_daily_report(sim_id: str, report_date: str) -> dict:
    reports_dir = _storage.sim_dir(sim_id) / "reports" / "daily"
    matches = sorted(reports_dir.glob(f"{report_date}*.json"), reverse=True)
    if not matches:
        raise HTTPException(status_code=404, detail=f"No report for {report_date} in sim '{sim_id}'")
    return _storage.read_json(matches[0])
