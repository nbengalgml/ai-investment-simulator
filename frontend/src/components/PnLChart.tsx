import { useState } from 'react'
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import type { PortfolioState } from '../api/types'
import { fmt } from '../utils/format'

type Range = '7D' | '30D' | '90D'

interface ChartPoint {
  date: string
  value: number
  label: string
}

function toPoints(history: PortfolioState[]): ChartPoint[] {
  return history.map(snap => ({
    date: snap.last_updated.slice(0, 10),
    value: snap.total_market_value + snap.cash_available,
    label: snap.last_updated.slice(0, 10),
  }))
}

function filterRange(points: ChartPoint[], range: Range): ChartPoint[] {
  const days = range === '7D' ? 7 : range === '30D' ? 30 : 90
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  const cutoffStr = cutoff.toISOString().slice(0, 10)
  return points.filter(p => p.date >= cutoffStr)
}

interface Props {
  history: PortfolioState[]
}

export function PnLChart({ history }: Props) {
  const [range, setRange] = useState<Range>('30D')

  const all = toPoints(history)
  const points = filterRange(all, range)

  const baseline = points[0]?.value ?? 0
  const isUp = points.length > 1 && points[points.length - 1].value >= baseline

  if (points.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-600 text-sm">
        No history data — run a full agent cycle first.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Portfolio Value
        </span>
        <div className="flex gap-1">
          {(['7D', '30D', '90D'] as Range[]).map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`text-xs px-2 py-0.5 rounded transition-colors ${
                range === r
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={points} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isUp ? '#10b981' : '#ef4444'} stopOpacity={0.3} />
              <stop offset="95%" stopColor={isUp ? '#10b981' : '#ef4444'} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: '#6b7280', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#6b7280', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={v => `$${(v / 1000).toFixed(0)}k`}
            width={44}
          />
          <Tooltip
            formatter={(v: number) => [fmt.usd(v), 'Value']}
            contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 6 }}
            labelStyle={{ color: '#e5e7eb', fontSize: 11 }}
            itemStyle={{ color: '#9ca3af', fontSize: 11 }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={isUp ? '#10b981' : '#ef4444'}
            strokeWidth={2}
            fill="url(#pnlGrad)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
