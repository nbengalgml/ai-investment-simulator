# AI Investment Simulator — Product Requirements Document
**Version**: 1.0 | **Date**: May 2026 | **Status**: Ready for Claude Code

---

## 1. Project Overview

### 1.1 Concept
An autonomous, multi-agent AI "investment company" that simulates a real investment firm. It employs a cast of specialized AI agents (CEO, Product Manager, Developer, Frontend Developer, Market Researcher, Analyst, QA, Scheduler, Deployment) that collaborate daily to analyze markets, generate portfolio recommendations, and simulate trade execution — all without real money changing hands.

### 1.2 Core Purpose
- **Paper trading simulator** — no real trades, no real brokerage connections
- **AI-driven analysis pipeline** — agents ingest news, SEC filings, Reddit sentiment, and analyst ratings
- **Portfolio recommendation engine** — max 5 stocks at a time, growth-focused strategy
- **Full reporting suite** — daily morning briefing, intraday updates, end-of-day summary, weekly/monthly performance views
- **Account-type awareness** — models tax treatment differences between Brokerage (post-tax) and Traditional/Rollover IRA (pre-tax)

### 1.3 Non-Goals
- No real trade execution or brokerage API integration
- No financial advice (all output is clearly labeled as simulation)
- No user authentication system at MVP
- No paid data APIs at launch (free tier only: yfinance, NewsAPI free, Reddit PRAW, SEC EDGAR)

---

## 2. System Architecture

### 2.1 Tech Stack
| Layer | Technology |
|---|---|
| Agent Backend | Python 3.11+ |
| API Server | FastAPI |
| Frontend | TypeScript + React (Vite) |
| State / Storage | JSON flat files (per-agent and shared portfolio state) |
| Scheduling | APScheduler (Python, in-process cron) |
| Containerization | Docker + Docker Compose |
| Version Control | Git (all agents, configs, and data schemas under git) |
| AI Runtime | Claude API (claude-sonnet-4-20250514) via Anthropic SDK |
| Market Data | yfinance (free) |
| News | NewsAPI free tier |
| Social Sentiment | Reddit PRAW (free) |
| SEC Data | SEC EDGAR full-text search API (free) |
| Analyst Ratings | Yahoo Finance via yfinance (free tier) |

### 2.2 Top-Level Folder Structure

```
ai-investment-simulator/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
│
├── agents/                          # Each agent = standalone Claude Code workspace
│   ├── ceo/
│   ├── product-manager/
│   ├── market-researcher/
│   ├── analyst/
│   ├── developer/
│   ├── frontend-developer/
│   ├── qa-engineer/
│   ├── scheduler/
│   └── deployment/
│
├── shared/                          # Shared libraries imported by agents
│   ├── data_models/                 # Pydantic schemas (portfolio, trade, report)
│   ├── storage/                     # JSON read/write utilities
│   ├── market_data/                 # yfinance wrappers
│   ├── news_feeds/                  # NewsAPI + Reddit PRAW + SEC EDGAR clients
│   └── claude_client/               # Anthropic SDK wrapper with prompt templates
│
├── data/                            # JSON flat file persistence (gitignored except schema)
│   ├── simulations/                 # One sub-dir per simulation track
│   │   └── {sector}-{account_type}/ # e.g. AI-brokerage, cloud-traditional_ira
│   │       ├── portfolio/
│   │       │   ├── state.json       # Current holdings, cash, account metadata
│   │       │   └── history/         # Daily snapshots: YYYY-MM-DD.json
│   │       ├── trades/
│   │       │   └── log.json         # Append-only trade log with full rationale
│   │       ├── reports/daily/       # CEO daily executive summaries
│   │       └── research/
│   │           └── recommendations/ # Analyst reports (sim-specific — tax rules differ)
│   ├── research/
│   │   └── market_snapshots/        # Shared market data (fetched once per sector/cycle)
│   └── agent_memory/                # Per-agent MEMORY.md state exports
│
├── frontend/                        # React + TypeScript dashboard
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── api/                     # FastAPI client (axios)
│   ├── package.json
│   └── vite.config.ts
│
└── tests/                           # Integration and unit tests
    ├── agents/
    ├── shared/
    └── e2e/
```

