import { createElement, type HTMLAttributes, type ReactNode } from 'react'

type SurfaceProps = HTMLAttributes<HTMLElement> & {
  as?: 'div' | 'section' | 'article'
  children: ReactNode
}

export function Surface({ as = 'div', children, className = '', ...props }: SurfaceProps) {
  return createElement(as, { ...props, className: ['ui-surface', className].filter(Boolean).join(' ') }, children)
}
