import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useDailyReports() {
  return useQuery({
    queryKey: ['reports', 'daily'],
    queryFn: api.dailyReports,
    staleTime: 300_000,
  })
}

export function useDailyReport(date: string | null) {
  return useQuery({
    queryKey: ['reports', 'daily', date],
    queryFn: () => api.dailyReport(date!),
    enabled: date !== null,
    staleTime: 300_000,
  })
}
