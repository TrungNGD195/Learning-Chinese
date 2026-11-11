import { adminLabel } from './labels'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { authApi } from '../auth/api'
import { createAppRoutes } from '../../app/router/routes'
import * as api from './api'
import * as readingApi from './readingApi'
import {
  invalidateAssessmentLifecycle, invalidateCurriculumOrder, invalidateHskMetadata,
  invalidateLessonContent, invalidateLessonLifecycle,
} from './invalidation'

vi.mock('./api', () => Object.fromEntries([
  'listHskLevels', 'updateHskLevel', 'getAdminCurriculum', 'replaceAdminCurriculum',
  'listAdminLessons', 'getAdminLesson', 'createAdminLesson', 'updateAdminLesson', 'publishAdminLesson', 'archiveAdminLesson', 'unpublishAdminLesson', 'publishAdminLessonPackage',
  'listLessonVocabulary', 'attachVocabulary', 'updateLessonVocabulary', 'detachVocabulary',
  'listLessonGrammar', 'attachGrammar', 'updateLessonGrammar', 'detachGrammar',
  'listAdminAssessments', 'getAdminAssessment', 'createAdminAssessment', 'updateAdminAssessment',
  'listAssessmentQuestions', 'createAssessmentQuestion', 'updateAssessmentQuestion', 'deleteAssessmentQuestion',
  'submitAssessmentReview', 'publishAdminAssessment', 'archiveAdminAssessment', 'getAdminStats', 'generateAssessmentDraft',
  'listAdminDocuments', 'getAdminDocument', 'getAdminDocumentPreview', 'uploadDocument',
  'processAdminDocument', 'approveAdminDocument', 'rejectAdminDocument', 'retryAdminDocumentKnowledge',
].map((name) => [name, vi.fn()])))
vi.mock('./readingApi', () => ({ listLessonReadings: vi.fn(), createLessonReading: vi.fn(), updateLessonReading: vi.fn(), deleteLessonReading: vi.fn() }))

vi.mock('../auth/api', () => ({ authApi: {
  register: vi.fn(), login: vi.fn(), getMe: vi.fn(), refresh: vi.fn(), logout: vi.fn(), logoutAll: vi.fn(),
  changePassword: vi.fn(), requestPasswordReset: vi.fn(), confirmPasswordReset: vi.fn(),
} }))

const admin = { id: 'admin-id', email: 'admin@example.test', full_name: "Quản trị", role: 'ADMIN' as const }
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

function openMetadata() {
  const button = screen.queryByRole('button', { name: /^Thông tin (bài học|bài luyện tập)$/ })
  if (button && button.getAttribute('aria-pressed') !== 'true') fireEvent.click(button)
}
function fill(label: string, value: string) {
  if (["Tiêu đề", "Mô tả", "Điểm đạt (%)"].includes(label)) openMetadata()
  const form = Array.from(document.querySelectorAll('.admin-assessment-question-form')).find((node) => !node.closest('[hidden]'))
  fireEvent.change(form ? within(form as HTMLElement).getByLabelText(label) : screen.getByLabelText(label), { target: { value } })
}
function confirmOpenDialog(label: string) { fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: label })) }
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((fulfill, fail) => { resolve = fulfill; reject = fail })
  return { promise, resolve, reject }
}

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
  vi.mocked(api.unpublishAdminLesson).mockResolvedValue(lesson)
  vi.mocked(api.publishAdminLessonPackage).mockResolvedValue({ ...lesson, status: 'PUBLISHED' })
  vi.mocked(readingApi.listLessonReadings).mockResolvedValue([])
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
  it('puts content management first and retains all administrator destinations', async () => {
    renderAt('/admin')
    const nav = screen.getByRole('navigation', { name: "Điều hướng quản trị" })
    expect(within(nav).getAllByRole('link').map((link) => link.textContent)).toEqual(["Tổng quan", "Bài học", "Kiểm tra định kỳ", "Tài liệu", "Hồ sơ"])
    const destinations = within(document.querySelector('.admin-workbench')!)
    for (const [name, href] of [['Sắp xếp bài học', '/admin/lessons?view=curriculum'], ['Quản lý tất cả bài học', '/admin/lessons'], ['Quản lý bài kiểm tra', '/admin/assessments'], ['Mở kho tài liệu', '/admin/documents']]) {
      expect(destinations.getByRole('link', { name })).toHaveAttribute('href', href)
    }
    expect(screen.getByRole('heading', {name:'Bài học'})).toBeInTheDocument()
    expect(await screen.findByText('82.5%')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: "Tổng tài khoản" })).not.toBeInTheDocument()
    expect(api.getAdminStats).toHaveBeenCalledTimes(1)
  })

  it('keeps an authenticated Learner on the D-041 Forbidden page', () => {
    renderAt('/admin/lessons?view=curriculum', learner)
    expect(screen.getByTestId('admin-forbidden')).toBeInTheDocument()
    expect(api.listHskLevels).not.toHaveBeenCalled()
  })

  it('renders ADMIN_REQUIRED without logging out or clearing current User', async () => {
    vi.mocked(api.listHskLevels).mockRejectedValueOnce(apiError(403, 'ADMIN_REQUIRED'))
    const { client, router } = renderAt('/admin/lessons?view=curriculum')
    expect(await screen.findByRole('alert')).toHaveTextContent("Tài khoản của bạn không có quyền quản trị.")
    expect(authApi.logout).not.toHaveBeenCalled()
    expect(client.getQueryData(queryKeys.authMe)).toEqual(admin)
    expect(router.state.location.pathname).toBe('/admin/lessons')
  })

  it('renders the real Documents list and upload entry', async () => {
    renderAt('/admin/documents')
    expect(await screen.findByRole('heading', { name: "Tải tài liệu nguồn lên" })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: "Tải tài liệu lên" })).toBeDisabled()
    expect(screen.queryByText('Document management will be implemented in Phase 5.')).not.toBeInTheDocument()
  })
})

