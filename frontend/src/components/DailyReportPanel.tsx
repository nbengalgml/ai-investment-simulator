import type { DailyReport } from '../api/types'
import { fmt } from '../utils/format'

interface Props {
  report: DailyReport
}

export function DailyReportPanel({ report }: Props) {
  const perf = report.portfolio_performance
  const pnlPos = perf.day_pnl >= 0

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
            Daily Report — {report.report_date}
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-xl font-semibold tabular-nums ${pnlPos ? 'text-green-400' : 'text-red-400'}`}>
              {fmt.pnl(perf.day_pnl)}
            </span>
            <span className={`text-sm ${pnlPos ? 'text-green-500' : 'text-red-500'}`}>
              ({fmt.pct(perf.day_pnl_pct)})
            </span>
          </div>
        </div>
      </div>

      {/* Executive summary */}
      <div className="border border-gray-800 rounded-lg p-4">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Executive Summary
        </div>
        <p className="text-sm text-gray-300 leading-relaxed">{report.executive_summary}</p>
      </div>

      {/* Market conditions */}
      <div className="border border-gray-800 rounded-lg p-4">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Market Conditions
        </div>
        <p className="text-sm text-gray-400 leading-relaxed">{report.market_conditions}</p>
      </div>

      {/* Top signals */}
      {report.top_signals.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Top Signals
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-xs text-gray-600">
                  <th className="text-left py-1.5 pr-4 font-medium">Ticker</th>
                  <th className="text-right py-1.5 pr-4 font-medium">Score</th>
                  <th className="text-right py-1.5 font-medium">20D Momentum</th>
                </tr>
              </thead>
              <tbody>
                {report.top_signals.map((s, i) => (
                  <tr key={i} className="border-b border-gray-900">
                    <td className="py-1.5 pr-4 font-bold">{String(s.ticker)}</td>
                    <td className="py-1.5 pr-4 text-right tabular-nums text-gray-300">
                      {Number(s.composite_score ?? 0).toFixed(0)}
                    </td>
                    <td className={`py-1.5 text-right tabular-nums ${Number(s.momentum_20d_pct ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {fmt.pct(Number(s.momentum_20d_pct ?? 0))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Next day watchlist */}
      {report.next_day_watchlist.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Tomorrow's Watchlist
          </div>
          <div className="flex flex-wrap gap-2">
            {report.next_day_watchlist.map(t => (
              <span key={t} className="text-xs px-2.5 py-1 rounded border border-gray-700 text-gray-300">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Pending recommendations */}
      {report.recommendations_pending.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Pending Review ({report.recommendations_pending.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {report.recommendations_pending.map((r, i) => (
              <span key={i} className="text-xs px-2.5 py-1 rounded border border-yellow-800 text-yellow-600">
                {String(r.ticker)} · {String(r.action)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
