import { useState } from 'react'
import type { TradeLogEntry } from '../api/types'
import { fmt } from '../utils/format'

const ACTION_COLORS: Record<string, string> = {
  BUY: 'text-green-400',
  SELL: 'text-red-400',
  HOLD: 'text-yellow-400',
}

interface Props {
  trades: TradeLogEntry[]
}

export function TradeLog({ trades }: Props) {
  const [filter, setFilter] = useState<'ALL' | 'BUY' | 'SELL' | 'HOLD'>('ALL')

  const filtered = filter === 'ALL' ? trades : trades.filter(t => t.action === filter)

  if (trades.length === 0) {
    return (
      <div className="text-center py-12 text-gray-600 text-sm">
        No trades yet — run a CEO agent cycle to execute recommendations.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        {(['ALL', 'BUY', 'SELL', 'HOLD'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`text-xs px-2.5 py-1 rounded transition-colors ${
              filter === f
                ? 'bg-gray-700 text-gray-100'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {f}
          </button>
        ))}
        <span className="ml-auto text-xs text-gray-600">{filtered.length} entries</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-xs text-gray-500 uppercase tracking-wider">
              <th className="text-left py-2 pr-4 font-medium">Date</th>
              <th className="text-left py-2 pr-4 font-medium">Action</th>
              <th className="text-left py-2 pr-4 font-medium">Ticker</th>
              <th className="text-right py-2 pr-4 font-medium">Shares</th>
              <th className="text-right py-2 pr-4 font-medium">Price</th>
              <th className="text-right py-2 pr-4 font-medium">Value</th>
              <th className="text-left py-2 font-medium">Rationale</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(t => (
              <tr key={t.trade_id} className="border-b border-gray-900 hover:bg-gray-900/50">
                <td className="py-2 pr-4 text-gray-500 tabular-nums whitespace-nowrap">
                  {t.timestamp.slice(0, 10)}
                </td>
                <td className={`py-2 pr-4 font-semibold ${ACTION_COLORS[t.action] ?? 'text-gray-300'}`}>
                  {t.action}
                </td>
                <td className="py-2 pr-4 font-bold">{t.ticker}</td>
                <td className="py-2 pr-4 text-right tabular-nums text-gray-300">
                  {t.shares.toFixed(3)}
                </td>
                <td className="py-2 pr-4 text-right tabular-nums text-gray-300">
                  {fmt.usd(t.price)}
                </td>
                <td className="py-2 pr-4 text-right tabular-nums text-gray-200 font-medium">
                  {fmt.usd(t.total_value)}
                </td>
                <td className="py-2 text-gray-500 max-w-xs truncate" title={t.rationale}>
                  {t.rationale}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
