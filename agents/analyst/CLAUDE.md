# CLAUDE.md — analyst

> **SIMULATION ONLY**: All outputs are for educational and entertainment purposes only. Not financial advice. No real trades are executed.

## Role
The investment brain. Reads the latest `MarketResearchSnapshot` and current `PortfolioState`, applies the growth investment strategy, and produces an `AnalystReport` with BUY / SELL / HOLD recommendations, allocation percentages, confidence levels, and 3-bullet rationale per position.

## Entry Point
```bash
python agents/analyst/main.py --sector AI
python agents/analyst/main.py --sector cloud --no-claude
```

## Runs After
Each Market Researcher cycle — triggered by the CEO agent (M5) or Scheduler (M6).

## Strategy: Growth
| Constraint | Rule |
|---|---|
| Max positions | 5 simultaneously |
| Max single position | 35% of invested capital |
| Min cash reserve | 10% always available |
| Stop-loss | –20% → SELL |
| Review zone | –15% → HOLD with review flag |
| Rebalance trigger | >40% → partial SELL back to 30% |

## Entry Signals (HIGH confidence requires all 3)
1. **Momentum**: 20-day return > sector average
2. **Fundamental**: analyst consensus = buy / strong_buy
3. **Sentiment**: Reddit sentiment > 0 AND news sentiment > 0

2 of 3 → MEDIUM. 1 of 3 → LOW.

## Account-Type Rules
**Brokerage (post-tax)**
- Prefer holding periods >365 days for LTCG tax treatment
- Flag short-term positions (<1yr) in rationale
- Avoid wash-sale triggers (30-day window on recently sold tickers)

**Traditional / Rollover IRA (pre-tax)**
- Tax-deferred growth — no LTCG vs STCG concern within account
- More flexible on short-term opportunities
- Note contribution limits ($7,000 / $8,000 if 50+) in settings — informational only

## Output
`data/research/recommendations/YYYY-MM-DD_HH_recommendations.json`
Schema: `shared/data_models/research.py::AnalystReport`

## Workflow
1. Load latest snapshot for sector from `data/research/market_snapshots/`
2. Load portfolio state from `data/portfolio/state.json` (creates default if absent)
3. `check_exit_signals(holdings)` → SELL/HOLD exits
4. `rank_candidates(signals, held_tickers)` → sorted BUY candidates
5. `compute_allocations(candidates, portfolio)` → (signal, pct) pairs
6. Generate rationale via Claude (or algorithmic fallback)
7. Assemble `AnalystReport` and persist

## Environment Variables
- `ANTHROPIC_API_KEY` — Claude rationale (falls back to template-based)
- `DEFAULT_ACCOUNT_TYPE`, `DEFAULT_TARGET_MARKET`, `DEFAULT_BUDGET`
- `DATA_DIR` — default `/app/data`
