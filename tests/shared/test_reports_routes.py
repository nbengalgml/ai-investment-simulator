"""Tests for GET /reports/daily endpoints."""

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

_REPORT = {
    "report_date": "2026-05-03",
    "generated_at": "2026-05-03T16:20:00Z",
    "executive_summary": "Strong day for AI sector.",
    "market_conditions": "Bullish momentum across sector.",
    "portfolio_performance": {"day_pnl": 285.0, "day_pnl_pct": 2.14, "total_unrealized_pnl": 500.0},
    "actions_taken": [],
    "top_signals": [],
    "recommendations_pending": [],
    "next_day_watchlist": ["AMD", "PLTR"],
}


def _write_report(tmp_path: Path, report: dict, filename: str | None = None) -> None:
    d = tmp_path / "reports" / "daily"
    d.mkdir(parents=True, exist_ok=True)
    name = filename or f"{report['report_date']}_executive_summary.json"
    (d / name).write_text(json.dumps(report))


# ── GET /reports/daily ────────────────────────────────────────────────────────

def test_list_daily_reports_empty_when_no_dir(tmp_path):
    import app.routes.reports as _route
    _route.DATA_DIR = tmp_path
    resp = client.get("/reports/daily")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_daily_reports_returns_all(tmp_path):
    import app.routes.reports as _route
    _route.DATA_DIR = tmp_path
    for d in ["2026-05-01", "2026-05-02", "2026-05-03"]:
        _write_report(tmp_path, {**_REPORT, "report_date": d})
    resp = client.get("/reports/daily")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_list_daily_reports_newest_first(tmp_path):
    import app.routes.reports as _route
    _route.DATA_DIR = tmp_path
    for d in ["2026-05-01", "2026-05-02", "2026-05-03"]:
        _write_report(tmp_path, {**_REPORT, "report_date": d})
    resp = client.get("/reports/daily")
    dates = [r["report_date"] for r in resp.json()]
    assert dates == sorted(dates, reverse=True)


# ── GET /reports/daily/{date} ─────────────────────────────────────────────────

def test_get_daily_report_404(tmp_path):
    import app.routes.reports as _route
    _route.DATA_DIR = tmp_path
    resp = client.get("/reports/daily/2026-05-03")
    assert resp.status_code == 404


def test_get_daily_report_returns_report(tmp_path):
    import app.routes.reports as _route
    _route.DATA_DIR = tmp_path
    _write_report(tmp_path, _REPORT)
    resp = client.get("/reports/daily/2026-05-03")
    assert resp.status_code == 200
    assert resp.json()["executive_summary"] == "Strong day for AI sector."


def test_get_daily_report_has_watchlist(tmp_path):
    import app.routes.reports as _route
    _route.DATA_DIR = tmp_path
    _write_report(tmp_path, _REPORT)
    resp = client.get("/reports/daily/2026-05-03")
    assert "AMD" in resp.json()["next_day_watchlist"]