describe('HSK and curriculum editing', () => {
  it('loads fixed HSK levels and sends only metadata fields with duplicate-submit protection', async () => {
    vi.mocked(api.updateHskLevel).mockImplementationOnce(() => new Promise(() => {}))
    const { client } = renderAt('/admin/lessons?view=curriculum')
    expect(await screen.findByText('Thông tin HSK 1')).toBeInTheDocument()
    await act(async () => {})
    expect(screen.queryByLabelText(/level number|order index/i)).not.toBeInTheDocument()
    fill("Tiêu đề", 'HSK One')
    const save = screen.getByRole('button', { name: "Lưu thông tin HSK" })
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

  it('keeps confirmed HSK metadata during a delayed canonical refetch and locks inputs while saving', async () => {
    const save = deferred<Awaited<ReturnType<typeof api.updateHskLevel>>>()
    const refresh = deferred<Awaited<ReturnType<typeof api.listHskLevels>>>()
    const saved = { ...level, title: 'Confirmed title', description: 'Confirmed description' }
    vi.mocked(api.updateHskLevel).mockReturnValueOnce(save.promise)
    vi.mocked(api.listHskLevels).mockResolvedValueOnce([level]).mockReturnValueOnce(refresh.promise)
    renderAt('/admin/lessons?view=curriculum')
    expect(await screen.findByText('Thông tin HSK 1')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByLabelText("Tiêu đề")).toHaveValue(level.title))
    fill("Tiêu đề", 'Draft title')
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin HSK" }))
    await waitFor(() => expect(api.updateHskLevel).toHaveBeenCalledWith(level.id, { title: 'Draft title', description: level.description }))
    expect(screen.getByLabelText("Tiêu đề")).toBeDisabled()
    expect(screen.getByLabelText("Mô tả")).toBeDisabled()
    expect(screen.getByRole('button', { name: /Đang lưu/ })).toBeDisabled()
    act(() => { save.resolve(saved) })
    await waitFor(() => expect(api.listHskLevels).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title))
    expect(screen.getByLabelText("Mô tả")).toHaveValue(saved.description)
    expect(screen.getByLabelText("Tiêu đề")).not.toHaveValue(level.title)
    await act(async () => { refresh.resolve([{ ...saved, title: 'Canonical title' }]) })
    await waitFor(() => expect(screen.getByLabelText("Tiêu đề")).toHaveValue('Canonical title'))
  })

  it('retains the confirmed HSK response when canonical refetch fails', async () => {
    const saved = { ...level, title: 'Saved title' }
    vi.mocked(api.updateHskLevel).mockResolvedValueOnce(saved)
    vi.mocked(api.listHskLevels).mockResolvedValueOnce([level]).mockRejectedValueOnce(apiError(503, 'TEMPORARY_FAILURE'))
    renderAt('/admin/lessons?view=curriculum')
    expect(await screen.findByText('Thông tin HSK 1')).toBeInTheDocument()
    fill("Tiêu đề", saved.title)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin HSK" }))
    expect(await screen.findByText("Chưa cập nhật được cấp độ HSK.")).toBeInTheDocument()
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    expect(screen.getByRole('button', { name: "Lưu thông tin HSK" })).toBeDisabled()
  })

  it('preserves HSK metadata drafts through background refetch and failed Save', async () => {
    vi.mocked(api.listHskLevels).mockResolvedValueOnce([level]).mockResolvedValueOnce([{ ...level, title: 'External title' }])
    vi.mocked(api.updateHskLevel).mockRejectedValueOnce(apiError(409, 'CONFLICT'))
    const { client } = renderAt('/admin/lessons?view=curriculum')
    expect(await screen.findByText('Thông tin HSK 1')).toBeInTheDocument()
    fill("Tiêu đề", 'Local draft')
    await act(async () => { await client.invalidateQueries({ queryKey: queryKeys.adminHskLevels }) })
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue('Local draft')
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin HSK" }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue('Local draft')
    expect(screen.getByLabelText("Tiêu đề")).toBeEnabled()
    expect(screen.getByRole('button', { name: "Lưu thông tin HSK" })).toBeEnabled()
  })

  it('reorders canonical membership, normalizes 1..N, confirms, PUTs the exact body and refetches', async () => {
    vi.mocked(api.getAdminCurriculum).mockResolvedValueOnce(curriculum).mockResolvedValueOnce([curriculum[1], curriculum[0]])
    renderAt('/admin/lessons?view=curriculum')
    expect(await screen.findByText(/1\. Bài học: Greetings/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: "Đưa HSK Test lên" }))
    expect(screen.getByText(/1\. Kiểm tra định kỳ: HSK Test/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    expect(screen.getByRole('dialog', { name: "Lưu thay đổi lộ trình?" })).toBeInTheDocument()
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: "Hủy" }))
    expect(api.replaceAdminCurriculum).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    confirmOpenDialog("Lưu lộ trình")
    await waitFor(() => expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(1))
    expect(api.replaceAdminCurriculum).toHaveBeenCalledWith(level.id, { units: [
      { unit_type: 'PERIODIC_TEST', target_id: assessment.id, order_index: 1 },
      { unit_type: 'LESSON', target_id: lesson.id, order_index: 2 },
    ] })
    await waitFor(() => expect(api.getAdminCurriculum).toHaveBeenCalledTimes(2))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('preserves a dirty reorder draft through background refetch and retains it after save failure', async () => {
    vi.mocked(api.replaceAdminCurriculum).mockRejectedValue(apiError(422, 'INVALID_CURRICULUM'))
    const { client } = renderAt('/admin/lessons?view=curriculum')
    expect(await screen.findByText(/1\. Bài học: Greetings/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: "Đưa HSK Test lên" }))
    await act(async () => { await client.invalidateQueries({ queryKey: queryKeys.adminCurriculum(level.id) }) })
    expect(screen.getByText(/1\. Kiểm tra định kỳ: HSK Test/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    confirmOpenDialog("Lưu lộ trình")
    expect(await screen.findByRole('alert')).toHaveTextContent("Thứ tự lộ trình không hợp lệ.")
    expect(screen.getByText(/1\. Kiểm tra định kỳ: HSK Test/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: "Gỡ Greetings khỏi lộ trình" })).toBeInTheDocument()
  })

  it('adds published Lesson and Periodic Test candidates, detaches locally, reorders, and PUTs full canonical membership', async () => {
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
    const { client } = renderAt('/admin/lessons?view=curriculum')
    const invalidate = vi.spyOn(client, 'invalidateQueries')

    expect(await screen.findByRole('button', { name: "Thêm Family words vào lộ trình" })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: "Thêm Published test vào lộ trình" })).toBeInTheDocument()
    expect(api.listAdminLessons).toHaveBeenCalledWith({ page: 1, page_size: 20, status: 'PUBLISHED', hsk_level_id: level.id })
    expect(api.listAdminAssessments).toHaveBeenCalledWith({ page: 1, page_size: 20, status: 'PUBLISHED', assessment_type: 'PERIODIC_TEST' })
    expect(screen.queryByText('Draft test')).not.toBeInTheDocument()
    expect(screen.queryByText('Published exercise')).not.toBeInTheDocument()
    expect(screen.queryByText('Archived lesson')).not.toBeInTheDocument()
    expect(screen.queryByText('unit-1')).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/target id/i)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: "Gỡ Greetings khỏi lộ trình" }))
    fireEvent.click(screen.getByRole('button', { name: "Thêm Family words vào lộ trình" }))
    fireEvent.click(screen.getByRole('button', { name: "Thêm Published test vào lộ trình" }))
    expect(api.replaceAdminCurriculum).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: "Đưa Family words lên" }))
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    expect(screen.getByRole('dialog', { name: "Lưu thay đổi lộ trình?" })).toBeInTheDocument()
    confirmOpenDialog("Lưu lộ trình")
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
    expect(screen.getByText(/1\. Bài học: Family words/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: "Lưu lộ trình" })).toBeDisabled()
  })

  it('keeps the local membership draft after a failed PUT and retries only after an explicit click', async () => {
    vi.mocked(api.listAdminLessons).mockResolvedValue({ items: [publishedCandidateLesson], page: 1, page_size: 20, total: 1 })
    vi.mocked(api.replaceAdminCurriculum).mockRejectedValueOnce(apiError(422, 'INVALID_CURRICULUM_TARGET'))
    renderAt('/admin/lessons?view=curriculum')
    fireEvent.click(await screen.findByRole('button', { name: "Thêm Family words vào lộ trình" }))
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    confirmOpenDialog("Lưu lộ trình")
    expect(await screen.findByRole('alert')).toHaveTextContent("Một nội dung trong lộ trình không còn khả dụng.")
    expect(screen.getByRole('button', { name: "Gỡ Family words khỏi lộ trình" })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: "Lưu lộ trình" })).toBeEnabled()
    expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    confirmOpenDialog("Lưu lộ trình")
    await waitFor(() => expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(2))
  })

  it('prevents duplicate saves while pending and preserves draft across candidate page changes', async () => {
    let resolveSave!: (value: typeof curriculum) => void
    vi.mocked(api.replaceAdminCurriculum).mockReturnValueOnce(new Promise((resolve) => { resolveSave = resolve }))
    vi.mocked(api.listAdminLessons).mockImplementation(async (filters) => ({
      items: filters.page === 1 ? [publishedCandidateLesson] : [], page: filters.page ?? 1, page_size: 20, total: 21,
    }))
    const { client } = renderAt('/admin/lessons?view=curriculum')
    fireEvent.click(await screen.findByRole('button', { name: "Thêm Family words vào lộ trình" }))
    fireEvent.click(screen.getByRole('button', { name: "Trang bài học tiếp" }))
    expect(await screen.findByText("Trang bài học 2")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: "Gỡ Family words khỏi lộ trình" })).toBeInTheDocument()
    expect(api.listAdminLessons).toHaveBeenCalledTimes(2)
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    confirmOpenDialog("Lưu lộ trình")
    const save = await screen.findByRole('button', { name: /Đang lưu lộ trình/ })
    expect(save).toBeDisabled()
    fireEvent.click(save)
    expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(1)
    resolveSave(curriculum)
    await waitFor(() => expect(screen.getByRole('button', { name: "Lưu lộ trình" })).toBeDisabled())
    expect(client.getQueryData(queryKeys.adminCurriculum(level.id))).toEqual(curriculum)
  })

  it('locks membership edits during PUT and adopts the canonical order on success', async () => {
    const save = deferred<typeof curriculum>()
    const canonical = [
      { ...curriculum[1], assessment_title: 'Canonical HSK Test', order_index: 1 },
      { ...curriculum[0], order_index: 2 },
    ]
    vi.mocked(api.listAdminLessons).mockResolvedValue({ items: [publishedCandidateLesson], page: 1, page_size: 20, total: 1 })
    vi.mocked(api.getAdminCurriculum).mockResolvedValueOnce(curriculum).mockResolvedValueOnce(canonical)
    vi.mocked(api.replaceAdminCurriculum).mockReturnValueOnce(save.promise)
    renderAt('/admin/lessons?view=curriculum')
    expect(await screen.findByText(/1\. Bài học: Greetings/)).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: "Thêm Family words vào lộ trình" })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: "Đưa HSK Test lên" }))
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    confirmOpenDialog("Lưu lộ trình")
    await waitFor(() => expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(1))
    expect(screen.getByRole('button', { name: "Đưa HSK Test xuống" })).toBeDisabled()
    expect(screen.getByRole('button', { name: "Đưa HSK Test lên" })).toBeDisabled()
    expect(screen.getByRole('button', { name: "Gỡ HSK Test khỏi lộ trình" })).toBeDisabled()
    expect(screen.getByRole('button', { name: "Thêm Family words vào lộ trình" })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Đang lưu lộ trình/ })).toBeDisabled()
    act(() => { save.resolve(canonical) })
    await waitFor(() => expect(api.getAdminCurriculum).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.getByText(/1\. Kiểm tra định kỳ: Canonical HSK Test/)).toBeInTheDocument())
    await waitFor(() => expect(screen.getByRole('button', { name: "Lưu lộ trình" })).toBeDisabled())
  })

  it('unlocks membership edits and retains the draft after a pending PUT fails until explicit retry', async () => {
    const save = deferred<typeof curriculum>()
    vi.mocked(api.replaceAdminCurriculum).mockReturnValueOnce(save.promise).mockResolvedValueOnce(curriculum)
    renderAt('/admin/lessons?view=curriculum')
    expect(await screen.findByText(/1\. Bài học: Greetings/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: "Đưa HSK Test lên" }))
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    confirmOpenDialog("Lưu lộ trình")
    expect(screen.getByRole('button', { name: "Gỡ Greetings khỏi lộ trình" })).toBeDisabled()
    act(() => { save.reject(apiError(422, 'INVALID_CURRICULUM')) })
    expect(await screen.findByRole('alert')).toHaveTextContent("Thứ tự lộ trình không hợp lệ.")
    expect(screen.getByText(/1\. Kiểm tra định kỳ: HSK Test/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: "Gỡ Greetings khỏi lộ trình" })).toBeEnabled()
    expect(screen.getByRole('button', { name: "Lưu lộ trình" })).toBeEnabled()
    expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: "Lưu lộ trình" }))
    confirmOpenDialog("Lưu lộ trình")
    await waitFor(() => expect(api.replaceAdminCurriculum).toHaveBeenCalledTimes(2))
  })
})

