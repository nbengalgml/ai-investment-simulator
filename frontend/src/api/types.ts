export type AccountType = 'brokerage' | 'traditional_ira'
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW'
export type TradeAction = 'BUY' | 'SELL' | 'HOLD'

export interface Holding {
  ticker: string
  shares: number
  avg_cost_basis: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  allocation_pct: number
  open_date: string
  analyst_rating: string
  confidence: Confidence
}

export interface PortfolioState {
  account_type: AccountType
  target_market: string
  budget_total: number
  cash_available: number
  last_updated: string
  holdings: Holding[]
  total_market_value: number
  total_unrealized_pnl: number
  total_unrealized_pnl_pct: number
  strategy: string
  max_positions: number
}

export interface TaxImpact {
  holding_period_days: number
  gain_loss: number
  tax_treatment: string
}

export interface TradeLogEntry {
  trade_id: string
  timestamp: string
  action: TradeAction
  ticker: string
  shares: number
  price: number
  total_value: number
  rationale: string
  data_sources: string[]
  approved_by: string
  account_type: AccountType
  simulated_tax_impact: TaxImpact
}

export interface PortfolioPerformance {
  day_pnl: number
  day_pnl_pct: number
  total_unrealized_pnl: number
}

export interface DailyReport {
  report_date: string
  generated_at: string
  executive_summary: string
  market_conditions: string
  portfolio_performance: PortfolioPerformance
  actions_taken: Record<string, unknown>[]
  top_signals: Record<string, unknown>[]
  recommendations_pending: Record<string, unknown>[]
  next_day_watchlist: string[]
}

export type AgentStatusMap = Record<string, boolean>

export interface SimulationSummary {
  sim_id: string
  sector: string
  account_type: AccountType
  has_data: boolean
  total_market_value?: number
  budget_total?: number
  total_unrealized_pnl?: number
  total_unrealized_pnl_pct?: number
  cash_available?: number
  holdings_count?: number
  last_updated?: string
}

export interface Settings {
  budget_total: number
  account_type: AccountType
  target_market: string
}

export interface PnLPoint {
  date: string
  value: number
  pnl: number
}
