# SKILL.md — ceo

> **SIMULATION ONLY** — not financial advice.

## Approval Logic

```python
def approve_recommendations(report, portfolio):
    # SELL / HOLD → always approved
    # BUY → approved only if:
    #   len(rec.data_sources) >= 2
    #   rec.allocation_pct <= 35.0
    #   current_positions (after pending SELLs + pending BUYs) < 5
```

## Trade Execution

```python
# BUY
shares = (portfolio.budget_total * rec.allocation_pct / 100) / current_price
Holding(open_date=today, avg_cost_basis=current_price, ...)

# SELL (full)
gain_loss = (current_price - h.avg_cost_basis) * h.shares
# holding removed from portfolio
```

## Tax Impact Rules

| Account | Holding Days | Treatment |
|---|---|---|
| IRA | any | `tax-deferred (IRA)` |
| Brokerage | < 365 | `short-term gain, taxed as ordinary income` |
| Brokerage | ≥ 365 | `long-term capital gain (LTCG)` |
| BUY | n/a | `n/a` |

## Day P&L Calculation

```python
day_pnl = sum(holding.market_value * signal.price_change_1d_pct / 100)
day_pnl_pct = day_pnl / portfolio.total_market_value * 100
```
Uses pre-trade portfolio values — represents market move, not trade profit.

## Portfolio Recalculation After Trades

```python
total_invested_pct = sum(h.allocation_pct for h in new_holdings)
cash_available = budget_total * (1 - total_invested_pct / 100)
total_market_value = budget_total * total_invested_pct / 100
```

## Next-Day Watchlist
Top 5 unowned tickers by `composite_score` from latest snapshot.

## Memory Entry Format
```markdown
## YYYY-MM-DD
- P&L: $+XXX.XX
- Holdings: N | Cash: $X,XXX.XX
- Bought: TICK1, TICK2
- Sold: TICK3
- Rejected: N recommendation(s)
```
