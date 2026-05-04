# /latest — show the most recent market snapshot

Finds and displays the latest market snapshot JSON for the AI sector (or sector passed as argument).

```bash
ls -t data/research/market_snapshots/*${ARGUMENTS:-AI}*.json 2>/dev/null | head -1 | xargs cat
```

Usage:
- `/latest` — show latest AI sector snapshot
- `/latest cloud` — show latest cloud sector snapshot
