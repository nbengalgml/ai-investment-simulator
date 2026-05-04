import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export function useAgentStatus() {
  return useQuery({
    queryKey: ['agents', 'status'],
    queryFn: api.agentStatus,
    refetchInterval: 30_000,
    retry: 2,
  })
}

export function useTriggerAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ agent, sector, account_type }: { agent: string; sector?: string; account_type?: string }) =>
      api.triggerAgent(agent, sector, account_type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', 'status'] })
    },
  })
}
