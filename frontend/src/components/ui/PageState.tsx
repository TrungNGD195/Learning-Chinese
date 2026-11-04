import { useContext, type ReactNode } from 'react'
import { ArtworkContext } from '../academy/artworkContext'
import { SceneIllustration } from '../academy/AcademyArtwork'

type StateProps = {
  title?: ReactNode
  children?: ReactNode
  action?: ReactNode
  className?: string
}

export function LoadingState({ children = 'Loading…', className = '' }: Pick<StateProps, 'children' | 'className'>) {
  return <div className={['ui-page-state', className].filter(Boolean).join(' ')} role="status">{children}</div>
}

export function EmptyState({ title, children, action, className = '' }: StateProps) {
  const artwork = useContext(ArtworkContext)
  return <section className={['ui-page-state', className].filter(Boolean).join(' ')}>
    {artwork && <SceneIllustration scene={artwork.scene} className="academy-empty-illustration"/>}
    {title && <h2>{title}</h2>}
    {children && <p>{children}</p>}
    {action && <div className="ui-page-state__action">{action}</div>}
  </section>
}
