# CLAUDE.md — qa-engineer

> **SIMULATION ONLY**: All outputs are for educational and entertainment purposes only. Not financial advice.

## Role
Runs the full test suite (unit + integration + E2E), writes a QA report to `data/qa/`, and exits non-zero on failure. Triggered daily at 16:30 ET by the Scheduler after the CEO cycle.

## Entry Point
```bash
python agents/qa-engineer/main.py
```

## What It Does
1. Runs `pytest tests/` from the repo root with `-q --tb=short`
2. Parses passed/failed/error counts from output
3. Writes `data/qa/YYYY-MM-DD_qa_report.json` with results
4. Exits 0 on all-pass, 1 on any failure

## Output Schema
```json
{
  "report_date": "YYYY-MM-DD",
  "generated_at": "ISO8601",
  "suite": "full",
  "exit_code": 0,
  "passed": 162,
  "failed": 0,
  "errors": 0,
  "total": 162,
  "success": true,
  "output_tail": "...last 2000 chars of pytest output..."
}
```

## Test Suite Structure
| Directory | What It Tests |
|---|---|
| `tests/shared/` | Pydantic models, storage, market data, news feeds, API routes |
| `tests/agents/` | Market Researcher, Analyst, CEO, Scheduler algorithms |
| `tests/e2e/` | Full pipeline: Researcher → Analyst → CEO → assert all outputs |

## Environment Variables
- `DATA_DIR` — where to write QA reports (default `/app/data`)
