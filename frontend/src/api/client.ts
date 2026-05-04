import axios from 'axios'
import type { AgentStatusMap, DailyReport, PortfolioState, Settings, SimulationSummary, TradeLogEntry } from './types'

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
  triggerAgent: (agent: string, sector?: string, account_type?: string) =>
    http.post(`/agents/${agent}/trigger`, {
      sector: sector ?? 'AI',
      account_type: account_type ?? 'brokerage',
    }).then(r => r.data),
  settings: () => http.get<Settings>('/settings').then(r => r.data),
  updateSettings: (body: Partial<Settings>) => http.post<Settings>('/settings', body).then(r => r.data),

  // Market data
  priceHistory: (tickers: string[], range: string) =>
    http.get<{ range: string; series: Record<string, { t: string; p: number }[]> }>(
      `/market/price-history?tickers=${tickers.join(',')}&range=${range}`
    ).then(r => r.data),

  // Multi-simulation endpoints
  simulations: () => http.get<SimulationSummary[]>('/simulations').then(r => r.data),
  simPortfolio: (simId: string) =>
    http.get<PortfolioState>(`/simulations/${simId}/portfolio`).then(r => r.data),
  simPortfolioHistory: (simId: string) =>
    http.get<PortfolioState[]>(`/simulations/${simId}/portfolio/history`).then(r => r.data),
  simTrades: (simId: string) =>
    http.get<TradeLogEntry[]>(`/simulations/${simId}/trades`).then(r => r.data),
  simReports: (simId: string) =>
    http.get<DailyReport[]>(`/simulations/${simId}/reports/daily`).then(r => r.data),
}
