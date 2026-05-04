# /portfolio — show current portfolio state

Displays the current portfolio: holdings, allocation, cash, and total value.

```bash
python3 -c "
import json, sys
try:
    d = json.load(open('data/portfolio/state.json'))
    print(f'Total: \${d[\"total_market_value\"]:,.2f}  Cash: \${d[\"cash_available\"]:,.2f}')
    print(f'Budget: \${d[\"budget_total\"]:,.2f}  Account: {d[\"account_type\"]}')
    print()
    for h in d.get('holdings', []):
        pnl = (h['current_price'] - h['avg_cost_basis']) / h['avg_cost_basis'] * 100
        print(f'  {h[\"ticker\"]:6}  {h[\"allocation_pct\"]:5.1f}%  {pnl:+.1f}%  \${h[\"market_value\"]:,.2f}')
except FileNotFoundError:
    print('No portfolio state found. Run /run to initialize.')
"
```