---

## 3. Agent Specifications

Every agent directory follows this structure:
```
agents/<agent-name>/
├── CLAUDE.md        # Agent identity, role, decision rules, workflow
├── MEMORY.md        # Persistent state: decisions made, context carried forward
├── SKILL.md         # Domain knowledge and tools this agent invokes
├── hooks/
│   ├── pre_tool.sh  # Safety/audit checks before tool calls
│   └── post_tool.sh # Logging after tool calls
├── commands/
│   └── run.md       # Slash commands: /run, /status, /report, /reset
├── agents/          # Sub-agents spawned by this agent (if any)
├── main.py          # Entry point for this agent
└── tests/
    └── test_agent.py
```

---

### 3.1 Agent: CEO (`agents/ceo/`)

**Role**: Orchestrates all other agents. Sets daily investment thesis, arbitrates conflicts, approves final portfolio changes, and produces the executive summary report.

**CLAUDE.md key sections**:
- Tech stack: Python, Claude API
- Decision authority: final say on portfolio changes proposed by Analyst
- Workflow: morning → trigger Market Researcher + Analyst → review recommendations → approve/reject → trigger Frontend update → log decision rationale in MEMORY.md
- Constraints: enforce max 5 stocks rule, enforce account-type tax rules, never approve a recommendation with < 3 supporting data sources

**Key outputs**:
- `data/reports/daily/YYYY-MM-DD_executive_summary.json`
- Portfolio approval/rejection with rationale

**Runs at**: 6:00 AM ET, 12:00 PM ET, 4:15 PM ET

---

### 3.2 Agent: Product Manager (`agents/product-manager/`)

**Role**: Manages the product backlog of the simulator itself. Tracks feature completeness, writes user stories, prioritizes bugs, and maintains the product roadmap. This agent is meta — it manages the AI company's own product development.

**CLAUDE.md key sections**:
- Owns: feature roadmap, backlog JSON, sprint state
- Workflow: weekly review of QA reports → update backlog → generate sprint plan
- Tools: reads QA failure reports, reads user feedback logs, writes `data/product/backlog.json`

**Key outputs**:
- `data/product/backlog.json`
- `data/product/sprint_YYYY_WNN.json`

**Runs at**: Every Monday 7:00 AM ET

---

### 3.3 Agent: Market Researcher (`agents/market-researcher/`)

**Role**: Primary data ingestion agent. Pulls live market data, news, SEC filings, Reddit sentiment, and analyst ratings. Synthesizes raw signals into structured research reports for the Analyst.

**CLAUDE.md key sections**:
- Data sources (priority order):
  1. SEC EDGAR full-text search — earnings reports, 8-K filings
  2. NewsAPI free — financial news headlines filtered by target market sector
  3. Reddit PRAW — r/wallstreetbets, r/investing, r/stocks sentiment scan
  4. yfinance — price history, analyst price targets, earnings calendar
- Target market parameter: passed in at runtime (e.g. "AI", "cloud", "networking", "alternative energy")
- Output: structured JSON with signal scores per ticker

**SKILL.md key sections**:
- SEC EDGAR query patterns for earnings events
- Reddit sentiment scoring rubric (upvote velocity, mention frequency, sentiment polarity)
- NewsAPI query construction for sector-specific filtering
- yfinance data extraction: price momentum, P/E ratio, 52-week range, analyst consensus

**Key outputs**:
- `data/research/market_snapshots/YYYY-MM-DD_HH_<sector>.json`

**Runs at**: 5:30 AM ET (pre-market), 9:15 AM ET (pre-open), 1:00 PM ET, 3:30 PM ET

