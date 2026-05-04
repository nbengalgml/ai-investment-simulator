import { render, screen } from '@testing-library/react'
import { HoldingsGrid } from '../HoldingsGrid'
import { mockHolding } from '../../test/mockData'

describe('HoldingsGrid', () => {
  it('renders one card per holding', () => {
    const holdings = [
      mockHolding({ ticker: 'NVDA' }),
      mockHolding({ ticker: 'MSFT' }),
      mockHolding({ ticker: 'GOOGL' }),
    ]
    render(<HoldingsGrid holdings={holdings} />)
    expect(screen.getByText('NVDA')).toBeInTheDocument()
    expect(screen.getByText('MSFT')).toBeInTheDocument()
    expect(screen.getByText('GOOGL')).toBeInTheDocument()
  })

  it('shows empty state when no holdings', () => {
    render(<HoldingsGrid holdings={[]} />)
    expect(screen.getByText(/No open positions/i)).toBeInTheDocument()
  })

  it('renders 5 cards for 5 holdings', () => {
    const tickers = ['NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN']
    const holdings = tickers.map(t => mockHolding({ ticker: t }))
    render(<HoldingsGrid holdings={holdings} />)
    tickers.forEach(t => expect(screen.getByText(t)).toBeInTheDocument())
  })

  it('shows HIGH confidence badge', () => {
    render(<HoldingsGrid holdings={[mockHolding({ confidence: 'HIGH' })]} />)
    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })

  it('shows MEDIUM confidence badge', () => {
    render(<HoldingsGrid holdings={[mockHolding({ confidence: 'MEDIUM' })]} />)
    expect(screen.getByText('MEDIUM')).toBeInTheDocument()
  })

  it('shows LOW confidence badge', () => {
    render(<HoldingsGrid holdings={[mockHolding({ confidence: 'LOW' })]} />)
    expect(screen.getByText('LOW')).toBeInTheDocument()
  })

  it('shows unrealized P&L as positive', () => {
    render(<HoldingsGrid holdings={[mockHolding({ unrealized_pnl: 175, unrealized_pnl_pct: 8.24 })]} />)
    expect(screen.getByText(/\+\$175\.00/)).toBeInTheDocument()
  })

  it('shows unrealized P&L as negative', () => {
    render(<HoldingsGrid holdings={[mockHolding({ unrealized_pnl: -150, unrealized_pnl_pct: -17.6 })]} />)
    expect(screen.getByText(/-\$150\.00/)).toBeInTheDocument()
  })

  it('shows allocation percentage', () => {
    render(<HoldingsGrid holdings={[mockHolding({ allocation_pct: 23.0 })]} />)
    expect(screen.getByText(/23\.0% alloc/)).toBeInTheDocument()
  })

  it('shows analyst rating', () => {
    render(<HoldingsGrid holdings={[mockHolding({ analyst_rating: 'BUY' })]} />)
    expect(screen.getByText('BUY')).toBeInTheDocument()
  })
})
