import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from './api/client'
import { Dashboard } from './pages/Dashboard'

const FONT_SIZES = [11, 12, 13, 14, 15, 16, 18, 20]
const DEFAULT_FONT_SIZE = 14
const LS_KEY = 'ui-font-size'

function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 30_000,
  })
}

export default function App() {
  const { data, isError } = useHealth()
  const [fontSize, setFontSize] = useState<number>(() => {
    const saved = localStorage.getItem(LS_KEY)
    return saved ? Number(saved) : DEFAULT_FONT_SIZE
  })

  useEffect(() => {
    document.documentElement.style.fontSize = `${fontSize}px`
    localStorage.setItem(LS_KEY, String(fontSize))
  }, [fontSize])

  const canDecrease = fontSize > FONT_SIZES[0]
  const canIncrease = fontSize < FONT_SIZES[FONT_SIZES.length - 1]

  const decrease = () => {
    const idx = FONT_SIZES.indexOf(fontSize)
    if (idx > 0) setFontSize(FONT_SIZES[idx - 1])
  }
  const increase = () => {
    const idx = FONT_SIZES.indexOf(fontSize)
    if (idx < FONT_SIZES.length - 1) setFontSize(FONT_SIZES[idx + 1])
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans flex flex-col">
      <header className="border-b border-gray-800 px-6 py-3 flex items-center gap-3 flex-shrink-0">
        <h1 className="text-base font-semibold tracking-wide">AI Investment Simulator</h1>
        <span className="text-xs text-yellow-400 border border-yellow-400 px-1.5 py-0.5 rounded font-mono">
          SIMULATION ONLY
        </span>
        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-1">
            <button
              onClick={decrease}
              disabled={!canDecrease}
              title="Decrease font size"
              className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-gray-200 disabled:opacity-30 rounded hover:bg-gray-800 transition-colors text-sm leading-none select-none"
            >
              A-
            </button>
            <span className="text-xs text-gray-700 tabular-nums w-7 text-center font-mono">{fontSize}px</span>
            <button
              onClick={increase}
              disabled={!canIncrease}
              title="Increase font size"
              className="w-6 h-6 flex items-center justify-center text-gray-500 hover:text-gray-200 disabled:opacity-30 rounded hover:bg-gray-800 transition-colors text-sm leading-none select-none"
            >
              A+
            </button>
          </div>
          <span className="text-xs text-gray-500">
            API:{' '}
            <span className={isError ? 'text-red-400' : 'text-green-400'}>
              {isError ? 'unreachable' : (data?.status ?? '…')}
            </span>
          </span>
        </div>
      </header>
      <main className="flex-1 min-h-0 overflow-auto">
        <Dashboard />
      </main>
    </div>
  )
}
