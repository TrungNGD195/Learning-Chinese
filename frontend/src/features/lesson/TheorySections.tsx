import { SectionIcon } from '../../components/academy/AcademyArtwork'
import { Alert, Button, EmptyState, StatusBadge, Surface } from '../../components/ui'
import type { components } from '../../types/api.generated'
import { Companion } from '../../components/academy/Companion'

type Grammar = components['schemas']['GrammarLessonItem']

type TheoryProps<T> = {
  items: T[]
  viewed: Record<string, boolean>
  expanded: Record<string, boolean>
  pending: Record<string, boolean>
  errors: Record<string, string | undefined>
  onToggle: (id: string, wasOpen: boolean) => void
}

function SectionHeading({ chinese, vietnamese, count, id }: { chinese: string; vietnamese: string; count: string; id: string }) {
  return <div className="lesson-section__heading">
    <div><SectionIcon kind={id === 'vocabulary-title' ? 'vocabulary' : 'grammar'}/><h2 id={id}>{vietnamese} <span lang="zh-Hans" className="academy-section-chinese" aria-hidden="true">{chinese}</span></h2></div>
    <span className="lesson-section__eyebrow">{count}</span>
  </div>
}

export function GrammarSection({ items, viewed, expanded, pending, errors, onToggle }: TheoryProps<Grammar>) {
  const viewedCount = items.filter((item) => viewed[item.id]).length
  return <section className="lesson-section" id="grammar" aria-labelledby="grammar-title">
    <SectionHeading chinese="语法" vietnamese="Ngữ pháp" count={`${viewedCount} / ${items.length} đã xem`} id="grammar-title" />
    {items.length === 0 ? <EmptyState title="Chưa có ngữ pháp">Bài học này chưa có nội dung ngữ pháp.</EmptyState> : <div className="lesson-card-grid">
      {items.map((entry) => {
        const isOpen = Boolean(expanded[entry.id])
        const isPending = Boolean(pending[entry.id])
        return <Surface as="article" className="learner-surface lesson-theory-card" key={entry.id}>
          <h3>{entry.item.name}</h3>
          {entry.item.structure && <p className="lesson-theory-card__structure">{entry.item.structure}</p>}
          <StatusBadge tone={viewed[entry.id] ? 'success' : 'neutral'}>{viewed[entry.id] ? "Đã xem" : "Chưa xem"}</StatusBadge>
          <Button aria-expanded={isOpen} disabled={isPending} onClick={() => onToggle(entry.id, isOpen)}>{isOpen ? "Ẩn chi tiết" : "Xem chi tiết"}</Button>
          {isPending && <p role="status">Đang lưu trạng thái đã xem…</p>}
          {errors[entry.id] && <Alert role="alert" tone="error">{errors[entry.id]}</Alert>}
          {isOpen && <div className="lesson-theory-card__details">
            <p>{entry.item.explanation}</p>
            {entry.item.usage && <p>Cách dùng: {entry.item.usage}</p>}
            {entry.example && <p>Ví dụ: <span lang="zh-Hans">{entry.example}</span></p>}
            {entry.note && <div className="academy-theory-note"><Companion pose="truc" decorative/><p>Lưu ý: {entry.note}</p></div>}
          </div>}
        </Surface>
      })}
    </div>}
  </section>
}
