import type { components } from '../../types/api.generated'
import type { AssessmentQuestion, DraftAnswer } from './QuestionRenderer'

export type SubmitRequest = components['schemas']['SubmitAttemptRequest']

function answerFor(question: AssessmentQuestion, draft: DraftAnswer | undefined): SubmitRequest['answers'][number]['answer'] | null {
  switch (question.type) {
    case 'multiple_choice':
      return draft?.kind === 'multiple_choice' && question.options.some((option) => option.id === draft.option_id)
        ? { option_id: draft.option_id } : null
    case 'fill_blank':
      return draft?.kind === 'text' && draft.text.trim() ? { text: draft.text } : null
    case 'matching': {
      if (draft?.kind !== 'matching' || draft.pairs.length !== question.config.left_items.length) return null
      const leftIds = new Set(question.config.left_items.map((item) => item.id))
      const rightIds = new Set(question.config.right_items.map((item) => item.id))
      const selectedLeft = new Set(draft.pairs.map((pair) => pair.left_id))
      const selectedRight = new Set(draft.pairs.map((pair) => pair.right_id))
      if (selectedLeft.size !== draft.pairs.length || selectedRight.size !== draft.pairs.length) return null
      if (draft.pairs.some((pair) => !leftIds.has(pair.left_id) || !rightIds.has(pair.right_id))) return null
      return { pairs: draft.pairs.map(({ left_id, right_id }) => ({ left_id, right_id })) }
    }
    case 'reorder_sentence': {
      if (draft?.kind !== 'reorder_sentence') return null
      const expected = new Set(question.config.items.map((item) => item.id))
      return draft.item_ids.length === expected.size && new Set(draft.item_ids).size === expected.size && draft.item_ids.every((id) => expected.has(id))
        ? { item_ids: [...draft.item_ids] } : null
    }
    case 'translate_vi_zh':
    case 'translate_zh_vi':
    case 'sentence_writing':
      return draft?.kind === 'text' && draft.text.trim() ? { text: draft.text } : null
  }
}

export function createSubmitRequest(questions: AssessmentQuestion[], drafts: Record<string, DraftAnswer>): SubmitRequest | null {
  const answers: SubmitRequest['answers'] = []
  for (const question of questions) {
    const answer = answerFor(question, drafts[question.id])
    if (!answer) return null
    answers.push({ question_id: question.id, answer })
  }
  return { answers }
}
