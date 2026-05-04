# /run — start the scheduler (long-lived process)

Starts APScheduler with all registered cron jobs. Runs until interrupted.

```bash
python agents/scheduler/main.py --sector $ARGUMENTS
```

If `$ARGUMENTS` is empty, defaults to `AI`.

Usage:
- `/run` — start scheduler for AI sector (blocks until Ctrl+C)
- `/run cloud` — start scheduler for cloud sector
- `/run AI --dry-run` — fire all agents once immediately, then exit

The scheduler only triggers agents on NYSE trading days. Non-trading days are silently skipped.
Jobs post to `$API_BASE_URL` (default: `http://api:8000`).
