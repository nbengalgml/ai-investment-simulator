"""
Tests for the Scheduler agent — jobs.py.
No real HTTP calls; trigger_agent is mocked.
"""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SCHEDULER = Path(__file__).parent.parent.parent / "agents" / "scheduler"
if str(_SCHEDULER) not in sys.path:
    sys.path.insert(0, str(_SCHEDULER))

from jobs import is_trading_day, make_job, register_jobs, run_dry_run, trigger_agent


# ── is_trading_day ─────────────────────────────────────────────────────────────

def test_trading_day_weekday():
    assert is_trading_day(date(2026, 5, 4)) is True   # Monday


def test_not_trading_day_saturday():
    assert is_trading_day(date(2026, 5, 2)) is False  # Saturday


def test_not_trading_day_sunday():
    assert is_trading_day(date(2026, 5, 3)) is False  # Sunday


def test_not_trading_day_nyse_holiday():
    # July 4th 2026 falls on a Saturday, so the holiday is observed on Friday July 3rd
    assert is_trading_day(date(2026, 7, 3)) is False


def test_trading_day_regular_friday():
    assert is_trading_day(date(2026, 5, 1)) is True   # Friday


def test_not_trading_day_thanksgiving():
    # Thanksgiving 2026: November 26
    assert is_trading_day(date(2026, 11, 26)) is False


def test_trading_day_black_friday():
    # Day after Thanksgiving 2026: November 27 — NYSE closes early but IS a trading day
    assert is_trading_day(date(2026, 11, 27)) is True


# ── trigger_agent ──────────────────────────────────────────────────────────────

def test_trigger_agent_success():
    with patch("jobs.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
        result = trigger_agent("analyst", "http://api:8000", {"sector": "AI"})
    assert result is True


def test_trigger_agent_http_error():
    import requests as _requests
    with patch("jobs.requests.post") as mock_post:
        mock_post.side_effect = _requests.exceptions.ConnectionError("refused")
        result = trigger_agent("analyst", "http://api:8000")
    assert result is False


def test_trigger_agent_server_error():
    import requests as _requests
    with patch("jobs.requests.post") as mock_post:
        resp = MagicMock()
        resp.raise_for_status.side_effect = _requests.exceptions.HTTPError("500")
        mock_post.return_value = resp
        result = trigger_agent("analyst", "http://api:8000")
    assert result is False


def test_trigger_agent_builds_correct_url():
    with patch("jobs.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
        trigger_agent("market-researcher", "http://api:8000")
    called_url = mock_post.call_args[0][0]
    assert called_url == "http://api:8000/agents/market-researcher/trigger"


def test_trigger_agent_trailing_slash_in_base():
    with patch("jobs.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
        trigger_agent("analyst", "http://api:8000/")
    called_url = mock_post.call_args[0][0]
    assert called_url == "http://api:8000/agents/analyst/trigger"


# ── make_job ───────────────────────────────────────────────────────────────────

def test_make_job_skips_on_non_trading_day():
    with patch("jobs.is_trading_day", return_value=False), \
         patch("jobs.trigger_agent") as mock_trigger:
        job = make_job("analyst", "http://api:8000", "AI")
        job()
    mock_trigger.assert_not_called()


def test_make_job_triggers_on_trading_day():
    with patch("jobs.is_trading_day", return_value=True), \
         patch("jobs.trigger_agent") as mock_trigger:
        mock_trigger.return_value = True
        job = make_job("analyst", "http://api:8000", "AI")
        job()
    mock_trigger.assert_called_once_with("analyst", "http://api:8000", {"sector": "AI"})


def test_make_job_skip_holiday_check():
    with patch("jobs.is_trading_day") as mock_cal, \
         patch("jobs.trigger_agent") as mock_trigger:
        mock_trigger.return_value = True
        job = make_job("analyst", "http://api:8000", "AI", skip_holiday_check=True)
        job()
    mock_cal.assert_not_called()
    mock_trigger.assert_called_once()


def test_make_job_passes_sector():
    with patch("jobs.is_trading_day", return_value=True), \
         patch("jobs.trigger_agent") as mock_trigger:
        mock_trigger.return_value = True
        job = make_job("ceo", "http://api:8000", "cloud")
        job()
    _, _, payload = mock_trigger.call_args[0]
    assert payload["sector"] == "cloud"


# ── register_jobs ──────────────────────────────────────────────────────────────

def test_register_jobs_count():
    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = [MagicMock()] * 13  # 11 daily + 1 weekly + 1 monthly
    register_jobs(mock_scheduler, "http://api:8000", "AI")
    # 11 daily + 1 weekly + 1 monthly = 13 add_job calls
    assert mock_scheduler.add_job.call_count == 13


def test_register_jobs_all_use_cron_trigger():
    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = []
    register_jobs(mock_scheduler, "http://api:8000", "AI")
    for call in mock_scheduler.add_job.call_args_list:
        assert call.kwargs.get("trigger") == "cron"


def test_register_jobs_have_unique_ids():
    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = []
    register_jobs(mock_scheduler, "http://api:8000", "AI")
    ids = [call.kwargs.get("id") for call in mock_scheduler.add_job.call_args_list]
    assert len(ids) == len(set(ids)), "Duplicate job IDs found"


def test_register_jobs_weekly_uses_day_of_week():
    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = []
    register_jobs(mock_scheduler, "http://api:8000", "AI")
    weekly = [
        call for call in mock_scheduler.add_job.call_args_list
        if call.kwargs.get("id") == "weekly_ceo_review"
    ]
    assert len(weekly) == 1
    assert weekly[0].kwargs["day_of_week"] == "mon"


def test_register_jobs_monthly_uses_day_1():
    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = []
    register_jobs(mock_scheduler, "http://api:8000", "AI")
    monthly = [
        call for call in mock_scheduler.add_job.call_args_list
        if call.kwargs.get("id") == "monthly_report"
    ]
    assert len(monthly) == 1
    assert monthly[0].kwargs["day"] == 1


# ── run_dry_run ────────────────────────────────────────────────────────────────

def test_dry_run_triggers_all_agents():
    with patch("jobs.trigger_agent", return_value=True) as mock_trigger:
        results = run_dry_run("http://api:8000", "AI")
    agents_called = [call[0][0] for call in mock_trigger.call_args_list]
    assert "market-researcher" in agents_called
    assert "analyst" in agents_called
    assert "ceo" in agents_called
    assert "qa-engineer" in agents_called


def test_dry_run_returns_successful_agents():
    def _side_effect(agent, url, payload=None):
        return agent != "qa-engineer"

    with patch("jobs.trigger_agent", side_effect=_side_effect):
        results = run_dry_run("http://api:8000", "AI")
    assert "qa-engineer" not in results
    assert "analyst" in results


def test_dry_run_partial_failure_continues():
    import requests as _requests
    call_count = 0

    def _side_effect(agent, url, payload=None):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            return False
        return True

    with patch("jobs.trigger_agent", side_effect=_side_effect):
        results = run_dry_run("http://api:8000", "AI")
    assert call_count == 4  # all 4 agents attempted despite one failure
