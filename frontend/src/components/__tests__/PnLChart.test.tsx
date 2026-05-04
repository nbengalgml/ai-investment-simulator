import { render, screen, fireEvent } from '@testing-library/react'
import { PnLChart } from '../PnLChart'
import { mockPortfolio } from '../../test/mockData'
import type { PortfolioState } from '../../api/types'

global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

function makeHistory(n: number): PortfolioState[] {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date('2026-05-01')
    d.setDate(d.getDate() + i)
    return mockPortfolio({
      last_updated: d.toISOString(),
      total_market_value: 6500 + i * 50,
      cash_available: 3500,
    })
  })
}

describe('PnLChart', () => {
  it('renders without crashing with history data', () => {
    const { container } = render(<PnLChart history={makeHistory(10)} />)
    expect(container.firstChild).not.toBeNull()
  })

  it('shows empty state when history is empty', () => {
    render(<PnLChart history={[]} />)
    expect(screen.getByText(/No history data/i)).toBeInTheDocument()
  })

  it('renders range toggle buttons', () => {
    render(<PnLChart history={makeHistory(10)} />)
    expect(screen.getByText('7D')).toBeInTheDocument()
    expect(screen.getByText('30D')).toBeInTheDocument()
    expect(screen.getByText('90D')).toBeInTheDocument()
  })

  it('7D button becomes active when clicked', () => {
    render(<PnLChart history={makeHistory(10)} />)
    const btn7d = screen.getByText('7D')
    fireEvent.click(btn7d)
    expect(btn7d.className).toContain('bg-blue-600')
  })

  it('shows chart title', () => {
    render(<PnLChart history={makeHistory(5)} />)
    expect(screen.getByText(/Portfolio Value/i)).toBeInTheDocument()
  })
})
