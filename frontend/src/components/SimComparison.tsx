import type { SimulationSummary } from '../api/types'

interface Props {
  sims: SimulationSummary[]
  activeSim: string
  onSelect: (simId: string) => void
}

const ACCOUNT_LABEL: Record<string, string> = {
  brokerage: 'Brokerage',
  traditional_ira: 'IRA',
}

export function SimComparison({ sims, activeSim, onSelect }: Props) {
  const withData = sims.filter(s => s.has_data)
  const sorted = [...withData].sort(
    (a, b) => (b.total_unrealized_pnl_pct ?? 0) - (a.total_unrealized_pnl_pct ?? 0),
  )

  if (sorted.length === 0) {
    return (
      <div className="text-gray-600 text-xs text-center py-4">
        No simulations have data yet.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-2 pr-3 font-medium">#</th>
            <th className="text-left py-2 pr-3 font-medium">Sim</th>
            <th className="text-right py-2 pr-3 font-medium">Value</th>
            <th className="text-right py-2 pr-3 font-medium">P&amp;L</th>
            <th className="text-right py-2 font-medium">Return</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((s, i) => {
            const pnlPct = s.total_unrealized_pnl_pct ?? 0
            const pnl = s.total_unrealized_pnl ?? 0
            const isActive = s.sim_id === activeSim
            return (
              <tr
                key={s.sim_id}
                onClick={() => onSelect(s.sim_id)}
                className={`border-b border-gray-800/50 cursor-pointer transition-colors ${
                  isActive ? 'bg-blue-900/20' : 'hover:bg-gray-800/40'
                }`}
              >
                <td className="py-2 pr-3 text-gray-600">{i + 1}</td>
                <td className="py-2 pr-3">
                  <div className="font-medium text-gray-200">{s.sector.toUpperCase()}</div>
                  <div className="text-gray-500">{ACCOUNT_LABEL[s.account_type] ?? s.account_type}</div>
                </td>
                <td className="py-2 pr-3 text-right text-gray-300">
                  ${(s.total_market_value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </td>
                <td className={`py-2 pr-3 text-right ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {pnl >= 0 ? '+' : ''}${pnl.toFixed(0)}
                </td>
                <td className={`py-2 text-right font-semibold ${pnlPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
