import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function usePortfolio() {
  return useQuery({
    queryKey: ['portfolio'],
    queryFn: api.portfolio,
    refetchInterval: 60_000,
    retry: 2,
  })
}

export function usePortfolioHistory() {
  return useQuery({
    queryKey: ['portfolio', 'history'],
    queryFn: api.portfolioHistory,
    staleTime: 300_000,
  })
}
