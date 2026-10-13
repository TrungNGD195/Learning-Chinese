import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { authApi } from '../auth/api'
import { createAppRoutes } from '../../app/router/routes'
import * as api from './api'
import {
  invalidateAssessmentLifecycle, invalidateCurriculumOrder, invalidateHskMetadata,
  invalidateLessonContent, invalidateLessonLifecycle,
} from './invalidation'

vi.mock('./api', () => Object.fromEntries([
  'listHskLevels', 'updateHskLevel', 'getAdminCurriculum', 'replaceAdminCurriculum',
  'listAdminLessons', 'getAdminLesson', 'createAdminLesson', 'updateAdminLesson', 'publishAdminLesson', 'archiveAdminLesson',
  'listLessonVocabulary', 'attachVocabulary', 'updateLessonVocabulary', 'detachVocabulary',
  'listLessonGrammar', 'attachGrammar', 'updateLessonGrammar', 'detachGrammar',
  'listAdminAssessments', 'getAdminAssessment', 'createAdminAssessment', 'updateAdminAssessment',
  'listAssessmentQuestions', 'createAssessmentQuestion', 'updateAssessmentQuestion', 'deleteAssessmentQuestion',
  'submitAssessmentReview', 'publishAdminAssessment', 'archiveAdminAssessment', 'getAdminStats',
  'listAdminDocuments', 'getAdminDocument', 'getAdminDocumentPreview', 'uploadDocument',
  'processAdminDocument', 'approveAdminDocument', 'rejectAdminDocument', 'retryAdminDocumentKnowledge',
].map((name) => [name, vi.fn()])))

vi.mock('../auth/api', () => ({ authApi: {
  register: vi.fn(), login: vi.fn(), getMe: vi.fn(), refresh: vi.fn(), logout: vi.fn(), logoutAll: vi.fn(),
  changePassword: vi.fn(), requestPasswordReset: vi.fn(), confirmPasswordReset: vi.fn(),
} }))

const admin = { id: 'admin-id', email: 'admin@example.test', full_name: 'Admin', role: 'ADMIN' as const }
const learner = { ...admin, id: 'learner-id', role: 'LEARNER' as const }
const level = { id: 'hsk-1', level_number: 1, title: 'Starter', description: 'Basic level', order_index: 1 }
const lesson = { id: 'lesson-1', hsk_level_id: level.id, lesson_number: 1, title: 'Greetings', description: 'Say hello', status: 'DRAFT' as const, published_at: null }
const publishedCandidateLesson = { id: 'lesson-candidate', hsk_level_id: level.id, lesson_number: 2, title: 'Family words', description: null, status: 'PUBLISHED' as const, published_at: '2026-10-13T00:00:00Z' }
const assessment = { id: 'assessment-1', type: 'PERIODIC_TEST' as const, lesson_id: null, title: 'HSK Test', description: null, status: 'DRAFT' as const, pass_threshold: 90, published_at: null }
const publishedCandidateTest = { id: 'assessment-candidate', type: 'PERIODIC_TEST' as const, lesson_id: null, title: 'Published test', description: null, status: 'PUBLISHED' as const, pass_threshold: 90, published_at: '2026-10-13T00:00:00Z' }
const question = { id: 'question-1', assessment_id: assessment.id, type: 'sentence_writing' as const, prompt: 'Write a sentence', order_index: 1, reference_answer: null, rubric: null, config: null, points: 1, options: [] }
type AdminQuestion = Awaited<ReturnType<typeof api.listAssessmentQuestions>>[number]
const curriculum = [
  { id: 'unit-1', unit_type: 'LESSON' as const, lesson_id: lesson.id, assessment_id: null, lesson_title: lesson.title, assessment_title: null, order_index: 1 },
  { id: 'unit-2', unit_type: 'PERIODIC_TEST' as const, lesson_id: null, assessment_id: assessment.id, lesson_title: null, assessment_title: assessment.title, order_index: 2 },
]

function apiError(status: number, code: string) { return new ApiError({ status, code, message: 'test error', details: null }) }

function renderAt(path: string, user: typeof admin | typeof learner = admin) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  client.setQueryDefaults(queryKeys.authMe, { staleTime: Infinity })
  client.setQueryData(queryKeys.authMe, user)
  const router = createMemoryRouter(createAppRoutes(), { initialEntries: [path] })
  const view = render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
  return { ...view, client, router }
}

