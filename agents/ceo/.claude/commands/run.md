# /run — execute a CEO approval and trade cycle

Run the CEO agent for the specified sector (default: AI).

```bash
python agents/ceo/main.py --sector $ARGUMENTS
```

If `$ARGUMENTS` is empty, defaults to `AI`.

Usage:
- `/run` — full CEO cycle with Claude executive summary
- `/run AI --no-claude` — algorithmic summary (no Anthropic API call)

Requires a recent analyst report in `data/research/recommendations/`.
Output files:
- `data/portfolio/state.json` — updated portfolio
- `data/portfolio/history/YYYY-MM-DD.json` — daily snapshot
- `data/trades/log.json` — appended trade entries
- `data/reports/daily/YYYY-MM-DD_executive_summary.json` — daily report
