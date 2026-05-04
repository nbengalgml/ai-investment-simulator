import { useState, useEffect } from 'react'
import type { Settings } from '../api/types'

const TARGET_MARKETS = ['AI', 'Cloud', 'Networking', 'Alternative Energy', 'Gas', 'Finance']

interface Props {
  settings: Settings
  onSave: (updated: Partial<Settings>) => void
  isSaving?: boolean
  savedAt?: Date | null
}

export function SettingsPanel({ settings, onSave, isSaving, savedAt }: Props) {
  const [budget, setBudget] = useState(String(settings.budget_total))
  const [accountType, setAccountType] = useState(settings.account_type)
  const [market, setMarket] = useState(settings.target_market)

  useEffect(() => {
    setBudget(String(settings.budget_total))
    setAccountType(settings.account_type)
    setMarket(settings.target_market)
  }, [settings])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const parsed = parseFloat(budget)
    if (isNaN(parsed) || parsed <= 0) return
    onSave({ budget_total: parsed, account_type: accountType, target_market: market })
  }

  const isDirty =
    parseFloat(budget) !== settings.budget_total ||
    accountType !== settings.account_type ||
    market !== settings.target_market

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6 max-w-md">
      <div className="text-xs text-gray-600">
        SIMULATION ONLY — settings affect future agent cycles only.
        No real money or trades are involved.
      </div>

      {/* Budget */}
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Simulation Budget (USD)
        </label>
        <input
          type="number"
          value={budget}
          onChange={e => setBudget(e.target.value)}
          min={100}
          step={100}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 text-sm focus:outline-none focus:border-blue-500 tabular-nums"
          aria-label="Simulation budget"
        />
      </div>

      {/* Account type */}
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Account Type
        </label>
        <div className="flex gap-3">
          {(['brokerage', 'traditional_ira'] as const).map(at => (
            <label key={at} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="account_type"
                value={at}
                checked={accountType === at}
                onChange={() => setAccountType(at)}
                className="accent-blue-500"
              />
              <span className="text-sm text-gray-300">
                {at === 'brokerage' ? 'Brokerage (post-tax)' : 'Traditional IRA (pre-tax)'}
              </span>
            </label>
          ))}
        </div>
        {accountType === 'traditional_ira' && (
          <p className="text-xs text-gray-600">
            2026 contribution limit: $7,000 ($8,000 if 50+) — informational only.
          </p>
        )}
      </div>

      {/* Target market */}
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          Target Market
        </label>
        <select
          value={market}
          onChange={e => setMarket(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-gray-100 text-sm focus:outline-none focus:border-blue-500"
          aria-label="Target market"
        >
          {TARGET_MARKETS.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      {/* Save */}
      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={!isDirty || isSaving}
          className="text-sm px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {isSaving ? 'Saving…' : 'Save Settings'}
        </button>
        {savedAt && !isDirty && (
          <span className="text-xs text-green-500">
            Saved at {savedAt.toLocaleTimeString()}
          </span>
        )}
      </div>
    </form>
  )
}
