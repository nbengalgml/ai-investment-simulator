import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useTrades() {
  return useQuery({
    queryKey: ['trades'],
    queryFn: api.trades,
    staleTime: 60_000,
  })
}
