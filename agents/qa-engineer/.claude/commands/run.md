# /run — execute the full test suite

Runs pytest across all test directories and writes a QA report.

```bash
python agents/qa-engineer/main.py
```

Runs: `pytest tests/ -q --tb=short` (300s timeout)

Output: `data/qa/YYYY-MM-DD_qa_report.json`
Exit code: 0 if all tests pass, 1 if any failures.

To run a specific subset directly:
- Unit only: `pytest tests/shared/ tests/agents/ -q`
- E2E only: `pytest tests/e2e/ -q --tb=short`
- Single file: `pytest tests/agents/test_ceo.py -v`