describe('Lesson list, canonical editor, lifecycle and content', () => {
  it('keeps archived lesson vocabulary read-only after translating status labels', async () => {
    vi.mocked(api.getAdminLesson).mockResolvedValue({ ...lesson, status: 'ARCHIVED' })
    vi.mocked(api.listLessonVocabulary).mockResolvedValue([{ id: 'archived-word', vocabulary_id: 'word', grammar_id: null, hanzi: '你', pinyin: 'nǐ', vietnamese_meaning: 'bạn', part_of_speech: null, name: null, structure: null, explanation: null, usage: null, order_index: 1, note: null, example: null }])
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByText('Chỉ đọc')).toBeInTheDocument()
    expect(screen.getByLabelText('Chữ Hán')).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Lưu nội dung' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Gỡ từ vựng' })).not.toBeInTheDocument()
    expect(api.updateLessonVocabulary).not.toHaveBeenCalled()
    expect(api.detachVocabulary).not.toHaveBeenCalled()
  })
  it('filters and paginates the lesson list, creates exact payload without status, then opens canonical detail', async () => {
    vi.mocked(api.listAdminLessons).mockResolvedValue({ items: [lesson], page: 1, page_size: 20, total: 40 })
    const { router } = renderAt('/admin/lessons')
    expect(await screen.findByRole('link', { name: 'Biên soạn bài học: Greetings' })).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: "Tạo bài học" }).at(-1)!)
    fireEvent.click(screen.getByRole('button', { name: "Đóng tạo bài học" }))
    expect(api.createAdminLesson).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText("Trạng thái"), { target: { value: 'DRAFT' } })
    fireEvent.change(screen.getAllByLabelText('HSK', { selector: 'select' }).at(-1)!, { target: { value: level.id } })
    await waitFor(() => expect(screen.getByRole('button', { name: "Tiếp" })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: "Tiếp" }))
    await waitFor(() => expect(api.listAdminLessons).toHaveBeenCalledWith({ page: 2, page_size: 20, status: 'DRAFT', hsk_level_id: level.id }))
    fireEvent.click(screen.getAllByRole('button', { name: "Tạo bài học" }).at(-1)!)
    fill("Số thứ tự bài học", '2'); fill("Tiêu đề", 'Introduce yourself'); fill("Mô tả", '');
    fireEvent.change(screen.getAllByLabelText('HSK', { selector: 'select' }).at(0)!, { target: { value: level.id } })
    fireEvent.click(screen.getAllByRole('button', { name: "Tạo bài học" }).at(-1)!)
    await waitFor(() => expect(api.createAdminLesson).toHaveBeenCalledWith({ hsk_level_id: level.id, lesson_number: 2, title: 'Introduce yourself' }))
    await waitFor(() => expect(router.state.location.pathname).toBe(`/admin/lessons/${lesson.id}`))
  })

  it('loads the Lesson editor by canonical GET, edits Published metadata, and archives only after confirmation', async () => {
    vi.mocked(api.getAdminLesson).mockResolvedValue({ ...lesson, status: 'PUBLISHED' })
    vi.mocked(api.updateAdminLesson).mockResolvedValue({ ...lesson, status: 'PUBLISHED', title: 'Greetings revised' })
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: "Bài 1 · Greetings" })).toBeInTheDocument()
    expect(screen.getByText('HSK 1 · 1')).toBeInTheDocument()
    expect(api.getAdminLesson).toHaveBeenCalledWith(lesson.id)
    expect(screen.queryByLabelText('HSK level id')).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Số thứ tự bài học")).not.toBeInTheDocument()
    fill("Tiêu đề", 'Greetings revised')
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminLesson).toHaveBeenCalledWith(lesson.id, { title: 'Greetings revised', description: lesson.description }))
    expect(screen.getByRole('button', { name: "Lưu trữ bài học" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: "Lưu trữ bài học" }))
    expect(screen.getByRole('dialog', { name: "Lưu trữ bài học?" })).toBeInTheDocument()
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: "Hủy" }))
    expect(api.archiveAdminLesson).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: "Lưu trữ bài học" }))
    confirmOpenDialog("Lưu trữ bài học")
    await waitFor(() => expect(api.archiveAdminLesson).toHaveBeenCalledWith(lesson.id))
    expect(api.archiveAdminLesson).toHaveBeenCalledTimes(1)
    expect(api.publishAdminLesson).not.toHaveBeenCalled()
  })

  it('locks Lesson metadata during a pending PATCH and sends the draft only once', async () => {
    const pending = deferred<Awaited<ReturnType<typeof api.updateAdminLesson>>>()
    vi.mocked(api.updateAdminLesson).mockReturnValueOnce(pending.promise)
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: "Bài 1 · Greetings" })).toBeInTheDocument()
    fill("Tiêu đề", '  Updated greeting  ')
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminLesson).toHaveBeenCalledWith(lesson.id, { title: 'Updated greeting', description: lesson.description }))
    expect(screen.getByLabelText("Tiêu đề")).toBeDisabled()
    expect(screen.getByLabelText("Mô tả")).toBeDisabled()
    expect(screen.getByRole('button', { name: "Đang lưu…" })).toBeDisabled()
    fireEvent.submit(document.querySelector('.admin-lesson-metadata-form')!)
    expect(api.updateAdminLesson).toHaveBeenCalledTimes(1)
    act(() => { pending.reject(apiError(503, 'NETWORK_ERROR')) })
    expect(await screen.findByRole('alert')).toHaveTextContent("Có sự cố tạm thời. Vui lòng thử lại.")
    expect(screen.getByLabelText("Tiêu đề")).toBeEnabled()
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue('  Updated greeting  ')
  })

  it('keeps the confirmed Lesson response above a stale in-flight GET until canonical refetch finishes', async () => {
    const stale = deferred<Awaited<ReturnType<typeof api.getAdminLesson>>>()
    const canonical = deferred<Awaited<ReturnType<typeof api.getAdminLesson>>>()
    const saved = { ...lesson, title: 'Saved greeting', description: 'Saved description' }
    vi.mocked(api.getAdminLesson).mockResolvedValueOnce(lesson).mockReturnValueOnce(stale.promise).mockReturnValueOnce(canonical.promise)
    vi.mocked(api.updateAdminLesson).mockResolvedValueOnce(saved)
    const { client } = renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: "Bài 1 · Greetings" })).toBeInTheDocument()
    fill("Tiêu đề", saved.title)
    void client.invalidateQueries({ queryKey: queryKeys.adminLesson(lesson.id) })
    await waitFor(() => expect(api.getAdminLesson).toHaveBeenCalledTimes(2))
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminLesson).toHaveBeenCalledWith(lesson.id, { title: saved.title, description: lesson.description }))
    await waitFor(() => expect(api.getAdminLesson).toHaveBeenCalledTimes(3))
    expect(client.getQueryData(queryKeys.adminLesson(lesson.id))).toEqual(saved)
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    expect(screen.getByLabelText("Mô tả")).toHaveValue(saved.description)
    await act(async () => { stale.resolve({ ...lesson, title: 'Stale background title' }); await Promise.resolve() })
    expect(client.getQueryData(queryKeys.adminLesson(lesson.id))).toEqual(saved)
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    await act(async () => { canonical.resolve({ ...saved, title: 'Canonical greeting' }) })
    await waitFor(() => expect(screen.getByLabelText("Tiêu đề")).toHaveValue('Canonical greeting'))
    expect(screen.getByRole('heading', { name: "Bài 1 · Canonical greeting" })).toBeInTheDocument()
  })

  it('retains confirmed Lesson metadata when the canonical GET fails', async () => {
    const saved = { ...lesson, title: 'Saved greeting', description: 'Saved description' }
    vi.mocked(api.updateAdminLesson).mockResolvedValueOnce(saved)
    vi.mocked(api.getAdminLesson).mockResolvedValueOnce(lesson).mockRejectedValueOnce(apiError(503, 'TEMPORARY_FAILURE'))
    const { client } = renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: "Bài 1 · Greetings" })).toBeInTheDocument()
    fill("Tiêu đề", saved.title)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminLesson).toHaveBeenCalledTimes(1))
    expect(await screen.findByText("Chưa cập nhật được bài học. Đang hiển thị dữ liệu đã tải.")).toBeInTheDocument()
    expect(client.getQueryData(queryKeys.adminLesson(lesson.id))).toEqual(saved)
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    expect(screen.getByLabelText("Mô tả")).toHaveValue(saved.description)
    expect(screen.getByRole('button', { name: "Lưu thông tin" })).toBeDisabled()
  })

  it('retains a Lesson draft after failed PATCH and retries only after another Save', async () => {
    const saved = { ...lesson, title: 'Local draft' }
    vi.mocked(api.updateAdminLesson).mockRejectedValueOnce(apiError(503, 'NETWORK_ERROR')).mockResolvedValueOnce(saved)
    vi.mocked(api.getAdminLesson).mockResolvedValueOnce(lesson).mockResolvedValueOnce(saved)
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: "Bài 1 · Greetings" })).toBeInTheDocument()
    fill("Tiêu đề", saved.title)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Có sự cố tạm thời. Vui lòng thử lại.")
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    expect(screen.getByRole('button', { name: "Lưu thông tin" })).toBeEnabled()
    expect(api.updateAdminLesson).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminLesson).toHaveBeenCalledTimes(2))
    expect(api.updateAdminLesson).toHaveBeenLastCalledWith(lesson.id, { title: saved.title, description: lesson.description })
  })

  it('keeps a dirty Lesson draft and conflict invalidation after a 409 until explicit retry', async () => {
    const server = { ...lesson, title: 'Server revision' }
    const saved = { ...server, title: 'Local draft' }
    vi.mocked(api.getAdminLesson).mockResolvedValueOnce(lesson).mockResolvedValueOnce(server).mockResolvedValueOnce(saved)
    vi.mocked(api.updateAdminLesson).mockRejectedValueOnce(apiError(409, 'LESSON_IMMUTABLE')).mockResolvedValueOnce(saved)
    const { client } = renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: "Bài 1 · Greetings" })).toBeInTheDocument()
    fill("Tiêu đề", saved.title)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Bài học này không còn cho phép chỉnh sửa.")
    await waitFor(() => expect(api.getAdminLesson).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(client.getQueryData(queryKeys.adminLesson(lesson.id))).toEqual(server))
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    expect(screen.getByRole('button', { name: "Lưu thông tin" })).toBeEnabled()
    expect(api.updateAdminLesson).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminLesson).toHaveBeenCalledTimes(2))
    expect(api.updateAdminLesson).toHaveBeenLastCalledWith(lesson.id, { title: saved.title, description: lesson.description })
  })

  it('does not carry an unsaved Lesson draft to another Lesson ID', async () => {
    const second = { ...lesson, id: 'lesson-2', lesson_number: 2, title: 'Second Lesson', description: 'Second description' }
    vi.mocked(api.getAdminLesson).mockImplementation(async (id) => id === lesson.id ? lesson : second)
    const { router } = renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: "Bài 1 · Greetings" })).toBeInTheDocument()
    fill("Tiêu đề", 'Unsaved first Lesson')
    await act(async () => { await router.navigate(`/admin/lessons/${second.id}`) })
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    confirmOpenDialog('Rời trang')
    expect(await screen.findByRole('heading', { name: "Bài 2 · Second Lesson" })).toBeInTheDocument()
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(second.title)
    expect(screen.getByLabelText("Mô tả")).toHaveValue(second.description)
    expect(api.updateAdminLesson).not.toHaveBeenCalled()
    await act(async () => { await router.navigate(`/admin/lessons/${lesson.id}`) })
    expect(await screen.findByRole('heading', { name: "Bài 1 · Greetings" })).toBeInTheDocument()
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(lesson.title)
  })

  it('reviews theory and practice together before one publication action', async () => {
    const practice = { ...assessment, type: 'LESSON_EXERCISE' as const, lesson_id: lesson.id, pass_threshold: 80 }
    vi.mocked(api.listAdminAssessments).mockResolvedValue({ items: [practice], page: 1, page_size: 100, total: 1 })
    vi.mocked(api.getAdminAssessment).mockResolvedValue(practice)
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue(Array.from({ length: 30 }, (_, index) => ({ ...question, id: `question-${index}`, assessment_id: practice.id, order_index: index + 1, type: (['fill_blank', 'translate_zh_vi', 'sentence_writing'] as const)[index % 3] })))
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('button', { name: 'Duyệt và xuất bản' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Thêm từ vựng' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: "Ngữ pháp" }))
    expect(screen.getByRole('button', { name: 'Thêm ngữ pháp' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Gỡ từ vựng|Gỡ ngữ pháp/i })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Duyệt và xuất bản' }))
    const publish = await screen.findByRole('button', { name: 'Xác nhận xuất bản toàn bộ' })
    await waitFor(() => expect(publish).toBeEnabled())
    expect(screen.getByText('30/30 câu · 3 dạng bài · Điểm đạt 80%')).toBeInTheDocument()
    expect(api.publishAdminLessonPackage).not.toHaveBeenCalled()
    fireEvent.click(publish)
    await waitFor(() => expect(api.publishAdminLessonPackage).toHaveBeenCalledExactlyOnceWith(lesson.id))
    expect(api.publishAdminLesson).not.toHaveBeenCalled()
    expect(api.submitAssessmentReview).not.toHaveBeenCalled()
    expect(api.publishAdminAssessment).not.toHaveBeenCalled()
  })

  it('edits practice in the lesson and retains unsaved question changes across theory and review', async () => {
    const practice = { ...assessment, type: 'LESSON_EXERCISE' as const, lesson_id: lesson.id, pass_threshold: 80 }
    vi.mocked(api.listAdminAssessments).mockResolvedValue({ items: [practice], page: 1, page_size: 100, total: 1 })
    vi.mocked(api.getAdminAssessment).mockResolvedValue(practice)
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([question])
    const { router } = renderAt(`/admin/lessons/${lesson.id}?section=exercises&exercise=${practice.id}`)
    const prompt = await screen.findByLabelText('Nội dung câu hỏi')
    fireEvent.change(prompt, { target: { value: 'Câu hỏi đang sửa' } })
    fireEvent.click(screen.getByRole('button', { name: 'Từ vựng' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Duyệt xuất bản' }))
    expect(await screen.findByText('Lưu các thay đổi ở từng mục trước khi xuất bản.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Luyện tập' }))
    expect(screen.getByLabelText('Nội dung câu hỏi')).toHaveValue('Câu hỏi đang sửa')
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
    expect(screen.queryByRole('button', { name: 'Gửi duyệt' })).not.toBeInTheDocument()
    expect(router.state.location.pathname).toBe(`/admin/lessons/${lesson.id}`)
    fireEvent.click(screen.getByRole('button', { name: 'Lưu câu hỏi' }))
    await waitFor(() => expect(api.updateAssessmentQuestion).toHaveBeenCalledWith(practice.id, question.id, expect.objectContaining({ prompt: 'Câu hỏi đang sửa' })))
  })

  it('requires confirmation to unpublish and returns to Draft without archiving', async () => {
    vi.mocked(api.getAdminLesson).mockResolvedValueOnce({ ...lesson, status: 'PUBLISHED' }).mockResolvedValue(lesson)
    renderAt(`/admin/lessons/${lesson.id}`)
    fireEvent.click(await screen.findByRole('button', { name: 'Hủy xuất bản' }))
    expect(api.unpublishAdminLesson).not.toHaveBeenCalled()
    confirmOpenDialog('Hủy xuất bản')
    await waitFor(() => expect(api.unpublishAdminLesson).toHaveBeenCalledExactlyOnceWith(lesson.id))
    expect(api.archiveAdminLesson).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Hủy xuất bản' })).not.toBeInTheDocument())
  })

  it('creates and attaches Vocabulary without an existing UUID field and keeps canonical/association groups separate', async () => {
    renderAt(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: "Từ vựng" })).toBeInTheDocument()
    const vocabularySection = screen.getByRole('region', { name: "Bài học · từ vựng" })
    fireEvent.click(within(vocabularySection).getByRole('button', { name: 'Thêm từ vựng' }))
    fill("Chữ Hán", '你好'); fill("Phiên âm", 'nǐ hǎo'); fill("Nghĩa tiếng Việt", 'xin chào'); fireEvent.change(within(vocabularySection).getByLabelText("Thứ tự"), { target: { value: '3' } }); fireEvent.change(within(vocabularySection).getByLabelText("Lưu ý"), { target: { value: 'greeting' } })
    expect(within(vocabularySection).getByText("Thông tin trong bài học này")).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: "Tạo và thêm từ vựng" }))
    await waitFor(() => expect(api.attachVocabulary).toHaveBeenCalledWith(lesson.id, {
      hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', order_index: 3, note: 'greeting',
    }))
    expect(screen.queryByLabelText(/vocabulary id/i)).not.toBeInTheDocument()
  })

  it('detaches Lesson content only after the R1 Dialog is confirmed', async () => {
    vi.mocked(api.listLessonVocabulary).mockResolvedValue([{ id: 'vocab-link', vocabulary_id: 'vocab-id', hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', part_of_speech: null, order_index: 1, note: null, example: null, grammar_id: null, name: null, structure: null, explanation: null, usage: null }])
    renderAt(`/admin/lessons/${lesson.id}`)
    fireEvent.click(await screen.findByRole('button', { name: "Gỡ từ vựng" }))
    expect(screen.getByRole('dialog', { name: "Gỡ từ vựng khỏi bài học?" })).toHaveTextContent('Nội dung gốc dùng chung vẫn được giữ lại.')
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: "Hủy" }))
    expect(api.detachVocabulary).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: "Gỡ từ vựng" }))
    confirmOpenDialog("Gỡ từ vựng")
    await waitFor(() => expect(api.detachVocabulary).toHaveBeenCalledWith(lesson.id, 'vocab-link'))
    expect(api.detachVocabulary).toHaveBeenCalledTimes(1)
  })

  it('does not expose detach on Published Lessons and permits Grammar content updates', async () => {
    vi.mocked(api.getAdminLesson).mockResolvedValue({ ...lesson, status: 'PUBLISHED' })
    vi.mocked(api.listLessonGrammar).mockResolvedValue([{ id: 'grammar-link', vocabulary_id: null, hanzi: null, pinyin: null, vietnamese_meaning: null, part_of_speech: null, order_index: 1, note: null, example: null, grammar_id: 'grammar-id', name: 'A-not-A', structure: 'A 不 A', explanation: 'Choice question', usage: null }])
    renderAt(`/admin/lessons/${lesson.id}`)
    fireEvent.click(await screen.findByRole('button', { name: "Ngữ pháp" }))
    expect(await screen.findByRole('button', { name: /A-not-A/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: "Gỡ ngữ pháp" })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: "Chỉnh sửa nội dung" })).toBeInTheDocument()
    fireEvent.change(screen.getAllByLabelText("Tên").at(0)!, { target: { value: 'A-not-A revised' } })
    fireEvent.click(screen.getByRole('button', { name: "Lưu nội dung" }))
    await waitFor(() => expect(api.updateLessonGrammar).toHaveBeenCalledWith(lesson.id, 'grammar-link', expect.objectContaining({ name: 'A-not-A revised', order_index: 1 })))
  })
})

