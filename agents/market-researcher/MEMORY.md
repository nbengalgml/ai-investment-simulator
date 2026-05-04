# Market Researcher MEMORY.md

## Role
Primary data ingestion agent. Runs 4× daily (05:30, 09:15, 13:00, 15:30 ET) on NYSE
trading days. Outputs `MarketResearchSnapshot` JSON consumed by the Analyst.

## Data Source Status
- yfinance: always available (no API key required)
- NewsAPI: requires `NEWSAPI_KEY` — gracefully skipped if absent
- Reddit PRAW: requires `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` — skipped if absent
- SEC EDGAR: free, rate-limited to 5 tickers per cycle

## Scoring
Composite = momentum×0.40 + fundamental×0.35 + sentiment×0.25  
Claude fallback: `_score_algorithmic()` — fully deterministic, no API required.

## Output Pattern
`data/research/market_snapshots/YYYY-MM-DD_HH_<sector>.json`

## Simulation Status
Initialized. Awaiting first scheduled trigger from Scheduler agent.