function fill(label: string, value: string) { fireEvent.change(screen.getByLabelText(label), { target: { value } }) }

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.listHskLevels).mockResolvedValue([level])
  vi.mocked(api.updateHskLevel).mockResolvedValue(level)
  vi.mocked(api.getAdminCurriculum).mockResolvedValue(curriculum)
  vi.mocked(api.replaceAdminCurriculum).mockResolvedValue(curriculum)
  vi.mocked(api.listAdminLessons).mockResolvedValue({ items: [lesson], page: 1, page_size: 20, total: 1 })
  vi.mocked(api.getAdminLesson).mockResolvedValue(lesson)
  vi.mocked(api.createAdminLesson).mockResolvedValue(lesson)
  vi.mocked(api.updateAdminLesson).mockResolvedValue(lesson)
  vi.mocked(api.publishAdminLesson).mockResolvedValue({ ...lesson, status: 'PUBLISHED' })
  vi.mocked(api.archiveAdminLesson).mockResolvedValue({ ...lesson, status: 'ARCHIVED' })
  vi.mocked(api.listLessonVocabulary).mockResolvedValue([])
  vi.mocked(api.attachVocabulary).mockResolvedValue({ id: 'vocab-link', vocabulary_id: 'vocab-id', hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', part_of_speech: null, order_index: 1, note: null, example: null, grammar_id: null, name: null, structure: null, explanation: null, usage: null })
  vi.mocked(api.updateLessonVocabulary).mockResolvedValue({ id: 'vocab-link', vocabulary_id: 'vocab-id', hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', part_of_speech: null, order_index: 1, note: null, example: null, grammar_id: null, name: null, structure: null, explanation: null, usage: null })
  vi.mocked(api.detachVocabulary).mockResolvedValue(undefined)
  vi.mocked(api.listLessonGrammar).mockResolvedValue([])
  vi.mocked(api.attachGrammar).mockResolvedValue({ id: 'grammar-link', vocabulary_id: null, hanzi: null, pinyin: null, vietnamese_meaning: null, part_of_speech: null, order_index: 1, note: null, example: null, grammar_id: 'grammar-id', name: 'A-not-A', structure: 'A 不 A', explanation: 'Choice question', usage: null })
  vi.mocked(api.updateLessonGrammar).mockResolvedValue({ id: 'grammar-link', vocabulary_id: null, hanzi: null, pinyin: null, vietnamese_meaning: null, part_of_speech: null, order_index: 1, note: null, example: null, grammar_id: 'grammar-id', name: 'A-not-A', structure: 'A 不 A', explanation: 'Choice question', usage: null })
  vi.mocked(api.detachGrammar).mockResolvedValue(undefined)
  vi.mocked(api.listAdminAssessments).mockResolvedValue({ items: [], page: 1, page_size: 20, total: 0 })
  vi.mocked(api.getAdminAssessment).mockResolvedValue(assessment)
  vi.mocked(api.createAdminAssessment).mockResolvedValue(assessment)
  vi.mocked(api.updateAdminAssessment).mockResolvedValue(assessment)
  vi.mocked(api.listAssessmentQuestions).mockResolvedValue([])
  vi.mocked(api.createAssessmentQuestion).mockResolvedValue(question)
  vi.mocked(api.updateAssessmentQuestion).mockResolvedValue(question)
  vi.mocked(api.deleteAssessmentQuestion).mockResolvedValue(undefined)
  vi.mocked(api.submitAssessmentReview).mockResolvedValue({ ...assessment, status: 'REVIEW' })
  vi.mocked(api.publishAdminAssessment).mockResolvedValue({ ...assessment, status: 'PUBLISHED' })
  vi.mocked(api.archiveAdminAssessment).mockResolvedValue({ ...assessment, status: 'ARCHIVED' })
  vi.mocked(api.getAdminStats).mockResolvedValue({ total_users: 8, users_by_current_hsk: [{ hsk_level: 1, users: 3 }], average_exercise_score: 82.5 })
  vi.mocked(api.listAdminDocuments).mockResolvedValue({ items: [], page: 1, page_size: 20, total: 0 })
})

afterEach(() => vi.restoreAllMocks())

describe('Step 4.7 Admin routes and authorization', () => {
  it('shows Dashboard as a small entry surface and adds Curriculum navigation', () => {
    renderAt('/admin')
    const nav = screen.getByRole('navigation', { name: 'Admin navigation' })
    expect(within(nav).getAllByRole('link').map((link) => link.textContent)).toEqual(['Dashboard', 'Curriculum', 'Lessons', 'Assessments', 'Documents', 'Stats'])
    expect(screen.getByRole('link', { name: /Edit HSK display metadata/ })).toHaveAttribute('href', '/admin/curriculum')
    expect(screen.queryByText(/Total Users/)).not.toBeInTheDocument()
  })

  it('keeps an authenticated Learner on the D-041 Forbidden page', () => {
    renderAt('/admin/curriculum', learner)
    expect(screen.getByTestId('admin-forbidden')).toBeInTheDocument()
    expect(api.listHskLevels).not.toHaveBeenCalled()
  })

  it('renders ADMIN_REQUIRED without logging out or clearing current User', async () => {
    vi.mocked(api.listHskLevels).mockRejectedValueOnce(apiError(403, 'ADMIN_REQUIRED'))
    const { client, router } = renderAt('/admin/curriculum')
    expect(await screen.findByRole('alert')).toHaveTextContent('Your account does not have Admin access.')
    expect(authApi.logout).not.toHaveBeenCalled()
    expect(client.getQueryData(queryKeys.authMe)).toEqual(admin)
    expect(router.state.location.pathname).toBe('/admin/curriculum')
  })

  it('renders the real Documents list and upload entry', async () => {
    renderAt('/admin/documents')
    expect(await screen.findByRole('heading', { name: 'Upload a source document' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload document' })).toBeDisabled()
    expect(screen.queryByText('Document management will be implemented in Phase 5.')).not.toBeInTheDocument()
  })
})

describe('HSK and curriculum editing', () => {
  it('loads fixed HSK levels and sends only metadata fields with duplicate-submit protection', async () => {
    vi.mocked(api.updateHskLevel).mockImplementationOnce(() => new Promise(() => {}))
    const { client } = renderAt('/admin/curriculum')
    expect(await screen.findByText('HSK 1 metadata')).toBeInTheDocument()
    expect(screen.queryByLabelText(/level number|order index/i)).not.toBeInTheDocument()
    fill('Title', 'HSK One')
    const save = screen.getByRole('button', { name: 'Save HSK metadata' })
    await waitFor(() => expect(save).toBeEnabled())
    fireEvent.click(save)
    await waitFor(() => expect(save).toBeDisabled())
    fireEvent.click(save)
    expect(api.updateHskLevel).toHaveBeenCalledTimes(1)
    expect(api.updateHskLevel).toHaveBeenCalledWith(level.id, { title: 'HSK One', description: level.description })
    client.setQueryData(['unrelated', 'chat'], { kept: true })
    expect(client.getQueryData(['unrelated', 'chat'])).toEqual({ kept: true })
    expect(client.getQueryData(queryKeys.authMe)).toEqual(admin)
  })

  it('reorders canonical membership, normalizes 1..N, confirms, PUTs the exact body and refetches', async () => {
    const confirm = vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    vi.mocked(api.getAdminCurriculum).mockResolvedValueOnce(curriculum).mockResolvedValueOnce([curriculum[1], curriculum[0]])
    renderAt('/admin/curriculum')
    expect(await screen.findByText(/1\. Lesson: Greetings/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Move HSK Test up' }))
    expect(screen.getByText(/1\. Periodic test: HSK Test/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Save curriculum' }))
    expect(confirm).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(1))
    expect(api.replaceAdminCurriculum).toHaveBeenCalledWith(level.id, { units: [
      { unit_type: 'PERIODIC_TEST', target_id: assessment.id, order_index: 1 },
      { unit_type: 'LESSON', target_id: lesson.id, order_index: 2 },
    ] })
    await waitFor(() => expect(api.getAdminCurriculum).toHaveBeenCalledTimes(2))
    expect(confirm).toHaveBeenCalled()
  })

  it('preserves a dirty reorder draft through background refetch and retains it after save failure', async () => {
    vi.mocked(api.replaceAdminCurriculum).mockRejectedValue(apiError(422, 'INVALID_CURRICULUM'))
    const { client } = renderAt('/admin/curriculum')
    expect(await screen.findByText(/1\. Lesson: Greetings/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Move HSK Test up' }))
    await act(async () => { await client.invalidateQueries({ queryKey: queryKeys.adminCurriculum(level.id) }) })
    expect(screen.getByText(/1\. Periodic test: HSK Test/)).toBeInTheDocument()
    vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    fireEvent.click(screen.getByRole('button', { name: 'Save curriculum' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('The curriculum order is invalid.')
    expect(screen.getByText(/1\. Periodic test: HSK Test/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove Greetings from curriculum' })).toBeInTheDocument()
  })

  it('adds published Lesson and Periodic Test candidates, detaches locally, reorders, and PUTs full canonical membership', async () => {
    const confirm = vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    const canonical = [
      { id: 'server-unit-a', unit_type: 'LESSON' as const, lesson_id: publishedCandidateLesson.id, assessment_id: null, lesson_title: publishedCandidateLesson.title, assessment_title: null, order_index: 1 },
      { id: 'server-unit-b', unit_type: 'PERIODIC_TEST' as const, lesson_id: null, assessment_id: assessment.id, lesson_title: null, assessment_title: assessment.title, order_index: 2 },
      { id: 'server-unit-c', unit_type: 'PERIODIC_TEST' as const, lesson_id: null, assessment_id: publishedCandidateTest.id, lesson_title: null, assessment_title: publishedCandidateTest.title, order_index: 3 },
    ]
    vi.mocked(api.listAdminLessons).mockResolvedValue({ items: [
      lesson, publishedCandidateLesson, { ...lesson, id: 'archived-lesson', title: 'Archived lesson', status: 'ARCHIVED' },
    ], page: 1, page_size: 20, total: 3 })
    vi.mocked(api.listAdminAssessments).mockResolvedValue({ items: [
      publishedCandidateTest, { ...publishedCandidateTest, id: 'draft-test', title: 'Draft test', status: 'DRAFT' },
      { ...publishedCandidateTest, id: 'published-exercise', type: 'LESSON_EXERCISE', title: 'Published exercise' },
    ], page: 1, page_size: 20, total: 3 })
    vi.mocked(api.replaceAdminCurriculum).mockResolvedValue(canonical)
    vi.mocked(api.getAdminCurriculum).mockResolvedValueOnce(curriculum).mockResolvedValueOnce(canonical)
    const { client } = renderAt('/admin/curriculum')
    const invalidate = vi.spyOn(client, 'invalidateQueries')

    expect(await screen.findByRole('button', { name: 'Add Family words to curriculum' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Add Published test to curriculum' })).toBeInTheDocument()
    expect(api.listAdminLessons).toHaveBeenCalledWith({ page: 1, page_size: 20, status: 'PUBLISHED', hsk_level_id: level.id })
    expect(api.listAdminAssessments).toHaveBeenCalledWith({ page: 1, page_size: 20, status: 'PUBLISHED', assessment_type: 'PERIODIC_TEST' })
    expect(screen.queryByText('Draft test')).not.toBeInTheDocument()
    expect(screen.queryByText('Published exercise')).not.toBeInTheDocument()
    expect(screen.queryByText('Archived lesson')).not.toBeInTheDocument()
    expect(screen.queryByText('unit-1')).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/target id/i)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Remove Greetings from curriculum' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add Family words to curriculum' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add Published test to curriculum' }))
    expect(api.replaceAdminCurriculum).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Move Family words up' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save curriculum' }))
    expect(confirm).toHaveBeenCalledWith('Save this curriculum membership and order?')
    await waitFor(() => expect(api.replaceAdminCurriculum).toHaveBeenCalledWith(level.id, { units: [
      { unit_type: 'LESSON', target_id: publishedCandidateLesson.id, order_index: 1 },
      { unit_type: 'PERIODIC_TEST', target_id: assessment.id, order_index: 2 },
      { unit_type: 'PERIODIC_TEST', target_id: publishedCandidateTest.id, order_index: 3 },
    ] }))
    await waitFor(() => expect(api.getAdminCurriculum).toHaveBeenCalledTimes(2))
    for (const key of [
      queryKeys.adminCurriculum(level.id), queryKeys.curriculumLevels, queryKeys.curriculumHsk(level.id),
      queryKeys.progressOverview, queryKeys.progressHsk(level.id), queryKeys.dashboard,
    ]) expect(invalidate).toHaveBeenCalledWith({ queryKey: key })
    expect(screen.getByText(/1\. Lesson: Family words/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save curriculum' })).toBeDisabled()
  })

  it('keeps the local membership draft after a failed PUT and retries only after an explicit click', async () => {
    vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    vi.mocked(api.listAdminLessons).mockResolvedValue({ items: [publishedCandidateLesson], page: 1, page_size: 20, total: 1 })
    vi.mocked(api.replaceAdminCurriculum).mockRejectedValueOnce(apiError(422, 'INVALID_CURRICULUM_TARGET'))
    renderAt('/admin/curriculum')
    fireEvent.click(await screen.findByRole('button', { name: 'Add Family words to curriculum' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save curriculum' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('A curriculum item is no longer available.')
    expect(screen.getByRole('button', { name: 'Remove Family words from curriculum' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save curriculum' })).toBeEnabled()
    expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Save curriculum' }))
    await waitFor(() => expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(2))
  })

  it('prevents duplicate saves while pending and preserves draft across candidate page changes', async () => {
    vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    let resolveSave!: (value: typeof curriculum) => void
    vi.mocked(api.replaceAdminCurriculum).mockReturnValueOnce(new Promise((resolve) => { resolveSave = resolve }))
    vi.mocked(api.listAdminLessons).mockImplementation(async (filters) => ({
      items: filters.page === 1 ? [publishedCandidateLesson] : [], page: filters.page ?? 1, page_size: 20, total: 21,
    }))
    const { client } = renderAt('/admin/curriculum')
    fireEvent.click(await screen.findByRole('button', { name: 'Add Family words to curriculum' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next Lesson candidates' }))
    expect(await screen.findByText('Lesson candidate page 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove Family words from curriculum' })).toBeInTheDocument()
    expect(api.listAdminLessons).toHaveBeenCalledTimes(2)
    fireEvent.click(screen.getByRole('button', { name: 'Save curriculum' }))
    const save = await screen.findByRole('button', { name: /Saving curriculum/ })
    expect(save).toBeDisabled()
    fireEvent.click(save)
    expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(1)
    resolveSave(curriculum)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save curriculum' })).toBeDisabled())
    expect(client.getQueryData(queryKeys.adminCurriculum(level.id))).toEqual(curriculum)
  })
})

describe('Lesson list, canonical editor, lifecycle and content', () => {
  it('filters and paginates the lesson list, creates exact payload without status, then opens canonical detail', async () => {
    vi.mocked(api.listAdminLessons).mockResolvedValue({ items: [lesson], page: 1, page_size: 20, total: 40 })
    const { router } = renderAt('/admin/lessons')
    expect(await screen.findByText('Greetings')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'DRAFT' } })
    fireEvent.change(screen.getAllByLabelText('HSK', { selector: 'select' }).at(-1)!, { target: { value: level.id } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(api.listAdminLessons).toHaveBeenCalledWith({ page: 2, page_size: 20, status: 'DRAFT', hsk_level_id: level.id }))
    fireEvent.click(screen.getAllByRole('button', { name: 'Create Lesson' }).at(-1)!)
    fill('Lesson number', '2'); fill('Title', 'Introduce yourself'); fill('Description', '');
    fireEvent.change(screen.getAllByLabelText('HSK', { selector: 'select' }).at(-1)!, { target: { value: level.id } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Lesson' }))
    await waitFor(() => expect(api.createAdminLesson).toHaveBeenCalledWith({ hsk_level_id: level.id, lesson_number: 2, title: 'Introduce yourself' }))
    await waitFor(() => expect(router.state.location.pathname).toBe(`/admin/lessons/${lesson.id}`))
  })

  it('loads the Lesson editor by canonical GET, edits Published metadata, and archives only after confirmation', async () => {
    vi.mocked(api.getAdminLesson).mockResolvedValue({ ...lesson, status: 'PUBLISHED' })
    const confirm = vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByText('HSK 1')).toBeInTheDocument()
    expect(api.getAdminLesson).toHaveBeenCalledWith(lesson.id)
    expect(screen.queryByLabelText('HSK level id')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Lesson number')).not.toBeInTheDocument()
    fill('Title', 'Greetings revised')
    fireEvent.click(screen.getByRole('button', { name: 'Save metadata' }))
    await waitFor(() => expect(api.updateAdminLesson).toHaveBeenCalledWith(lesson.id, { title: 'Greetings revised', description: lesson.description }))
    expect(screen.getByRole('button', { name: 'Archive Lesson' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Archive Lesson' }))
    expect(confirm).toHaveBeenCalledWith('Archive this lesson?')
    await waitFor(() => expect(api.archiveAdminLesson).toHaveBeenCalledWith(lesson.id))
    expect(api.publishAdminLesson).not.toHaveBeenCalled()
  })

  it('publishes a Draft Lesson and shows content actions without detach', async () => {
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('button', { name: 'Publish Lesson' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create and attach vocabulary' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create and attach grammar' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Detach vocabulary|Detach grammar/i })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Publish Lesson' }))
    await waitFor(() => expect(api.publishAdminLesson).toHaveBeenCalledTimes(1))
  })

  it('creates and attaches Vocabulary without an existing UUID field and keeps canonical/association groups separate', async () => {
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: 'Vocabulary' })).toBeInTheDocument()
    const vocabularySection = screen.getByRole('region', { name: 'Lesson vocabulary' })
    fill('Hanzi', '你好'); fill('Pinyin', 'nǐ hǎo'); fill('Vietnamese meaning', 'xin chào'); fireEvent.change(within(vocabularySection).getByLabelText('Order'), { target: { value: '3' } }); fireEvent.change(within(vocabularySection).getByLabelText('Note'), { target: { value: 'greeting' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create and attach vocabulary' }))
    await waitFor(() => expect(api.attachVocabulary).toHaveBeenCalledWith(lesson.id, {
      hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', order_index: 3, note: 'greeting',
    }))
    expect(screen.queryByLabelText(/vocabulary id/i)).not.toBeInTheDocument()
    expect(within(vocabularySection).getByText('Lesson association')).toBeInTheDocument()
  })

  it('does not expose detach on Published Lessons and permits Grammar content updates', async () => {
    vi.mocked(api.getAdminLesson).mockResolvedValue({ ...lesson, status: 'PUBLISHED' })
    vi.mocked(api.listLessonGrammar).mockResolvedValue([{ id: 'grammar-link', vocabulary_id: null, hanzi: null, pinyin: null, vietnamese_meaning: null, part_of_speech: null, order_index: 1, note: null, example: null, grammar_id: 'grammar-id', name: 'A-not-A', structure: 'A 不 A', explanation: 'Choice question', usage: null }])
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByText('A-not-A')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Detach grammar' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Edit content and placement' }))
    fireEvent.change(screen.getAllByLabelText('Name').at(0)!, { target: { value: 'A-not-A revised' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save content changes' }))
    await waitFor(() => expect(api.updateLessonGrammar).toHaveBeenCalledWith(lesson.id, 'grammar-link', expect.objectContaining({ name: 'A-not-A revised', order_index: 1 })))
  })
})

describe('Assessment metadata, lifecycle, questions and Stats', () => {
  it('creates a Lesson Exercise from a readable paginated Lesson selector with exact payload', async () => {
    renderAt('/admin/assessments')
    fireEvent.click(screen.getByRole('button', { name: 'Create Assessment' }))
    expect(await screen.findByRole('option', { name: 'HSK 1 · Lesson 1 · Greetings' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Lesson'), { target: { value: lesson.id } })
    fill('Title', 'Lesson practice'); fill('Description', ''); fill('Pass threshold', '85')
    fireEvent.click(screen.getByRole('button', { name: 'Create Assessment' }))
    await waitFor(() => expect(api.createAdminAssessment).toHaveBeenCalledWith({ type: 'LESSON_EXERCISE', lesson_id: lesson.id, title: 'Lesson practice', pass_threshold: 85 }))
  })

  it('creates PERIODIC_TEST without deferred scope fields', async () => {
    renderAt('/admin/assessments')
    fireEvent.click(screen.getByRole('button', { name: 'Create Assessment' }))
    fireEvent.change(screen.getAllByLabelText('Type').at(-1)!, { target: { value: 'PERIODIC_TEST' } })
    fill('Title', 'Periodic test'); fill('Pass threshold', '90')
    fireEvent.click(screen.getAllByRole('button', { name: 'Create Assessment' }).at(-1)!)
    await waitFor(() => expect(api.createAdminAssessment).toHaveBeenCalledWith({ type: 'PERIODIC_TEST', title: 'Periodic test', pass_threshold: 90 }))
    const payload = vi.mocked(api.createAdminAssessment).mock.calls[0]?.[0]
    expect(payload).not.toHaveProperty('lesson_id')
    expect(payload).not.toHaveProperty('lesson_ids')
    expect(payload).not.toHaveProperty('vocabulary_ids')
    expect(payload).not.toHaveProperty('grammar_ids')
  })

  it('loads assessment detail directly and sends only visible metadata fields on PERIODIC_TEST PATCH', async () => {
    renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText('Status: DRAFT')).toBeInTheDocument()
    expect(api.getAdminAssessment).toHaveBeenCalledWith(assessment.id)
    fill('Title', 'HSK Test Revised')
    fireEvent.click(screen.getByRole('button', { name: 'Save metadata' }))
    await waitFor(() => expect(api.updateAdminAssessment).toHaveBeenCalledWith(assessment.id, { title: 'HSK Test Revised', description: null, pass_threshold: 90 }))
    const patchBody = vi.mocked(api.updateAdminAssessment).mock.calls[0]?.[1]
    for (const deferred of ['lesson_ids', 'vocabulary_ids', 'grammar_ids']) expect(patchBody).not.toHaveProperty(deferred)
  })

  it('requires a Question before Review and follows the legal Assessment lifecycle', async () => {
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([question])
    vi.mocked(api.submitAssessmentReview).mockResolvedValue({ ...assessment, status: 'REVIEW' })
    const { client } = renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByRole('button', { name: 'Submit Review' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Submit Review' }))
    await waitFor(() => expect(api.submitAssessmentReview).toHaveBeenCalledWith(assessment.id))
    client.setQueryData(queryKeys.adminAssessment(assessment.id), { ...assessment, status: 'REVIEW' })
  })

  it('walks the remaining Assessment lifecycle using canonical refetch and archive confirmation', async () => {
    const confirm = vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([question])
    vi.mocked(api.getAdminAssessment)
      .mockResolvedValueOnce(assessment)
      .mockResolvedValueOnce({ ...assessment, status: 'REVIEW' })
      .mockResolvedValueOnce({ ...assessment, status: 'PUBLISHED' })
      .mockResolvedValueOnce({ ...assessment, status: 'ARCHIVED' })
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: 'Submit Review' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Publish Assessment' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Archive Assessment' }))
    expect(confirm).toHaveBeenCalledWith('Archive this assessment?')
    await waitFor(() => expect(api.archiveAdminAssessment).toHaveBeenCalledWith(assessment.id))
    expect(await screen.findByText('Status: ARCHIVED')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Submit Review|Publish Assessment|Archive Assessment/ })).not.toBeInTheDocument()
  })

  it('renders backend Stats exactly with empty and null states', async () => {
    vi.mocked(api.getAdminStats).mockResolvedValueOnce({ total_users: 11, users_by_current_hsk: [], average_exercise_score: null })
    renderAt('/admin/stats')
    expect(await screen.findByText('11')).toBeInTheDocument()
    expect(screen.getByText('No learner HSK data yet.')).toBeInTheDocument()
    expect(screen.getByText('No graded lesson-exercise attempts yet.')).toBeInTheDocument()
    expect(api.getAdminStats).toHaveBeenCalledTimes(1)
  })

  it('renders non-empty Stats aggregates exactly as returned by the backend', async () => {
    vi.mocked(api.getAdminStats).mockResolvedValueOnce({ total_users: 8, users_by_current_hsk: [{ hsk_level: 1, users: 3 }, { hsk_level: 2, users: 5 }], average_exercise_score: 82.5 })
    renderAt('/admin/stats')
    expect(await screen.findByText('8')).toBeInTheDocument()
    expect(screen.getByRole('row', { name: 'HSK 1 3' })).toBeInTheDocument()
    expect(screen.getByRole('row', { name: 'HSK 2 5' })).toBeInTheDocument()
    expect(screen.getByText('82.5%')).toBeInTheDocument()
  })
})

describe('type-specific Question editors', () => {
  async function openQuestionForm(type?: string) {
    vi.mocked(api.getAdminAssessment).mockResolvedValue(assessment)
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([])
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: 'Add Question' }))
    if (type) fireEvent.change(screen.getByLabelText('Question type'), { target: { value: type } })
    fill('Prompt', 'Question prompt')
  }

  it('creates multiple choice with option rows and exactly one correct option', async () => {
    await openQuestionForm()
    fill('Option 1', 'A'); fill('Option 2', 'B')
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.createAssessmentQuestion).toHaveBeenCalledWith(assessment.id, {
      type: 'multiple_choice', prompt: 'Question prompt', order_index: 1, points: 1,
      options: [{ option_text: 'A', is_correct: true }, { option_text: 'B', is_correct: false }],
    }))
  })

  it('creates fill blank with reference answer and accepted_answers config', async () => {
    await openQuestionForm('fill_blank')
    fill('Reference answer', '你好'); fill('Accepted answers (one per line)', '您好\n你们好')
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.createAssessmentQuestion).toHaveBeenCalledWith(assessment.id, expect.objectContaining({ type: 'fill_blank', reference_answer: '你好', config: { accepted_answers: ['您好', '你们好'] } })))
  })

  it('creates Matching with opaque item IDs and explicit pairs', async () => {
    await openQuestionForm('matching')
    fireEvent.click(screen.getByRole('button', { name: 'Add left item' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add right item' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add left item' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add right item' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add left item' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add right item' }))
    fill('Left item 1', '你'); fill('Left item 2', '好'); fill('Right item 1', 'you'); fill('Right item 2', 'good')
    const pairs = screen.getAllByLabelText(/Pair for/)
    fireEvent.change(pairs[0]!, { target: { value: pairs[0]!.querySelector('option:nth-child(2)')?.getAttribute('value') } })
    fireEvent.change(pairs[1]!, { target: { value: pairs[1]!.querySelector('option:nth-child(3)')?.getAttribute('value') } })
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.createAssessmentQuestion).toHaveBeenCalledTimes(1))
    const payload = vi.mocked(api.createAssessmentQuestion).mock.calls[0]![1]
    expect(payload.type).toBe('matching')
    const config = payload.config
    expect(config && 'left_items' in config ? config.left_items[0]?.id : '').toMatch(/^[\w-]+$/)
    expect(config && 'correct_pairs' in config ? config.correct_pairs : []).toHaveLength(2)
  })

  it('keeps existing Matching IDs when editing text', async () => {
    const matching = { ...question, type: 'matching' as const, config: { left_items: [{ id: 'left-a', text: 'old left' }], right_items: [{ id: 'right-a', text: 'old right' }], correct_pairs: [{ left_id: 'left-a', right_id: 'right-a' }] } }
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([matching])
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: 'Edit question' }))
    fill('Left item 1', 'new left')
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.updateAssessmentQuestion).toHaveBeenCalledWith(assessment.id, matching.id, expect.objectContaining({ config: { left_items: [{ id: 'left-a', text: 'new left' }], right_items: [{ id: 'right-a', text: 'old right' }], correct_pairs: [{ left_id: 'left-a', right_id: 'right-a' }] } })))
    expect(vi.mocked(api.updateAssessmentQuestion).mock.calls[0]?.[2]).not.toHaveProperty('type')
  })

  it('sets reorder_sentence correct_order to row order while preserving IDs', async () => {
    const reorder = { ...question, type: 'reorder_sentence' as const, config: { items: [{ id: 'first', text: 'first' }, { id: 'second', text: 'second' }], correct_order: ['first', 'second'] } }
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([reorder])
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: 'Edit question' }))
    fireEvent.click(screen.getByRole('button', { name: 'Move second up' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.updateAssessmentQuestion).toHaveBeenCalledWith(assessment.id, reorder.id, expect.objectContaining({ config: { items: [{ id: 'second', text: 'second' }, { id: 'first', text: 'first' }], correct_order: ['second', 'first'] } })))
  })

  it('requires confirmation before deleting a question and reports learner history conflicts', async () => {
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([question])
    vi.mocked(api.deleteAssessmentQuestion).mockRejectedValue(apiError(409, 'QUESTION_HAS_HISTORY'))
    const confirm = vi.spyOn(globalThis, 'confirm').mockReturnValue(false)
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: 'Delete question' }))
    expect(api.deleteAssessmentQuestion).not.toHaveBeenCalled()
    confirm.mockReturnValue(true)
    fireEvent.click(screen.getByRole('button', { name: 'Delete question' }))
    expect(confirm).toHaveBeenCalledWith('Delete this question?')
    expect(await screen.findByRole('alert')).toHaveTextContent('This question has learner history and cannot be deleted.')
    expect(api.deleteAssessmentQuestion).toHaveBeenCalledWith(assessment.id, question.id)
  })

  it.each(['translate_vi_zh', 'translate_zh_vi', 'sentence_writing'] as const)('creates free-form type %s without a config editor', async (type) => {
    await openQuestionForm(type)
    fill('Reference answer (optional)', 'sample answer')
    fill('Rubric (optional)', 'use correct grammar')
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.createAssessmentQuestion).toHaveBeenCalledWith(assessment.id, expect.objectContaining({ type, reference_answer: 'sample answer', rubric: 'use correct grammar' })))
    expect(screen.queryByLabelText(/JSON|config/i)).not.toBeInTheDocument()
  })

  it.each(['translate_vi_zh', 'translate_zh_vi', 'sentence_writing'] as const)('clears persisted optional fields on %s edit', async (type) => {
    const existing = { ...question, type, prompt: 'Existing prompt', reference_answer: 'existing answer', rubric: 'existing rubric' } as AdminQuestion
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([existing])
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: 'Edit question' }))
    fireEvent.change(screen.getByLabelText('Reference answer (optional)'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Rubric (optional)'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.updateAssessmentQuestion).toHaveBeenCalledTimes(1))
    expect(api.updateAssessmentQuestion).toHaveBeenCalledWith(assessment.id, existing.id, {
      prompt: 'Existing prompt', order_index: 1, points: 1, reference_answer: null, rubric: null,
    })
    expect(vi.mocked(api.updateAssessmentQuestion).mock.calls[0]?.[2]).not.toHaveProperty('type')
    await waitFor(() => expect(vi.mocked(api.listAssessmentQuestions).mock.calls.length).toBeGreaterThan(1))
  })

  it.each([
    { reference_answer: ' updated answer ', rubric: '', expected: { reference_answer: 'updated answer', rubric: null } },
    { reference_answer: '', rubric: ' revised rubric ', expected: { reference_answer: null, rubric: 'revised rubric' } },
  ])('keeps non-empty free-form values while explicitly clearing a blank field', async ({ reference_answer, rubric, expected }) => {
    const existing = { ...question, type: 'translate_vi_zh' as const, reference_answer: 'old answer', rubric: 'old rubric' }
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([existing])
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: 'Edit question' }))
    fireEvent.change(screen.getByLabelText('Reference answer (optional)'), { target: { value: reference_answer } })
    fireEvent.change(screen.getByLabelText('Rubric (optional)'), { target: { value: rubric } })
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.updateAssessmentQuestion).toHaveBeenCalledWith(assessment.id, existing.id, expect.objectContaining(expected)))
  })

  it('continues omitting blank optional fields when creating a free-form question', async () => {
    await openQuestionForm('sentence_writing')
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.createAssessmentQuestion).toHaveBeenCalledTimes(1))
    const payload = vi.mocked(api.createAssessmentQuestion).mock.calls[0]?.[1]
    expect(payload).not.toHaveProperty('reference_answer')
    expect(payload).not.toHaveProperty('rubric')
  })

  it.each(['multiple_choice', 'fill_blank', 'matching', 'reorder_sentence', 'translate_vi_zh', 'translate_zh_vi', 'sentence_writing'] as const)('edits %s without changing its immutable type', async (type) => {
    const options = type === 'multiple_choice' ? [
      { id: 'option-1', option_text: 'A', order_index: 1, is_correct: true },
      { id: 'option-2', option_text: 'B', order_index: 2, is_correct: false },
    ] : []
    const config = type === 'fill_blank' ? { accepted_answers: ['accepted'] }
      : type === 'matching' ? { left_items: [{ id: 'left', text: 'left' }], right_items: [{ id: 'right', text: 'right' }], correct_pairs: [{ left_id: 'left', right_id: 'right' }] }
      : type === 'reorder_sentence' ? { items: [{ id: 'item', text: 'first' }], correct_order: ['item'] }
      : null
    const item = { ...question, type, reference_answer: type === 'fill_blank' ? 'answer' : null, config, options } as unknown as AdminQuestion
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([item])
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: 'Edit question' }))
    expect(screen.getByLabelText('Question type')).toHaveAttribute('readOnly')
    fill('Prompt', 'Updated prompt')
    fireEvent.click(screen.getByRole('button', { name: 'Save question' }))
    await waitFor(() => expect(api.updateAssessmentQuestion).toHaveBeenCalledWith(assessment.id, item.id, expect.objectContaining({ prompt: 'Updated prompt' })))
    expect(vi.mocked(api.updateAssessmentQuestion).mock.calls[0]?.[2]).not.toHaveProperty('type')
  })
})

