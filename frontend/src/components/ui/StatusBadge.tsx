import type { HTMLAttributes, ReactNode } from 'react'

export type StatusBadgeTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

type StatusBadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: StatusBadgeTone
  children: ReactNode
}

export function StatusBadge({ tone = 'neutral', children, className = '', ...props }: StatusBadgeProps) {
  return <span {...props} className={['ui-status-badge', `ui-status-badge--${tone}`, className].filter(Boolean).join(' ')}>
    {children}
  </span>
}
