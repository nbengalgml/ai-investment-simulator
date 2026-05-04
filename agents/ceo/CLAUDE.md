# CLAUDE.md — ceo

> **SIMULATION ONLY**: All outputs are for educational and entertainment purposes only. Not financial advice. No real trades are executed.

## Role
Orchestrator and final decision-maker. Reads the latest `AnalystReport` and current `PortfolioState`, applies CEO approval rules, simulates trade execution, and produces a `DailyReport` with executive summary.

## Entry Point
```bash
python agents/ceo/main.py --sector AI
python agents/ceo/main.py --sector AI --no-claude
```

## Runs After
Analyst agent — triggered by the Scheduler (M6) or manually via `POST /agents/ceo/trigger`.

## Approval Rules
| Rule | Threshold |
|---|---|
| BUY requires min data sources | ≥ 2 |
| Max portfolio positions | 5 |
| Max single position | 35% |
| SELL / HOLD | Always approved |

## Trade Simulation
- **BUY**: `shares = (budget_total * allocation_pct / 100) / current_price`
- **SELL (full)**: removes holding from portfolio; records gain/loss
- Cash is recalculated after all trades

## Tax Simulation
- Brokerage: < 365 days → short-term gain; ≥ 365 days → LTCG
- IRA: tax-deferred regardless of holding period
- Tax impact embedded in `TradeLogEntry.simulated_tax_impact`

## Output Files
| File | Content |
|---|---|
| `data/portfolio/state.json` | Updated `PortfolioState` |
| `data/portfolio/history/YYYY-MM-DD.json` | Daily portfolio snapshot |
| `data/trades/log.json` | Appended `TradeLogEntry` list |
| `data/reports/daily/YYYY-MM-DD_executive_summary.json` | `DailyReport` |
| `agents/ceo/MEMORY.md` | Appended daily summary |

## Workflow
1. Load latest `AnalystReport` from `data/research/recommendations/`
2. Load latest `MarketResearchSnapshot` for sector
3. Load `PortfolioState` from `data/portfolio/state.json`
4. `approve_recommendations(report, portfolio)` → (approved, rejected)
5. `apply_trades(approved, portfolio, signal_map, today)` → (updated_portfolio, trade_log)
6. `compute_day_pnl(portfolio, signal_map)` → (day_pnl, day_pnl_pct)
7. `generate_daily_report(...)` → `DailyReport` (Claude narrative or algorithmic)
8. Persist portfolio state, history, trade log, daily report
9. `update_memory(...)` → append to `MEMORY.md`

## Environment Variables
- `ANTHROPIC_API_KEY` — Claude narrative (falls back to template)
- `DEFAULT_ACCOUNT_TYPE`, `DEFAULT_TARGET_MARKET`, `DEFAULT_BUDGET`
- `DATA_DIR` — default `/app/data`
