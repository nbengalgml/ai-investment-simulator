import type { PortfolioState } from '../api/types'
import { fmt } from '../utils/format'

interface Props {
  portfolio: PortfolioState
}

export function PortfolioHeader({ portfolio }: Props) {
  const totalValue = portfolio.total_market_value + portfolio.cash_available
  const pnlPositive = portfolio.total_unrealized_pnl >= 0
  const cashPct = portfolio.budget_total > 0
    ? (portfolio.cash_available / portfolio.budget_total) * 100
    : 0

  return (
    <div className="border-b border-gray-800 px-6 py-4 flex flex-wrap items-center gap-6">
      <div>
        <div className="text-xs text-gray-500 uppercase tracking-wider">Portfolio Value</div>
        <div className="text-2xl font-semibold tabular-nums">{fmt.usd(totalValue)}</div>
      </div>

      <div>
        <div className="text-xs text-gray-500 uppercase tracking-wider">Unrealized P&amp;L</div>
        <div className={`text-xl font-semibold tabular-nums ${pnlPositive ? 'text-green-400' : 'text-red-400'}`}>
          {fmt.pnl(portfolio.total_unrealized_pnl)}{' '}
          <span className="text-sm">({fmt.pct(portfolio.total_unrealized_pnl_pct)})</span>
        </div>
      </div>

      <div>
        <div className="text-xs text-gray-500 uppercase tracking-wider">Cash</div>
        <div className="text-xl font-semibold tabular-nums text-gray-200">
          {fmt.usd(portfolio.cash_available)}{' '}
          <span className="text-sm text-gray-400">({cashPct.toFixed(1)}%)</span>
        </div>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <span className="text-xs px-2 py-1 rounded border border-blue-500 text-blue-400 uppercase tracking-wider">
          {portfolio.account_type === 'traditional_ira' ? 'IRA' : 'Brokerage'}
        </span>
        <span className="text-xs px-2 py-1 rounded border border-purple-500 text-purple-400 uppercase tracking-wider">
          {portfolio.target_market}
        </span>
        <span className="text-xs text-gray-600">
          {portfolio.holdings.length}/{portfolio.max_positions} positions
        </span>
      </div>
    </div>
  )
}
