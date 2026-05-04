import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../api/client'
import type { Holding } from '../api/types'

type Range = '1D' | '5D' | '1M' | '1Y'

const RANGES: Range[] = ['1D', '5D', '1M', '1Y']

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#64748b']

interface Props {
  holdings: Holding[]
}

function formatTick(t: string, range: Range): string {
  if (!t) return ''
  try {
    const d = new Date(t)
    if (range === '1D' || range === '5D') {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
  } catch {
    return t.slice(5) // MM-DD fallback
  }
}

export function PortfolioStockChart({ holdings }: Props) {
  const [range, setRange] = useState<Range>('1M')

  const tickers = holdings.map(h => h.ticker)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['price-history', tickers.join(','), range],
    queryFn: () => api.priceHistory(tickers, range),
    enabled: tickers.length > 0,
    staleTime: 5 * 60_000,
  })

  if (tickers.length === 0) return null

  // Build unified time axis: merge all timestamps, normalise each series to % change from first point
  const series = data?.series ?? {}
  const allTimes = [...new Set(
    Object.values(series).flatMap(pts => pts.map(p => p.t))
  )].sort()

  const baseMap: Record<string, number> = {}
  for (const [ticker, pts] of Object.entries(series)) {
    if (pts.length > 0) baseMap[ticker] = pts[0].p
  }

  const chartData = allTimes.map(t => {
    const row: Record<string, string | number> = { t }
    for (const [ticker, pts] of Object.entries(series)) {
      const pt = pts.find(p => p.t === t)
      if (pt && baseMap[ticker]) {
        row[ticker] = parseFloat(((pt.p / baseMap[ticker] - 1) * 100).toFixed(3))
      }
    }
    return row
  })

  return (
    <div className="mt-6 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Holdings Performance
        </span>
        <div className="flex gap-1">
          {RANGES.map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`text-xs px-2.5 py-1 rounded transition-colors ${
                range === r
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="h-52 flex items-center justify-center text-gray-600 text-sm animate-pulse">
          Loading price data…
        </div>
      )}

      {isError && (
        <div className="h-52 flex items-center justify-center text-gray-600 text-sm">
          Unable to load price history.
        </div>
      )}

      {!isLoading && !isError && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
            <XAxis
              dataKey="t"
              tickFormatter={t => formatTick(t, range)}
              tick={{ fill: '#6b7280', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: '#6b7280', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={v => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`}
              width={52}
            />
            <Tooltip
              formatter={(v: number, name: string) => [
                `${v > 0 ? '+' : ''}${v.toFixed(2)}%`,
                name,
              ]}
              contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 6 }}
              labelFormatter={t => formatTick(t as string, range)}
              labelStyle={{ color: '#e5e7eb', fontSize: 11 }}
              itemStyle={{ fontSize: 11 }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
              formatter={(value) => <span style={{ color: '#9ca3af' }}>{value}</span>}
            />
            {Object.keys(series).map((ticker, i) => (
              <Line
                key={ticker}
                type="monotone"
                dataKey={ticker}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={1.5}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}

      {!isLoading && !isError && chartData.length === 0 && (
        <div className="h-52 flex items-center justify-center text-gray-600 text-sm">
          No price data available for selected range.
        </div>
      )}
    </div>
  )
}
