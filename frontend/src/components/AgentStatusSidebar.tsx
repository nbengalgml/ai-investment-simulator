import type { AgentStatusMap } from '../api/types'

const AGENT_LABELS: Record<string, string> = {
  'market-researcher': 'Market Researcher',
  analyst: 'Analyst',
  ceo: 'CEO',
  'qa-engineer': 'QA Engineer',
}

interface Props {
  status: AgentStatusMap
  onTrigger?: (agent: string) => void
}

export function AgentStatusSidebar({ status, onTrigger }: Props) {
  const agents = Object.keys(AGENT_LABELS)

  return (
    <div className="border border-gray-800 rounded-lg p-4 flex flex-col gap-3">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
        Agent Status
      </div>
      {agents.map(agent => {
        const available = status[agent]
        return (
          <div key={agent} className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={`w-2 h-2 rounded-full flex-shrink-0 ${available ? 'bg-green-500' : 'bg-red-500'}`}
                aria-label={available ? 'online' : 'offline'}
              />
              <span className="text-sm text-gray-300 truncate">
                {AGENT_LABELS[agent] ?? agent}
              </span>
            </div>
            {onTrigger && (
              <button
                onClick={() => onTrigger(agent)}
                className="text-xs text-blue-400 hover:text-blue-300 flex-shrink-0 transition-colors"
                aria-label={`Trigger ${agent}`}
              >
                ▶
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
