"""Scheduler Agent — entry point."""

import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("scheduler")

TIMEZONE = os.getenv("TIMEZONE", "America/New_York")
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
DEFAULT_SECTOR = os.getenv("DEFAULT_TARGET_MARKET", "AI")


async def _startup_cycle(api_base_url: str) -> None:
    """Fire one full research→analyst→CEO cycle on startup (trading days only)."""
    from datetime import date
    from jobs import is_trading_day, make_researcher_job, make_analyst_job, make_ceo_job
    if not is_trading_day(date.today()):
        logger.info("Startup cycle skipped — not a trading day")
        return
    logger.info("Startup cycle: running full research→analyst→CEO pass")
    await asyncio.to_thread(make_researcher_job(api_base_url))
    await asyncio.to_thread(make_analyst_job(api_base_url))
    await asyncio.to_thread(make_ceo_job(api_base_url))
    logger.info("Startup cycle complete")


async def _run_scheduler(api_base_url: str, sector: str) -> None:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from jobs import register_jobs

    from datetime import datetime, timedelta, timezone

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    register_jobs(scheduler, api_base_url, sector)

    # Fire one full cycle 30s after startup so data is always current on boot.
    # Use UTC-aware datetime so APScheduler doesn't misinterpret it as ET.
    startup_time = datetime.now(timezone.utc) + timedelta(seconds=30)
    scheduler.add_job(
        _startup_cycle, trigger="date",
        run_date=startup_time,
        id="startup_cycle", replace_existing=True,
        args=[api_base_url],
    )

    scheduler.start()
    logger.info(
        "Scheduler running | sector=%s | api=%s | %d jobs registered (startup cycle in 30s)",
        sector, api_base_url, len(scheduler.get_jobs()),
    )
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped")


def _run_dry_run(api_base_url: str, sector: str) -> None:
    from jobs import run_dry_run
    logger.info("Dry-run mode: firing all agent jobs once | sector=%s", sector)
    triggered = run_dry_run(api_base_url, sector)
    logger.info("Dry-run complete: %d/%d agents responded", len(triggered), 4)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scheduler Agent")
    parser.add_argument(
        "--sector",
        default=DEFAULT_SECTOR,
        help="Sector for all agent triggers",
    )
    parser.add_argument(
        "--api-base-url",
        default=API_BASE_URL,
        help="FastAPI base URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fire all jobs once immediately and exit",
    )
    args = parser.parse_args()

    if args.dry_run:
        _run_dry_run(args.api_base_url, args.sector)
    else:
        asyncio.run(_run_scheduler(args.api_base_url, args.sector))


if __name__ == "__main__":
    main()
