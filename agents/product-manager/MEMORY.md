# Product Manager MEMORY.md

## Architecture: Multi-Simulation Tracking (implemented 2026-05-04)

Each simulation is identified by `sim_id = "{sector}-{account_type}"` e.g. `AI-brokerage`, `AI-traditional_ira`.

**Data namespacing:**
- Market snapshots: `data/research/market_snapshots/` — shared across all sims for the same sector (no duplicate fetches)
- Per-sim data root: `data/simulations/{sim_id}/`
  - `portfolio/state.json` — current portfolio
  - `portfolio/history/{date}.json` — daily snapshots
  - `trades/log.json` — full trade log with rationale
  - `reports/daily/` — CEO daily reports
  - `research/recommendations/` — analyst reports

**Agent args:**
- `market-researcher` — unchanged, writes shared snapshots
- `analyst --sector AI --account-type brokerage` — writes to sim-specific recommendations dir
- `ceo --sector AI --account-type brokerage` — reads sim-specific recs, writes all sim-specific outputs

**API:**
- `GET /simulations` — leaderboard of all sim cards with P&L
- `GET /simulations/{sim_id}/portfolio|trades|reports/daily`
- `POST /agents/{agent}/trigger` — now accepts `account_type` in payload

**Frontend:**
- Parent tabs: Brokerage (post-tax) | Traditional IRA (pre-tax)
- Left sidebar: sector picker (AI, Cloud, Networking, Alternative Energy, Gas, Finance) + live leaderboard sorted by return
- Main area: Portfolio | P&L Chart | Trade Log | Daily Report tabs per selected sim
- `↻ Run Cycle` button in tab bar to trigger a new cycle for the active sim

## Active Simulations
Up to 12 parallel simulations: 6 sectors × 2 account types.
All share market data; diverge on recommendations and execution due to account-type tax rules.

## Goal
After 1 month of daily cycles, compare total return % across all 12 sims to identify the winning (sector, account_type) combo.
