import type { Holding } from '../api/types'
import { fmt } from '../utils/format'

const CONFIDENCE_COLORS = {
  HIGH: 'text-green-400 border-green-700',
  MEDIUM: 'text-yellow-400 border-yellow-700',
  LOW: 'text-red-400 border-red-700',
}

interface HoldingCardProps {
  holding: Holding
}

function HoldingCard({ holding: h }: HoldingCardProps) {
  const pnlPos = h.unrealized_pnl >= 0
  const confColor = CONFIDENCE_COLORS[h.confidence] ?? 'text-gray-400 border-gray-700'

  return (
    <div className="border border-gray-800 rounded-lg p-4 flex flex-col gap-3 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-lg font-bold tracking-wide">{h.ticker}</span>
          <span className={`ml-2 text-xs px-1.5 py-0.5 rounded border ${confColor}`}>
            {h.confidence}
          </span>
        </div>
        <span className="text-xs text-gray-500 uppercase">{h.analyst_rating}</span>
      </div>

      <div className="grid grid-cols-2 gap-y-1 text-sm">
        <div className="text-gray-500">Price</div>
        <div className="text-right tabular-nums">{fmt.usd(h.current_price)}</div>

        <div className="text-gray-500">Shares</div>
        <div className="text-right tabular-nums">{h.shares.toFixed(3)}</div>

        <div className="text-gray-500">Value</div>
        <div className="text-right tabular-nums">{fmt.usd(h.market_value)}</div>

        <div className="text-gray-500">Avg Cost</div>
        <div className="text-right tabular-nums">{fmt.usd(h.avg_cost_basis)}</div>
      </div>

      <div className="border-t border-gray-800 pt-2 flex items-center justify-between">
        <div className={`text-sm font-semibold tabular-nums ${pnlPos ? 'text-green-400' : 'text-red-400'}`}>
          {fmt.pnl(h.unrealized_pnl)}{' '}
          <span className="font-normal text-xs">({fmt.pct(h.unrealized_pnl_pct)})</span>
        </div>
        <div className="text-xs text-gray-500">
          {h.allocation_pct.toFixed(1)}% alloc
        </div>
      </div>
    </div>
  )
}

interface Props {
  holdings: Holding[]
}

export function HoldingsGrid({ holdings }: Props) {
  if (holdings.length === 0) {
    return (
      <div className="text-center py-12 text-gray-600">
        No open positions — run the analyst agent to generate recommendations.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
      {holdings.map(h => (
        <HoldingCard key={h.ticker} holding={h} />
      ))}
    </div>
  )
}
