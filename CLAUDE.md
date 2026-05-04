# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **SIMULATION ONLY**: All portfolio recommendations, trade simulations, and performance projections produced by this system are for educational and entertainment purposes only. This is not financial advice. No real trades are executed. Past simulated performance does not indicate future real-world results.

---

## Commands

### Run the full stack
```bash
docker compose up --build -d
```

### Backend (FastAPI)
```bash
# From repo root — runs the API server directly (no Docker)
cd shared && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Install Python deps
pip install -r requirements.txt
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev        # Dev server on :3000
npm run build      # Production build
npm run lint       # ESLint
```

### Tests
```bash
# Backend unit + integration tests
pytest tests/

# Single test file
pytest tests/shared/test_storage.py

# Single test
pytest tests/shared/test_storage.py::test_read_portfolio

# Frontend tests
cd frontend && npm run test

# Full day cycle E2E
pytest tests/e2e/test_full_day_cycle.py
```

---

## Architecture

This is a greenfield project — only the PRD exists so far. The intended structure is documented in `AI_INVESTMENT_SIMULATOR_PRD.md`. Key architectural decisions:

### Agent System
Each directory under `agents/` is a standalone Claude Code workspace with its own `CLAUDE.md`, `MEMORY.md`, `SKILL.md`, hooks, and `main.py` entry point. Agents communicate by reading/writing JSON files in `data/` and via HTTP POST to `/agents/{agent}/trigger` on the FastAPI server. There is no direct agent-to-agent function call — all coordination is file-based or HTTP-based, orchestrated by the CEO agent.

Agent execution order (daily):
```
Market Researcher → Analyst → CEO → (Frontend refresh) → QA Engineer
```

### Data Flow
All persistence is flat JSON files under `data/`. No database. Pydantic models in `shared/data_models/` define the schemas; all agent outputs must validate against them. The `data/` directory is gitignored except for `data/qa/` and schema definition files. All agent `MEMORY.md` files are committed.

### Shared Libraries (`shared/`)
| Module | Purpose |
|---|---|
| `data_models/` | Pydantic schemas: portfolio state, trade log, reports |
| `storage/` | JSON read/write utilities used by all agents |
| `market_data/` | yfinance wrappers |
| `news_feeds/` | NewsAPI, Reddit PRAW, SEC EDGAR clients |
| `claude_client/` | Anthropic SDK wrapper + prompt templates for all agents |

The FastAPI app lives in `shared/` and serves as the API layer between agents and the frontend.

### Frontend
React 18 + TypeScript + Vite under `frontend/`. Uses TanStack Query for all data fetching with two polling intervals: 60s for portfolio state, 30s for agent status. Recharts for all charts. Tailwind CSS with a dark-first Bloomberg-terminal aesthetic. Connects to the FastAPI backend via `VITE_API_BASE_URL`.

### Scheduling
APScheduler (`AsyncIOScheduler`) runs inside the `agents/scheduler/` container. It is the only process that triggers agent cycles. NYSE holidays are handled via `pandas_market_calendars`. Agents can also be triggered manually via `POST /agents/{agent}/trigger`.

### AI Runtime
All agents call Claude (`claude-sonnet-4-20250514`) through `shared/claude_client/`. Use prompt caching for any long system prompts or repeated context. The Anthropic SDK is the only AI dependency.

---

## Key Constraints

- **Max 5 portfolio positions** at any time
- **Max 35% allocation** per single stock; **min 10% cash reserve** always
- Stop-loss at **-20%** triggers sell recommendation; **-15%** triggers review
- HIGH confidence requires all three signals: momentum + fundamental + sentiment
- All agent outputs must include the simulation disclaimer
- No write access to `.env`; no `rm -rf` (enforced by pre-tool hooks)

## Environment Variables
Copy `.env.example` to `.env`. Required keys: `ANTHROPIC_API_KEY`, `NEWSAPI_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`. See `.env.example` for all variables.

## Git Strategy
- Branches: `main` (stable), `develop` (integration), `feature/<agent-name>/<description>`
- Conventional commits: `feat(analyst): add stop-loss signal`, `fix(scheduler): handle NYSE holiday`
- No direct pushes to `main`
