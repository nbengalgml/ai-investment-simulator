"""
/simulations — list and read data for all parallel simulation tracks.

Each sim_id = "{sector}-{account_type}", e.g. "AI-brokerage", "AI-traditional_ira".
Data lives under data/simulations/{sim_id}/.
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException

import storage as _storage

logger = logging.getLogger(__name__)

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


def _fetch_live_prices(tickers: list[str]) -> dict[str, float]:
    """Batch-fetch current prices via yfinance. Returns {ticker: price}."""
    if not tickers:
        return {}
    try:
        import pandas as pd
        import yfinance as yf

        raw = yf.download(tickers, period="1d", auto_adjust=True, progress=False, threads=True)

        # Normalise to a DataFrame whose columns are ticker symbols
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            # Single ticker downloaded without list → Series or flat DataFrame
            close = raw[["Close"]].rename(columns={"Close": tickers[0]})

        live: dict[str, float] = {}
        for t in tickers:
            if t in close.columns:
                col = close[t].dropna()
                if not col.empty:
                    live[t] = float(col.iloc[-1])
        return live
    except Exception as exc:
        logger.warning("Live price fetch failed for %s: %s", tickers, exc)
        return {}


def _apply_prices(portfolio: dict, live: dict[str, float]) -> dict:
    """Recompute holding-level and portfolio-level values using fetched prices."""
    holdings = portfolio.get("holdings", [])
    budget = portfolio.get("budget_total", 0)
    for h in holdings:
        price = live.get(h["ticker"])
        if not price:
            continue
        cost = h.get("avg_cost_basis", price)
        shares = h.get("shares", 0)
        mv = round(price * shares, 2)
        h["current_price"] = price
        h["market_value"] = mv
        h["unrealized_pnl"] = round((price - cost) * shares, 2)
        h["unrealized_pnl_pct"] = round((price - cost) / cost * 100.0 if cost else 0.0, 4)
        h["allocation_pct"] = round(mv / budget * 100.0, 2) if budget else h.get("allocation_pct", 0)

    if holdings:
        total_mv = round(sum(h["market_value"] for h in holdings), 2)
        total_pnl = round(sum(h["unrealized_pnl"] for h in holdings), 2)
        portfolio["total_market_value"] = total_mv
        portfolio["total_unrealized_pnl"] = total_pnl
        portfolio["total_unrealized_pnl_pct"] = round(
            total_pnl / total_mv * 100.0 if total_mv else 0.0, 2
        )
    return portfolio


@router.get("")
async def list_simulations() -> list[dict]:
    """Return summary card for every known simulation, enriched with live prices."""
    sim_ids = _list_sim_ids()
    portfolios = {sid: _read_sim_portfolio(sid) for sid in sim_ids}

    # Collect all unique tickers across all sims for a single batch fetch
    all_tickers: list[str] = []
    seen: set[str] = set()
    for p in portfolios.values():
        if p:
            for h in p.get("holdings", []):
                t = h["ticker"]
                if t not in seen:
                    all_tickers.append(t)
                    seen.add(t)

    if all_tickers:
        live = await asyncio.to_thread(_fetch_live_prices, all_tickers)
    else:
        live = {}

    result = []
    for sim_id in sim_ids:
        portfolio = portfolios.get(sim_id)
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
            portfolio = _apply_prices(portfolio, live)
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
    tickers = [h["ticker"] for h in portfolio.get("holdings", [])]
    if tickers:
        live = await asyncio.to_thread(_fetch_live_prices, tickers)
        portfolio = _apply_prices(portfolio, live)
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