---

### 3.4 Agent: Analyst (`agents/analyst/`)

**Role**: The investment brain. Consumes Market Researcher output and applies the growth investment strategy to rank stocks and generate buy/sell/hold recommendations with simulated allocation percentages.

**CLAUDE.md key sections**:
- Strategy: Growth (max capital appreciation, higher risk tolerance)
- Max positions: 5 stocks simultaneously
- Account-type rules:
  - **Brokerage (post-tax)**: no contribution limits, short-term capital gains taxed as income, long-term gains at preferential rate. Prefer longer holding periods (>1yr) for tax efficiency. Avoid wash-sale simulations.
  - **Traditional/Rollover IRA (pre-tax)**: tax-deferred growth, no capital gains tax on trades within account, RMD simulation not required at MVP. More flexible on short-term trading simulation. Annual contribution limit awareness (display only, not enforced).
- Decision framework:
  1. Score each candidate stock 0–100 on: momentum, fundamental strength, analyst consensus, sentiment
  2. Rank top 5 candidates
  3. Recommend allocation % per stock (must sum to ≤ 100% of invested capital; remainder in simulated cash)
  4. Assign confidence level: HIGH / MEDIUM / LOW
  5. Provide 3-bullet rationale per recommendation

**SKILL.md key sections**:
- Growth stock scoring algorithm
- Sector rotation logic
- Stop-loss threshold (default: -15% triggers review, -20% triggers sell recommendation)
- Position sizing rules: no single stock > 35% of portfolio

**Key outputs**:
- `data/research/recommendations/YYYY-MM-DD_HH_recommendations.json`

**Runs at**: After each Market Researcher cycle completes (triggered by CEO agent)

---

### 3.5 Agent: Developer (`agents/developer/`)

**Role**: Builds and maintains the Python backend — FastAPI server, shared libraries, data models, agent infrastructure, and the scheduler. Also builds any new data connectors or tools needed by other agents.

**CLAUDE.md key sections**:
- Owns: `shared/`, FastAPI app, Docker config, APScheduler configuration
- Coding standards: type hints on all functions, Pydantic models for all data schemas, async FastAPI endpoints, 80%+ test coverage target
- Git discipline: feature branches, conventional commits, no direct pushes to main

**SKILL.md key sections**:
- FastAPI endpoint patterns
- Pydantic schema design for portfolio state
- yfinance async data fetching patterns
- APScheduler cron job setup
- Docker multi-stage build patterns

**Key outputs**:
- All Python source files in `shared/` and agent `main.py` files
- `docker-compose.yml`, `Dockerfile` per service

---

### 3.6 Agent: Frontend Developer (`agents/frontend-developer/`)

**Role**: Builds and maintains the React + TypeScript dashboard. Implements all views: portfolio overview, per-stock cards, trade log, daily/weekly/monthly performance charts, and the account configuration panel.

**CLAUDE.md key sections**:
- Owns: `frontend/` directory
- Stack: React 18, TypeScript, Vite, Recharts for data visualization, TanStack Query for API state, Tailwind CSS
- Polling interval: 60 seconds for live price updates
- Design principles: dark-first theme, financial data density (think Bloomberg terminal aesthetic, not a consumer app)

**SKILL.md key sections**:
- Recharts patterns for line/area/bar charts
- TanStack Query setup with FastAPI
- Real-time polling pattern (60s interval with stale-while-revalidate)
- Portfolio P&L color coding (green/red with colorblind-safe alternatives)

**Key dashboard pages**:
1. `/` — Portfolio Overview (current holdings, total P&L, allocation pie)
2. `/holdings/:ticker` — Per-stock detail (price chart, analyst notes, trade history)
3. `/reports/daily` — Daily report viewer
4. `/reports/weekly` — Weekly performance
5. `/reports/monthly` — Monthly performance
6. `/trades` — Full simulated trade log
7. `/settings` — Budget, account type, target market selector

