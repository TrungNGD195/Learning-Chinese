import type { components } from '../../types/api.generated'

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

export function VocabularySection({ items, viewed, expanded, pending, errors, onToggle }: TheoryProps<Vocabulary>) {
  const viewedCount = items.filter((item) => viewed[item.id]).length
  return <section className="learning-section" aria-labelledby="vocabulary-title">
    <div className="section-heading"><h2 id="vocabulary-title">Vocabulary</h2><span>{viewedCount} / {items.length} viewed</span></div>
    {items.length === 0 && <p>No vocabulary in this lesson.</p>}
    <div className="section-grid">
      {items.map((entry) => {
        const isOpen = Boolean(expanded[entry.id])
        const isPending = Boolean(pending[entry.id])
        return <article className="theory-card" key={entry.id}>
          <h3>{entry.item.hanzi}</h3><p className="pinyin">{entry.item.pinyin}</p><p>{entry.item.vietnamese_meaning}</p>
          <p className="viewed-indicator">{viewed[entry.id] ? 'Viewed' : 'Not viewed'}</p>
          <button type="button" className="secondary-action" aria-expanded={isOpen} disabled={isPending}
            onClick={() => onToggle(entry.id, isOpen)}>{isOpen ? 'Hide details' : 'Show details'}</button>
          {isPending && <p role="status">Saving viewed state…</p>}
          {errors[entry.id] && <p role="alert">{errors[entry.id]}</p>}
          {isOpen && <div className="theory-details">
            {entry.item.part_of_speech && <p>Part of speech: {entry.item.part_of_speech}</p>}
            {entry.example && <p>Example: {entry.example}</p>}
            {entry.note && <p>Note: {entry.note}</p>}
          </div>}
        </article>
      })}
    </div>
  </section>
}

export function GrammarSection({ items, viewed, expanded, pending, errors, onToggle }: TheoryProps<Grammar>) {
  const viewedCount = items.filter((item) => viewed[item.id]).length
  return <section className="learning-section" aria-labelledby="grammar-title">
    <div className="section-heading"><h2 id="grammar-title">Grammar</h2><span>{viewedCount} / {items.length} viewed</span></div>
    {items.length === 0 && <p>No grammar in this lesson.</p>}
    <div className="section-grid">
      {items.map((entry) => {
        const isOpen = Boolean(expanded[entry.id])
        const isPending = Boolean(pending[entry.id])
        return <article className="theory-card" key={entry.id}>
          <h3>{entry.item.name}</h3>{entry.item.structure && <p className="pinyin">{entry.item.structure}</p>}
          <p className="viewed-indicator">{viewed[entry.id] ? 'Viewed' : 'Not viewed'}</p>
          <button type="button" className="secondary-action" aria-expanded={isOpen} disabled={isPending}
            onClick={() => onToggle(entry.id, isOpen)}>{isOpen ? 'Hide details' : 'Show details'}</button>
          {isPending && <p role="status">Saving viewed state…</p>}
          {errors[entry.id] && <p role="alert">{errors[entry.id]}</p>}
          {isOpen && <div className="theory-details">
            <p>{entry.item.explanation}</p>
            {entry.item.usage && <p>Usage: {entry.item.usage}</p>}
            {entry.example && <p>Example: {entry.example}</p>}
            {entry.note && <p>Note: {entry.note}</p>}
          </div>}
        </article>
      })}
    </div>
  </section>
}
