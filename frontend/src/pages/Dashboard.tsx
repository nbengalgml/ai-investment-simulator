import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAgentStatus, useTriggerAgent } from '../hooks/useAgentStatus'
import { useSettings, useUpdateSettings } from '../hooks/useSettings'
import {
  useSimulations,
  useSimPortfolio,
  useSimPortfolioHistory,
  useSimTrades,
  useSimReports,
} from '../hooks/useSimulations'
import { PortfolioHeader } from '../components/PortfolioHeader'
import { HoldingsGrid } from '../components/HoldingsGrid'
import { AllocationChart } from '../components/AllocationChart'
import { AgentStatusSidebar } from '../components/AgentStatusSidebar'
import { PnLChart } from '../components/PnLChart'
import { TradeLog } from '../components/TradeLog'
import { DailyReportPanel } from '../components/DailyReportPanel'
import { SettingsPanel } from '../components/SettingsPanel'
import { SimComparison } from '../components/SimComparison'
import type { Settings } from '../api/types'

type AccountTab = 'brokerage' | 'traditional_ira'
type DetailTab = 'portfolio' | 'pnl' | 'trades' | 'report'

const ACCOUNT_TABS: { id: AccountTab; label: string }[] = [
  { id: 'brokerage', label: 'Brokerage (post-tax)' },
  { id: 'traditional_ira', label: 'Traditional IRA (pre-tax)' },
]

const DETAIL_TABS: { id: DetailTab; label: string }[] = [
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'pnl', label: 'P&L Chart' },
  { id: 'trades', label: 'Trade Log' },
  { id: 'report', label: 'Daily Report' },
]

const SECTORS = ['AI', 'cloud', 'networking', 'alternative_energy', 'gas', 'finance']

const CYCLE_STEPS = [
  { agent: 'market-researcher', label: 'Market Researcher', delay: 15_000 },
  { agent: 'analyst',           label: 'Analyst',           delay: 12_000 },
  { agent: 'ceo',               label: 'CEO',               delay: 12_000 },
]

