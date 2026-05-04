import { render, screen } from '@testing-library/react'
import { AllocationChart } from '../AllocationChart'
import { mockPortfolio } from '../../test/mockData'

// Recharts uses ResizeObserver — provide a stub
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

describe('AllocationChart', () => {
  it('renders without crashing', () => {
    const { container } = render(<AllocationChart portfolio={mockPortfolio()} />)
    expect(container.firstChild).not.toBeNull()
  })

  it('shows ticker labels in legend', () => {
    render(<AllocationChart portfolio={mockPortfolio()} />)
    expect(screen.getByText(/NVDA/)).toBeInTheDocument()
    expect(screen.getByText(/MSFT/)).toBeInTheDocument()
  })

  it('shows Cash slice when portfolio is not fully invested', () => {
    // mock has 23% + 20% = 43% invested → 57% cash
    render(<AllocationChart portfolio={mockPortfolio()} />)
    expect(screen.getByText(/Cash/)).toBeInTheDocument()
  })

  it('does not show Cash slice when fully invested', () => {
    const portfolio = mockPortfolio({
      holdings: [
        { ticker: 'NVDA', shares: 1, avg_cost_basis: 100, current_price: 100,
          market_value: 5000, unrealized_pnl: 0, unrealized_pnl_pct: 0,
          allocation_pct: 100, open_date: '2026-01-01', analyst_rating: 'BUY', confidence: 'HIGH' },
      ],
    })
    render(<AllocationChart portfolio={portfolio} />)
    expect(screen.queryByText(/Cash/)).toBeNull()
  })

  it('shows empty state when no holdings', () => {
    render(<AllocationChart portfolio={mockPortfolio({ holdings: [] })} />)
    expect(screen.getByText(/No data/i)).toBeInTheDocument()
  })
})