describe('bounded Admin and learner cache invalidation', () => {
  it('invalidates HSK metadata dependencies without clearing unrelated or Admin Stats caches', async () => {
    const client = new QueryClient()
    for (const key of [queryKeys.adminHskLevels, queryKeys.adminCurriculum(level.id), queryKeys.curriculumLevels, queryKeys.curriculumHsk(level.id), queryKeys.progressOverview, queryKeys.progressHsk(level.id), queryKeys.dashboard, queryKeys.adminStats]) client.setQueryData(key, {})
    client.setQueryData(queryKeys.adminStats, { kept: true })
    client.setQueryData(['unrelated'], { kept: true })
    await invalidateHskMetadata(client, level.id)
    for (const key of [queryKeys.adminHskLevels, queryKeys.adminCurriculum(level.id), queryKeys.curriculumLevels, queryKeys.curriculumHsk(level.id), queryKeys.progressOverview, queryKeys.progressHsk(level.id), queryKeys.dashboard]) expect(client.getQueryState(key)?.isInvalidated).toBe(true)
    expect(client.getQueryState(queryKeys.adminStats)?.isInvalidated).toBe(false)
    expect(client.getQueryData(['unrelated'])).toEqual({ kept: true })
  })

  it('keeps lifecycle invalidation specific to a Lesson or Assessment type', async () => {
    const client = new QueryClient()
    for (const key of [queryKeys.adminCurriculum(level.id), queryKeys.adminLessonGrammar(lesson.id), queryKeys.lesson(lesson.id), queryKeys.lessonProgress(lesson.id), queryKeys.adminLesson(lesson.id), queryKeys.curriculumLevels, queryKeys.progressOverview, queryKeys.assessment(assessment.id), queryKeys.curriculumHskRoot, queryKeys.progressHskRoot, queryKeys.dashboard]) client.setQueryData(key, {})
    await invalidateCurriculumOrder(client, level.id)
    await invalidateLessonContent(client, lesson.id, level.id, 'grammar')
    await invalidateLessonLifecycle(client, lesson.id, level.id)
    await invalidateAssessmentLifecycle(client, { id: assessment.id, type: 'LESSON_EXERCISE', lesson_id: lesson.id })
    for (const key of [queryKeys.adminCurriculum(level.id), queryKeys.adminLessonGrammar(lesson.id), queryKeys.lesson(lesson.id), queryKeys.lessonProgress(lesson.id), queryKeys.adminLesson(lesson.id), queryKeys.curriculumLevels, queryKeys.progressOverview, queryKeys.assessment(assessment.id)]) expect(client.getQueryState(key)?.isInvalidated).toBe(true)
    const periodic = new QueryClient()
    for (const key of [queryKeys.adminAssessment(assessment.id), queryKeys.adminAssessmentsRoot, queryKeys.curriculumHskRoot, queryKeys.progressHskRoot, queryKeys.dashboard, queryKeys.progressOverview, queryKeys.curriculumLevels, queryKeys.assessment(assessment.id)]) periodic.setQueryData(key, {})
    await invalidateAssessmentLifecycle(periodic, assessment)
    for (const key of [queryKeys.curriculumHskRoot, queryKeys.progressHskRoot, queryKeys.dashboard, queryKeys.progressOverview, queryKeys.curriculumLevels]) expect(periodic.getQueryState(key)?.isInvalidated).toBe(true)
  })
})
