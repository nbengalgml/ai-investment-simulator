# SKILL.md — analyst

> **SIMULATION ONLY** — not financial advice.

## Confidence Determination

```python
def _confidence(signal, avg_momentum) -> "HIGH" | "MEDIUM" | "LOW":
    met = 0
    if signal.momentum_20d_pct > avg_momentum:          met += 1  # entry signal 1
    if analyst_consensus in ("buy", "strong_buy"):      met += 1  # entry signal 2
    if reddit_sentiment > 0 and news_sentiment > 0:     met += 1  # entry signal 3
    return "HIGH" if met >= 3 else ("MEDIUM" if met == 2 else "LOW")
```

## Exit Signal Rules

| Condition | Action | Trigger key |
|---|---|---|
| `(current_price - avg_cost) / avg_cost * 100 ≤ -20` | SELL | `stop_loss` |
| `allocation_pct > 40` | SELL (partial to 30%) | `rebalance` |
| `(current - avg_cost) / avg_cost * 100 ≤ -15` | HOLD (review) | `review_zone` |

## Allocation Sizing

```python
# open_slots = MAX_POSITIONS (5) - current_holdings + freed_by_sells
# available = 100% - current_invested% - MIN_CASH_PCT (10%)
# per stock: min(composite_score / total_score * available, MAX_SINGLE_PCT (35%))
```

Scores used: `StockSignal.composite_score` (0–100) from Market Researcher.
If composite_score is None, defaults to 50.

## Sector Average Momentum

```python
avg_momentum = sum(s.momentum_20d_pct for s in signals) / len(signals)
```
Used as the benchmark for entry signal #1.

## Brokerage Tax Notes (embed in rationale)
- Holding period < 365 days → "short-term gain, taxed as ordinary income"
- Holding period ≥ 365 days → "qualifies for preferential LTCG rate"
- Wash-sale rule: if ticker was sold at a loss within last 30 days, flag it

## IRA Tax Notes (embed in rationale)
- All gains tax-deferred within account — no short/long-term distinction
- Can trade more actively without tax penalty
- Annual contribution limit is informational only ($7,000 / $8,000 if 50+)

## Rationale Format
Claude prompt produces 3 bullets per recommendation.
Each bullet references a specific data point (score, %, count, filing).
Algorithmic fallback uses templates in `_algo_rationale()`.

## Composite Score Weighting (from Market Researcher)
```
composite = momentum * 0.40 + fundamental * 0.35 + sentiment * 0.25
```
Analyst trusts this score; does not recompute — focuses on ranking and allocation.
