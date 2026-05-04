# /cycle — run a full simulated trading day

Executes the complete agent pipeline in order: market-researcher → analyst → ceo → qa-engineer.

```bash
SECTOR=${ARGUMENTS:-AI}
echo "=== Market Researcher ===" && python agents/market-researcher/main.py --sector $SECTOR --no-claude
echo "=== Analyst ===" && python agents/analyst/main.py --sector $SECTOR --no-claude
echo "=== CEO ===" && python agents/ceo/main.py --sector $SECTOR --no-claude
echo "=== QA Engineer ===" && python agents/qa-engineer/main.py
```

All agents run with `--no-claude` (algorithmic fallback) so no API credits are consumed.
To use Claude for narrative generation, remove the `--no-claude` flags.