**Runs**: Continuously (React dev server in Docker, Nginx in production)

---

### 3.7 Agent: QA Engineer (`agents/qa-engineer/`)

**Role**: Writes and runs tests for all agents and shared libraries. Validates data pipeline integrity, confirms report generation works end-to-end, and flags when agent outputs violate defined schemas.

**CLAUDE.md key sections**:
- Test framework: pytest (backend), Vitest + React Testing Library (frontend)
- Schema validation: all JSON outputs validated against Pydantic models in CI
- Integration test: full pipeline dry-run with mocked API responses
- Performance test: full cycle must complete in < 90 seconds on reference hardware

**SKILL.md key sections**:
- pytest fixtures for mock market data
- FastAPI TestClient patterns
- JSON schema diffing for breaking change detection
- Agent pipeline integration test: trigger Market Researcher → Analyst → CEO → assert final report exists and is valid

**Key outputs**:
- `data/qa/test_results_YYYY-MM-DD.json`
- Failure alerts written to `data/qa/alerts.json` (polled by CEO agent)

**Runs at**: After each end-of-day CEO cycle (4:30 PM ET), and on-demand via `/run` command

---

### 3.8 Agent: Scheduler (`agents/scheduler/`)

**Role**: The master clock. Manages all cron jobs, market-hour awareness, and triggers agent execution sequences in the correct order. Knows US market holidays and skips non-trading days.

**CLAUDE.md key sections**:
- Uses APScheduler with AsyncIOScheduler
- Market hours: 9:30 AM – 4:00 PM ET, Mon–Fri, excludes NYSE holidays
- Daily cycle:
  ```
  05:30 ET → Market Researcher (pre-market scan)
  06:00 ET → CEO (morning thesis + approve/reject overnight news)
  09:15 ET → Market Researcher (pre-open scan)
  09:30 ET → Analyst (opening recommendations)
  10:00 ET → Frontend refresh trigger
  13:00 ET → Market Researcher (midday scan)
  13:30 ET → Analyst (midday review)
  15:30 ET → Market Researcher (pre-close scan)
  16:00 ET → Analyst (end-of-day recommendations)
  16:15 ET → CEO (end-of-day approval + daily report generation)
  16:30 ET → QA Engineer (daily validation run)
  17:00 ET → Report archiver (snapshot portfolio state to history/)
  ```
- Weekly cycle: Monday 07:00 ET → Product Manager sprint review
- Monthly cycle: 1st of month 06:00 ET → Monthly report generation

**SKILL.md key sections**:
- APScheduler AsyncIOScheduler setup
- NYSE holiday calendar (pandas_market_calendars)
- Agent trigger via subprocess or HTTP POST to FastAPI `/agents/{agent}/trigger`

---

### 3.9 Agent: Deployment (`agents/deployment/`)

**Role**: Manages Docker build, container health checks, environment configuration, and the deployment runbook. Also owns the `.env` secrets management pattern.

