import { render, screen } from '@testing-library/react'
import { PortfolioHeader } from '../PortfolioHeader'
import { mockPortfolio } from '../../test/mockData'

describe('PortfolioHeader', () => {
  it('renders total portfolio value', () => {
    render(<PortfolioHeader portfolio={mockPortfolio()} />)
    // total = total_market_value + cash_available = 6500 + 3500 = 10000
    expect(screen.getByText(/\$10,000\.00/)).toBeInTheDocument()
  })

  it('renders unrealized P&L with sign', () => {
    render(<PortfolioHeader portfolio={mockPortfolio()} />)
    expect(screen.getByText(/\+\$500\.00/)).toBeInTheDocument()
  })

  it('colors P&L green when positive', () => {
    const { container } = render(<PortfolioHeader portfolio={mockPortfolio({ total_unrealized_pnl: 200 })} />)
    const pnlEl = container.querySelector('.text-green-400')
    expect(pnlEl).not.toBeNull()
  })

  it('colors P&L red when negative', () => {
    const { container } = render(
      <PortfolioHeader portfolio={mockPortfolio({ total_unrealized_pnl: -300, total_unrealized_pnl_pct: -3 })} />
    )
    const pnlEl = container.querySelector('.text-red-400')
    expect(pnlEl).not.toBeNull()
  })

  it('shows account type badge — brokerage', () => {
    render(<PortfolioHeader portfolio={mockPortfolio({ account_type: 'brokerage' })} />)
    expect(screen.getByText(/Brokerage/i)).toBeInTheDocument()
  })

  it('shows account type badge — IRA', () => {
    render(<PortfolioHeader portfolio={mockPortfolio({ account_type: 'traditional_ira' })} />)
    expect(screen.getByText(/IRA/i)).toBeInTheDocument()
  })

  it('shows target market badge', () => {
    render(<PortfolioHeader portfolio={mockPortfolio({ target_market: 'AI' })} />)
    expect(screen.getByText('AI')).toBeInTheDocument()
  })

  it('shows positions count', () => {
    const p = mockPortfolio()
    render(<PortfolioHeader portfolio={p} />)
    expect(screen.getByText(`${p.holdings.length}/${p.max_positions} positions`)).toBeInTheDocument()
  })

  it('shows cash available', () => {
    render(<PortfolioHeader portfolio={mockPortfolio({ cash_available: 3500 })} />)
    expect(screen.getByText(/\$3,500\.00/)).toBeInTheDocument()
  })
})
