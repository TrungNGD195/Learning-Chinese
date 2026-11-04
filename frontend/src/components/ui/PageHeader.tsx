import type { ReactNode } from 'react'
import { HeaderArtwork } from '../academy/AcademyArtwork'

type PageHeaderProps = {
  title: ReactNode
  description?: ReactNode
  eyebrow?: ReactNode
  titleId?: string
  back?: ReactNode
  breadcrumb?: ReactNode
  actions?: ReactNode
  artwork?: ReactNode
}

export function PageHeader({ title, description, eyebrow, titleId, back, breadcrumb, actions, artwork }: PageHeaderProps) {
  const context = back ?? breadcrumb
  return <header className="ui-page-header">
    <div className="ui-page-header__copy">
      {context && <div className="ui-page-header__context">{context}</div>}
      {eyebrow && <p className="ui-page-header__eyebrow">{eyebrow}</p>}
      <h1 id={titleId}>{title}</h1>
      {description && <p className="ui-page-header__description">{description}</p>}
    </div>
    {artwork === false ? null : artwork ?? <HeaderArtwork/>}
    {actions && <div className="ui-page-header__actions">{actions}</div>}
  </header>
}
