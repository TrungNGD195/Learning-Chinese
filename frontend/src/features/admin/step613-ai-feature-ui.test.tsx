import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { components } from '../../types/api.generated'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import * as adminApi from './api'
import { AdminAssessmentEditorPage, AdminAssessmentsPage } from './AdminAssessmentsPage'

type Lesson = components['schemas']['LessonAdminResponse']
type LessonVocabulary = components['schemas']['LessonContentAdminResponse']
type LessonGrammar = components['schemas']['LessonContentAdminResponse']
type GenerationResult = components['schemas']['AssessmentGenerationDraftResponse']

const lessons: Lesson[] = [
  { id: 'lesson-a', hsk_level_id: 'hsk-1', lesson_number: 1, title: 'Greetings', description: null, status: 'PUBLISHED', published_at: null },
  { id: 'lesson-b', hsk_level_id: 'hsk-1', lesson_number: 2, title: 'Names', description: null, status: 'PUBLISHED', published_at: null },
]

const vocabularyA: LessonVocabulary[] = [
  { id: 'association-a-shared', vocabulary_id: 'vocab-shared', hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', order_index: 1, note: null, example: null },
  { id: 'association-a-only', vocabulary_id: 'vocab-a-only', hanzi: '再见', pinyin: 'zàijiàn', vietnamese_meaning: 'tạm biệt', order_index: 2, note: null, example: null },
]
const vocabularyB: LessonVocabulary[] = [
  { id: 'association-b-shared', vocabulary_id: 'vocab-shared', hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', order_index: 1, note: null, example: null },
]
const grammarA: LessonGrammar[] = [
  { id: 'grammar-association-a', grammar_id: 'grammar-a', name: 'A 叫 B', structure: 'A + 叫 + B', explanation: 'Naming pattern', order_index: 1, note: null, example: null },
]
const grammarB: LessonGrammar[] = [
  { id: 'grammar-association-b', grammar_id: 'grammar-b', name: '吗 question', structure: 'statement + 吗', explanation: 'Yes/no question', order_index: 1, note: null, example: null },
]

function lessonsPage(items = lessons) {
  return { items, page: 1, page_size: 50, total: items.length }
}

function generatedResult(id = 'generated-assessment', questions: GenerationResult['questions'] = []): GenerationResult {
  return {
    assessment: { id, type: 'PERIODIC_TEST', lesson_id: null, title: 'Generated test', description: null, status: 'DRAFT', pass_threshold: 90, published_at: null },
    questions,
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

function renderAdmin() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const router = createMemoryRouter([
    { path: '/admin/assessments', element: <AdminAssessmentsPage /> },
    { path: '/admin/assessments/:assessmentId', element: <AdminAssessmentEditorPage /> },
  ], { initialEntries: ['/admin/assessments'] })
  render(<QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>)
  return { queryClient, router }
}

async function openGenerationForm() {
  fireEvent.click(await screen.findByRole('button', { name: 'Generate AI Draft' }))
  expect(await screen.findByRole('heading', { name: 'Generate AI Draft' })).toBeInTheDocument()
}

async function fillCommonFields() {
  fireEvent.change(screen.getByLabelText('Difficulty'), { target: { value: 'MEDIUM' } })
}

describe('Step 6.13 AI feature UI integration', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(adminApi, 'listHskLevels').mockResolvedValue([{ id: 'hsk-1', level_number: 1, title: 'HSK 1', description: null, order_index: 1 }])
    vi.spyOn(adminApi, 'listAdminLessons').mockResolvedValue(lessonsPage())
    vi.spyOn(adminApi, 'listAdminAssessments').mockResolvedValue({ items: [], page: 1, page_size: 20, total: 0 })
    vi.spyOn(adminApi, 'listLessonVocabulary').mockImplementation(async (id) => id === 'lesson-a' ? vocabularyA : vocabularyB)
    vi.spyOn(adminApi, 'listLessonGrammar').mockImplementation(async (id) => id === 'lesson-a' ? grammarA : grammarB)
    vi.spyOn(adminApi, 'listAssessmentQuestions').mockResolvedValue([])
    vi.spyOn(adminApi, 'getAdminAssessment').mockResolvedValue(generatedResult().assessment)
    vi.spyOn(adminApi, 'getAdminLesson').mockResolvedValue(lessons[0])
    vi.spyOn(adminApi, 'generateAssessmentDraft').mockResolvedValue(generatedResult())
    vi.spyOn(adminApi, 'publishAdminAssessment').mockResolvedValue(generatedResult().assessment)
  })

  it('sends Lesson Exercise with lesson_id only and keeps generation settings backend-owned', async () => {
    const { router, queryClient } = renderAdmin()
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    fireEvent.change(screen.getByLabelText('Title (optional)'), { target: { value: '  Practice  ' } })
    fireEvent.change(screen.getByLabelText('Question count'), { target: { value: '3' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    await waitFor(() => expect(adminApi.generateAssessmentDraft).toHaveBeenCalledWith({
      type: 'LESSON_EXERCISE', lesson_id: 'lesson-a', title: 'Practice', pass_threshold: 90,
      question_count: 3, allowed_types: ['multiple_choice'], difficulty: 'MEDIUM',
    }))
    expect(adminApi.listLessonVocabulary).not.toHaveBeenCalled()
    expect(adminApi.listLessonGrammar).not.toHaveBeenCalled()
    await waitFor(() => expect(router.state.location.pathname).toBe('/admin/assessments/generated-assessment'))
    await waitFor(() => expect(adminApi.getAdminAssessment).toHaveBeenCalledWith('generated-assessment'))
    await waitFor(() => expect(adminApi.listAssessmentQuestions).toHaveBeenCalledWith('generated-assessment'))
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: queryKeys.adminAssessmentsRoot })
    expect(adminApi.publishAdminAssessment).not.toHaveBeenCalled()
  })

  it('maps the seven human-readable question controls to exactly the seven canonical values', async () => {
    renderAdmin()
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    const controlMap = [
      ['Multiple Choice', 'multiple_choice'],
      ['Fill in the Blank', 'fill_blank'],
      ['Matching', 'matching'],
      ['Reorder Sentence', 'reorder_sentence'],
      ['Translate Vietnamese → Chinese', 'translate_vi_zh'],
      ['Translate Chinese → Vietnamese', 'translate_zh_vi'],
      ['Sentence Writing', 'sentence_writing'],
    ] as const
    expect(screen.getAllByRole('checkbox')).toHaveLength(controlMap.length)
    for (const [label] of controlMap) {
      const control = screen.getByLabelText(label) as HTMLInputElement
      if (!control.checked) fireEvent.click(control)
      expect(control).toBeChecked()
    }
    expect(controlMap.map(([, canonicalValue]) => canonicalValue)).toEqual([
      'multiple_choice', 'fill_blank', 'matching', 'reorder_sentence', 'translate_vi_zh', 'translate_zh_vi', 'sentence_writing',
    ])
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    await waitFor(() => expect(adminApi.generateAssessmentDraft).toHaveBeenCalledWith(expect.objectContaining({
      type: 'LESSON_EXERCISE', lesson_id: 'lesson-a',
      allowed_types: ['multiple_choice', 'fill_blank', 'matching', 'reorder_sentence', 'translate_vi_zh', 'translate_zh_vi', 'sentence_writing'],
    })))
  })

  it('requires at least one allowed question type', async () => {
    renderAdmin()
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    const onlySelectedType = screen.getByLabelText('Multiple Choice')
    expect(onlySelectedType).toBeChecked()
    fireEvent.click(onlySelectedType)
    expect(onlySelectedType).not.toBeChecked()
    expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeDisabled()
    expect(adminApi.generateAssessmentDraft).not.toHaveBeenCalled()
  })

  it.each([-1, 101])('rejects pass_threshold=%s without sending a generation request', async (threshold) => {
    renderAdmin()
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    fireEvent.change(screen.getByLabelText('Pass threshold'), { target: { value: String(threshold) } })
    expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeDisabled()
    expect(adminApi.generateAssessmentDraft).not.toHaveBeenCalled()
  })

  it.each([0, 100])('accepts pass_threshold=%s at the boundary', async (threshold) => {
    renderAdmin()
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    fireEvent.change(screen.getByLabelText('Pass threshold'), { target: { value: String(threshold) } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    await waitFor(() => expect(adminApi.generateAssessmentDraft).toHaveBeenCalledWith(expect.objectContaining({ pass_threshold: threshold })))
  })

  it('requires a difficulty, then accepts a valid choice when the remaining scope is valid', async () => {
    renderAdmin()
    await openGenerationForm()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    expect(screen.getByLabelText('Difficulty')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeDisabled()
    expect(adminApi.generateAssessmentDraft).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Difficulty'), { target: { value: 'EASY' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    await waitFor(() => expect(adminApi.generateAssessmentDraft).toHaveBeenCalledWith(expect.objectContaining({ difficulty: 'EASY' })))
  })

  it('omits a blank optional title and blank description instead of inventing values', async () => {
    renderAdmin()
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    await waitFor(() => expect(adminApi.generateAssessmentDraft).toHaveBeenCalled())
    const request = vi.mocked(adminApi.generateAssessmentDraft).mock.calls[0][0]
    expect(request).not.toHaveProperty('title')
    expect(request).not.toHaveProperty('description')
    expect(JSON.stringify(request)).not.toContain('Generated assessment')
  })

  it('loads content only for selected Lessons and sends canonical entity IDs for Periodic Test', async () => {
    const { router } = renderAdmin()
    await openGenerationForm()
    fireEvent.change(screen.getByLabelText('Assessment type'), { target: { value: 'PERIODIC_TEST' } })
    await fillCommonFields()
    fireEvent.click(await screen.findByLabelText(/HSK 1 · Lesson 1 · Greetings/))
    await screen.findByLabelText(/你好 \(nǐ hǎo\)/)
    expect(adminApi.listLessonVocabulary).toHaveBeenCalledTimes(1)
    expect(adminApi.listLessonVocabulary).toHaveBeenCalledWith('lesson-a')
    expect(adminApi.listLessonVocabulary).not.toHaveBeenCalledWith('lesson-b')

    fireEvent.click(await screen.findByLabelText(/HSK 1 · Lesson 2 · Names/))
    const sharedItem = await screen.findByLabelText(/你好 \(nǐ hǎo\)/)
    expect(screen.getAllByLabelText(/你好 \(nǐ hǎo\)/)).toHaveLength(1)
    fireEvent.click(sharedItem)
    fireEvent.click(screen.getByLabelText(/A 叫 B/))
    fireEvent.click(screen.getByLabelText(/吗 question/))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))

    await waitFor(() => expect(adminApi.generateAssessmentDraft).toHaveBeenCalledWith({
      type: 'PERIODIC_TEST', lesson_ids: ['lesson-a', 'lesson-b'], vocabulary_ids: ['vocab-shared'],
      grammar_ids: ['grammar-a', 'grammar-b'], pass_threshold: 90, question_count: 1,
      allowed_types: ['multiple_choice'], difficulty: 'MEDIUM',
    }))
    const submitted = vi.mocked(adminApi.generateAssessmentDraft).mock.calls[0][0]
    expect(JSON.stringify(submitted)).not.toContain('association-a-shared')
    expect(JSON.stringify(submitted)).not.toContain('association-b-shared')
    expect(JSON.stringify(submitted)).not.toContain('grammar-association-a')
    await waitFor(() => expect(router.state.location.pathname).toBe('/admin/assessments/generated-assessment'))
  })

  it('deduplicates Grammar by canonical grammar_id rather than Lesson association id', async () => {
    vi.mocked(adminApi.listLessonGrammar).mockImplementation(async (id) => [{
      id: id === 'lesson-a' ? 'grammar-association-a' : 'grammar-association-b',
      grammar_id: 'grammar-shared', name: 'Shared Grammar', structure: 'A + B', explanation: 'Shared rule',
      order_index: 1, note: null, example: null,
    }])
    renderAdmin()
    await openGenerationForm()
    fireEvent.change(screen.getByLabelText('Assessment type'), { target: { value: 'PERIODIC_TEST' } })
    await fillCommonFields()
    fireEvent.click(await screen.findByLabelText(/HSK 1 · Lesson 1 · Greetings/))
    fireEvent.click(await screen.findByLabelText(/HSK 1 · Lesson 2 · Names/))
    const sharedGrammar = await screen.findByLabelText(/Shared Grammar/)
    expect(screen.getAllByLabelText(/Shared Grammar/)).toHaveLength(1)
    fireEvent.click(sharedGrammar)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    await waitFor(() => expect(adminApi.generateAssessmentDraft).toHaveBeenCalledWith(expect.objectContaining({
      lesson_ids: ['lesson-a', 'lesson-b'], vocabulary_ids: [], grammar_ids: ['grammar-shared'],
    })))
    const submitted = vi.mocked(adminApi.generateAssessmentDraft).mock.calls[0][0]
    expect(JSON.stringify(submitted)).not.toContain('grammar-association-a')
    expect(JSON.stringify(submitted)).not.toContain('grammar-association-b')
  })

  it('keeps draft questions out of a local preview and loads canonical editor questions by returned ID', async () => {
    const returned = generatedResult('canonical-question-read-id', [{
      id: 'response-only-question', assessment_id: 'canonical-question-read-id', type: 'multiple_choice',
      prompt: 'Response-only question must not act as editor authority', order_index: 1,
      reference_answer: null, rubric: null, config: null, points: 1, options: [],
    }])
    vi.mocked(adminApi.generateAssessmentDraft).mockResolvedValueOnce(returned)
    const { router } = renderAdmin()
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/admin/assessments/canonical-question-read-id'))
    await waitFor(() => expect(adminApi.listAssessmentQuestions).toHaveBeenCalledWith('canonical-question-read-id'))
    expect(screen.queryByText('Response-only question must not act as editor authority')).not.toBeInTheDocument()
    expect(adminApi.publishAdminAssessment).not.toHaveBeenCalled()
  })

  it('keeps Generate disabled while selected-Lesson discovery is pending', async () => {
    const pendingVocabulary = deferred<LessonVocabulary[]>()
    vi.mocked(adminApi.listLessonVocabulary).mockImplementationOnce(() => pendingVocabulary.promise)
    renderAdmin()
    await openGenerationForm()
    fireEvent.change(screen.getByLabelText('Assessment type'), { target: { value: 'PERIODIC_TEST' } })
    await fillCommonFields()
    fireEvent.click(await screen.findByLabelText(/HSK 1 · Lesson 1 · Greetings/))
    expect(await screen.findByText(/Loading selected Lesson content/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeDisabled()
    expect(adminApi.generateAssessmentDraft).not.toHaveBeenCalled()
    pendingVocabulary.resolve(vocabularyA)
    expect(await screen.findByLabelText(/你好/)).toBeInTheDocument()
    expect(adminApi.generateAssessmentDraft).not.toHaveBeenCalled()
  })

  it('prunes content IDs that no longer belong to selected Lessons', async () => {
    renderAdmin()
    await openGenerationForm()
    fireEvent.change(screen.getByLabelText('Assessment type'), { target: { value: 'PERIODIC_TEST' } })
    await fillCommonFields()
    fireEvent.click(await screen.findByLabelText(/HSK 1 · Lesson 1 · Greetings/))
    fireEvent.click(await screen.findByLabelText(/HSK 1 · Lesson 2 · Names/))
    fireEvent.click(await screen.findByLabelText(/再见/))
    fireEvent.click(screen.getByLabelText(/A 叫 B/))
    fireEvent.click(screen.getByLabelText(/HSK 1 · Lesson 1 · Greetings/))
    fireEvent.click(await screen.findByLabelText(/你好 \(nǐ hǎo\)/))
    fireEvent.click(screen.getByLabelText(/吗 question/))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    await waitFor(() => expect(adminApi.generateAssessmentDraft).toHaveBeenCalledWith(expect.objectContaining({
      type: 'PERIODIC_TEST', lesson_ids: ['lesson-b'], vocabulary_ids: ['vocab-shared'], grammar_ids: ['grammar-b'],
    })))
  })

  it('prevents invalid settings and duplicate requests while pending, then navigates to the canonical editor', async () => {
    let resolveGeneration!: (value: GenerationResult) => void
    vi.mocked(adminApi.generateAssessmentDraft).mockImplementationOnce(() => new Promise((resolve) => { resolveGeneration = resolve }))
    renderAdmin()
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    fireEvent.change(screen.getByLabelText('Question count'), { target: { value: '11' } })
    expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Question count'), { target: { value: '1' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    expect(await screen.findByRole('button', { name: 'Generating draft…' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Close AI Draft Form' }))
    expect(adminApi.generateAssessmentDraft).toHaveBeenCalledTimes(1)
    resolveGeneration(generatedResult('canonical-editor-id'))
    expect(await screen.findByRole('heading', { name: 'Admin Assessment Editor' })).toBeInTheDocument()
    await waitFor(() => expect(adminApi.getAdminAssessment).toHaveBeenCalledWith('canonical-editor-id'))
  })

  it('maps generation errors without clearing user input and requires an explicit retry', async () => {
    vi.mocked(adminApi.generateAssessmentDraft)
      .mockRejectedValueOnce(new ApiError({ status: 503, code: 'AI_GENERATION_UNAVAILABLE', message: 'raw provider detail', details: null }))
      .mockResolvedValueOnce(generatedResult())
    renderAdmin()
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    fireEvent.change(screen.getByLabelText('Title (optional)'), { target: { value: 'Keep this title' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('AI generation is temporarily unavailable. You can explicitly retry.')
    expect(screen.getByRole('alert')).not.toHaveTextContent('raw provider detail')
    expect(screen.getByLabelText('Title (optional)')).toHaveValue('Keep this title')
    expect(adminApi.generateAssessmentDraft).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    expect(await screen.findByRole('heading', { name: 'Admin Assessment Editor' })).toBeInTheDocument()
    expect(adminApi.generateAssessmentDraft).toHaveBeenCalledTimes(2)
  })

  it.each([
    ['INVALID_REQUEST', 422, 'Check the generation settings and try again.'],
    ['INVALID_GENERATION_SCOPE', 422, 'Review the selected Lessons, Vocabulary, and Grammar, then try again.'],
    ['AI_GENERATION_INPUT_TOO_LARGE', 422, 'The selected generation scope is too large. Reduce the selected Lessons or content items.'],
    ['AI_GENERATION_INVALID_OUTPUT', 502, 'AI generation returned an invalid result. Review the settings and explicitly retry.'],
    ['AI_GENERATION_UNAVAILABLE', 503, 'AI generation is temporarily unavailable. You can explicitly retry.'],
    ['AI_GENERATION_PERSISTENCE_FAILED', 500, 'The generated draft could not be saved. No draft was created; you can explicitly retry.'],
    ['ADMIN_REQUIRED', 403, 'Your account does not have Admin access.'],
  ])('maps %s to safe UI text without automatic replay', async (code, status, message) => {
    vi.mocked(adminApi.generateAssessmentDraft).mockRejectedValueOnce(new ApiError({
      status, code, message: 'private provider detail', details: { trace: 'private' },
    }))
    renderAdmin()
    await openGenerationForm()
    await fillCommonFields()
    fireEvent.change(screen.getByLabelText('Lesson', { selector: 'select' }), { target: { value: 'lesson-a' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(message)
    expect(alert).not.toHaveTextContent('private provider detail')
    expect(alert).not.toHaveTextContent('private')
    expect(adminApi.generateAssessmentDraft).toHaveBeenCalledTimes(1)
  })

  it('retains the selected Lesson and blocks generation until per-Lesson discovery can be retried', async () => {
    vi.mocked(adminApi.listLessonVocabulary)
      .mockRejectedValueOnce(new Error('temporary discovery issue'))
      .mockResolvedValue(vocabularyA)
    renderAdmin()
    await openGenerationForm()
    fireEvent.change(screen.getByLabelText('Assessment type'), { target: { value: 'PERIODIC_TEST' } })
    await fillCommonFields()
    fireEvent.click(await screen.findByLabelText(/HSK 1 · Lesson 1 · Greetings/))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load Vocabulary for the selected Lesson.')
    expect(screen.getByLabelText(/HSK 1 · Lesson 1 · Greetings/)).toBeChecked()
    expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry Vocabulary' }))
    expect(await screen.findByLabelText(/你好 \(nǐ hǎo\)/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate Draft' })).toBeDisabled()
    fireEvent.click(screen.getByLabelText(/你好 \(nǐ hǎo\)/))
    fireEvent.click(screen.getByRole('button', { name: 'Generate Draft' }))
    expect(await screen.findByRole('heading', { name: 'Admin Assessment Editor' })).toBeInTheDocument()
    expect(adminApi.listLessonGrammar).toHaveBeenCalledWith('lesson-a')
  })
})
