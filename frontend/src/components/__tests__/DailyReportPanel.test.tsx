import { render, screen } from '@testing-library/react'
import { DailyReportPanel } from '../DailyReportPanel'
import type { DailyReport } from '../../api/types'

const mockReport: DailyReport = {
  report_date: '2026-05-03',
  generated_at: '2026-05-03T16:20:00Z',
  executive_summary: 'AI sector delivered strong gains today.',
  market_conditions: 'Bullish momentum across AI stocks.',
  portfolio_performance: { day_pnl: 285.0, day_pnl_pct: 2.14, total_unrealized_pnl: 500.0 },
  actions_taken: [],
  top_signals: [
    { ticker: 'NVDA', composite_score: 88, momentum_20d_pct: 12.5 },
    { ticker: 'MSFT', composite_score: 75, momentum_20d_pct: -1.2 },
  ],
  recommendations_pending: [
    { ticker: 'AMD', action: 'BUY', composite_score: 70 },
  ],
  next_day_watchlist: ['AMD', 'PLTR', 'SOUN'],
}

describe('DailyReportPanel', () => {
  it('renders report date', () => {
    render(<DailyReportPanel report={mockReport} />)
    expect(screen.getByText(/2026-05-03/)).toBeInTheDocument()
  })

  it('shows executive summary', () => {
    render(<DailyReportPanel report={mockReport} />)
    expect(screen.getByText('AI sector delivered strong gains today.')).toBeInTheDocument()
  })

  it('shows market conditions', () => {
    render(<DailyReportPanel report={mockReport} />)
    expect(screen.getByText('Bullish momentum across AI stocks.')).toBeInTheDocument()
  })

  it('shows day P&L as positive green', () => {
    const { container } = render(<DailyReportPanel report={mockReport} />)
    expect(container.querySelector('.text-green-400')).not.toBeNull()
    expect(screen.getByText(/\+\$285\.00/)).toBeInTheDocument()
  })

  it('shows day P&L as negative red', () => {
    const negReport = {
      ...mockReport,
      portfolio_performance: { day_pnl: -120, day_pnl_pct: -1.1, total_unrealized_pnl: -120 },
    }
    const { container } = render(<DailyReportPanel report={negReport} />)
    expect(container.querySelector('.text-red-400')).not.toBeNull()
  })

  it('renders top signals table', () => {
    render(<DailyReportPanel report={mockReport} />)
    expect(screen.getByText('Top Signals')).toBeInTheDocument()
    expect(screen.getByText('NVDA')).toBeInTheDocument()
    expect(screen.getByText('MSFT')).toBeInTheDocument()
  })

  it('renders next day watchlist', () => {
    render(<DailyReportPanel report={mockReport} />)
    expect(screen.getByText('AMD')).toBeInTheDocument()
    expect(screen.getByText('PLTR')).toBeInTheDocument()
    expect(screen.getByText('SOUN')).toBeInTheDocument()
  })

  it('renders pending recommendations', () => {
    render(<DailyReportPanel report={mockReport} />)
    expect(screen.getByText(/Pending Review/)).toBeInTheDocument()
  })

  it('does not render top signals section when empty', () => {
    const r = { ...mockReport, top_signals: [] }
    render(<DailyReportPanel report={r} />)
    expect(screen.queryByText('Top Signals')).toBeNull()
  })

  it('does not render watchlist section when empty', () => {
    const r = { ...mockReport, next_day_watchlist: [] }
    render(<DailyReportPanel report={r} />)
    expect(screen.queryByText("Tomorrow's Watchlist")).toBeNull()
  })
})