**CLAUDE.md key sections**:
- Docker Compose services: `api`, `scheduler`, `frontend`, `nginx`
- Health check endpoints: `GET /health` on API service
- Environment variables (all stored in `.env`, never committed):
  - `ANTHROPIC_API_KEY`
  - `NEWSAPI_KEY`
  - `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
- Deployment runbook: `docker compose up --build -d`
- Log aggregation: all agents write structured JSON logs to `data/logs/`

**SKILL.md key sections**:
- Docker multi-stage Python builds
- Nginx config for React SPA with API proxy
- `docker compose` health check patterns
- Secrets rotation procedure

---

## 4. Data Models

### 4.1 Portfolio State (`data/portfolio/state.json`)
```json
{
  "account_type": "brokerage | traditional_ira",
  "target_market": "AI",
  "budget_total": 10000.00,
  "cash_available": 3500.00,
  "last_updated": "2026-05-03T16:15:00Z",
  "holdings": [
    {
      "ticker": "NVDA",
      "shares": 2.5,
      "avg_cost_basis": 850.00,
      "current_price": 920.00,
      "market_value": 2300.00,
      "unrealized_pnl": 175.00,
      "unrealized_pnl_pct": 8.24,
      "allocation_pct": 23.0,
      "open_date": "2026-04-15",
      "analyst_rating": "BUY",
      "confidence": "HIGH"
    }
  ],
  "total_market_value": 6500.00,
  "total_unrealized_pnl": 500.00,
  "total_unrealized_pnl_pct": 8.33,
  "strategy": "growth",
  "max_positions": 5
}
```

### 4.2 Simulated Trade Log Entry (`data/trades/log.json`)
```json
{
  "trade_id": "TRD-20260503-001",
  "timestamp": "2026-05-03T09:35:12Z",
  "action": "BUY | SELL | HOLD",
  "ticker": "NVDA",
  "shares": 2.5,
  "price": 850.00,
  "total_value": 2125.00,
  "rationale": "Strong Q1 earnings beat, AI chip demand signal from SEC 8-K filing, Reddit mention velocity +340% in 48h",
  "data_sources": ["SEC EDGAR 8-K 2026-04-29", "NewsAPI: 3 articles", "Reddit: r/investing sentiment 0.82"],
  "approved_by": "CEO",
  "account_type": "brokerage",
  "simulated_tax_impact": {
    "holding_period_days": 0,
    "gain_loss": 0,
    "tax_treatment": "N/A (new position)"
  }
}
```

### 4.3 Daily Report (`data/reports/daily/YYYY-MM-DD.json`)
```json
{
  "report_date": "2026-05-03",
  "generated_at": "2026-05-03T16:20:00Z",
  "executive_summary": "...",
  "market_conditions": "...",
  "portfolio_performance": {
    "day_pnl": 285.00,
    "day_pnl_pct": 2.14,
    "total_unrealized_pnl": 500.00
  },
  "actions_taken": [...],
  "top_signals": [...],
  "recommendations_pending": [...],
  "next_day_watchlist": [...]
}
```

---

## 5. API Endpoints (FastAPI)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/portfolio` | Current portfolio state (legacy single-sim) |
| GET | `/portfolio/history` | All daily snapshots (legacy) |
| GET | `/trades` | Full simulated trade log (legacy) |
| GET | `/reports/daily` | List of daily reports (legacy) |
| GET | `/reports/daily/{date}` | Specific daily report (legacy) |
| GET | `/agents/status` | All agent script availability |
| POST | `/agents/{agent}/trigger` | Trigger agent — body: `{sector, account_type, no_claude}` |
| POST | `/settings` | Update global defaults |
| GET | `/simulations` | Leaderboard: all sim cards with P&L summary |
| GET | `/simulations/{sim_id}/portfolio` | Portfolio for a specific sim |
| GET | `/simulations/{sim_id}/portfolio/history` | Daily history for a sim |
| GET | `/simulations/{sim_id}/trades` | Trade log for a sim (newest first) |
| GET | `/simulations/{sim_id}/reports/daily` | All daily reports for a sim |
| GET | `/simulations/{sim_id}/reports/daily/{date}` | Specific report for a sim |

**sim_id format**: `{sector}-{account_type}` — e.g. `AI-brokerage`, `cloud-traditional_ira`

---

## 6. Frontend Dashboard Specification

### 6.1 Design Aesthetic
Bloomberg terminal meets modern fintech — high information density, dark-first theme, monospace numerical displays, green/red P&L coloring (with accessible alternatives), minimal chrome, maximum data.

