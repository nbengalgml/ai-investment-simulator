# CLAUDE.md — market-researcher

> **SIMULATION ONLY**: All outputs are for educational and entertainment purposes only. Not financial advice. No real trades are executed.

## Role
Primary data ingestion agent. Fetches market data, news, SEC filings, Reddit sentiment, and analyst ratings for a target sector. Synthesizes raw signals into a scored `MarketResearchSnapshot` JSON file consumed by the Analyst agent.

## Entry Point
```bash
python agents/market-researcher/main.py --sector AI
python agents/market-researcher/main.py --sector cloud --no-claude
```

## Run Schedule
| Time (ET) | Trigger |
|---|---|
| 05:30 | Pre-market scan |
| 09:15 | Pre-open scan |
| 13:00 | Midday scan |
| 15:30 | Pre-close scan |

Triggered by the Scheduler agent via `POST /agents/market-researcher/trigger` (M6).

## Data Sources (priority order)
1. **SEC EDGAR** full-text search — 8-K filings (earnings, guidance, material events)
2. **NewsAPI** free tier — financial headlines filtered by sector + tickers
3. **Reddit PRAW** — r/wallstreetbets, r/investing, r/stocks mention velocity + sentiment
4. **yfinance** — price history, P/E, analyst ratings, earnings calendar

All data sources are optional; the agent runs with any subset available.

## Sector → Ticker Universe
Defined in `shared/config.py` (`SECTOR_TICKERS`). 10 tickers per sector. SEC EDGAR limited to top 5 to respect rate limits.

## Output
`data/research/market_snapshots/YYYY-MM-DD_HH_<sector>.json`

Schema: `shared/data_models/research.py::MarketResearchSnapshot`

Each `StockSignal` carries:
- Raw signals: prices, P/E, analyst consensus, news count, reddit count, SEC filing summary
- Scored fields: `momentum_score`, `fundamental_score`, `sentiment_score`, `composite_score` (all 0–100)

## Scoring
Primary: Claude (`claude-sonnet-4-6`) via `shared/claude_client/`. System prompt is cached.
Fallback: `_score_algorithmic()` in `research.py` — rule-based, no API required.

Composite = momentum×0.40 + fundamental×0.35 + sentiment×0.25

## Workflow
1. `get_tickers(sector)` → universe
2. `fetch_stock_data(ticker)` per ticker (yfinance)
3. `fetch_sector_news(sector, tickers)` (NewsAPI)
4. `fetch_ticker_mentions(tickers)` (Reddit)
5. `fetch_batch_8k(tickers[:5])` (SEC EDGAR)
6. Assemble `StockSignal` objects
7. Score via Claude or algorithmic fallback
8. Save `MarketResearchSnapshot` JSON

## Environment Variables Required
- `ANTHROPIC_API_KEY` — Claude scoring (optional; falls back to algorithmic)
- `NEWSAPI_KEY` — news headlines (optional; skipped if absent)
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` — Reddit (optional; skipped if absent)
- `DEFAULT_TARGET_MARKET` — default sector if `--sector` not passed
- `DATA_DIR` — output path (default: `/app/data`)
