import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Settings } from '../api/types'

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: api.settings,
    staleTime: 300_000,
  })
}

export function useUpdateSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<Settings>) => api.updateSettings(body),
    onSuccess: (updated) => {
      qc.setQueryData(['settings'], updated)
    },
  })
}
