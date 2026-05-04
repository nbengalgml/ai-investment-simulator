import { useState } from 'react'
import { createPortal } from 'react-dom'
import type { Holding } from '../api/types'
import { fmt } from '../utils/format'
import { TickerBadge } from './TickerBadge'
import { getTickerInfo } from '../data/tickers'

const CONFIDENCE_COLORS = {
  HIGH: 'text-green-400 border-green-700',
  MEDIUM: 'text-yellow-400 border-yellow-700',
  LOW: 'text-orange-400 border-orange-700',
}

const CONFIDENCE_DETAILS: Record<string, { label: string; signals: string[] }> = {
  HIGH: {
    label: 'All 3 signals met',
    signals: [
      '20-day momentum above sector average',
      'Analyst consensus = buy or strong_buy',
      'Positive news sentiment AND Reddit mentions',
    ],
  },
  MEDIUM: {
    label: '2 of 3 signals met',
    signals: [
      '20-day momentum above sector average',
      'Analyst consensus = buy or strong_buy',
      'Sentiment signal not required (needs API keys)',
    ],
  },
  LOW: {
    label: '1 of 3 signals met',
    signals: [
      'At least one positive indicator present',
      'Used by IRA accounts (lower threshold)',
      'Brokerage requires MEDIUM or higher',
    ],
  },
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const colorClass = CONFIDENCE_COLORS[confidence] ?? 'text-gray-400 border-gray-700'
  const details = CONFIDENCE_DETAILS[confidence]

  return (
    <div
      className="relative inline-block"
      onMouseEnter={e => setPos({ x: e.clientX, y: e.clientY })}
      onMouseMove={e => setPos({ x: e.clientX, y: e.clientY })}
      onMouseLeave={() => setPos(null)}
    >
      <span className={`mt-1 inline-block text-xs px-1.5 py-0.5 rounded border cursor-default ${colorClass}`}>
        {confidence}
      </span>
      {pos && details && createPortal(
        <div
          className="fixed z-[9999] w-60 bg-gray-900 border border-gray-700 rounded-lg shadow-xl p-3 text-left pointer-events-none"
          style={{ left: pos.x + 12, top: pos.y + 12 }}
        >
          <div className="text-xs font-semibold text-gray-200 mb-2">{details.label}</div>
          <ul className="space-y-1">
            {details.signals.map((s, i) => (
              <li key={i} className="text-xs text-gray-400 flex gap-1.5">
                <span className="text-gray-600 flex-shrink-0">{i + 1}.</span>
                {s}
              </li>
            ))}
          </ul>
        </div>,
        document.body
      )}
    </div>
  )
}

interface HoldingCardProps {
  holding: Holding
}

function HoldingCard({ holding: h }: HoldingCardProps) {
  const pnlPos = h.unrealized_pnl >= 0
  const info = getTickerInfo(h.ticker)

  return (
    <div className="border border-gray-800 rounded-lg p-4 flex flex-col gap-3 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <TickerBadge ticker={h.ticker} className="text-lg" />
          {info && <div className="text-xs text-gray-500 mt-0.5 truncate max-w-[140px]">{info.name}</div>}
          <ConfidenceBadge confidence={h.confidence} />
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