### 6.2 Key Components
- **Account Type Parent Tabs**: `Brokerage (post-tax)` | `Traditional IRA (pre-tax)` — top-level switch
- **Sector Sidebar**: Picker for AI / Cloud / Networking / Alternative Energy / Gas / Finance
- **Simulation Leaderboard**: Live table of all sims sorted by total return % — click any row to jump to that sim
- **Portfolio Header Bar**: Total value, day P&L, cash, strategy badge for the active sim
- **Holdings Grid**: Card per stock — ticker, price, shares, P&L, allocation %, confidence badge
- **P&L Chart**: Area chart with 7D/30D/90D toggle per sim (Recharts AreaChart)
- **Trade Log**: Full audit log with rationale per trade, filterable by BUY/SELL/HOLD
- **Daily Report Panel**: CEO executive summary, top signals, next-day watchlist per sim
- **↻ Run Cycle button**: Inline in tab bar — triggers market-researcher → analyst → ceo for the active sim
- **Agent Status Sidebar**: Script-existence check per agent

### 6.3 Polling Strategy
- Portfolio state: 60-second polling via TanStack Query
- Agent status: 30-second polling
- Reports: on-demand (no auto-refresh)

---

## 7. Account Type Tax Simulation Rules

### 7.1 Brokerage (Post-Tax)
- Capital gains are tracked and reported in trade log
- Short-term gain: holding period < 365 days — annotated as "ordinary income rate"
- Long-term gain: holding period ≥ 365 days — annotated as "preferential LTCG rate"
- Analyst recommendations favor positions with > 365-day holding potential
- Wash-sale warning: if a stock is sold at a loss and a similar position is opened within 30 days, flag in report

### 7.2 Traditional / Rollover IRA (Pre-Tax)
- No capital gains tax tracking needed within the account
- All growth is tax-deferred
- Trade rationale notes can prioritize short-term opportunities more aggressively
- Annual contribution limit displayed on settings panel ($7,000 for 2026, $8,000 if 50+) — informational only
- Required Minimum Distributions: not simulated at MVP; noted as future feature

---

## 8. Investment Strategy Rules (Growth Profile)

Applied by the Analyst agent:

1. **Universe**: S&P 500 + NASDAQ 100 stocks within the selected target market sector
2. **Maximum 5 positions** at any time
3. **Maximum single position**: 35% of invested capital
4. **Minimum cash reserve**: 10% of total portfolio always available
5. **Entry signals** (all three required for HIGH confidence):
   - Price momentum: 20-day return > sector average
   - Fundamental: positive earnings surprise OR analyst upgrade in last 30 days
   - Sentiment: Reddit mention velocity positive AND NewsAPI headline sentiment positive
6. **Exit signals** (any one triggers sell recommendation):
   - Stop-loss: position down > 20% from entry
   - Momentum loss: price below 50-day SMA for 3 consecutive trading days
   - Negative catalyst: SEC 8-K with earnings miss > 10% or guidance cut
7. **HOLD signals**: position within -15% to +5% with mixed signals → hold and monitor
8. **Rebalancing**: if a position grows to > 40% of portfolio, recommend partial sale to trim to 30%

---

## 9. Testing Strategy

### 9.1 Unit Tests (pytest)
- All Pydantic data models
- JSON storage read/write utilities
- Market data fetching with mocked yfinance responses
- Analyst scoring algorithm with known inputs
- Tax simulation calculations

### 9.2 Integration Tests
- Full pipeline: mock market data → Market Researcher → Analyst → CEO → assert report file exists and validates against schema
- FastAPI endpoint tests with TestClient
- Scheduler dry-run: fire all jobs once with mock agents, assert no exceptions

### 9.3 Frontend Tests (Vitest + RTL)
- Portfolio header renders correctly with mock data
- Holdings grid renders N cards for N holdings
- Charts render without crash
- Settings form submits and updates state

### 9.4 End-to-End Tests
- `tests/e2e/test_full_day_cycle.py` — simulates one full trading day: pre-market → midday → close, asserts daily report generated and portfolio state updated

