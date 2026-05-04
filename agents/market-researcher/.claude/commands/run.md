# /run — execute a market research cycle

Run the market-researcher agent for the specified sector (default: AI).

```bash
python agents/market-researcher/main.py --sector $ARGUMENTS
```

If `$ARGUMENTS` is empty, defaults to `AI`.

Usage:
- `/run` — scan AI sector
- `/run cloud` — scan cloud sector
- `/run AI --no-claude` — use algorithmic scoring (no Anthropic API call)

Output written to: `data/research/market_snapshots/YYYY-MM-DD_HH_<sector>.json`
