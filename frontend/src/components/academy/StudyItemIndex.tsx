import { useEffect, useRef } from 'react'
import { Link } from 'react-router'

type Entry = { id: string; number: number; text: string; pinyin: string; active: boolean; label: string; to?: string; onSelect?: () => void; disabled?: boolean }
export function StudyItemIndex({ title, count, groups, className = '' }: {
  title: string; count: string; className?: string; groups: { title?: string; items: Entry[] }[]
}) {
  const list = useRef<HTMLDivElement>(null)
  const active = groups.flatMap(group => group.items).find(item => item.active)?.id
  useEffect(() => {
    const container = list.current
    const selected = container?.querySelector<HTMLElement>('[aria-current]')
    if (!container || !selected) return
    const top = selected.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop
    if (top < container.scrollTop || top + selected.offsetHeight > container.scrollTop + container.clientHeight) {
      container.scrollTop = top - container.clientHeight / 2 + selected.offsetHeight / 2
    }
  }, [active])
  return <aside className={`study-item-index ${className}`} aria-label={`Chọn ${title.toLocaleLowerCase('vi')}`}>
    <div className="study-item-index__heading"><h2>{title}</h2><span>{count}</span></div>
    <div ref={list} className="study-item-index__list pronunciation-sound-index__list">
      {groups.map((group, index) => <section key={group.title ?? index}>{group.title && <h3>{group.title}</h3>}<ol start={group.items[0]?.number ?? 1}>
        {group.items.map(item => {
          const content = <><span className="study-item-index__number" aria-hidden="true">{item.number}</span><span className="study-item-index__word"><strong lang="zh-Hans">{item.text}</strong><small>{item.pinyin}</small></span></>
          return <li key={item.id}>{item.to ? <Link to={item.to} aria-label={item.label} aria-current={item.active ? 'page' : undefined} aria-controls="lesson-study-content">{content}</Link>
            : <button type="button" disabled={item.disabled} aria-label={item.label} aria-current={item.active ? 'true' : undefined} aria-controls="lesson-study-content" onClick={item.onSelect}>{content}</button>}</li>
        })}
      </ol></section>)}
    </div>
  </aside>
}
