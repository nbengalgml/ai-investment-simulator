# SKILL.md — qa-engineer

## Test Categories

### Unit Tests (`tests/shared/`, `tests/agents/`)
- Pure function tests with no I/O — no mocking needed
- Pydantic model construction + validation
- JSON storage read/write (use `tmp_path` fixture for isolation)
- Algorithm correctness (scoring, allocation, exit signals)

### Integration Tests (`tests/agents/`, `tests/shared/`)
- Agent pipelines with `use_claude=False` and `_storage.DATA_DIR = tmp_path`
- FastAPI `TestClient` for all route tests
- External API calls mocked via `unittest.mock.patch`

### E2E Tests (`tests/e2e/`)
- Full day cycle: Researcher → Analyst → CEO
- All external APIs mocked (yfinance, NewsAPI, PRAW, SEC EDGAR)
- Asserts file outputs exist + validate against Pydantic schemas

## Key Test Patterns

```python
# Override DATA_DIR for file isolation
import storage as _storage
_storage.DATA_DIR = tmp_path  # must use module-level import, not `from storage import DATA_DIR`

# Mock yfinance
with patch("yfinance.Ticker", side_effect=lambda t: mock_ticker(t)):
    result = run_research_cycle("AI", use_claude=False)

# FastAPI route tests
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
resp = client.get("/portfolio")
```

## Adding New Tests
1. Unit: add to `tests/shared/test_<module>.py` or `tests/agents/test_<agent>.py`
2. Integration: same files, use `tmp_path` + mocks
3. E2E: add to `tests/e2e/test_full_day_cycle.py`

## QA Report Location
`data/qa/YYYY-MM-DD_qa_report.json`
