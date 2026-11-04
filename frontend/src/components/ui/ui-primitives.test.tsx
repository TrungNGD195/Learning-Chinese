import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { Alert, Button, Dialog, EmptyState, LoadingState, PageHeader, StatusBadge, Surface, TableContainer } from './index'

describe('shared presentation primitives', () => {
  it('defaults Button to type button and preserves disabled and variant presentation', () => {
    const onClick = vi.fn()
    render(<Button variant="primary" disabled onClick={onClick}>Save</Button>)
    const button = screen.getByRole('button', { name: 'Save' })
    expect(button).toHaveAttribute('type', 'button')
    expect(button).toBeDisabled()
    expect(button).toHaveClass('ui-button--primary')
    fireEvent.click(button)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('shows StatusBadge text and tone without interpreting its value', () => {
    render(<StatusBadge tone="warning">PROCESSING</StatusBadge>)
    expect(screen.getByText('PROCESSING')).toHaveClass('ui-status-badge--warning')
  })

  it('keeps Alert semantics caller-controlled and renders its action', () => {
    const { rerender } = render(<Alert tone="success" action={<button>Retry</button>}>Saved</Alert>)
    expect(screen.getByText('Saved').closest('[role]')).toBeNull()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    rerender(<Alert role="alert" tone="error">Failed</Alert>)
    expect(screen.getByRole('alert')).toHaveTextContent('Failed')
  })

  it('renders loading and empty states with an optional action', () => {
    render(<><LoadingState>Loading lessons</LoadingState><EmptyState title="Nothing here" action={<button>Create</button>}>No lessons yet.</EmptyState></>)
    expect(screen.getByRole('status')).toHaveTextContent('Loading lessons')
    expect(screen.getByRole('heading', { name: 'Nothing here' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create' })).toBeInTheDocument()
  })

  it('keeps a semantic table inside responsive containment', () => {
    render(<TableContainer><table><caption>Lessons</caption><tbody><tr><th scope="row">Lesson 1</th></tr></tbody></table></TableContainer>)
    expect(screen.getByRole('table', { name: 'Lessons' })).toBeInTheDocument()
    expect(screen.getByRole('table').parentElement).toHaveClass('ui-table-container')
  })

  it('supports Surface semantic element selection', () => {
    render(<Surface as="article" aria-label="Learning card">Content</Surface>)
    expect(screen.getByRole('article', { name: 'Learning card' })).toHaveClass('ui-surface')
  })

  it('applies an optional title id to the PageHeader heading', () => {
    const { rerender } = render(<PageHeader title="Learning" />)
    expect(screen.getByRole('heading', { level: 1, name: 'Learning' })).not.toHaveAttribute('id')
    rerender(<PageHeader title="Learning" titleId="page-title" />)
    expect(screen.getByRole('heading', { level: 1, name: 'Learning' })).toHaveAttribute('id', 'page-title')
  })
})

function ControlledDialog({ onConfirm, onCancel, busy = false }: { onConfirm?: () => void | Promise<void>; onCancel: () => void; busy?: boolean }) {
  const [open, setOpen] = useState(false)
  return <>
    <button onClick={() => setOpen(true)}>Open dialog</button>
    <Dialog open={open} title="Confirm action" onConfirm={onConfirm} onCancel={() => { onCancel(); setOpen(false) }} busy={busy}>
      Continue with this action?
    </Dialog>
  </>
}

function ControlledDecisionDialog({ onLeave }: { onLeave: () => void }) {
  const [open, setOpen] = useState(false)
  return <>
    <button onClick={() => setOpen(true)}>Open dialog</button>
    <Dialog open={open} title="Unsaved answers" cancelLabel="Stay" confirmLabel="Leave"
      onCancel={() => setOpen(false)} onConfirm={() => { onLeave(); setOpen(false) }}>
      You have unsaved answers.
    </Dialog>
  </>
}

describe('Dialog', () => {
  it('is closed by default when controlled closed', () => {
    render(<Dialog open={false} title="Closed">Body</Dialog>)
    expect(screen.getByRole('dialog', { hidden: true })).not.toHaveAttribute('open')
  })

  it('notifies Cancel exactly once for the button and Escape cancel event', () => {
    const onCancel = vi.fn()
    render(<ControlledDialog onCancel={onCancel} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open dialog' }))
    const dialog = screen.getByRole('dialog', { name: 'Confirm action' })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
    expect(dialog).not.toHaveAttribute('open')
  })

  it('handles the native cancel event as Escape without duplicate notifications', () => {
    const onCancel = vi.fn()
    render(<ControlledDialog onCancel={onCancel} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open dialog' }))
    const dialog = screen.getByRole('dialog', { name: 'Confirm action' })
    fireEvent(dialog, new Event('cancel', { bubbles: false, cancelable: true }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('invokes Confirm once and disables it while busy', () => {
    const onConfirm = vi.fn()
    const { rerender } = render(<Dialog open title="Confirm action" onConfirm={onConfirm} busy>Body</Dialog>)
    const confirm = screen.getByRole('button', { name: 'Confirm' })
    expect(confirm).toBeDisabled()
    fireEvent.click(confirm)
    expect(onConfirm).not.toHaveBeenCalled()
    rerender(<Dialog open title="Confirm action" onConfirm={onConfirm}>Body</Dialog>)
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('keeps the primary confirm presentation by default and supports danger confirmation', () => {
    const { rerender } = render(<Dialog open title="Confirm action" onConfirm={() => undefined}>Body</Dialog>)
    expect(screen.getByRole('button', { name: 'Confirm' })).toHaveClass('ui-button--primary')
    rerender(<Dialog open title="Confirm action" onConfirm={() => undefined} confirmVariant="danger">Body</Dialog>)
    expect(screen.getByRole('button', { name: 'Confirm' })).toHaveClass('ui-button--danger')
  })

  it('restores focus to the trigger when the controlled dialog closes', async () => {
    const onCancel = vi.fn()
    render(<ControlledDialog onCancel={onCancel} />)
    const trigger = screen.getByRole('button', { name: 'Open dialog' })
    trigger.focus()
    fireEvent.click(trigger)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('focuses the dialog initially and sends the first Tab to the first enabled control', () => {
    render(<ControlledDecisionDialog onLeave={() => undefined} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open dialog' }))
    const dialog = screen.getByRole('dialog', { name: 'Unsaved answers' })
    const stay = screen.getByRole('button', { name: 'Stay' })
    expect(dialog).toHaveFocus()

    const tab = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    fireEvent(dialog, tab)
    expect(tab.defaultPrevented).toBe(true)
    expect(stay).toHaveFocus()
  })

  it('allows normal Tab movement through enabled controls before wrapping forward', () => {
    render(<ControlledDecisionDialog onLeave={() => undefined} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open dialog' }))
    const dialog = screen.getByRole('dialog', { name: 'Unsaved answers' })
    const stay = screen.getByRole('button', { name: 'Stay' })
    const leave = screen.getByRole('button', { name: 'Leave' })
    expect(dialog).toHaveFocus()

    const initialTab = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    fireEvent(dialog, initialTab)
    expect(initialTab.defaultPrevented).toBe(true)
    expect(stay).toHaveFocus()

    // jsdom does not perform the browser's default Tab movement, so place focus on the next control.
    leave.focus()
    expect(leave).toHaveFocus()
    const tab = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    fireEvent(leave, tab)
    expect(tab.defaultPrevented).toBe(true)
    expect(stay).toHaveFocus()
  })

  it('wraps Shift+Tab from the first enabled control to the final control', () => {
    render(<ControlledDecisionDialog onLeave={() => undefined} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open dialog' }))
    const stay = screen.getByRole('button', { name: 'Stay' })
    const leave = screen.getByRole('button', { name: 'Leave' })
    const reverseTab = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true })
    fireEvent(stay, reverseTab)
    expect(reverseTab.defaultPrevented).toBe(true)
    expect(leave).toHaveFocus()
  })

  it('wraps Shift+Tab from the initially focused dialog to the final control', () => {
    render(<ControlledDecisionDialog onLeave={() => undefined} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open dialog' }))
    const dialog = screen.getByRole('dialog', { name: 'Unsaved answers' })
    const leave = screen.getByRole('button', { name: 'Leave' })
    const reverseTab = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true })
    fireEvent(dialog, reverseTab)
    expect(reverseTab.defaultPrevented).toBe(true)
    expect(leave).toHaveFocus()
  })

  it('skips disabled controls while cycling focus', () => {
    render(<ControlledDecisionDialog onLeave={() => undefined} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open dialog' }))
    const dialog = screen.getByRole('dialog', { name: 'Unsaved answers' })
    const stay = screen.getByRole('button', { name: 'Stay' })
    const leave = screen.getByRole('button', { name: 'Leave' })
    stay.setAttribute('disabled', '')
    const tab = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    fireEvent(dialog, tab)
    expect(tab.defaultPrevented).toBe(true)
    expect(leave).toHaveFocus()
    const reverseTab = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true })
    fireEvent(leave, reverseTab)
    expect(reverseTab.defaultPrevented).toBe(true)
    expect(leave).toHaveFocus()
  })

  it('keeps focus on the only enabled control when Tab would wrap', () => {
    render(<Dialog open title="One control" onCancel={() => undefined}>Body</Dialog>)
    const dialog = screen.getByRole('dialog', { name: 'One control' })
    const cancel = screen.getByRole('button', { name: 'Cancel' })
    cancel.focus()
    const tab = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    fireEvent(cancel, tab)
    expect(tab.defaultPrevented).toBe(true)
    expect(cancel).toHaveFocus()
    const reverseTab = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true })
    fireEvent(cancel, reverseTab)
    expect(reverseTab.defaultPrevented).toBe(true)
    expect(cancel).toHaveFocus()
    expect(dialog).toHaveAttribute('open')
  })

  it('keeps focus on the dialog when no controls are enabled', () => {
    render(<ControlledDecisionDialog onLeave={() => undefined} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open dialog' }))
    const dialog = screen.getByRole('dialog', { name: 'Unsaved answers' })
    screen.getByRole('button', { name: 'Stay' }).setAttribute('disabled', '')
    screen.getByRole('button', { name: 'Leave' }).setAttribute('disabled', '')
    expect(dialog).toHaveFocus()
    const tab = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    fireEvent(dialog, tab)
    expect(tab.defaultPrevented).toBe(true)
    expect(dialog).toHaveFocus()
    const reverseTab = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true, cancelable: true })
    fireEvent(dialog, reverseTab)
    expect(reverseTab.defaultPrevented).toBe(true)
    expect(dialog).toHaveFocus()
  })

  it('restores focus after Escape closes the dialog', async () => {
    const onCancel = vi.fn()
    render(<ControlledDialog onCancel={onCancel} />)
    const trigger = screen.getByRole('button', { name: 'Open dialog' })
    trigger.focus()
    fireEvent.click(trigger)
    const dialog = screen.getByRole('dialog', { name: 'Confirm action' })
    fireEvent(dialog, new Event('cancel', { bubbles: false, cancelable: true }))
    expect(onCancel).toHaveBeenCalledOnce()
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('keeps Stay cancellation and focus restoration intact', async () => {
    render(<ControlledDecisionDialog onLeave={() => undefined} />)
    const trigger = screen.getByRole('button', { name: 'Open dialog' })
    trigger.focus()
    fireEvent.click(trigger)
    const dialog = screen.getByRole('dialog', { name: 'Unsaved answers' })
    fireEvent.click(screen.getByRole('button', { name: 'Stay' }))
    expect(dialog).not.toHaveAttribute('open')
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('invokes Leave and closes without preventing the caller navigation action', async () => {
    const onLeave = vi.fn()
    render(<ControlledDecisionDialog onLeave={onLeave} />)
    fireEvent.click(screen.getByRole('button', { name: 'Open dialog' }))
    const dialog = screen.getByRole('dialog', { name: 'Unsaved answers' })
    fireEvent.click(screen.getByRole('button', { name: 'Leave' }))
    expect(onLeave).toHaveBeenCalledOnce()
    await waitFor(() => expect(dialog).not.toHaveAttribute('open'))
  })

  it('does not contain focus after close or after unmount', () => {
    const { unmount } = render(<ControlledDecisionDialog onLeave={() => undefined} />)
    const trigger = screen.getByRole('button', { name: 'Open dialog' })
    fireEvent.click(trigger)
    const dialog = screen.getByRole('dialog', { name: 'Unsaved answers' })
    fireEvent.click(screen.getByRole('button', { name: 'Stay' }))
    trigger.focus()
    const afterClose = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    fireEvent(dialog, afterClose)
    expect(afterClose.defaultPrevented).toBe(false)
    expect(trigger).toHaveFocus()

    unmount()
    const afterUnmount = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    fireEvent(dialog, afterUnmount)
    expect(afterUnmount.defaultPrevented).toBe(false)
  })
})
