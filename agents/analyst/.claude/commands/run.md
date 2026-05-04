# /run — execute an analyst recommendation cycle

Run the analyst agent for the specified sector (default: AI).

```bash
python agents/analyst/main.py --sector $ARGUMENTS
```

If `$ARGUMENTS` is empty, defaults to `AI`.

Usage:
- `/run` — analyze AI sector with Claude rationale
- `/run cloud` — analyze cloud sector
- `/run AI --no-claude` — use algorithmic rationale (no Anthropic API call)

Requires a recent market snapshot in `data/research/market_snapshots/`.
Output written to: `data/research/recommendations/YYYY-MM-DD_HH_recommendations.json`
