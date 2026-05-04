# QA Engineer MEMORY.md

## Role
Runs the full test suite (unit + integration + E2E) after each CEO EOD cycle (16:30 ET).
Writes a QA report JSON to `data/qa/`. Exits non-zero on failure — scheduler logs the error.

## Test Suite
- `tests/shared/` — Pydantic models, storage, market data, news feeds, API routes
- `tests/agents/` — Market Researcher, Analyst, CEO, Scheduler algorithm tests
- `tests/e2e/` — Full pipeline with all external APIs mocked

## Key Pattern
All agent tests use `_storage.DATA_DIR = tmp_path` + `use_claude=False` for isolation.
No real API calls in the test suite.

## QA Report Location
`data/qa/YYYY-MM-DD_qa_report.json`

## Simulation Status
Initialized. Awaiting first scheduled trigger from Scheduler.
