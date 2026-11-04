import { useEffect, useId, useRef, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from 'react'
import { Button, type ButtonVariant } from './Button'

const focusableSelector = [
  'a[href]',
  'area[href]',
  'button',
  'input:not([type="hidden"])',
  'select',
  'textarea',
  'summary',
  'audio[controls]',
  'video[controls]',
  'iframe',
  'object',
  'embed',
  '[contenteditable]:not([contenteditable="false"])',
  '[tabindex]',
].join(',')

function isVisibleFocusable(element: HTMLElement, dialog: HTMLDialogElement) {
  if (element.tabIndex < 0 || element.matches(':disabled') || element.closest('[hidden], [inert], [aria-hidden="true"]')) return false
  if (element.matches('summary') && element.parentElement?.querySelector(':scope > summary') !== element) return false

  const elementVisibility = window.getComputedStyle(element).visibility
  if (elementVisibility === 'hidden' || elementVisibility === 'collapse') return false

  let ancestor: HTMLElement | null = element
  while (ancestor) {
    if (window.getComputedStyle(ancestor).display === 'none') return false
    if (ancestor === dialog) break
    ancestor = ancestor.parentElement
  }

  if (element instanceof HTMLInputElement && element.type === 'radio' && element.name) {
    const group = Array.from(dialog.querySelectorAll<HTMLInputElement>('input[type="radio"]'))
      .filter((radio) => radio.name === element.name && radio.form === element.form && !radio.disabled)
    const tabStop = group.find((radio) => radio.checked) ?? group[0]
    return element === tabStop
  }

  return true
}

type DialogProps = {
  open: boolean
  title: ReactNode
  children: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  onConfirm?: () => void | Promise<void>
  onCancel?: () => void
  onClose?: () => void
  busy?: boolean
  confirmVariant?: ButtonVariant
}

export function Dialog({
  open,
  title,
  children,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  onClose,
  busy = false,
  confirmVariant = 'primary',
}: DialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)
  const confirming = useRef(false)
  const titleId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open) {
      previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
      if (typeof dialog.showModal === 'function') {
        try { dialog.showModal() } catch { dialog.setAttribute('open', '') }
      } else {
        dialog.setAttribute('open', '')
      }
      dialog.focus()
      return
    }

    if (dialog.open) {
      try { dialog.close() } catch { dialog.removeAttribute('open') }
    }
    const restoreTarget = previousFocus.current
    previousFocus.current = null
    if (restoreTarget?.isConnected) window.setTimeout(() => restoreTarget.focus(), 0)
  }, [open])

  const notifyCancel = () => {
    if (onCancel) onCancel()
    else onClose?.()
  }

  const containTabFocus = (event: ReactKeyboardEvent<HTMLDialogElement>) => {
    const dialog = dialogRef.current
    if (event.key !== 'Tab' || !open || !dialog?.open) return

    const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(focusableSelector))
      .filter((element) => isVisibleFocusable(element, dialog))
    if (focusable.length === 0) {
      event.preventDefault()
      dialog.focus()
      return
    }

    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const active = document.activeElement
    if (event.shiftKey && (active === first || active === dialog || !dialog.contains(active))) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && (active === last || active === dialog || !dialog.contains(active))) {
      event.preventDefault()
      first.focus()
    }
  }

  const confirm = async () => {
    if (busy || confirming.current || !onConfirm) return
    confirming.current = true
    try {
      await onConfirm()
    } finally {
      confirming.current = false
    }
  }

  return <dialog
    ref={dialogRef}
    className="ui-dialog"
    aria-labelledby={titleId}
    tabIndex={-1}
    onKeyDown={containTabFocus}
    onCancel={(event) => { event.preventDefault(); notifyCancel() }}
  >
    <div className="ui-dialog__content">
      <h2 id={titleId}>{title}</h2>
      <div className="ui-dialog__body">{children}</div>
      <div className="ui-dialog__actions">
        <Button variant="secondary" onClick={notifyCancel}>{cancelLabel}</Button>
        {onConfirm && <Button variant={confirmVariant} disabled={busy} onClick={() => void confirm()}>{confirmLabel}</Button>}
      </div>
    </div>
  </dialog>
}
