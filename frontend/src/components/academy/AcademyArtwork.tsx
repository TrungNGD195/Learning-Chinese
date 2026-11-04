import { useContext, type CSSProperties, type ReactNode } from 'react'
import { useLocation } from 'react-router'
import { ArtworkContext, type LearningScene } from './artworkContext'
import { Companion, type CompanionPose } from './Companion'
import { AcademyIcon } from './AcademyIcon'

const sceneCells: Record<LearningScene, number> = { greeting: 0, family: 1, study: 2, path: 3, practice: 4, library: 5 }
export function SceneIllustration({ scene, className = '' }: { scene: LearningScene; className?: string }) {
  const cell = sceneCells[scene]
  return <span aria-hidden="true" className={`academy-scene-illustration ${className}`} data-scene={scene} style={{ backgroundPosition: `${cell % 3 * 50}% ${Math.floor(cell / 3) * 100}%` } as CSSProperties}/>
}
export function sceneForTitle(title: string, fallback: LearningScene = 'study'): LearningScene {
  if (/chào|greeting|你好|giao tiếp/i.test(title)) return 'greeting'
  if (/gia đình|family|家庭/i.test(title)) return 'family'
  return fallback
}
export function ArtworkProvider({ children, admin = false }: { children: ReactNode; admin?: boolean }) {
  const { pathname } = useLocation()
  const scene: LearningScene = /documents/.test(pathname) ? 'library' : /assessment/.test(pathname) ? 'practice' : /pronunciation|curriculum|\/hsk\//.test(pathname) ? 'path' : /history/.test(pathname) ? 'library' : 'study'
  return <ArtworkContext.Provider value={{ scene, admin }}>{children}</ArtworkContext.Provider>
}
export function HeaderArtwork({ scene, pose }: { scene?: LearningScene; pose?: CompanionPose }) {
  const context = useContext(ArtworkContext)
  if (!context && !scene) return null
  const selected = scene ?? context?.scene ?? 'study'
  return <div className="academy-header-art" aria-hidden="true"><SceneIllustration scene={selected}/><Companion pose={pose ?? (selected === 'practice' ? 'but' : selected === 'library' ? 'truc' : 'guide')} decorative/></div>
}
export function ActivityIllustration({ scene, title, children }: { scene: LearningScene; title: string; children?: ReactNode }) {
  return <div className="academy-activity-illustration"><SceneIllustration scene={scene}/><div><strong>{title}</strong>{children && <p>{children}</p>}</div></div>
}
export function SectionIcon({ kind }: { kind: 'vocabulary' | 'grammar' | 'practice' | 'path' | 'library' | 'history' }) {
  return <span className={`academy-section-icon academy-section-icon--${kind}`} aria-hidden="true"><AcademyIcon name={{ vocabulary: 'book', grammar: 'structure', practice: 'exercise', path: 'path', library: 'library', history: 'history' }[kind]} size={24}/></span>
}