describe('Assessment metadata, lifecycle, questions and Stats', () => {
  it('creates a lesson exercise inside its lesson without a second management page', async () => {
    const practice = { ...assessment, type: 'LESSON_EXERCISE' as const, lesson_id: lesson.id, title: 'Lesson practice', pass_threshold: 80 }
    vi.mocked(api.createAdminAssessment).mockImplementation(async () => {
      vi.mocked(api.listAdminAssessments).mockResolvedValue({ items: [practice], page: 1, page_size: 100, total: 1 })
      vi.mocked(api.getAdminAssessment).mockResolvedValue(practice)
      return practice
    })
    const { router } = renderAt(`/admin/lessons/${lesson.id}?section=exercises`)
    fireEvent.click(await screen.findByRole('button', { name: 'Thêm bài luyện tập' }))
    fireEvent.change(screen.getByLabelText('Tiêu đề bài luyện tập'), { target: { value: 'Lesson practice' } })
    fireEvent.click(screen.getByRole('button', { name: "Tạo bài luyện tập" }))
    await waitFor(() => expect(api.createAdminAssessment).toHaveBeenCalledWith({ type: 'LESSON_EXERCISE', lesson_id: lesson.id, title: 'Lesson practice', description: null, pass_threshold: 80 }))
    expect(router.state.location.pathname).toBe(`/admin/lessons/${lesson.id}`)
    expect(await screen.findByRole('heading', { name: practice.title })).toBeInTheDocument()
  })

  it('generates practice for the current lesson and opens it without navigating away', async () => {
    const practice = { ...assessment, type: 'LESSON_EXERCISE' as const, lesson_id: lesson.id, title: 'Generated lesson practice', pass_threshold: 80 }
    vi.mocked(api.generateAssessmentDraft).mockImplementation(async () => {
      vi.mocked(api.listAdminAssessments).mockResolvedValue({ items: [practice], page: 1, page_size: 100, total: 1 })
      vi.mocked(api.getAdminAssessment).mockResolvedValue(practice)
      return { assessment: practice, questions: [] }
    })
    const { router } = renderAt(`/admin/lessons/${lesson.id}?section=exercises`)
    fireEvent.click(await screen.findByRole('button', { name: 'Tạo bản nháp bằng AI' }))
    expect(screen.queryByLabelText('Loại bài luyện tập')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Bài học', { selector: 'select' })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Độ khó'), { target: { value: 'EASY' } })
    fireEvent.click(screen.getByRole('button', { name: 'Tạo bản nháp' }))
    await waitFor(() => expect(api.generateAssessmentDraft).toHaveBeenCalledWith(expect.objectContaining({ type: 'LESSON_EXERCISE', lesson_id: lesson.id, question_count: 30, pass_threshold: 80 })))
    expect(await screen.findByRole('heading', { name: practice.title })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(`/admin/lessons/${lesson.id}`)
    expect(api.listAdminLessons).not.toHaveBeenCalled()
  })

  it('redirects a legacy lesson exercise editor URL to its owning lesson', async () => {
    const practice = { ...assessment, type: 'LESSON_EXERCISE' as const, lesson_id: lesson.id }
    vi.mocked(api.getAdminAssessment).mockResolvedValue(practice)
    vi.mocked(api.listAdminAssessments).mockResolvedValue({ items: [practice], page: 1, page_size: 100, total: 1 })
    const { router } = renderAt(`/admin/assessments/${practice.id}`)
    await waitFor(() => expect(router.state.location.pathname).toBe(`/admin/lessons/${lesson.id}`))
    expect(router.state.location.search).toBe(`?section=exercises&exercise=${practice.id}`)
  })

  it('creates PERIODIC_TEST without deferred scope fields', async () => {
    renderAt('/admin/assessments')
    await waitFor(() => expect(api.listAdminAssessments).toHaveBeenCalledWith({ page: 1, page_size: 20, assessment_type: 'PERIODIC_TEST' }))
    fireEvent.click(screen.getByRole('button', { name: 'Tạo bài kiểm tra' }))
    expect(screen.queryByLabelText('Loại')).not.toBeInTheDocument()
    fill("Tiêu đề", "Kiểm tra định kỳ"); fill("Điểm đạt (%)", '90')
    fireEvent.click(screen.getAllByRole('button', { name: 'Tạo bài kiểm tra' }).at(-1)!)
    await waitFor(() => expect(api.createAdminAssessment).toHaveBeenCalledWith({ type: 'PERIODIC_TEST', title: "Kiểm tra định kỳ", pass_threshold: 90 }))
    const payload = vi.mocked(api.createAdminAssessment).mock.calls[0]?.[0]
    expect(payload).not.toHaveProperty('lesson_id')
    expect(payload).not.toHaveProperty('lesson_ids')
    expect(payload).not.toHaveProperty('vocabulary_ids')
    expect(payload).not.toHaveProperty('grammar_ids')
  })

  it('loads assessment detail directly and sends only visible metadata fields on PERIODIC_TEST PATCH', async () => {
    renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    expect(api.getAdminAssessment).toHaveBeenCalledWith(assessment.id)
    fill("Tiêu đề", 'HSK Test Revised')
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminAssessment).toHaveBeenCalledWith(assessment.id, { title: 'HSK Test Revised', description: null, pass_threshold: 90 }))
    const patchBody = vi.mocked(api.updateAdminAssessment).mock.calls[0]?.[1]
    for (const deferred of ['lesson_ids', 'vocabulary_ids', 'grammar_ids']) expect(patchBody).not.toHaveProperty(deferred)
  })

  it('locks Assessment metadata during a pending PATCH and sends one exact payload', async () => {
    const pending = deferred<Awaited<ReturnType<typeof api.updateAdminAssessment>>>()
    vi.mocked(api.updateAdminAssessment).mockReturnValueOnce(pending.promise)
    renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    fill("Tiêu đề", '  Revised assessment  ')
    fill("Mô tả", 'Local description')
    fill("Điểm đạt (%)", '85')
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminAssessment).toHaveBeenCalledWith(assessment.id, { title: 'Revised assessment', description: 'Local description', pass_threshold: 85 }))
    expect(screen.getByLabelText("Tiêu đề")).toBeDisabled()
    expect(screen.getByLabelText("Mô tả")).toBeDisabled()
    expect(screen.getByLabelText("Điểm đạt (%)")).toBeDisabled()
    expect(screen.getByRole('button', { name: "Đang lưu…" })).toBeDisabled()
    fireEvent.submit(document.querySelector('.admin-assessment-metadata-form')!)
    expect(api.updateAdminAssessment).toHaveBeenCalledTimes(1)
    act(() => { pending.reject(apiError(503, 'NETWORK_ERROR')) })
    expect(await screen.findByRole('alert')).toHaveTextContent("Có sự cố tạm thời. Vui lòng thử lại.")
    expect(screen.getByLabelText("Tiêu đề")).toBeEnabled()
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue('  Revised assessment  ')
  })

  it('keeps confirmed Assessment metadata above a stale GET until canonical refetch finishes', async () => {
    const stale = deferred<Awaited<ReturnType<typeof api.getAdminAssessment>>>()
    const canonical = deferred<Awaited<ReturnType<typeof api.getAdminAssessment>>>()
    const saved = { ...assessment, title: 'Saved assessment', description: 'Saved description', pass_threshold: 85 }
    vi.mocked(api.getAdminAssessment).mockResolvedValueOnce(assessment).mockReturnValueOnce(stale.promise).mockReturnValueOnce(canonical.promise)
    vi.mocked(api.updateAdminAssessment).mockResolvedValueOnce(saved)
    const { client } = renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    fill("Tiêu đề", saved.title)
    void client.invalidateQueries({ queryKey: queryKeys.adminAssessment(assessment.id) })
    await waitFor(() => expect(api.getAdminAssessment).toHaveBeenCalledTimes(2))
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminAssessment).toHaveBeenCalledWith(assessment.id, { title: saved.title, description: null, pass_threshold: 90 }))
    await waitFor(() => expect(api.getAdminAssessment).toHaveBeenCalledTimes(3))
    expect(client.getQueryData(queryKeys.adminAssessment(assessment.id))).toEqual(saved)
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    expect(screen.getByLabelText("Mô tả")).toHaveValue(saved.description)
    expect(screen.getByLabelText("Điểm đạt (%)")).toHaveValue(85)
    await act(async () => { stale.resolve({ ...assessment, title: 'Stale background assessment' }); await Promise.resolve() })
    expect(client.getQueryData(queryKeys.adminAssessment(assessment.id))).toEqual(saved)
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    await act(async () => { canonical.resolve({ ...saved, title: 'Canonical assessment' }) })
    await waitFor(() => expect(screen.getByLabelText("Tiêu đề")).toHaveValue('Canonical assessment'))
    expect(screen.getByRole('heading', { name: 'Canonical assessment' })).toBeInTheDocument()
  })

  it('retains confirmed Assessment metadata when canonical GET fails', async () => {
    const saved = { ...assessment, title: 'Saved assessment', description: 'Saved description', pass_threshold: 85 }
    vi.mocked(api.updateAdminAssessment).mockResolvedValueOnce(saved)
    vi.mocked(api.getAdminAssessment).mockResolvedValueOnce(assessment).mockRejectedValueOnce(apiError(503, 'TEMPORARY_FAILURE'))
    const { client } = renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    fill("Tiêu đề", saved.title)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminAssessment).toHaveBeenCalledTimes(1))
    expect(await screen.findByText("Chưa cập nhật được bài luyện tập. Đang hiển thị dữ liệu đã tải.")).toBeInTheDocument()
    expect(client.getQueryData(queryKeys.adminAssessment(assessment.id))).toEqual(saved)
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    expect(screen.getByLabelText("Mô tả")).toHaveValue(saved.description)
    expect(screen.getByLabelText("Điểm đạt (%)")).toHaveValue(85)
    expect(screen.getByRole('button', { name: "Lưu thông tin" })).toBeDisabled()
  })

  it('retains an Assessment draft after failed PATCH and retries only after another Save', async () => {
    const saved = { ...assessment, title: 'Local draft' }
    vi.mocked(api.updateAdminAssessment).mockRejectedValueOnce(apiError(503, 'NETWORK_ERROR')).mockResolvedValueOnce(saved)
    vi.mocked(api.getAdminAssessment).mockResolvedValueOnce(assessment).mockResolvedValueOnce(saved)
    renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    fill("Tiêu đề", saved.title)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Có sự cố tạm thời. Vui lòng thử lại.")
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    expect(screen.getByRole('button', { name: "Lưu thông tin" })).toBeEnabled()
    expect(api.updateAdminAssessment).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminAssessment).toHaveBeenCalledTimes(2))
    expect(api.updateAdminAssessment).toHaveBeenLastCalledWith(assessment.id, { title: saved.title, description: null, pass_threshold: 90 })
  })

  it('keeps a dirty Assessment draft and conflict invalidation after 409 until explicit retry', async () => {
    const server = { ...assessment, title: 'Server revision' }
    const saved = { ...server, title: 'Local draft' }
    vi.mocked(api.getAdminAssessment).mockResolvedValueOnce(assessment).mockResolvedValueOnce(server).mockResolvedValueOnce(saved)
    vi.mocked(api.updateAdminAssessment).mockRejectedValueOnce(apiError(409, 'ASSESSMENT_IMMUTABLE')).mockResolvedValueOnce(saved)
    const { client } = renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    fill("Tiêu đề", saved.title)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Bài luyện tập này không còn cho phép chỉnh sửa.")
    await waitFor(() => expect(api.getAdminAssessment).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(client.getQueryData(queryKeys.adminAssessment(assessment.id))).toEqual(server))
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(saved.title)
    expect(screen.getByRole('button', { name: "Lưu thông tin" })).toBeEnabled()
    expect(api.updateAdminAssessment).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    await waitFor(() => expect(api.updateAdminAssessment).toHaveBeenCalledTimes(2))
    expect(api.updateAdminAssessment).toHaveBeenLastCalledWith(assessment.id, { title: saved.title, description: null, pass_threshold: 90 })
  })

  it('keeps a 409 draft visible but read-only when canonical status becomes ARCHIVED', async () => {
    const archived = { ...assessment, status: 'ARCHIVED' as const }
    vi.mocked(api.getAdminAssessment).mockResolvedValueOnce(assessment).mockResolvedValueOnce(archived)
    vi.mocked(api.updateAdminAssessment).mockRejectedValueOnce(apiError(409, 'ASSESSMENT_IMMUTABLE'))
    renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    fill("Tiêu đề", 'Unsaved draft')
    fireEvent.click(screen.getByRole('button', { name: "Lưu thông tin" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Bài luyện tập này không còn cho phép chỉnh sửa.")
    expect(await screen.findByText("Trạng thái: Đã lưu trữ")).toBeInTheDocument()
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue('Unsaved draft')
    for (const label of ["Tiêu đề", "Mô tả", "Điểm đạt (%)"]) expect(screen.getByLabelText(label)).toBeDisabled()
    fireEvent.submit(document.querySelector('.admin-assessment-metadata-form')!)
    expect(api.updateAdminAssessment).toHaveBeenCalledTimes(1)
  })

  it('does not carry an unsaved Assessment draft to another Assessment ID', async () => {
    const second = { ...assessment, id: 'assessment-2', title: 'Second assessment', description: 'Second description' }
    vi.mocked(api.getAdminAssessment).mockImplementation(async (id) => id === assessment.id ? assessment : second)
    const { router } = renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    fill("Tiêu đề", 'Unsaved first assessment')
    await act(async () => { await router.navigate(`/admin/assessments/${second.id}`) })
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    confirmOpenDialog('Rời trang')
    expect(await screen.findByRole('heading', { name: second.title })).toBeInTheDocument()
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(second.title)
    expect(screen.getByLabelText("Mô tả")).toHaveValue(second.description)
    expect(api.updateAdminAssessment).not.toHaveBeenCalled()
    await act(async () => { await router.navigate(`/admin/assessments/${assessment.id}`) })
    expect(await screen.findByRole('heading', { name: assessment.title })).toBeInTheDocument()
    expect(screen.getByLabelText("Tiêu đề")).toHaveValue(assessment.title)
  })

  it('allows DRAFT and REVIEW metadata but keeps PUBLISHED and ARCHIVED read-only', async () => {
    const { client } = renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    expect(screen.getByLabelText("Tiêu đề")).toBeEnabled()
    act(() => { client.setQueryData(queryKeys.adminAssessment(assessment.id), { ...assessment, status: 'REVIEW' }) })
    expect(await screen.findByText("Trạng thái: Chờ duyệt")).toBeInTheDocument()
    expect(screen.getByLabelText("Tiêu đề")).toBeEnabled()
    for (const status of ['PUBLISHED', 'ARCHIVED'] as const) {
      act(() => { client.setQueryData(queryKeys.adminAssessment(assessment.id), { ...assessment, status }) })
      expect(await screen.findByText(`Trạng thái: ${adminLabel(status)}`)).toBeInTheDocument()
      for (const label of ["Tiêu đề", "Mô tả", "Điểm đạt (%)"]) expect(screen.getByLabelText(label)).toBeDisabled()
      fireEvent.submit(document.querySelector('.admin-assessment-metadata-form')!)
    }
    expect(api.updateAdminAssessment).not.toHaveBeenCalled()
  })

  it('rejects form submission for unchanged or out-of-range Assessment metadata', async () => {
    renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByText("Trạng thái: Bản nháp")).toBeInTheDocument()
    openMetadata()
    fireEvent.submit(document.querySelector('.admin-assessment-metadata-form')!)
    expect(api.updateAdminAssessment).not.toHaveBeenCalled()
    fill("Điểm đạt (%)", '101')
    expect(screen.getByRole('button', { name: "Lưu thông tin" })).toBeDisabled()
    fireEvent.submit(document.querySelector('.admin-assessment-metadata-form')!)
    expect(api.updateAdminAssessment).not.toHaveBeenCalled()
  })

  it('requires a Question before Review and follows the legal Assessment lifecycle', async () => {
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([question])
    vi.mocked(api.submitAssessmentReview).mockResolvedValue({ ...assessment, status: 'REVIEW' })
    const { client } = renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByRole('button', { name: "Gửi duyệt" })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: "Gửi duyệt" }))
    await waitFor(() => expect(api.submitAssessmentReview).toHaveBeenCalledWith(assessment.id))
    client.setQueryData(queryKeys.adminAssessment(assessment.id), { ...assessment, status: 'REVIEW' })
  })

  it('walks the remaining Assessment lifecycle using canonical refetch and archive confirmation', async () => {
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([question])
    vi.mocked(api.getAdminAssessment)
      .mockResolvedValueOnce(assessment)
      .mockResolvedValueOnce({ ...assessment, status: 'REVIEW' })
      .mockResolvedValueOnce({ ...assessment, status: 'PUBLISHED' })
      .mockResolvedValueOnce({ ...assessment, status: 'ARCHIVED' })
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: "Gửi duyệt" }))
    fireEvent.click(await screen.findByRole('button', { name: "Xuất bản bài luyện tập" }))
    fireEvent.click(await screen.findByRole('button', { name: "Lưu trữ bài luyện tập" }))
    expect(screen.getByRole('dialog', { name: "Lưu trữ bài luyện tập?" })).toBeInTheDocument()
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: "Hủy" }))
    expect(api.archiveAdminAssessment).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: "Lưu trữ bài luyện tập" }))
    confirmOpenDialog("Lưu trữ bài luyện tập")
    await waitFor(() => expect(api.archiveAdminAssessment).toHaveBeenCalledWith(assessment.id))
    expect(api.archiveAdminAssessment).toHaveBeenCalledTimes(1)
    expect(await screen.findByText("Trạng thái: Đã lưu trữ")).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Submit Review|Publish Assessment|Archive Assessment/ })).not.toBeInTheDocument()
  })

  it('prioritizes real lesson drafts and keeps statistics after all management sections', async () => {
    renderAt('/admin')
    expect(screen.getByRole('heading', {name:'Quản trị học liệu'})).toBeInTheDocument()
    const edit=await screen.findByRole('link', {name:'Tiếp tục chỉnh sửa: Greetings'})
    expect(edit).toHaveAttribute('href','/admin/lessons/lesson-1')
    expect(api.listAdminLessons).toHaveBeenCalledWith({status:'DRAFT',page:1,page_size:3})
    expect(api.listAdminAssessments).toHaveBeenCalledWith({assessment_type:'PERIODIC_TEST',page:1,page_size:2})
    const sections=['Bài học','Kiểm tra định kỳ','Sắp xếp HSK','Tài liệu nguồn','Thống kê tóm tắt'].map(name=>screen.getByRole('heading',{name}))
    sections.slice(1).forEach((heading,index)=>expect(sections[index].compareDocumentPosition(heading)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy())
    expect(screen.getByRole('link',{name:'Xem chi tiết'})).toHaveAttribute('href','/admin/stats')
  })

  it('offers creation without fabricating a continuation when no draft exists', async () => {
    vi.mocked(api.listAdminLessons).mockResolvedValue({items:[],page:1,page_size:3,total:0})
    renderAt('/admin')
    expect(await screen.findByText('Bắt đầu bản nháp mới?')).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:/Tiếp tục chỉnh sửa:/})).not.toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Tạo một bản nháp'})).toHaveAttribute('href','/admin/lessons?create=1')
  })

  it('opens the lesson creation form directly from the dashboard', async () => {
    const {router}=renderAt('/admin')
    fireEvent.click(screen.getByRole('link',{name:'Tạo bài học'}))
    expect(await screen.findByRole('heading',{name:"Tạo bài học"})).toBeInTheDocument()
    expect(router.state.location.search).toBe('?create=1')
    expect(screen.getByLabelText("Số thứ tự bài học")).toBeInTheDocument()
  })

  it('opens periodic-test generation from its dashboard section', async () => {
    renderAt('/admin')
    fireEvent.click(screen.getByRole('link',{name:'Tạo đề bằng AI'}))
    expect(await screen.findByRole('heading',{name:"Tạo bản nháp bằng AI"})).toBeInTheDocument()
    expect(screen.getByLabelText("Điểm đạt (%)")).toHaveValue(90)
    expect(screen.queryByLabelText('Loại bài luyện tập')).not.toBeInTheDocument()
  })

  it('isolates a failed draft request from the remaining management actions', async () => {
    vi.mocked(api.listAdminLessons).mockRejectedValue(new Error('temporary'))
    renderAt('/admin')
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể tải bản nháp bài học.')
    expect(screen.getByRole('link',{name:'Sắp xếp bài học'})).toHaveAttribute('href','/admin/lessons?view=curriculum')
    expect(screen.getByRole('link',{name:'Mở kho tài liệu'})).toHaveAttribute('href','/admin/documents')
    expect(screen.getByRole('link',{name:'Tạo bài học'})).toBeInTheDocument()
    expect(await screen.findByText('82.5%')).toBeInTheDocument()
  })

  it('renders backend Stats exactly with empty and null states', async () => {
    vi.mocked(api.getAdminStats).mockResolvedValueOnce({ total_users: 11, users_by_current_hsk: [], average_exercise_score: null })
    renderAt('/admin/stats')
    expect(await screen.findByText('11')).toBeInTheDocument()
    expect(screen.getByText("Chưa có dữ liệu cấp độ HSK của học viên.")).toBeInTheDocument()
    expect(screen.getByText("Chưa có lượt luyện tập bài học được chấm điểm.")).toBeInTheDocument()
    expect(api.getAdminStats).toHaveBeenCalledTimes(1)
  })

  it('renders non-empty Stats aggregates exactly as returned by the backend', async () => {
    vi.mocked(api.getAdminStats).mockResolvedValueOnce({ total_users: 8, users_by_current_hsk: [{ hsk_level: 1, users: 3 }, { hsk_level: 2, users: 5 }], average_exercise_score: 82.5 })
    renderAt('/admin/stats')
    expect(await screen.findByText('8')).toBeInTheDocument()
    expect(screen.getByRole('row', { name: 'HSK 1 3' })).toBeInTheDocument()
    expect(screen.getByRole('row', { name: 'HSK 2 5' })).toBeInTheDocument()
    const tableRegion = screen.getByRole('region', { name: "Bảng học viên theo cấp độ HSK" })
    expect(tableRegion).toHaveAttribute('tabindex', '0')
    expect(within(tableRegion).getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('82.5%')).toBeInTheDocument()
  })

  it('keeps dashboard links usable and retries when statistics fail to load', async () => {
    vi.mocked(api.getAdminStats).mockRejectedValueOnce(new Error('temporary'))
    renderAt('/admin')
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể tải thống kê.')
    expect(screen.getByRole('link', { name: 'Sắp xếp bài học' })).toHaveAttribute('href', '/admin/lessons?view=curriculum')
    fireEvent.click(screen.getByRole('button', { name: 'Thử tải lại thống kê' }))
    expect(await screen.findByText('82.5%')).toBeInTheDocument()
    expect(api.getAdminStats).toHaveBeenCalledTimes(2)
  })
})

