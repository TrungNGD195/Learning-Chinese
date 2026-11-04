import { SectionIcon } from '../../components/academy/AcademyArtwork'
import { Alert, Button, EmptyState, StatusBadge, Surface } from '../../components/ui'
import type { components } from '../../types/api.generated'
import { Companion, VocabularyIllustration } from '../../components/academy/Companion'

type Vocabulary = components['schemas']['VocabularyLessonItem']
type Grammar = components['schemas']['GrammarLessonItem']

type TheoryProps<T> = {
  items: T[]
  viewed: Record<string, boolean>
  expanded: Record<string, boolean>
  pending: Record<string, boolean>
  errors: Record<string, string | undefined>
  onToggle: (id: string, wasOpen: boolean) => void
}

function SectionHeading({ chinese, english, count, id }: { chinese: string; english: string; count: string; id: string }) {
  return <div className="lesson-section__heading">
    <div><SectionIcon kind={id === 'vocabulary-title' ? 'vocabulary' : 'grammar'}/><h2 id={id}>{english} <span lang="zh-Hans" className="academy-section-chinese" aria-hidden="true">{chinese}</span></h2></div>
    <span className="lesson-section__eyebrow">{count}</span>
  </div>
}

export function VocabularySection({ items, viewed, expanded, pending, errors, onToggle }: TheoryProps<Vocabulary>) {
  const viewedCount = items.filter((item) => viewed[item.id]).length
  return <section className="lesson-section" id="vocabulary" aria-labelledby="vocabulary-title">
    <SectionHeading chinese="生词" english="Vocabulary" count={`${viewedCount} / ${items.length} viewed`} id="vocabulary-title" />
    {items.length === 0 ? <EmptyState title="No vocabulary yet">There are no vocabulary items in this lesson.</EmptyState> : <div className="lesson-card-grid">
      {items.map((entry) => {
        const isOpen = Boolean(expanded[entry.id])
        const isPending = Boolean(pending[entry.id])
        return <Surface as="article" className="learner-surface lesson-theory-card" key={entry.id}>
          <div className="academy-vocabulary-identity"><div><h3 className="lesson-theory-card__hanzi" lang="zh-Hans">{entry.item.hanzi}</h3>
          <p className="lesson-theory-card__pinyin">{entry.item.pinyin}</p>
          <p className="lesson-theory-card__meaning">{entry.item.vietnamese_meaning}</p>
          </div><VocabularyIllustration hanzi={entry.item.hanzi}/></div>
          <StatusBadge tone={viewed[entry.id] ? 'success' : 'neutral'}>{viewed[entry.id] ? 'Viewed' : 'Not viewed'}</StatusBadge>
          <Button aria-expanded={isOpen} disabled={isPending} onClick={() => onToggle(entry.id, isOpen)}>{isOpen ? 'Hide details' : 'Show details'}</Button>
          {isPending && <p role="status">Saving viewed state…</p>}
          {errors[entry.id] && <Alert role="alert" tone="error">{errors[entry.id]}</Alert>}
          {isOpen && <div className="lesson-theory-card__details">
            {entry.item.part_of_speech && <p>Part of speech: {entry.item.part_of_speech}</p>}
            {entry.example && <p>Example: <span lang="zh-Hans">{entry.example}</span></p>}
            {entry.note && <div className="academy-theory-note"><Companion pose="truc" decorative/><p>Note: {entry.note}</p></div>}
          </div>}
        </Surface>
      })}
    </div>}
  </section>
}

export function GrammarSection({ items, viewed, expanded, pending, errors, onToggle }: TheoryProps<Grammar>) {
  const viewedCount = items.filter((item) => viewed[item.id]).length
  return <section className="lesson-section" id="grammar" aria-labelledby="grammar-title">
    <SectionHeading chinese="语法" english="Grammar" count={`${viewedCount} / ${items.length} viewed`} id="grammar-title" />
    {items.length === 0 ? <EmptyState title="No grammar yet">There are no grammar points in this lesson.</EmptyState> : <div className="lesson-card-grid">
      {items.map((entry) => {
        const isOpen = Boolean(expanded[entry.id])
        const isPending = Boolean(pending[entry.id])
        return <Surface as="article" className="learner-surface lesson-theory-card" key={entry.id}>
          <h3>{entry.item.name}</h3>
          {entry.item.structure && <p className="lesson-theory-card__structure">{entry.item.structure}</p>}
          <StatusBadge tone={viewed[entry.id] ? 'success' : 'neutral'}>{viewed[entry.id] ? 'Viewed' : 'Not viewed'}</StatusBadge>
          <Button aria-expanded={isOpen} disabled={isPending} onClick={() => onToggle(entry.id, isOpen)}>{isOpen ? 'Hide details' : 'Show details'}</Button>
          {isPending && <p role="status">Saving viewed state…</p>}
          {errors[entry.id] && <Alert role="alert" tone="error">{errors[entry.id]}</Alert>}
          {isOpen && <div className="lesson-theory-card__details">
            <p>{entry.item.explanation}</p>
            {entry.item.usage && <p>Usage: {entry.item.usage}</p>}
            {entry.example && <p>Example: <span lang="zh-Hans">{entry.example}</span></p>}
            {entry.note && <div className="academy-theory-note"><Companion pose="truc" decorative/><p>Note: {entry.note}</p></div>}
          </div>}
        </Surface>
      })}
    </div>}
  </section>
}
