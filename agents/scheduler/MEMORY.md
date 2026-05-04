# Scheduler MEMORY.md

## Role
Master clock. Registers APScheduler cron jobs, checks NYSE trading calendar,
and triggers agents via HTTP POST to FastAPI. Runs as a long-lived process.

## Schedule Summary
Daily (ET, NYSE trading days only):
05:30 market-researcher | 06:00 ceo | 09:15 market-researcher | 09:30 analyst
13:00 market-researcher | 13:30 analyst | 15:30 market-researcher | 16:00 analyst
16:15 ceo | 16:30 qa-engineer | 17:00 market-researcher

Weekly: Monday 07:00 — CEO weekly review  
Monthly: 1st of month 06:00 — monthly report

## Holiday Handling
Uses `pandas_market_calendars` NYSE calendar. Falls back to weekday check on error.
Non-trading days: all jobs silently skipped.

## Trigger Endpoint
`POST /agents/{agent}/trigger` → FastAPI background subprocess.

## Simulation Status
Initialized. Jobs registered on startup. Dry-run mode available via `--dry-run`.
