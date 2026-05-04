"""
Tests for POST /agents/{agent}/trigger FastAPI endpoints.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

_SHARED = Path(__file__).parent.parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from app.main import app

client = TestClient(app)


# ── /agents/status ────────────────────────────────────────────────────────────

def test_agents_status_returns_dict():
    resp = client.get("/agents/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "market-researcher" in data
    assert "analyst" in data
    assert "ceo" in data
    assert "qa-engineer" in data


def test_agents_status_values_are_bool():
    resp = client.get("/agents/status")
    for key, val in resp.json().items():
        assert isinstance(val, bool), f"{key} should be bool"


# ── POST /agents/{agent}/trigger ──────────────────────────────────────────────

def test_trigger_unknown_agent_returns_404():
    resp = client.post("/agents/unknown-agent/trigger", json={"sector": "AI"})
    assert resp.status_code == 404


def test_trigger_known_agent_missing_script_returns_503(tmp_path):
    with patch("app.routes.agents.AGENTS_DIR", tmp_path):
        resp = client.post("/agents/analyst/trigger", json={"sector": "AI"})
    assert resp.status_code == 503


def test_trigger_analyst_accepted(tmp_path):
    # Create a fake script so the existence check passes
    script_dir = tmp_path / "analyst"
    script_dir.mkdir(parents=True)
    (script_dir / "main.py").write_text("print('ok')")

    with patch("app.routes.agents.AGENTS_DIR", tmp_path), \
         patch("app.routes.agents._run_agent", new_callable=AsyncMock):
        resp = client.post("/agents/analyst/trigger", json={"sector": "AI"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["agent"] == "analyst"


def test_trigger_market_researcher_accepted(tmp_path):
    script_dir = tmp_path / "market-researcher"
    script_dir.mkdir(parents=True)
    (script_dir / "main.py").write_text("print('ok')")

    with patch("app.routes.agents.AGENTS_DIR", tmp_path), \
         patch("app.routes.agents._run_agent", new_callable=AsyncMock):
        resp = client.post("/agents/market-researcher/trigger", json={"sector": "cloud"})

    assert resp.status_code == 200
    assert resp.json()["agent"] == "market-researcher"


def test_trigger_ceo_accepted(tmp_path):
    script_dir = tmp_path / "ceo"
    script_dir.mkdir(parents=True)
    (script_dir / "main.py").write_text("print('ok')")

    with patch("app.routes.agents.AGENTS_DIR", tmp_path), \
         patch("app.routes.agents._run_agent", new_callable=AsyncMock):
        resp = client.post("/agents/ceo/trigger", json={"sector": "AI"})

    assert resp.status_code == 200


def test_trigger_default_sector_is_ai(tmp_path):
    script_dir = tmp_path / "analyst"
    script_dir.mkdir(parents=True)
    (script_dir / "main.py").write_text("")

    captured = {}

    async def _capture(script, sector, no_claude):
        captured["sector"] = sector

    with patch("app.routes.agents.AGENTS_DIR", tmp_path), \
         patch("app.routes.agents._run_agent", side_effect=_capture):
        # No sector in payload — should default to "AI"
        resp = client.post("/agents/analyst/trigger", json={})

    assert resp.status_code == 200
    assert captured.get("sector") == "AI"


def test_trigger_no_claude_flag(tmp_path):
    script_dir = tmp_path / "analyst"
    script_dir.mkdir(parents=True)
    (script_dir / "main.py").write_text("")

    captured = {}

    async def _capture(script, sector, no_claude):
        captured["no_claude"] = no_claude

    with patch("app.routes.agents.AGENTS_DIR", tmp_path), \
         patch("app.routes.agents._run_agent", side_effect=_capture):
        resp = client.post("/agents/analyst/trigger", json={"sector": "AI", "no_claude": True})

    assert resp.status_code == 200
    assert captured.get("no_claude") is True


def test_trigger_response_includes_sector_in_message(tmp_path):
    script_dir = tmp_path / "analyst"
    script_dir.mkdir(parents=True)
    (script_dir / "main.py").write_text("")

    with patch("app.routes.agents.AGENTS_DIR", tmp_path), \
         patch("app.routes.agents._run_agent", new_callable=AsyncMock):
        resp = client.post("/agents/analyst/trigger", json={"sector": "cloud"})

    assert "cloud" in resp.json()["message"]
