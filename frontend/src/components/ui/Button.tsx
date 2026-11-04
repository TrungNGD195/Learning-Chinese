import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
}

export function Button({ variant = 'secondary', type = 'button', className = '', ...props }: ButtonProps) {
  const classes = ['ui-button', `ui-button--${variant}`, className].filter(Boolean).join(' ')
  return <button {...props} className={classes} type={type} />
}
