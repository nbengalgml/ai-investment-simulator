import axios from 'axios'
import type { AgentStatusMap, DailyReport, PortfolioState, Settings, TradeLogEntry } from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const http = axios.create({ baseURL: BASE, timeout: 10_000 })

export const api = {
  health: () => http.get<{ status: string }>('/health').then(r => r.data),
  portfolio: () => http.get<PortfolioState>('/portfolio').then(r => r.data),
  portfolioHistory: () => http.get<PortfolioState[]>('/portfolio/history').then(r => r.data),
  trades: () => http.get<TradeLogEntry[]>('/trades').then(r => r.data),
  dailyReports: () => http.get<DailyReport[]>('/reports/daily').then(r => r.data),
  dailyReport: (date: string) => http.get<DailyReport>(`/reports/daily/${date}`).then(r => r.data),
  agentStatus: () => http.get<AgentStatusMap>('/agents/status').then(r => r.data),
  triggerAgent: (agent: string, sector?: string) =>
    http.post(`/agents/${agent}/trigger`, { sector: sector ?? 'AI' }).then(r => r.data),
  settings: () => http.get<Settings>('/settings').then(r => r.data),
  updateSettings: (body: Partial<Settings>) => http.post<Settings>('/settings', body).then(r => r.data),
}
