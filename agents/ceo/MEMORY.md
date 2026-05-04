# CEO MEMORY.md

Runtime daily log is written to `data/agent_memory/ceo.md`.
This file captures the agent's role context, committed to git.

## Role
Final decision-maker. Approves/rejects analyst recommendations, executes simulated
trades, generates daily executive summary. Runs at 06:00 ET (morning thesis) and
16:15 ET (EOD approval + daily report).

## Strategy
- Max 5 positions; max 35% per position; min 10% cash reserve
- BUY requires ≥ 2 data sources; SELL/HOLD always approved
- Tax: brokerage tracks short-term (<365d) vs LTCG; IRA all tax-deferred
- Day P&L computed from pre-trade `price_change_1d_pct`; not realized gains

## Simulation Status
Portfolio initialized. No trades executed yet. Awaiting first Analyst cycle.
