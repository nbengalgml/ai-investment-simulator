import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { PortfolioState } from '../api/types'
import { fmt } from '../utils/format'

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#64748b']

interface Props {
  portfolio: PortfolioState
}

export function AllocationChart({ portfolio }: Props) {
  if (portfolio.holdings.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-600 text-sm">
        No data
      </div>
    )
  }

  const slices = portfolio.holdings.map((h, i) => ({
    name: h.ticker,
    value: h.allocation_pct,
    color: COLORS[i % COLORS.length],
  }))

  const totalInvested = portfolio.holdings.reduce((s, h) => s + h.allocation_pct, 0)
  const cashPct = Math.max(0, 100 - totalInvested)
  if (cashPct > 0) {
    slices.push({ name: 'Cash', value: cashPct, color: '#374151' })
  }

  return (
    <div className="flex flex-col gap-3">
      <ResponsiveContainer width="100%" height={160}>
        <PieChart margin={{ top: 0, right: 16, bottom: 0, left: 16 }}>
          <Pie
            data={slices}
            cx="50%"
            cy="50%"
            innerRadius={42}
            outerRadius={62}
            paddingAngle={2}
            dataKey="value"
          >
            {slices.map((s, i) => (
              <Cell key={s.name} fill={s.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(val: number) => [`${val.toFixed(1)}%`, 'Allocation']}
            contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 6 }}
            labelStyle={{ color: '#e5e7eb' }}
            itemStyle={{ color: '#9ca3af' }}
          />
        </PieChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap gap-2 justify-center">
        {slices.map(s => (
          <div key={s.name} className="flex items-center gap-1.5 text-xs text-gray-400">
            <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: s.color }} />
            {s.name} {s.value.toFixed(1)}%
          </div>
        ))}
      </div>
    </div>
  )
}
