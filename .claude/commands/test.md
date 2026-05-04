# /test — run the test suite

Runs pytest across the full test suite with the given filter (optional).

```bash
pytest tests/ -q --tb=short $ARGUMENTS
```

Usage:
- `/test` — full suite
- `/test tests/agents/test_ceo.py` — single file
- `/test -k stop_loss` — filter by test name
- `/test -x` — stop on first failure

Frontend tests:
```bash
cd frontend && npm run test
```
