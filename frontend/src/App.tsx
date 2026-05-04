import { useQuery } from '@tanstack/react-query'
import { api } from './api/client'
import { Dashboard } from './pages/Dashboard'

function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 30_000,
  })
}

export default function App() {
  const { data, isError } = useHealth()

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-mono flex flex-col">
      <header className="border-b border-gray-800 px-6 py-3 flex items-center gap-3 flex-shrink-0">
        <h1 className="text-base font-semibold tracking-wide">AI Investment Simulator</h1>
        <span className="text-xs text-yellow-400 border border-yellow-400 px-1.5 py-0.5 rounded">
          SIMULATION ONLY
        </span>
        <span className="ml-auto text-xs text-gray-500">
          API:{' '}
          <span className={isError ? 'text-red-400' : 'text-green-400'}>
            {isError ? 'unreachable' : (data?.status ?? '…')}
          </span>
        </span>
      </header>
      <main className="flex-1 min-h-0 overflow-auto">
        <Dashboard />
      </main>
    </div>
  )
}
