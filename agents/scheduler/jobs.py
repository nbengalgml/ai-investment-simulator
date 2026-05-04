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

# All sectors and account types covered by autonomous scheduling
ALL_SECTORS = ["AI", "cloud", "networking", "alternative_energy", "gas", "finance"]
ALL_ACCOUNT_TYPES = ["brokerage", "traditional_ira"]

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


def make_researcher_job(api_base_url: str) -> Callable:
    """
    Fire market-researcher once per sector (6 total).
    Market data is sector-scoped but account-type agnostic — one snapshot serves both IRA and brokerage.
    """
    def _job() -> None:
        today = date.today()
        if not is_trading_day(today):
            logger.info("Skipping market-researcher — not a trading day (%s)", today)
            return
        for sector in ALL_SECTORS:
            trigger_agent("market-researcher", api_base_url, {"sector": sector, "account_type": "brokerage"})
    _job.__name__ = "job_market_researcher_all_sectors"
    return _job


def make_analyst_job(api_base_url: str) -> Callable:
    """Fire analyst for all 12 sims (6 sectors × 2 account types)."""
    def _job() -> None:
        today = date.today()
        if not is_trading_day(today):
            logger.info("Skipping analyst — not a trading day (%s)", today)
            return
        for sector in ALL_SECTORS:
            for acct in ALL_ACCOUNT_TYPES:
                trigger_agent("analyst", api_base_url, {"sector": sector, "account_type": acct})
    _job.__name__ = "job_analyst_all_sims"
    return _job


def make_ceo_job(api_base_url: str) -> Callable:
    """Fire CEO for all 12 sims (6 sectors × 2 account types)."""
    def _job() -> None:
        today = date.today()
        if not is_trading_day(today):
            logger.info("Skipping ceo — not a trading day (%s)", today)
            return
        for sector in ALL_SECTORS:
            for acct in ALL_ACCOUNT_TYPES:
                trigger_agent("ceo", api_base_url, {"sector": sector, "account_type": acct})
    _job.__name__ = "job_ceo_all_sims"
    return _job


def register_jobs(scheduler, api_base_url: str, sector: str = "AI") -> None:
    """
    Register the full daily, weekly, and monthly job schedule covering all 12 simulations.
    All times are in America/New_York (scheduler timezone).

    Daily cycle (market hours):
      05:30  market-researcher  — pre-market snapshot for all 6 sectors
      09:15  market-researcher  — pre-open refresh
      09:30  analyst            — opening analysis for all 12 sims
      13:00  market-researcher  — midday snapshot
      13:30  analyst            — midday re-evaluation
      15:30  market-researcher  — end-of-day data
      16:00  analyst            — close-of-day analysis
      16:15  ceo                — execute approved trades for all 12 sims
      16:30  market-researcher  — after-hours snapshot (for next morning)

    Weekly: Monday 06:00 — CEO reviews all sims (broader review, can add context)
    Monthly: 1st of month 06:00 — CEO generates monthly summary for all sims
    """
    tz = "America/New_York"

    # Daily jobs — all cover all 12 sims
    scheduler.add_job(
        make_researcher_job(api_base_url), trigger="cron",
        hour=5, minute=30, timezone=tz,
        id="daily_researcher_0530", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        make_researcher_job(api_base_url), trigger="cron",
        hour=9, minute=15, timezone=tz,
        id="daily_researcher_0915", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        make_analyst_job(api_base_url), trigger="cron",
        hour=9, minute=30, timezone=tz,
        id="daily_analyst_0930", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        make_researcher_job(api_base_url), trigger="cron",
        hour=13, minute=0, timezone=tz,
        id="daily_researcher_1300", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        make_analyst_job(api_base_url), trigger="cron",
        hour=13, minute=30, timezone=tz,
        id="daily_analyst_1330", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        make_researcher_job(api_base_url), trigger="cron",
        hour=15, minute=30, timezone=tz,
        id="daily_researcher_1530", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        make_analyst_job(api_base_url), trigger="cron",
        hour=16, minute=0, timezone=tz,
        id="daily_analyst_1600", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        make_ceo_job(api_base_url), trigger="cron",
        hour=16, minute=15, timezone=tz,
        id="daily_ceo_1615", replace_existing=True, misfire_grace_time=300,
    )
    scheduler.add_job(
        make_researcher_job(api_base_url), trigger="cron",
        hour=16, minute=30, timezone=tz,
        id="daily_researcher_1630", replace_existing=True, misfire_grace_time=300,
    )

    # Weekly: Monday 06:00 ET — broad CEO review of all sims
    scheduler.add_job(
        make_ceo_job(api_base_url), trigger="cron",
        day_of_week="mon", hour=6, minute=0, timezone=tz,
        id="weekly_ceo_review", replace_existing=True, misfire_grace_time=600,
    )

    # Monthly: 1st of month 06:00 ET — monthly summary for all sims
    scheduler.add_job(
        make_ceo_job(api_base_url), trigger="cron",
        day=1, hour=6, minute=0, timezone=tz,
        id="monthly_report", replace_existing=True, misfire_grace_time=600,
    )

    n = len(scheduler.get_jobs())
    logger.info("Registered %d jobs covering %d sims (%d sectors × %d account types)",
                n, len(ALL_SECTORS) * len(ALL_ACCOUNT_TYPES), len(ALL_SECTORS), len(ALL_ACCOUNT_TYPES))


def run_dry_run(api_base_url: str, sector: str = "AI") -> list[str]:
    """
    Fire one full cycle for all 12 sims immediately (no holiday check).
    Returns list of agents that triggered successfully.
    """
    results = []
    for s in ALL_SECTORS:
        ok = trigger_agent("market-researcher", api_base_url, {"sector": s, "account_type": "brokerage"})
        if ok:
            results.append(f"market-researcher/{s}")

    for s in ALL_SECTORS:
        for acct in ALL_ACCOUNT_TYPES:
            ok = trigger_agent("analyst", api_base_url, {"sector": s, "account_type": acct})
            if ok:
                results.append(f"analyst/{s}/{acct}")

    for s in ALL_SECTORS:
        for acct in ALL_ACCOUNT_TYPES:
            ok = trigger_agent("ceo", api_base_url, {"sector": s, "account_type": acct})
            if ok:
                results.append(f"ceo/{s}/{acct}")

    logger.info("Dry-run complete: %d/%d triggers succeeded",
                len(results), len(ALL_SECTORS) + len(ALL_SECTORS) * len(ALL_ACCOUNT_TYPES) * 2)
    return results
