import type { AgentStatusMap, Holding, PortfolioState } from '../api/types'

export const mockHolding = (overrides: Partial<Holding> = {}): Holding => ({
  ticker: 'NVDA',
  shares: 2.5,
  avg_cost_basis: 850,
  current_price: 920,
  market_value: 2300,
  unrealized_pnl: 175,
  unrealized_pnl_pct: 8.24,
  allocation_pct: 23,
  open_date: '2026-04-15',
  analyst_rating: 'BUY',
  confidence: 'HIGH',
  ...overrides,
})

export const mockPortfolio = (overrides: Partial<PortfolioState> = {}): PortfolioState => ({
  account_type: 'brokerage',
  target_market: 'AI',
  budget_total: 10000,
  cash_available: 3500,
  last_updated: '2026-05-03T16:15:00Z',
  holdings: [
    mockHolding({ ticker: 'NVDA', allocation_pct: 23 }),
    mockHolding({ ticker: 'MSFT', allocation_pct: 20, current_price: 420, avg_cost_basis: 400, unrealized_pnl: 50, unrealized_pnl_pct: 5.0, market_value: 2100 }),
  ],
  total_market_value: 6500,
  total_unrealized_pnl: 500,
  total_unrealized_pnl_pct: 8.33,
  strategy: 'growth',
  max_positions: 5,
  ...overrides,
})

export const mockAgentStatus: AgentStatusMap = {
  'market-researcher': true,
  analyst: true,
  ceo: false,
  'qa-engineer': true,
}
