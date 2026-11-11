import type { HTMLAttributes, ReactNode } from 'react'

type TableContainerProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode
}

export function TableContainer({ children, className = '', ...props }: TableContainerProps) {
  return <div {...props} className={['ui-table-container', className].filter(Boolean).join(' ')}>
    <span className="ui-table-container__hint">Cuộn ngang để xem đầy đủ các cột <span aria-hidden="true">→</span></span>
    {children}
  </div>
}
