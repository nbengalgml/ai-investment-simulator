import { render, screen, fireEvent } from '@testing-library/react'
import { TradeLog } from '../TradeLog'
import type { TradeLogEntry } from '../../api/types'

function makeTrade(overrides: Partial<TradeLogEntry> = {}): TradeLogEntry {
  return {
    trade_id: 'abc-123',
    timestamp: '2026-05-03T09:35:00Z',
    action: 'BUY',
    ticker: 'NVDA',
    shares: 2.5,
    price: 850.0,
    total_value: 2125.0,
    rationale: 'Strong AI momentum signal.',
    data_sources: ['yfinance', 'newsapi'],
    approved_by: 'CEO',
    account_type: 'brokerage',
    simulated_tax_impact: { holding_period_days: 0, gain_loss: 0, tax_treatment: 'n/a' },
    ...overrides,
  }
}

describe('TradeLog', () => {
  it('shows empty state when no trades', () => {
    render(<TradeLog trades={[]} />)
    expect(screen.getByText(/No trades yet/i)).toBeInTheDocument()
  })

  it('renders a row per trade', () => {
    const trades = [
      makeTrade({ ticker: 'NVDA' }),
      makeTrade({ ticker: 'MSFT', trade_id: 'xyz' }),
    ]
    render(<TradeLog trades={trades} />)
    expect(screen.getByText('NVDA')).toBeInTheDocument()
    expect(screen.getByText('MSFT')).toBeInTheDocument()
  })

  it('shows BUY action in green', () => {
    const { container } = render(<TradeLog trades={[makeTrade({ action: 'BUY' })]} />)
    expect(container.querySelector('.text-green-400')).not.toBeNull()
  })

  it('shows SELL action in red', () => {
    const { container } = render(<TradeLog trades={[makeTrade({ action: 'SELL' })]} />)
    expect(container.querySelector('.text-red-400')).not.toBeNull()
  })

  it('shows filter buttons', () => {
    // Render with no trades so there are no action-column cells that duplicate the labels
    render(<TradeLog trades={[]} />)
    // TradeLog shows empty state when trades=[], so render with a SELL to avoid BUY duplication
    const { unmount } = render(<TradeLog trades={[makeTrade({ action: 'SELL', trade_id: 'sell-1' })]} />)
    expect(screen.getAllByText('ALL').length).toBeGreaterThan(0)
    expect(screen.getAllByText('BUY').length).toBeGreaterThan(0)
    expect(screen.getAllByText('SELL').length).toBeGreaterThan(0)
    expect(screen.getAllByText('HOLD').length).toBeGreaterThan(0)
    unmount()
  })

  it('filters to only BUY trades', () => {
    const trades = [
      makeTrade({ ticker: 'NVDA', action: 'BUY' }),
      makeTrade({ ticker: 'MSFT', action: 'SELL', trade_id: 'xyz' }),
    ]
    render(<TradeLog trades={trades} />)
    // There are multiple BUY buttons (filter + cell), so find the filter button
    const buyButtons = screen.getAllByText('BUY')
    fireEvent.click(buyButtons[0])
    expect(screen.getByText('NVDA')).toBeInTheDocument()
    expect(screen.queryByText('MSFT')).toBeNull()
  })

  it('shows rationale text', () => {
    render(<TradeLog trades={[makeTrade({ rationale: 'Strong AI momentum signal.' })]} />)
    expect(screen.getByText('Strong AI momentum signal.')).toBeInTheDocument()
  })

  it('shows entry count', () => {
    const trades = [makeTrade(), makeTrade({ trade_id: 'b' }), makeTrade({ trade_id: 'c' })]
    render(<TradeLog trades={trades} />)
    expect(screen.getByText('3 entries')).toBeInTheDocument()
  })
})
