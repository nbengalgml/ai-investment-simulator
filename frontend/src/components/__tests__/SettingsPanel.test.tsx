import { render, screen, fireEvent } from '@testing-library/react'
import { SettingsPanel } from '../SettingsPanel'
import type { Settings } from '../../api/types'

const mockSettings: Settings = {
  budget_total: 10000,
  account_type: 'brokerage',
  target_market: 'AI',
}

describe('SettingsPanel', () => {
  it('renders budget input with current value', () => {
    render(<SettingsPanel settings={mockSettings} onSave={vi.fn()} />)
    const input = screen.getByLabelText(/Simulation budget/i) as HTMLInputElement
    expect(input.value).toBe('10000')
  })

  it('renders account type radios', () => {
    render(<SettingsPanel settings={mockSettings} onSave={vi.fn()} />)
    expect(screen.getByText(/Brokerage/)).toBeInTheDocument()
    expect(screen.getByText(/Traditional IRA/)).toBeInTheDocument()
  })

  it('brokerage radio is checked by default', () => {
    render(<SettingsPanel settings={mockSettings} onSave={vi.fn()} />)
    const radio = screen.getByDisplayValue('brokerage') as HTMLInputElement
    expect(radio.checked).toBe(true)
  })

  it('renders target market selector', () => {
    render(<SettingsPanel settings={mockSettings} onSave={vi.fn()} />)
    expect(screen.getByLabelText(/Target market/i)).toBeInTheDocument()
  })

  it('save button disabled when nothing changed', () => {
    render(<SettingsPanel settings={mockSettings} onSave={vi.fn()} />)
    const btn = screen.getByText('Save Settings') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('save button enabled after changing budget', () => {
    render(<SettingsPanel settings={mockSettings} onSave={vi.fn()} />)
    const input = screen.getByLabelText(/Simulation budget/i)
    fireEvent.change(input, { target: { value: '25000' } })
    const btn = screen.getByText('Save Settings') as HTMLButtonElement
    expect(btn.disabled).toBe(false)
  })

  it('calls onSave with updated values on submit', () => {
    const onSave = vi.fn()
    render(<SettingsPanel settings={mockSettings} onSave={onSave} />)
    const input = screen.getByLabelText(/Simulation budget/i)
    fireEvent.change(input, { target: { value: '20000' } })
    fireEvent.click(screen.getByText('Save Settings'))
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ budget_total: 20000 })
    )
  })

  it('shows IRA contribution note when IRA selected', () => {
    render(<SettingsPanel settings={{ ...mockSettings, account_type: 'traditional_ira' }} onSave={vi.fn()} />)
    expect(screen.getByText(/contribution limit/i)).toBeInTheDocument()
  })

  it('shows saving state when isSaving=true', () => {
    render(<SettingsPanel settings={mockSettings} onSave={vi.fn()} isSaving={true} />)
    expect(screen.getByText('Saving…')).toBeInTheDocument()
  })

  it('shows confirmation after save when savedAt provided', () => {
    render(
      <SettingsPanel
        settings={mockSettings}
        onSave={vi.fn()}
        savedAt={new Date()}
      />
    )
    expect(screen.getByText(/Saved at/i)).toBeInTheDocument()
  })
})
