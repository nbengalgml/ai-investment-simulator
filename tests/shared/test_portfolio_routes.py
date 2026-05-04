"""Tests for GET /portfolio and GET /portfolio/history FastAPI endpoints."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_SHARED = Path(__file__).parent.parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from app.main import app

client = TestClient(app)


def _write_portfolio(tmp_path: Path, data: dict) -> None:
    state = tmp_path / "portfolio" / "state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps(data))


def _write_history(tmp_path: Path, snapshots: list[dict]) -> None:
    history = tmp_path / "portfolio" / "history"
    history.mkdir(parents=True, exist_ok=True)
    for i, snap in enumerate(snapshots):
        (history / f"2026-05-{i+1:02d}.json").write_text(json.dumps(snap))


_MINIMAL = {
    "account_type": "brokerage",
    "target_market": "AI",
    "budget_total": 10000.0,
    "cash_available": 10000.0,
    "last_updated": "2026-05-03T16:00:00Z",
    "holdings": [],
    "total_market_value": 0.0,
    "total_unrealized_pnl": 0.0,
    "total_unrealized_pnl_pct": 0.0,
    "strategy": "growth",
    "max_positions": 5,
}


# ── GET /portfolio ─────────────────────────────────────────────────────────────

def test_get_portfolio_404_when_missing(tmp_path):
    import app.routes.portfolio as _route
    _route.DATA_DIR = tmp_path
    resp = client.get("/portfolio")
    assert resp.status_code == 404


def test_get_portfolio_returns_state(tmp_path):
    import app.routes.portfolio as _route
    _route.DATA_DIR = tmp_path
    _write_portfolio(tmp_path, _MINIMAL)
    resp = client.get("/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_type"] == "brokerage"
    assert body["budget_total"] == 10000.0


def test_get_portfolio_has_holdings_key(tmp_path):
    import app.routes.portfolio as _route
    _route.DATA_DIR = tmp_path
    _write_portfolio(tmp_path, _MINIMAL)
    resp = client.get("/portfolio")
    assert "holdings" in resp.json()


# ── GET /portfolio/history ─────────────────────────────────────────────────────

def test_get_portfolio_history_empty_when_no_dir(tmp_path):
    import app.routes.portfolio as _route
    _route.DATA_DIR = tmp_path
    resp = client.get("/portfolio/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_portfolio_history_returns_all_snapshots(tmp_path):
    import app.routes.portfolio as _route
    _route.DATA_DIR = tmp_path
    _write_history(tmp_path, [_MINIMAL, _MINIMAL, _MINIMAL])
    resp = client.get("/portfolio/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_get_portfolio_history_sorted_by_date(tmp_path):
    import app.routes.portfolio as _route
    _route.DATA_DIR = tmp_path
    snap1 = {**_MINIMAL, "last_updated": "2026-05-01T00:00:00Z"}
    snap2 = {**_MINIMAL, "last_updated": "2026-05-02T00:00:00Z"}
    _write_history(tmp_path, [snap1, snap2])
    resp = client.get("/portfolio/history")
    dates = [s["last_updated"] for s in resp.json()]
    assert dates == sorted(dates)
