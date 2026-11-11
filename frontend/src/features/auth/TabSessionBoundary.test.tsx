import { act, fireEvent, render, screen } from '@testing-library/react'
import { StrictMode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { prepareTabSession } from './tabSession'
import { TabSessionBoundary } from './TabSessionBoundary'

vi.mock('./tabSession', () => ({ prepareTabSession: vi.fn() }))
beforeEach(() => vi.resetAllMocks())

describe('tab session boundary', () => {
  it('withholds protected content and forms until initialization succeeds in StrictMode', async () => {
    let finish!: () => void
    const pending = new Promise<void>(resolve => { finish = resolve })
    vi.mocked(prepareTabSession).mockReturnValue(pending)
    render(<StrictMode><TabSessionBoundary><p>Protected content</p></TabSessionBoundary></StrictMode>)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
    await act(async () => finish())
    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })

  it('keeps content hidden on failure and offers an explicit retry', async () => {
    vi.mocked(prepareTabSession).mockRejectedValueOnce(new Error('private failure')).mockResolvedValue(undefined)
    render(<TabSessionBoundary><p>Protected content</p></TabSessionBoundary>)
    expect(await screen.findByRole('alert')).not.toHaveTextContent('private failure')
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }))
    expect(await screen.findByText('Protected content')).toBeInTheDocument()
  })
})
