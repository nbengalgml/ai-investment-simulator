"""
Scheduler Agent — job definitions and NYSE calendar helpers.
Importable by tests and by main.py.
"""

import logging
import os
from datetime import date, datetime
from typing import Callable

import requests

logger = logging.getLogger(__name__)

_nyse_calendar = None


def _get_nyse():
    global _nyse_calendar
    if _nyse_calendar is None:
        import pandas_market_calendars as mcal
        _nyse_calendar = mcal.get_calendar("NYSE")
    return _nyse_calendar


def is_trading_day(dt: date) -> bool:
    """Return True if dt is a NYSE trading day (Mon–Fri, excludes holidays)."""
    try:
        nyse = _get_nyse()
        schedule = nyse.schedule(
            start_date=dt.isoformat(),
            end_date=dt.isoformat(),
        )
        return not schedule.empty
    except Exception as exc:
        logger.warning("NYSE calendar check failed (%s) — assuming trading day", exc)
        return dt.weekday() < 5  # weekday fallback


def trigger_agent(agent: str, api_base_url: str, payload: dict | None = None) -> bool:
    """
    POST to /agents/{agent}/trigger on the FastAPI server.
    Returns True on success (2xx), False otherwise.
    """
    url = f"{api_base_url.rstrip('/')}/agents/{agent}/trigger"
    try:
        resp = requests.post(url, json=payload or {}, timeout=30)
        resp.raise_for_status()
        logger.info("Triggered %s → %s", agent, resp.status_code)
        return True
    except Exception as exc:
        logger.error("Failed to trigger %s: %s", agent, exc)
        return False


def make_job(agent: str, api_base_url: str, sector: str, skip_holiday_check: bool = False) -> Callable:
    """
    Returns a callable that:
    1. Checks it's a NYSE trading day (unless skip_holiday_check=True)
    2. POSTs to /agents/{agent}/trigger with sector payload
    """
    def _job() -> None:
        today = date.today()
        if not skip_holiday_check and not is_trading_day(today):
            logger.info("Skipping %s — not a trading day (%s)", agent, today)
            return
        trigger_agent(agent, api_base_url, {"sector": sector})

    _job.__name__ = f"job_{agent.replace('-', '_')}"
    return _job


def register_jobs(scheduler, api_base_url: str, sector: str) -> None:
    """
    Register the full daily, weekly, and monthly job schedule.
    All times are in America/New_York (scheduler timezone).
    """
    tz = "America/New_York"

    daily = [
        # (hour, minute, agent)
        (5,  30, "market-researcher"),
        (6,   0, "ceo"),
        (9,  15, "market-researcher"),
        (9,  30, "analyst"),
        (13,  0, "market-researcher"),
        (13, 30, "analyst"),
        (15, 30, "market-researcher"),
        (16,  0, "analyst"),
        (16, 15, "ceo"),
        (16, 30, "qa-engineer"),
        (17,  0, "market-researcher"),  # report archiver — triggers snapshot
    ]

    for hour, minute, agent in daily:
        scheduler.add_job(
            make_job(agent, api_base_url, sector),
            trigger="cron",
            hour=hour,
            minute=minute,
            timezone=tz,
            id=f"daily_{agent}_{hour:02d}{minute:02d}",
            replace_existing=True,
            misfire_grace_time=300,
        )

    # Weekly: Monday 07:00 ET — CEO weekly review
    scheduler.add_job(
        make_job("ceo", api_base_url, sector),
        trigger="cron",
        day_of_week="mon",
        hour=7,
        minute=0,
        timezone=tz,
        id="weekly_ceo_review",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Monthly: 1st of month 06:00 ET — monthly report
    scheduler.add_job(
        make_job("ceo", api_base_url, sector),
        trigger="cron",
        day=1,
        hour=6,
        minute=0,
        timezone=tz,
        id="monthly_report",
        replace_existing=True,
        misfire_grace_time=600,
    )

    n = len(scheduler.get_jobs())
    logger.info("Registered %d jobs for sector '%s'", n, sector)


def run_dry_run(api_base_url: str, sector: str) -> list[str]:
    """
    Fire each unique agent once immediately (no holiday check).
    Returns list of agents that were triggered successfully.
    """
    agents_to_fire = [
        "market-researcher",
        "analyst",
        "ceo",
        "qa-engineer",
    ]
    results = []
    for agent in agents_to_fire:
        ok = trigger_agent(agent, api_base_url, {"sector": sector})
        if ok:
            results.append(agent)
        logger.info("Dry-run: %s → %s", agent, "OK" if ok else "FAILED")
    return results