export function Dashboard() {
  const [accountTab, setAccountTab] = useState<AccountTab>('brokerage')
  const [sector, setSector] = useState('AI')
  const [detailTab, setDetailTab] = useState<DetailTab>('portfolio')
  const [savedAt, setSavedAt] = useState<Date | null>(null)
  const [cycleStep, setCycleStep] = useState<string | null>(null)
  const [cycleError, setCycleError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const queryClient = useQueryClient()

  const simId = `${sector}-${accountTab}`

  const simulations = useSimulations()
  const portfolio = useSimPortfolio(simId)
  const history = useSimPortfolioHistory(simId)
  const trades = useSimTrades(simId)
  const reports = useSimReports(simId)
  const agentStatus = useAgentStatus()
  const settings = useSettings()
  const trigger = useTriggerAgent()
  const updateSettings = useUpdateSettings()

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))

  const runFullCycle = async () => {
    setCycleError(null)
    try {
      for (const step of CYCLE_STEPS) {
        setCycleStep(step.label)
        await trigger.mutateAsync({ agent: step.agent, sector, account_type: accountTab })
        await sleep(step.delay)
      }
    } catch {
      setCycleError('An agent trigger failed. Check that the API is running.')
      setCycleStep(null)
      return
    }
    setCycleStep('Finalizing…')
    let attempts = 0
    pollRef.current = setInterval(async () => {
      attempts++
      await queryClient.invalidateQueries({ queryKey: ['simulations', simId] })
      await portfolio.refetch()
      if (portfolio.data || attempts >= 20) {
        clearInterval(pollRef.current!)
        pollRef.current = null
        setCycleStep(null)
        simulations.refetch()
      }
    }, 3_000)
  }

  const handleTrigger = (agent: string) => {
    trigger.mutate({ agent, sector, account_type: accountTab })
  }

  const handleSaveSettings = (updated: Partial<Settings>) => {
    updateSettings.mutate(updated, { onSuccess: () => setSavedAt(new Date()) })
  }

  const isCycleRunning = cycleStep !== null
  const hasPortfolio = !!portfolio.data
  const isLoading = portfolio.isLoading

  return (
    <div className="flex flex-col h-full">
      {/* ── Account type parent tabs ── */}
      <div className="border-b border-gray-700 bg-gray-900/60 px-6 flex items-center gap-0">
        {ACCOUNT_TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setAccountTab(t.id)}
            className={`text-sm px-5 py-3 font-medium transition-colors border-b-2 ${
              accountTab === t.id
                ? 'border-blue-400 text-blue-300'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            {t.label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2 text-xs text-gray-600 pr-1">
          Comparing {SECTORS.length * 2} simulations
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* ── Left sidebar: sector selector + leaderboard ── */}
        <div className="w-52 flex-shrink-0 border-r border-gray-800 flex flex-col">
          {/* Sector selector */}
          <div className="p-3 border-b border-gray-800">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Sector</div>
            <div className="flex flex-col gap-1">
              {SECTORS.map(s => (
                <button
                  key={s}
                  onClick={() => setSector(s)}
                  className={`text-left text-xs px-2.5 py-1.5 rounded transition-colors ${
                    sector === s
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                  }`}
                >
                  {s.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </button>
              ))}
            </div>
          </div>

          {/* Leaderboard */}
          <div className="flex-1 overflow-auto p-3">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              All Simulations
            </div>
            <SimComparison
              sims={simulations.data ?? []}
              activeSim={simId}
              onSelect={(id) => {
                const parts = id.split('-')
                const acct = parts[parts.length - 1] as AccountTab
                const sec = parts.slice(0, -1).join('-')
                setSector(sec)
                setAccountTab(acct)
              }}
            />
          </div>
        </div>

        {/* ── Main content ── */}
        <div className="flex-1 min-w-0 flex flex-col min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-gray-600 text-sm animate-pulse">
              Loading…
            </div>
          ) : !hasPortfolio ? (
            /* Empty state */
            <div className="flex flex-col items-center justify-center h-full gap-6 text-center px-6">
              <div>
                <div className="text-xl font-bold text-gray-200 mb-1">
                  {sector.toUpperCase()} · {accountTab === 'brokerage' ? 'Brokerage' : 'Traditional IRA'}
                </div>
                <div className="text-gray-500 text-sm max-w-xs">
                  No data yet for this simulation. Run a cycle to initialise it.
                </div>
              </div>

              {isCycleRunning ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="flex items-center gap-2 text-blue-400 text-sm">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                    </svg>
                    {cycleStep}
                  </div>
                  <div className="flex gap-2">
                    {CYCLE_STEPS.map(s => (
                      <div key={s.agent} className={`text-xs px-2 py-1 rounded border ${
                        cycleStep === s.label
                          ? 'border-blue-500 text-blue-400 bg-blue-500/10'
                          : cycleStep === 'Finalizing…'
                            ? 'border-green-700 text-green-500'
                            : 'border-gray-800 text-gray-600'
                      }`}>{s.label}</div>
                    ))}
                  </div>
                </div>
              ) : (
                <button
                  onClick={runFullCycle}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  Run Full Cycle
                </button>
              )}
              {cycleError && <div className="text-red-400 text-xs">{cycleError}</div>}
            </div>
          ) : (
            <>
              {/* Portfolio header */}
              <PortfolioHeader portfolio={portfolio.data!} />

              {/* Detail tabs */}
              <div className="border-b border-gray-800 px-4 flex items-center gap-1 flex-shrink-0">
                {DETAIL_TABS.map(t => (
                  <button
                    key={t.id}
                    onClick={() => setDetailTab(t.id)}
                    className={`text-sm px-4 py-2.5 transition-colors border-b-2 ${
                      detailTab === t.id
                        ? 'border-blue-500 text-gray-100'
                        : 'border-transparent text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}

                {/* Run cycle button — inline when data exists */}
                {!isCycleRunning ? (
                  <button
                    onClick={runFullCycle}
                    className="ml-auto mr-2 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded transition-colors border border-gray-700"
                  >
                    ↻ Run Cycle
                  </button>
                ) : (
                  <div className="ml-auto mr-2 flex items-center gap-1.5 text-xs text-blue-400">
                    <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                    </svg>
                    {cycleStep}
                  </div>
                )}
              </div>

              {/* Tab content + right sidebar */}
              <div className="flex flex-1 min-h-0">
                <div className="flex-1 min-w-0 overflow-auto p-5">
                  {detailTab === 'portfolio' && (
                    <HoldingsGrid holdings={portfolio.data!.holdings} />
                  )}
                  {detailTab === 'pnl' && (
                    <div className="max-w-3xl">
                      <PnLChart history={history.data ?? []} />
                    </div>
                  )}
                  {detailTab === 'trades' && (
                    <TradeLog trades={trades.data ?? []} />
                  )}
                  {detailTab === 'report' && (
                    reports.data && reports.data.length > 0
                      ? <DailyReportPanel report={reports.data[0]} />
                      : <div className="text-gray-600 text-sm py-12 text-center">No daily reports yet.</div>
                  )}
                </div>

                {/* Right sidebar */}
                <div className="w-52 flex-shrink-0 border-l border-gray-800 p-4 flex flex-col gap-4 overflow-auto">
                  <div className="border border-gray-800 rounded-lg p-3">
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Allocation</div>
                    <AllocationChart portfolio={portfolio.data!} />
                  </div>

                  {agentStatus.data && (
                    <AgentStatusSidebar status={agentStatus.data} onTrigger={handleTrigger} />
                  )}

                  <div className="border border-gray-800 rounded-lg p-3 text-xs text-gray-600 space-y-1">
                    <div className="font-semibold text-gray-500">Info</div>
                    <div>Budget: <span className="text-gray-400">${portfolio.data!.budget_total.toLocaleString()}</span></div>
                    <div>Strategy: <span className="text-gray-400 capitalize">{portfolio.data!.strategy}</span></div>
                    <div className="pt-1 text-gray-700">{new Date(portfolio.data!.last_updated).toLocaleTimeString()}</div>
                  </div>

                  {settings.data && (
                    <div className="border border-gray-800 rounded-lg overflow-hidden">
                      <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-800">
                        Settings
                      </div>
                      <div className="p-3">
                        <SettingsPanel
                          settings={settings.data}
                          onSave={handleSaveSettings}
                          isSaving={updateSettings.isPending}
                          savedAt={savedAt}
                          compact
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
