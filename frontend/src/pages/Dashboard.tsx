import { useState } from 'react'
import { usePortfolio, usePortfolioHistory } from '../hooks/usePortfolio'
import { useAgentStatus, useTriggerAgent } from '../hooks/useAgentStatus'
import { useTrades } from '../hooks/useTrades'
import { useDailyReports } from '../hooks/useReports'
import { useSettings, useUpdateSettings } from '../hooks/useSettings'
import { PortfolioHeader } from '../components/PortfolioHeader'
import { HoldingsGrid } from '../components/HoldingsGrid'
import { AllocationChart } from '../components/AllocationChart'
import { AgentStatusSidebar } from '../components/AgentStatusSidebar'
import { PnLChart } from '../components/PnLChart'
import { TradeLog } from '../components/TradeLog'
import { DailyReportPanel } from '../components/DailyReportPanel'
import { SettingsPanel } from '../components/SettingsPanel'
import type { Settings } from '../api/types'

type Tab = 'portfolio' | 'pnl' | 'trades' | 'report' | 'settings'

const TABS: { id: Tab; label: string }[] = [
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'pnl', label: 'P&L Chart' },
  { id: 'trades', label: 'Trade Log' },
  { id: 'report', label: 'Daily Report' },
  { id: 'settings', label: 'Settings' },
]

export function Dashboard() {
  const [tab, setTab] = useState<Tab>('portfolio')
  const [savedAt, setSavedAt] = useState<Date | null>(null)

  const portfolio = usePortfolio()
  const history = usePortfolioHistory()
  const agentStatus = useAgentStatus()
  const trades = useTrades()
  const reports = useDailyReports()
  const settings = useSettings()
  const trigger = useTriggerAgent()
  const updateSettings = useUpdateSettings()

  const handleTrigger = (agent: string) => {
    trigger.mutate({ agent, sector: portfolio.data?.target_market ?? 'AI' })
  }

  const handleSaveSettings = (updated: Partial<Settings>) => {
    updateSettings.mutate(updated, { onSuccess: () => setSavedAt(new Date()) })
  }

  if (portfolio.isError) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
        Unable to load portfolio. Ensure the API is running and an agent cycle has completed.
      </div>
    )
  }

  if (portfolio.isLoading || !portfolio.data) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-600 text-sm animate-pulse">
        Loading…
      </div>
    )
  }

  const p = portfolio.data

  return (
    <div className="flex flex-col h-full">
      <PortfolioHeader portfolio={p} />

      {/* Tab bar */}
      <div className="border-b border-gray-800 px-6 flex items-center gap-1 flex-shrink-0">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`text-sm px-4 py-2.5 transition-colors border-b-2 ${
              tab === t.id
                ? 'border-blue-500 text-gray-100'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content + sidebar */}
      <div className="flex flex-1 min-h-0 gap-0">
        <div className="flex-1 min-w-0 overflow-auto p-6">
          {tab === 'portfolio' && (
            <HoldingsGrid holdings={p.holdings} />
          )}

          {tab === 'pnl' && (
            <div className="max-w-3xl">
              <PnLChart history={history.data ?? []} />
            </div>
          )}

          {tab === 'trades' && (
            <TradeLog trades={trades.data ?? []} />
          )}

          {tab === 'report' && (
            reports.data && reports.data.length > 0
              ? <DailyReportPanel report={reports.data[0]} />
              : <div className="text-gray-600 text-sm py-12 text-center">
                  No daily reports yet — run a CEO agent cycle.
                </div>
          )}

          {tab === 'settings' && settings.data && (
            <SettingsPanel
              settings={settings.data}
              onSave={handleSaveSettings}
              isSaving={updateSettings.isPending}
              savedAt={savedAt}
            />
          )}
        </div>

        {/* Sidebar — always visible */}
        <div className="w-56 flex-shrink-0 border-l border-gray-800 p-4 flex flex-col gap-4 overflow-auto">
          <div className="border border-gray-800 rounded-lg p-3">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Allocation
            </div>
            <AllocationChart portfolio={p} />
          </div>

          {agentStatus.data && (
            <AgentStatusSidebar
              status={agentStatus.data}
              onTrigger={handleTrigger}
            />
          )}

          <div className="border border-gray-800 rounded-lg p-3 text-xs text-gray-600 space-y-1">
            <div className="font-semibold text-gray-500">Info</div>
            <div>Budget: <span className="text-gray-400">${p.budget_total.toLocaleString()}</span></div>
            <div>Strategy: <span className="text-gray-400 capitalize">{p.strategy}</span></div>
            <div className="pt-1 text-gray-700">
              {new Date(p.last_updated).toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
