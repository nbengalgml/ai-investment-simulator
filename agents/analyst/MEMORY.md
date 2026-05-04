# Analyst MEMORY.md

## Role
Investment brain. Reads the latest `MarketResearchSnapshot`, applies growth strategy
rules, and produces `AnalystReport` with BUY/SELL/HOLD recommendations.
Runs 3× daily (09:30, 13:30, 16:00 ET) after Market Researcher cycles.

## Strategy Constants
- MAX_POSITIONS = 5 | MAX_SINGLE_PCT = 35% | MIN_CASH_PCT = 10%
- STOP_LOSS = -20% → SELL | REVIEW_ZONE = -15% → HOLD
- REBALANCE: >40% allocation → partial SELL back to 30%

## Confidence Signal Logic
HIGH = all 3: (1) momentum > sector avg, (2) analyst buy/strong_buy, (3) reddit>0 AND news>0  
MEDIUM = 2 of 3 | LOW = 1 of 3

## Rationale
Claude produces 3 data-driven bullets per recommendation.
Algorithmic fallback in `_algo_rationale()` — no API required.

## Output Pattern
`data/research/recommendations/YYYY-MM-DD_HH_recommendations.json`

## Simulation Status
Initialized. Awaiting first Market Researcher snapshot.
