# CLAUDE.md — scheduler

> **SIMULATION ONLY**: All outputs are for educational and entertainment purposes only. Not financial advice.

## Role
Master clock. Manages all cron jobs, market-hour awareness, and triggers agent execution sequences in the correct order. Knows US market holidays and skips non-trading days.

## Entry Point
```bash
python agents/scheduler/main.py --sector AI
python agents/scheduler/main.py --dry-run          # fires all agents once and exits
```

## Daily Cycle (America/New_York)
| Time | Agent |
|---|---|
| 05:30 | market-researcher (pre-market scan) |
| 06:00 | ceo (morning thesis) |
| 09:15 | market-researcher (pre-open scan) |
| 09:30 | analyst (opening recommendations) |
| 13:00 | market-researcher (midday scan) |
| 13:30 | analyst (midday review) |
| 15:30 | market-researcher (pre-close scan) |
| 16:00 | analyst (end-of-day recommendations) |
| 16:15 | ceo (end-of-day approval + daily report) |
| 16:30 | qa-engineer (daily validation) |
| 17:00 | market-researcher (snapshot archiver) |

Weekly: Monday 07:00 — CEO weekly review  
Monthly: 1st of month 06:00 — monthly report

## Holiday Handling
All jobs call `is_trading_day(date.today())` before firing. Non-trading days are silently skipped. Uses `pandas_market_calendars` NYSE calendar with weekday fallback on error.

## Agent Triggering
Jobs POST to `http://api:8000/agents/{agent}/trigger` with `{"sector": "AI"}`. The FastAPI server runs the agent script as a background subprocess and returns immediately (async fire-and-forget).

## Environment Variables
- `API_BASE_URL` — FastAPI server (default `http://api:8000`)
- `DEFAULT_TARGET_MARKET` — sector (default `AI`)
- `TIMEZONE` — scheduler timezone (default `America/New_York`)
