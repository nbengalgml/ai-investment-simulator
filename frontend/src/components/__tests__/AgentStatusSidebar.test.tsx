import { render, screen, fireEvent } from '@testing-library/react'
import { AgentStatusSidebar } from '../AgentStatusSidebar'
import { mockAgentStatus } from '../../test/mockData'

describe('AgentStatusSidebar', () => {
  it('renders all four agents', () => {
    render(<AgentStatusSidebar status={mockAgentStatus} />)
    expect(screen.getByText('Market Researcher')).toBeInTheDocument()
    expect(screen.getByText('Analyst')).toBeInTheDocument()
    expect(screen.getByText('CEO')).toBeInTheDocument()
    expect(screen.getByText('QA Engineer')).toBeInTheDocument()
  })

  it('shows green dot for online agents', () => {
    const { container } = render(<AgentStatusSidebar status={{ analyst: true }} />)
    const greenDot = container.querySelector('.bg-green-500')
    expect(greenDot).not.toBeNull()
  })

  it('shows red dot for offline agents', () => {
    const { container } = render(<AgentStatusSidebar status={{ ceo: false }} />)
    const redDot = container.querySelector('.bg-red-500')
    expect(redDot).not.toBeNull()
  })

  it('renders trigger buttons when onTrigger is provided', () => {
    const onTrigger = vi.fn()
    render(<AgentStatusSidebar status={mockAgentStatus} onTrigger={onTrigger} />)
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('calls onTrigger with correct agent name', () => {
    const onTrigger = vi.fn()
    render(<AgentStatusSidebar status={mockAgentStatus} onTrigger={onTrigger} />)
    const analystButton = screen.getByLabelText('Trigger analyst')
    fireEvent.click(analystButton)
    expect(onTrigger).toHaveBeenCalledWith('analyst')
  })

  it('does not render trigger buttons when onTrigger is absent', () => {
    render(<AgentStatusSidebar status={mockAgentStatus} />)
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })
})
