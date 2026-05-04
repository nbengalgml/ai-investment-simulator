# /dryrun — trigger all agents once and exit

Fires all agents in the correct order (market-researcher → analyst → ceo → qa-engineer) immediately, without waiting for scheduled times. Useful for testing the full daily cycle.

```bash
python agents/scheduler/main.py --dry-run --sector ${ARGUMENTS:-AI}
```

Each agent is POSTed to `$API_BASE_URL/agents/{agent}/trigger`. Results (success/failure per agent) are printed and the process exits.
