import type { HTMLAttributes, ReactNode } from 'react'

export type AlertTone = 'info' | 'success' | 'warning' | 'error'

type AlertProps = HTMLAttributes<HTMLDivElement> & {
  tone?: AlertTone
  children: ReactNode
  action?: ReactNode
}

export function Alert({ tone = 'info', children, action, className = '', role, ...props }: AlertProps) {
  return <div {...props} className={['ui-alert', `ui-alert--${tone}`, className].filter(Boolean).join(' ')} role={role}>
    <div>{children}</div>
    {action && <div className="ui-alert__action">{action}</div>}
  </div>
}