### 9.5 Test Data
- `tests/fixtures/mock_portfolio.json` — known portfolio state
- `tests/fixtures/mock_market_data.json` — canned yfinance responses
- `tests/fixtures/mock_news.json` — canned NewsAPI responses
- `tests/fixtures/mock_reddit.json` — canned PRAW responses

---

## 10. Hooks Configuration

### 10.1 PreToolUse (all agents)
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "scripts/pre_tool_audit.sh",
        "timeout": 5
      }]
    }]
  }
}
```
`pre_tool_audit.sh`: logs tool call + timestamp to `data/logs/audit.jsonl`. Blocks any command containing `rm -rf` or writes to `.env`.

### 10.2 PostToolUse (all agents)
Logs tool result summary (success/failure, bytes read/written) to `data/logs/audit.jsonl`.

### 10.3 Permissions (all agents)
```json
{
  "permissions": {
    "allow": ["Read:*", "Bash:git:*", "Write:*.json", "Write:*.md"],
    "deny": ["Bash:sudo:*", "Bash:rm -rf:*", "Write:.env"]
  }
}
```

---

## 11. Environment Variables (`.env.example`)

```bash
# Anthropic
ANTHROPIC_API_KEY=your_key_here

# NewsAPI (free tier: https://newsapi.org)
NEWSAPI_KEY=your_key_here

# Reddit PRAW (https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=ai-investment-simulator/1.0

# App Config
DEFAULT_ACCOUNT_TYPE=brokerage
DEFAULT_TARGET_MARKET=AI
DEFAULT_BUDGET=10000
TIMEZONE=America/New_York
LOG_LEVEL=INFO

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

---

## 12. Docker Compose Services

```yaml
services:
  api:
    build: ./shared
    ports: ["8000:8000"]
    volumes: ["./data:/app/data"]
    env_file: .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s

  scheduler:
    build: ./agents/scheduler
    volumes: ["./data:/app/data", "./agents:/app/agents"]
    env_file: .env
    depends_on: [api]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    env_file: .env
    depends_on: [api]
```

---

## 13. Git Strategy

- `main` — stable, deployable
- `develop` — integration branch
- `feature/<agent-name>/<description>` — per-feature branches
- Conventional commits: `feat(analyst): add stop-loss signal`, `fix(scheduler): handle NYSE holiday edge case`
- All `data/` subdirectories except `data/qa/` and schema files are in `.gitignore`
- All agent `MEMORY.md` files are committed (they represent agent persistent state, not raw data)

---

## 14. MVP Milestones

| Milestone | Deliverable |
|---|---|
| M1 | Repo scaffolded, Docker Compose running, FastAPI health endpoint live |
| M2 | Shared data models, JSON storage, yfinance client working |
| M3 | Market Researcher agent producing valid research snapshots |
| M4 | Analyst agent producing valid recommendations from research |
| M5 | CEO agent producing daily report + approving portfolio changes |
| M6 | Scheduler running full daily cycle end-to-end |
| M7 | React frontend displaying portfolio + holdings |
| M8 | Full P&L charts, trade log, daily/weekly/monthly reports in UI |
| M9 | QA test suite green, Docker Compose production build |
| M10 | All agents have complete CLAUDE.md, MEMORY.md, SKILL.md, Hooks |

---

## 15. Disclaimer (Required in All Agent Outputs)

> **SIMULATION ONLY**: All portfolio recommendations, trade simulations, and performance projections produced by this system are for educational and entertainment purposes only. This is not financial advice. No real trades are executed. Past simulated performance does not indicate future real-world results. The creators of this system are not licensed financial advisors.

This disclaimer must appear in:
- Every daily/weekly/monthly report
- The frontend dashboard header
- Every agent's CLAUDE.md
- The project README.md

---

*PRD v1.0 — Ready to paste into Claude Code. Start with: `claude /init` in the repo root, then begin with M1.*
