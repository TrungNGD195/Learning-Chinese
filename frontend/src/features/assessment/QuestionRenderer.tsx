import type { components } from '../../types/api.generated'

export type AssessmentQuestion = components['schemas']['AssessmentResponse']['questions'][number]

export type DraftAnswer =
  | { kind: 'multiple_choice'; option_id: string }
  | { kind: 'text'; text: string }
  | { kind: 'matching'; pairs: { left_id: string; right_id: string }[] }
  | { kind: 'reorder_sentence'; item_ids: string[] }

export function QuestionRenderer({ question, draft, onChange }: {
  question: AssessmentQuestion
  draft: DraftAnswer | undefined
  onChange: (answer: DraftAnswer) => void
}) {
  switch (question.type) {
    case 'multiple_choice':
      return <fieldset className="question-fieldset">
        <legend>{question.prompt}</legend>
        {question.options.map((option) => <label className="answer-option" key={option.id}>
          <input type="radio" name={question.id} value={option.id}
            checked={draft?.kind === 'multiple_choice' && draft.option_id === option.id}
            onChange={() => onChange({ kind: 'multiple_choice', option_id: option.id })} />
          {option.option_text}
        </label>)}
      </fieldset>
    case 'fill_blank':
      return <label className="question-prompt">{question.prompt}
        <input type="text" value={draft?.kind === 'text' ? draft.text : ''}
          onChange={(event) => onChange({ kind: 'text', text: event.currentTarget.value })} />
      </label>
    case 'matching':
      return <fieldset className="question-fieldset">
        <legend>{question.prompt}</legend>
        <div className="matching-list">{question.config.left_items.map((item) => {
          const selected = draft?.kind === 'matching' ? draft.pairs.find((pair) => pair.left_id === item.id)?.right_id ?? '' : ''
          return <label className="matching-row" key={item.id}>
            <span>{item.text}</span>
            <select aria-label={`Match ${item.text}`} value={selected} onChange={(event) => {
              const pairs = draft?.kind === 'matching' ? draft.pairs.filter((pair) => pair.left_id !== item.id) : []
              if (event.currentTarget.value) pairs.push({ left_id: item.id, right_id: event.currentTarget.value })
              onChange({ kind: 'matching', pairs })
            }}>
              <option value="">Choose a match</option>
              {question.config.right_items.map((right) => <option key={right.id} value={right.id}>{right.text}</option>)}
            </select>
          </label>
        })}</div>
      </fieldset>
    case 'reorder_sentence': {
      const ids = draft?.kind === 'reorder_sentence' ? draft.item_ids : question.config.items.map((item) => item.id)
      const rows = ids.map((id) => question.config.items.find((item) => item.id === id)).filter((item) => item !== undefined)
      return <fieldset className="question-fieldset">
        <legend>{question.prompt}</legend>
        <ol className="reorder-list">{rows.map((item, index) => <li key={item.id}>
          <span>{item.text}</span>
          <button type="button" className="icon-action" aria-label={`Move ${item.text} up`} disabled={index === 0}
            onClick={() => { const next = [...ids]; [next[index - 1], next[index]] = [next[index], next[index - 1]]; onChange({ kind: 'reorder_sentence', item_ids: next }) }}>↑</button>
          <button type="button" className="icon-action" aria-label={`Move ${item.text} down`} disabled={index === rows.length - 1}
            onClick={() => { const next = [...ids]; [next[index + 1], next[index]] = [next[index], next[index + 1]]; onChange({ kind: 'reorder_sentence', item_ids: next }) }}>↓</button>
        </li>)}</ol>
        <button type="button" className="secondary-action" onClick={() => onChange({ kind: 'reorder_sentence', item_ids: [...ids] })}>Use this order</button>
      </fieldset>
    }
    case 'translate_vi_zh':
    case 'translate_zh_vi':
    case 'sentence_writing':
      return <label className="question-prompt">{question.prompt}
        <textarea rows={5} value={draft?.kind === 'text' ? draft.text : ''}
          onChange={(event) => onChange({ kind: 'text', text: event.currentTarget.value })} />
      </label>
  }
}
