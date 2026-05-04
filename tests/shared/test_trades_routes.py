"""Tests for GET /trades and GET|POST /settings endpoints."""

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

_TRADE = {
    "trade_id": "abc-123",
    "timestamp": "2026-05-03T09:35:00Z",
    "action": "BUY",
    "ticker": "NVDA",
    "shares": 2.5,
    "price": 850.0,
    "total_value": 2125.0,
    "rationale": "Strong momentum signal.",
    "data_sources": ["yfinance", "newsapi"],
    "approved_by": "CEO",
    "account_type": "brokerage",
    "simulated_tax_impact": {"holding_period_days": 0, "gain_loss": 0.0, "tax_treatment": "n/a"},
}


def _write_trades(tmp_path: Path, trades: list) -> None:
    log = tmp_path / "trades" / "log.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(trades))


# ── GET /trades ────────────────────────────────────────────────────────────────

def test_get_trades_empty_when_no_file(tmp_path):
    import app.routes.trades as _route
    _route.DATA_DIR = tmp_path
    resp = client.get("/trades")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_trades_returns_entries(tmp_path):
    import app.routes.trades as _route
    _route.DATA_DIR = tmp_path
    _write_trades(tmp_path, [_TRADE, {**_TRADE, "trade_id": "xyz-456"}])
    resp = client.get("/trades")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_trades_sorted_newest_first(tmp_path):
    import app.routes.trades as _route
    _route.DATA_DIR = tmp_path
    _write_trades(tmp_path, [
        {**_TRADE, "timestamp": "2026-05-01T10:00:00Z"},
        {**_TRADE, "timestamp": "2026-05-03T10:00:00Z"},
        {**_TRADE, "timestamp": "2026-05-02T10:00:00Z"},
    ])
    resp = client.get("/trades")
    timestamps = [t["timestamp"] for t in resp.json()]
    assert timestamps == sorted(timestamps, reverse=True)


# ── GET /settings ──────────────────────────────────────────────────────────────

def test_get_settings_returns_defaults(tmp_path):
    import app.routes.settings as _route
    _route.DATA_DIR = tmp_path
    resp = client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["budget_total"] == 10000.0
    assert body["account_type"] == "brokerage"
    assert body["target_market"] == "AI"


# ── POST /settings ─────────────────────────────────────────────────────────────

def test_post_settings_updates_budget(tmp_path):
    import app.routes.settings as _route
    _route.DATA_DIR = tmp_path
    resp = client.post("/settings", json={"budget_total": 25000.0})
    assert resp.status_code == 200
    assert resp.json()["budget_total"] == 25000.0


def test_post_settings_updates_account_type(tmp_path):
    import app.routes.settings as _route
    _route.DATA_DIR = tmp_path
    resp = client.post("/settings", json={"account_type": "traditional_ira"})
    assert resp.status_code == 200
    assert resp.json()["account_type"] == "traditional_ira"


def test_post_settings_invalid_account_type_returns_422(tmp_path):
    import app.routes.settings as _route
    _route.DATA_DIR = tmp_path
    resp = client.post("/settings", json={"account_type": "roth_ira"})
    assert resp.status_code == 422


def test_post_settings_updates_target_market(tmp_path):
    import app.routes.settings as _route
    _route.DATA_DIR = tmp_path
    resp = client.post("/settings", json={"target_market": "Cloud"})
    assert resp.status_code == 200
    assert resp.json()["target_market"] == "Cloud"


def test_post_settings_persists_across_gets(tmp_path):
    import app.routes.settings as _route
    _route.DATA_DIR = tmp_path
    client.post("/settings", json={"budget_total": 50000.0, "target_market": "Finance"})
    resp = client.get("/settings")
    assert resp.json()["budget_total"] == 50000.0
    assert resp.json()["target_market"] == "Finance"


def test_post_settings_partial_update_preserves_other_fields(tmp_path):
    import app.routes.settings as _route
    _route.DATA_DIR = tmp_path
    client.post("/settings", json={"budget_total": 20000.0})
    resp = client.post("/settings", json={"target_market": "Gas"})
    body = resp.json()
    assert body["budget_total"] == 20000.0
    assert body["target_market"] == "Gas"
