import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export function useSimulations() {
  return useQuery({
    queryKey: ['simulations'],
    queryFn: api.simulations,
    refetchInterval: 60_000,
    retry: 2,
  })
}

export function useSimPortfolio(simId: string) {
  return useQuery({
    queryKey: ['simulations', simId, 'portfolio'],
    queryFn: () => api.simPortfolio(simId),
    refetchInterval: 60_000,
    retry: 1,
    enabled: !!simId,
  })
}

export function useSimPortfolioHistory(simId: string) {
  return useQuery({
    queryKey: ['simulations', simId, 'history'],
    queryFn: () => api.simPortfolioHistory(simId),
    refetchInterval: 60_000,
    enabled: !!simId,
  })
}

export function useSimTrades(simId: string) {
  return useQuery({
    queryKey: ['simulations', simId, 'trades'],
    queryFn: () => api.simTrades(simId),
    refetchInterval: 60_000,
    enabled: !!simId,
  })
}

export function useSimReports(simId: string) {
  return useQuery({
    queryKey: ['simulations', simId, 'reports'],
    queryFn: () => api.simReports(simId),
    refetchInterval: 60_000,
    enabled: !!simId,
  })
}
