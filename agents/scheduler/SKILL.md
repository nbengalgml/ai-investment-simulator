# SKILL.md — scheduler

## NYSE Calendar Check

```python
import pandas_market_calendars as mcal

def is_trading_day(dt: date) -> bool:
    nyse = mcal.get_calendar("NYSE")
    schedule = nyse.schedule(start_date=dt.isoformat(), end_date=dt.isoformat())
    return not schedule.empty  # empty → holiday or weekend
```
Fallback: `dt.weekday() < 5` if pandas_market_calendars throws.

## APScheduler Setup

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler(timezone="America/New_York")
scheduler.add_job(
    func,
    trigger="cron",
    hour=9, minute=30,
    id="daily_analyst_0930",
    replace_existing=True,
    misfire_grace_time=300,   # fire up to 5 min late
)
scheduler.start()
```

## Job Factory Pattern

```python
def make_job(agent, api_base_url, sector, skip_holiday_check=False):
    def _job():
        if not skip_holiday_check and not is_trading_day(date.today()):
            return  # silent skip
        trigger_agent(agent, api_base_url, {"sector": sector})
    return _job
```

## HTTP Trigger

```python
requests.post(f"{api_base_url}/agents/{agent}/trigger",
              json={"sector": sector}, timeout=30)
```
Returns True on 2xx, False on any error — scheduler never crashes on agent failure.

## Dry-Run Mode
Fires `market-researcher`, `analyst`, `ceo`, `qa-engineer` once immediately.
Used for integration testing without waiting for cron times.
Invoked with `--dry-run` flag.

## Job ID Naming
- Daily: `daily_{agent_snake}_{HH}{MM}` e.g. `daily_market_researcher_0930`
- Weekly: `weekly_ceo_review`
- Monthly: `monthly_report`