describe('type-specific Question editors', () => {
  async function openQuestionForm(type?: string) {
    vi.mocked(api.getAdminAssessment).mockResolvedValue(assessment)
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([])
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: "Thêm câu hỏi" }))
    if (type) fireEvent.change(screen.getByLabelText("Dạng câu hỏi"), { target: { value: type } })
    fill("Nội dung câu hỏi", 'Question prompt')
  }

  it('creates multiple choice with option rows and exactly one correct option', async () => {
    await openQuestionForm()
    fill("Lựa chọn 1", 'A'); fill("Lựa chọn 2", 'B')
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
    await waitFor(() => expect(api.createAssessmentQuestion).toHaveBeenCalledWith(assessment.id, {
      type: 'multiple_choice', prompt: 'Question prompt', order_index: 1, points: 1,
      options: [{ option_text: 'A', is_correct: true }, { option_text: 'B', is_correct: false }],
    }))
  })

  it('creates fill blank with reference answer and accepted_answers config', async () => {
    await openQuestionForm('fill_blank')
    fill("Đáp án tham khảo", '你好'); fill("Đáp án được chấp nhận (mỗi dòng một đáp án)", '您好\n你们好')
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
    await waitFor(() => expect(api.createAssessmentQuestion).toHaveBeenCalledWith(assessment.id, expect.objectContaining({ type: 'fill_blank', reference_answer: '你好', config: { accepted_answers: ['您好', '你们好'] } })))
  })

  it('creates Matching with opaque item IDs and explicit pairs', async () => {
    await openQuestionForm('matching')
    fireEvent.click(screen.getByRole('button', { name: "Thêm mục bên trái" }))
    fireEvent.click(screen.getByRole('button', { name: "Thêm mục bên phải" }))
    fireEvent.click(screen.getByRole('button', { name: "Thêm mục bên trái" }))
    fireEvent.click(screen.getByRole('button', { name: "Thêm mục bên phải" }))
    fireEvent.click(screen.getByRole('button', { name: "Thêm mục bên trái" }))
    fireEvent.click(screen.getByRole('button', { name: "Thêm mục bên phải" }))
    fill("Mục bên trái 1", '你'); fill("Mục bên trái 2", '好'); fill("Mục bên phải 1", 'you'); fill("Mục bên phải 2", 'good')
    const pairs = screen.getAllByLabelText(/Ghép cho/)
    fireEvent.change(pairs[0]!, { target: { value: pairs[0]!.querySelector('option:nth-child(2)')?.getAttribute('value') } })
    fireEvent.change(pairs[1]!, { target: { value: pairs[1]!.querySelector('option:nth-child(3)')?.getAttribute('value') } })
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
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
    expect(await screen.findByRole('heading', { name: "Chỉnh sửa câu hỏi" })).toBeInTheDocument()
    fill("Mục bên trái 1", 'new left')
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
    await waitFor(() => expect(api.updateAssessmentQuestion).toHaveBeenCalledWith(assessment.id, matching.id, expect.objectContaining({ config: { left_items: [{ id: 'left-a', text: 'new left' }], right_items: [{ id: 'right-a', text: 'old right' }], correct_pairs: [{ left_id: 'left-a', right_id: 'right-a' }] } })))
    expect(vi.mocked(api.updateAssessmentQuestion).mock.calls[0]?.[2]).not.toHaveProperty('type')
  })

  it('sets reorder_sentence correct_order to row order while preserving IDs', async () => {
    const reorder = { ...question, type: 'reorder_sentence' as const, config: { items: [{ id: 'second', text: 'second' }, { id: 'first', text: 'first' }], correct_order: ['first', 'second'] } }
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([reorder])
    renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByRole('heading', { name: "Chỉnh sửa câu hỏi" })).toBeInTheDocument()
    expect(screen.getByLabelText('Mảnh câu 1')).toHaveValue('first')
    fireEvent.click(within(document.querySelector('.admin-assessment-question-form')!).getByRole('button', { name: "Đưa second lên" }))
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
    await waitFor(() => expect(api.updateAssessmentQuestion).toHaveBeenCalledWith(assessment.id, reorder.id, expect.objectContaining({ config: { items: [{ id: 'second', text: 'second' }, { id: 'first', text: 'first' }], correct_order: ['second', 'first'] } })))
  })

  it('requires confirmation before deleting a question and reports learner history conflicts', async () => {
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([question])
    vi.mocked(api.deleteAssessmentQuestion).mockRejectedValue(apiError(409, 'QUESTION_HAS_HISTORY'))
    renderAt(`/admin/assessments/${assessment.id}`)
    fireEvent.click(await screen.findByRole('button', { name: "Xóa câu hỏi" }))
    expect(screen.getByRole('dialog', { name: "Xóa câu hỏi?" })).toBeInTheDocument()
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: "Hủy" }))
    expect(api.deleteAssessmentQuestion).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: "Xóa câu hỏi" }))
    confirmOpenDialog("Xóa câu hỏi")
    expect(await screen.findByRole('alert')).toHaveTextContent("Câu hỏi đã có lịch sử làm bài nên không thể xóa.")
    expect(api.deleteAssessmentQuestion).toHaveBeenCalledWith(assessment.id, question.id)
  })

  it.each(['translate_vi_zh', 'translate_zh_vi', 'sentence_writing'] as const)('creates free-form type %s without a config editor', async (type) => {
    await openQuestionForm(type)
    fill("Đáp án tham khảo (không bắt buộc)", 'sample answer')
    fill("Tiêu chí chấm (không bắt buộc)", 'use correct grammar')
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
    await waitFor(() => expect(api.createAssessmentQuestion).toHaveBeenCalledWith(assessment.id, expect.objectContaining({ type, reference_answer: 'sample answer', rubric: 'use correct grammar' })))
    expect(screen.queryByLabelText(/JSON|config/i)).not.toBeInTheDocument()
  })

  it.each(['translate_vi_zh', 'translate_zh_vi', 'sentence_writing'] as const)('clears persisted optional fields on %s edit', async (type) => {
    const existing = { ...question, type, prompt: 'Existing prompt', reference_answer: 'existing answer', rubric: 'existing rubric' } as AdminQuestion
    vi.mocked(api.listAssessmentQuestions).mockResolvedValue([existing])
    renderAt(`/admin/assessments/${assessment.id}`)
    expect(await screen.findByRole('heading', { name: "Chỉnh sửa câu hỏi" })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Đáp án tham khảo (không bắt buộc)"), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText("Tiêu chí chấm (không bắt buộc)"), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
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
    expect(await screen.findByRole('heading', { name: "Chỉnh sửa câu hỏi" })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Đáp án tham khảo (không bắt buộc)"), { target: { value: reference_answer } })
    fireEvent.change(screen.getByLabelText("Tiêu chí chấm (không bắt buộc)"), { target: { value: rubric } })
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
    await waitFor(() => expect(api.updateAssessmentQuestion).toHaveBeenCalledWith(assessment.id, existing.id, expect.objectContaining(expected)))
  })

  it('continues omitting blank optional fields when creating a free-form question', async () => {
    await openQuestionForm('sentence_writing')
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
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
    expect(await screen.findByRole('heading', { name: "Chỉnh sửa câu hỏi" })).toBeInTheDocument()
    expect(screen.getByLabelText("Dạng câu hỏi")).toHaveAttribute('readOnly')
    fill("Nội dung câu hỏi", 'Updated prompt')
    fireEvent.click(screen.getByRole('button', { name: "Lưu câu hỏi" }))
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
