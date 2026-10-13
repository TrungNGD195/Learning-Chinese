import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter, Link, RouterProvider, useLocation } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { components } from '../types/api.generated'
import { ApiError } from '../lib/api/errors'
import { queryKeys } from '../app/query/keys'
import { getDashboard } from './dashboard/api'
import { getCurriculum, getHskLevels } from './curriculum/api'
import { getLesson, markGrammarViewed, markVocabularyViewed } from './lesson/api'
import { getLessonProgress, getHskProgress, getProgressOverview } from './progress/api'
import { getAssessment, getAttempt, startAttempt, submitAttempt } from './assessment/api'
import { DashboardPage } from './dashboard/DashboardPage'
import { HskCurriculumPage } from './curriculum/HskCurriculumPage'
import { LessonPage } from './lesson/LessonPage'
import { AssessmentPage } from './assessment/AssessmentPage'
import { AssessmentResultPage } from './assessment/AssessmentResultPage'
import { ProgressPage } from './progress/ProgressPage'

vi.mock('./dashboard/api', () => ({ getDashboard: vi.fn() }))
vi.mock('./curriculum/api', () => ({ getCurriculum: vi.fn(), getHskLevels: vi.fn() }))
vi.mock('./lesson/api', () => ({ getLesson: vi.fn(), markGrammarViewed: vi.fn(), markVocabularyViewed: vi.fn() }))
vi.mock('./progress/api', () => ({ getLessonProgress: vi.fn(), getHskProgress: vi.fn(), getProgressOverview: vi.fn() }))
vi.mock('./assessment/api', () => ({ getAssessment: vi.fn(), getAttempt: vi.fn(), startAttempt: vi.fn(), submitAttempt: vi.fn(), getAttempts: vi.fn() }))

type Lesson = components['schemas']['LessonResponse']
type LessonProgress = components['schemas']['LessonProgressResponse']
type Assessment = components['schemas']['AssessmentResponse']
type Attempt = components['schemas']['AttemptDetailResponse']

const theoryTimestamp = '2026-01-02T03:04:05Z'
const lessonExerciseCases: [string, string[]][] = [['no IDs', []], ['one ID', ['assessment-1']]]

function lessonFixture(): Lesson {
  return {
    id: 'lesson-1', hsk_level_id: 'hsk-1', lesson_number: 1, title: 'Greetings', description: 'Say hello.',
    vocabulary: [{ id: 'vocabulary-link-1', order_index: 1, note: 'A note', example: '你好。',
      item: { id: 'vocabulary-entity-1', hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', part_of_speech: 'phrase' } }],
    grammar: [{ id: 'grammar-link-1', order_index: 1, note: null, example: '我是学生。',
      item: { id: 'grammar-entity-1', name: 'A 是 B', structure: 'A + 是 + B', explanation: 'A is B.', usage: null } }],
    assessment_ids: ['assessment-1', 'assessment-2'],
  }
}

function lessonProgressFixture(viewed = false): LessonProgress {
  return { lesson_id: 'lesson-1', started_at: null, theory_completed_at: null, completed_at: null,
    vocabulary: [{ id: 'vocabulary-link-1', viewed }], grammar: [{ id: 'grammar-link-1', viewed }] }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

function questionFixture(): Assessment['questions'] {
  return [
    { id: 'q-mc', type: 'multiple_choice', prompt: 'Choose one', order_index: 1, points: 1, config: {},
      options: [{ id: 'option-1', option_text: 'Option One' }, { id: 'option-2', option_text: 'Option Two' }] },
    { id: 'q-fill', type: 'fill_blank', prompt: 'Fill the blank', order_index: 2, points: 1, config: {} },
    { id: 'q-match', type: 'matching', prompt: 'Match the pairs', order_index: 3, points: 1,
      config: { left_items: [{ id: 'left-1', text: 'Left one' }], right_items: [{ id: 'right-1', text: 'Right one' }] } },
    { id: 'q-reorder', type: 'reorder_sentence', prompt: 'Reorder the words', order_index: 4, points: 1,
      config: { items: [{ id: 'word-1', text: '你好' }] } },
    { id: 'q-vi-zh', type: 'translate_vi_zh', prompt: 'Translate Vietnamese to Chinese', order_index: 5, points: 1, config: {} },
    { id: 'q-zh-vi', type: 'translate_zh_vi', prompt: 'Translate Chinese to Vietnamese', order_index: 6, points: 1, config: {} },
    { id: 'q-write', type: 'sentence_writing', prompt: 'Write a sentence', order_index: 7, points: 1, config: {} },
  ]
}

function assessmentFixture(questions = questionFixture()): Assessment {
  return { id: 'assessment-1', type: 'LESSON_EXERCISE', title: 'Greetings practice', description: null, pass_threshold: 90, questions }
}

function dashboardFixture(target: NonNullable<components['schemas']['DashboardResponse']['continue_learning']> | null = null): components['schemas']['DashboardResponse'] {
  return { current_hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' }, current_unit: null,
    current_lesson: null, progress_percentage: 37.25, continue_learning: target }
}

function attemptFixture(overrides: Partial<Attempt> = {}): Attempt {
  return { id: 'attempt-1', assessment_id: 'assessment-1', attempt_number: 1, status: 'GRADING_FAILED',
    score: null, passed: null, submitted_at: null, answers: [], ...overrides }
}

function CurrentPath() {
  const location = useLocation()
  return <output data-testid="current-path">{location.pathname}</output>
}

function renderAt(path: string, queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
  const router = createMemoryRouter([
    { path: '/dashboard', element: <DashboardPage /> },
    { path: '/hsk/:hskLevel', element: <HskCurriculumPage /> },
    { path: '/lessons/:lessonId', element: <LessonPage /> },
    { path: '/assessments/:assessmentId', element: <><AssessmentPage /><Link to="/exit">Leave page</Link></> },
    { path: '/assessment-attempts/:attemptId/result', element: <AssessmentResultPage /> },
    { path: '/progress', element: <ProgressPage /> },
    { path: '/exit', element: <CurrentPath /> },
    { path: '*', element: <CurrentPath /> },
  ], { initialEntries: [path] })
  return render(<QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getLesson).mockResolvedValue(lessonFixture())
  vi.mocked(getLessonProgress).mockResolvedValue(lessonProgressFixture())
  vi.mocked(getHskLevels).mockResolvedValue([{ id: 'hsk-1', level_number: 1, title: 'HSK 1', description: null, state: 'AVAILABLE' }])
  vi.mocked(markVocabularyViewed).mockResolvedValue({ viewed_at: theoryTimestamp, theory_completed_at: null })
  vi.mocked(markGrammarViewed).mockResolvedValue({ viewed_at: theoryTimestamp, theory_completed_at: null })
  vi.mocked(getAssessment).mockResolvedValue(assessmentFixture())
  vi.mocked(startAttempt).mockResolvedValue({ id: 'attempt-1', assessment_id: 'assessment-1', attempt_number: 1, status: 'IN_PROGRESS', started_at: theoryTimestamp })
  vi.mocked(submitAttempt).mockResolvedValue({ attempt_id: 'attempt-1', status: 'GRADED', score: 100, passed: true })
  vi.mocked(getAttempt).mockResolvedValue(attemptFixture())
  vi.mocked(getDashboard).mockResolvedValue(dashboardFixture())
  vi.mocked(getCurriculum).mockResolvedValue({ hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' }, units: [] })
  vi.mocked(getProgressOverview).mockResolvedValue({ current_hsk: 1, progress_percentage: 37.25, pronunciation_complete: true,
    hsk_levels: [{ id: 'hsk-1', level_number: 1, title: 'HSK 1', description: null, state: 'AVAILABLE' }] })
  vi.mocked(getHskProgress).mockResolvedValue({ hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' }, progress_percentage: 12.34, units: [] })
})

describe('Step 4.3 lesson and theory behavior', () => {
  it('waits for getLesson to finish before reading persisted lesson progress', async () => {
    const order: string[] = []
    let finishLesson: ((lesson: Lesson) => void) | undefined
    vi.mocked(getLesson).mockImplementation(() => {
      order.push('getLesson started')
      return new Promise((resolve) => { finishLesson = (lesson) => { order.push('getLesson resolved'); resolve(lesson) } })
    })
    vi.mocked(getLessonProgress).mockImplementation(async () => {
      order.push('getLessonProgress started')
      return lessonProgressFixture()
    })

    renderAt('/lessons/lesson-1')
    expect(order).toEqual(['getLesson started'])
    await act(async () => { finishLesson?.(lessonFixture()) })
    expect(await screen.findByRole('heading', { name: 'Lesson 1: Greetings' })).toBeInTheDocument()
    expect(order).toEqual(['getLesson started', 'getLesson resolved', 'getLessonProgress started'])
  })

  it('renders Lesson content and every Exercise without viewed mutations on mount', async () => {
    renderAt('/lessons/lesson-1')
    expect(await screen.findByRole('heading', { name: 'Lesson 1: Greetings' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Vocabulary' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Grammar' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'AI Chat' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Exercise 1' })).toHaveAttribute('href', '/assessments/assessment-1')
    expect(screen.getByRole('link', { name: 'Open Exercise 2' })).toHaveAttribute('href', '/assessments/assessment-2')
    expect(markVocabularyViewed).not.toHaveBeenCalled()
    expect(markGrammarViewed).not.toHaveBeenCalled()
  })

  it('marks unviewed items only on explicit expansion and sends junction IDs', async () => {
    vi.mocked(getLessonProgress).mockResolvedValueOnce(lessonProgressFixture()).mockResolvedValueOnce({
      ...lessonProgressFixture(), vocabulary: [{ id: 'vocabulary-link-1', viewed: true }],
    })
    renderAt('/lessons/lesson-1')
    const vocabulary = await screen.findByRole('heading', { name: '你好' })
    fireEvent.click(within(vocabulary.closest('article') as HTMLElement).getByRole('button', { name: 'Show details' }))
    await waitFor(() => expect(markVocabularyViewed).toHaveBeenCalledWith('lesson-1', 'vocabulary-link-1'))
    expect(await screen.findByText('Viewed')).toBeInTheDocument()
  })

  it('refreshes authoritative progress after the final Vocabulary view and renders backend completion', async () => {
    const completedProgress: LessonProgress = {
      lesson_id: 'lesson-1', started_at: theoryTimestamp, theory_completed_at: theoryTimestamp, completed_at: theoryTimestamp,
      vocabulary: [{ id: 'vocabulary-link-1', viewed: true }], grammar: [{ id: 'grammar-link-1', viewed: true }],
    }
    vi.mocked(getLessonProgress).mockResolvedValueOnce(lessonProgressFixture()).mockResolvedValueOnce(completedProgress)
    renderAt('/lessons/lesson-1')
    const vocabulary = await screen.findByRole('heading', { name: '你好' })
    fireEvent.click(within(vocabulary.closest('article') as HTMLElement).getByRole('button', { name: 'Show details' }))
    await waitFor(() => expect(getLessonProgress).toHaveBeenCalledTimes(2))
    expect(markVocabularyViewed).toHaveBeenCalledWith('lesson-1', 'vocabulary-link-1')
    expect(await screen.findByText('Lesson: Complete')).toBeInTheDocument()
    expect(screen.getByText('Theory: Complete')).toBeInTheDocument()
    expect(screen.getByText('Started: Yes')).toBeInTheDocument()
  })

  it('does not derive completion from viewed rows or the partial viewed-mutation response', async () => {
    const viewedButIncomplete: LessonProgress = {
      lesson_id: 'lesson-1', started_at: null, theory_completed_at: null, completed_at: null,
      vocabulary: [{ id: 'vocabulary-link-1', viewed: true }], grammar: [{ id: 'grammar-link-1', viewed: true }],
    }
    vi.mocked(getLessonProgress).mockResolvedValueOnce(lessonProgressFixture()).mockResolvedValueOnce(viewedButIncomplete)
    vi.mocked(markVocabularyViewed).mockResolvedValue({ viewed_at: theoryTimestamp, theory_completed_at: theoryTimestamp })
    renderAt('/lessons/lesson-1')
    const vocabulary = await screen.findByRole('heading', { name: '你好' })
    const vocabularyCard = vocabulary.closest('article') as HTMLElement
    fireEvent.click(within(vocabularyCard).getByRole('button', { name: 'Show details' }))
    expect(await within(vocabularyCard).findByText('Viewed')).toBeInTheDocument()
    expect(screen.getByText('Theory: In progress')).toBeInTheDocument()
    expect(screen.getByText('Lesson: In progress')).toBeInTheDocument()
  })

  it('uses the same authoritative refresh after a Grammar viewed mutation', async () => {
    const grammarViewedProgress: LessonProgress = {
      ...lessonProgressFixture(), grammar: [{ id: 'grammar-link-1', viewed: true }],
    }
    vi.mocked(getLessonProgress).mockResolvedValueOnce(lessonProgressFixture()).mockResolvedValueOnce(grammarViewedProgress)
    renderAt('/lessons/lesson-1')
    const grammar = await screen.findByRole('heading', { name: 'A 是 B' })
    fireEvent.click(within(grammar.closest('article') as HTMLElement).getByRole('button', { name: 'Show details' }))
    await waitFor(() => expect(getLessonProgress).toHaveBeenCalledTimes(2))
    expect(markGrammarViewed).toHaveBeenCalledWith('lesson-1', 'grammar-link-1')
    expect(await screen.findByText('Viewed')).toBeInTheDocument()
  })

  it('keeps each Vocabulary item pending independently and prevents duplicate same-item mutations', async () => {
    const lesson = lessonFixture()
    lesson.vocabulary = [...lesson.vocabulary, { ...lesson.vocabulary[0], id: 'vocabulary-link-2', order_index: 2 }]
    vi.mocked(getLesson).mockResolvedValue(lesson)
    const first = deferred<Awaited<ReturnType<typeof markVocabularyViewed>>>()
    const second = deferred<Awaited<ReturnType<typeof markVocabularyViewed>>>()
    vi.mocked(markVocabularyViewed).mockImplementation((_lessonId, linkId) => linkId === 'vocabulary-link-1' ? first.promise : second.promise)
    renderAt('/lessons/lesson-1')
    await screen.findByRole('heading', { name: 'Vocabulary' })
    const vocabularyCards = screen.getByRole('heading', { name: 'Vocabulary' }).closest('section')?.querySelectorAll('article')
    const firstCard = vocabularyCards?.[0] as HTMLElement
    const secondCard = vocabularyCards?.[1] as HTMLElement
    const firstButton = within(firstCard).getByRole('button', { name: 'Show details' })
    const secondButton = within(secondCard).getByRole('button', { name: 'Show details' })

    fireEvent.click(firstButton)
    fireEvent.click(secondButton)
    expect(firstButton).toBeDisabled()
    expect(secondButton).toBeDisabled()
    await waitFor(() => expect(markVocabularyViewed).toHaveBeenCalledTimes(2))
    fireEvent.click(firstButton)
    expect(markVocabularyViewed).toHaveBeenCalledTimes(2)

    await act(async () => { first.resolve({ viewed_at: theoryTimestamp, theory_completed_at: null }) })
    await waitFor(() => expect(firstButton).toBeEnabled())
    expect(secondButton).toBeDisabled()
    expect(markVocabularyViewed).toHaveBeenCalledTimes(2)

    await act(async () => { second.resolve({ viewed_at: theoryTimestamp, theory_completed_at: null }) })
    await waitFor(() => expect(secondButton).toBeEnabled())
  })

  it('keeps each Grammar item pending independently and prevents duplicate same-item mutations', async () => {
    const lesson = lessonFixture()
    lesson.grammar = [...lesson.grammar, { ...lesson.grammar[0], id: 'grammar-link-2', order_index: 2 }]
    vi.mocked(getLesson).mockResolvedValue(lesson)
    const first = deferred<Awaited<ReturnType<typeof markGrammarViewed>>>()
    const second = deferred<Awaited<ReturnType<typeof markGrammarViewed>>>()
    vi.mocked(markGrammarViewed).mockImplementation((_lessonId, linkId) => linkId === 'grammar-link-1' ? first.promise : second.promise)
    renderAt('/lessons/lesson-1')
    await screen.findByRole('heading', { name: 'Grammar' })
    const grammarCards = screen.getByRole('heading', { name: 'Grammar' }).closest('section')?.querySelectorAll('article')
    const firstCard = grammarCards?.[0] as HTMLElement
    const secondCard = grammarCards?.[1] as HTMLElement
    const firstButton = within(firstCard).getByRole('button', { name: 'Show details' })
    const secondButton = within(secondCard).getByRole('button', { name: 'Show details' })

    fireEvent.click(firstButton)
    fireEvent.click(secondButton)
    expect(firstButton).toBeDisabled()
    expect(secondButton).toBeDisabled()
    await waitFor(() => expect(markGrammarViewed).toHaveBeenCalledTimes(2))
    fireEvent.click(firstButton)
    expect(markGrammarViewed).toHaveBeenCalledTimes(2)

    await act(async () => { first.resolve({ viewed_at: theoryTimestamp, theory_completed_at: null }) })
    await waitFor(() => expect(firstButton).toBeEnabled())
    expect(secondButton).toBeDisabled()
    expect(markGrammarViewed).toHaveBeenCalledTimes(2)

    await act(async () => { second.resolve({ viewed_at: theoryTimestamp, theory_completed_at: null }) })
    await waitFor(() => expect(secondButton).toBeEnabled())
  })

  it('does not mark already-viewed items and uses the Grammar link ID', async () => {
    vi.mocked(getLessonProgress).mockResolvedValue({ ...lessonProgressFixture(), vocabulary: [{ id: 'vocabulary-link-1', viewed: true }] })
    renderAt('/lessons/lesson-1')
    const buttons = await screen.findAllByRole('button', { name: 'Show details' })
    fireEvent.click(buttons[0])
    expect(markVocabularyViewed).not.toHaveBeenCalled()
    fireEvent.click(buttons[1])
    await waitFor(() => expect(markGrammarViewed).toHaveBeenCalledWith('lesson-1', 'grammar-link-1'))
    expect(markVocabularyViewed).not.toHaveBeenCalled()
  })

  it('keeps a failed viewed mutation unviewed and permits an explicit retry', async () => {
    vi.mocked(markVocabularyViewed).mockRejectedValueOnce(new Error('offline'))
    vi.mocked(getLessonProgress).mockResolvedValueOnce(lessonProgressFixture()).mockResolvedValueOnce({
      ...lessonProgressFixture(), vocabulary: [{ id: 'vocabulary-link-1', viewed: true }],
    })
    renderAt('/lessons/lesson-1')
    const vocabularyHeading = await screen.findByRole('heading', { name: '你好' })
    const vocabularyCard = vocabularyHeading.closest('article') as HTMLElement
    fireEvent.click(within(vocabularyCard).getByRole('button', { name: 'Show details' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not save viewed state')
    expect(vocabularyCard).toHaveTextContent('Not viewed')
    const hideButton = within(vocabularyCard).getByRole('button', { name: 'Hide details' })
    await waitFor(() => expect(hideButton).toBeEnabled())
    fireEvent.click(hideButton)
    fireEvent.click(within(vocabularyCard).getByRole('button', { name: 'Show details' }))
    await waitFor(() => expect(markVocabularyViewed).toHaveBeenCalledTimes(2))
    expect(await within(vocabularyCard).findByText('Viewed')).toBeInTheDocument()
  })
})

describe('Step 4.3 Assessment lifecycle and answer submission', () => {
  it.each(lessonExerciseCases)('renders safely with %s Lesson Exercise IDs', async (_label, assessmentIds) => {
    vi.mocked(getLesson).mockResolvedValue({ ...lessonFixture(), assessment_ids: assessmentIds })
    renderAt('/lessons/lesson-1')
    expect(await screen.findByRole('heading', { name: 'Lesson 1: Greetings' })).toBeInTheDocument()
    if (assessmentIds.length === 0) {
      expect(screen.getByText('No exercises are available in this lesson.')).toBeInTheDocument()
    } else {
      const exerciseLink = screen.getByRole('link', { name: 'Open Exercise 1' })
      expect(exerciseLink).toHaveAttribute('href', '/assessments/assessment-1')
      fireEvent.click(exerciseLink)
      expect(await screen.findByRole('heading', { name: 'Greetings practice' })).toBeInTheDocument()
    }
  })

  it('loads the assessment without starting an Attempt; explicit action renders all seven question types and submits exact shapes', async () => {
    renderAt('/assessments/assessment-1')
    expect(await screen.findByRole('heading', { name: 'Greetings practice' })).toBeInTheDocument()
    expect(getAssessment).toHaveBeenCalledWith('assessment-1')
    expect(startAttempt).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Start / Resume Assessment' }))
    expect(await screen.findByText('Question 1 of 7')).toBeInTheDocument()
    expect(startAttempt).toHaveBeenCalledWith('assessment-1')

    fireEvent.click(screen.getByLabelText('Option One'))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.change(await screen.findByLabelText('Fill the blank'), { target: { value: '你好' } })
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.change(await screen.findByLabelText('Match Left one'), { target: { value: 'right-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Use this order' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.change(await screen.findByLabelText('Translate Vietnamese to Chinese'), { target: { value: '你好' } })
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.change(await screen.findByLabelText('Translate Chinese to Vietnamese'), { target: { value: 'xin chào' } })
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    fireEvent.change(await screen.findByLabelText('Write a sentence'), { target: { value: '你好。' } })
    fireEvent.click(screen.getByRole('button', { name: 'Submit Assessment' }))

    await waitFor(() => expect(submitAttempt).toHaveBeenCalledWith('attempt-1', {
      answers: [
        { question_id: 'q-mc', answer: { option_id: 'option-1' } },
        { question_id: 'q-fill', answer: { text: '你好' } },
        { question_id: 'q-match', answer: { pairs: [{ left_id: 'left-1', right_id: 'right-1' }] } },
        { question_id: 'q-reorder', answer: { item_ids: ['word-1'] } },
        { question_id: 'q-vi-zh', answer: { text: '你好' } },
        { question_id: 'q-zh-vi', answer: { text: 'xin chào' } },
        { question_id: 'q-write', answer: { text: '你好。' } },
      ],
    }))
    expect(await screen.findByRole('heading', { name: 'Assessment Result' })).toBeInTheDocument()
    expect(getAttempt).toHaveBeenCalledWith('attempt-1')
  })

  it('navigates to the same Attempt result after AI_GRADING_UNAVAILABLE and does not resubmit it', async () => {
    vi.mocked(submitAttempt).mockRejectedValueOnce(new ApiError({ status: 503, code: 'AI_GRADING_UNAVAILABLE', message: 'unavailable', details: null }))
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADING_FAILED' }))
    vi.mocked(getAssessment).mockResolvedValue(assessmentFixture(questionFixture().slice(0, 1)))
    renderAt('/assessments/assessment-1')
    fireEvent.click(await screen.findByRole('button', { name: 'Start / Resume Assessment' }))
    fireEvent.click(await screen.findByLabelText('Option One'))
    fireEvent.click(screen.getByRole('button', { name: 'Submit Assessment' }))
    expect(await screen.findByText('Answers were saved, but grading could not be completed.')).toBeInTheDocument()
    expect(getAttempt).toHaveBeenCalledWith('attempt-1')
    expect(screen.getByRole('link', { name: 'Retry' })).toHaveAttribute('href', '/assessments/assessment-1')
    expect(submitAttempt).toHaveBeenCalledTimes(1)
    expect(startAttempt).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('link', { name: 'Retry' }))
    expect(await screen.findByRole('button', { name: 'Start / Resume Assessment' })).toBeInTheDocument()
    expect(startAttempt).toHaveBeenCalledTimes(1)
  })

  it('blocks navigation only for dirty active attempts and supports Stay, Leave, and beforeunload', async () => {
    vi.mocked(getAssessment).mockResolvedValue(assessmentFixture(questionFixture().slice(0, 1)))
    renderAt('/assessments/assessment-1')
    expect(screen.queryByRole('alertdialog', { name: 'Unsaved assessment answers' })).not.toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: 'Start / Resume Assessment' }))
    fireEvent.click(await screen.findByLabelText('Option One'))
    const beforeUnload = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(beforeUnload)
    expect(beforeUnload.defaultPrevented).toBe(true)

    fireEvent.click(screen.getByRole('link', { name: 'Leave page' }))
    expect(await screen.findByRole('alertdialog', { name: 'Unsaved assessment answers' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Stay' }))
    expect(screen.getByRole('heading', { name: 'Greetings practice' })).toBeInTheDocument()
    expect(screen.queryByTestId('current-path')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: 'Leave page' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Leave' }))
    expect(await screen.findByTestId('current-path')).toHaveTextContent('/exit')
  })

  it('preserves answers after other submit failures', async () => {
    vi.mocked(getAssessment).mockResolvedValue(assessmentFixture(questionFixture().slice(0, 1)))
    vi.mocked(submitAttempt).mockRejectedValueOnce(new ApiError({ status: null, code: 'NETWORK_ERROR', message: 'offline', details: null }))
    renderAt('/assessments/assessment-1')
    fireEvent.click(await screen.findByRole('button', { name: 'Start / Resume Assessment' }))
    const option = await screen.findByLabelText('Option One')
    fireEvent.click(option)
    fireEvent.click(screen.getByRole('button', { name: 'Submit Assessment' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Your answers are still here')
    expect(option).toBeChecked()
  })

  it('renders matching submitted and correct pairs as readable config text while keeping correctness backend-authoritative', async () => {
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADED', answers: [{
      question_id: 'q-match', type: 'matching', prompt: 'Match these', answer: { pairs: [{ left_id: 'left-1', right_id: 'right-2' }, { left_id: 'missing-left', right_id: 'right-1' }] },
      config: {
        left_items: [{ id: 'left-1', text: '你好' }],
        right_items: [{ id: 'right-1', text: 'Hello' }, { id: 'right-2', text: 'Goodbye' }],
        correct_pairs: [{ left_id: 'left-1', right_id: 'right-1' }],
      },
      grading_status: 'GRADED', score: 1, is_correct: true, feedback: null,
    }] }))
    renderAt('/assessment-attempts/attempt-1/result')
    const review = (await screen.findByText('Your submitted pairs')).closest('article') as HTMLElement
    expect(within(review).getByText('你好 → Goodbye')).toBeInTheDocument()
    expect(within(review).getByText('Unavailable item → Hello')).toBeInTheDocument()
    expect(within(review).getByText('你好 → Hello')).toBeInTheDocument()
    expect(within(review).getByText('Correct')).toBeInTheDocument()
    expect(review).not.toHaveTextContent('left-1')
    expect(review).not.toHaveTextContent('right-1')
  })

  it('renders submitted and correct Reorder text while presenting backend grading status', async () => {
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADED', answers: [{
      question_id: 'q-order', type: 'reorder_sentence', prompt: 'Order these words', answer: { item_ids: ['word-2', 'word-1'] },
      config: { items: [{ id: 'word-1', text: '你好' }, { id: 'word-2', text: '世界' }], correct_order: ['word-1', 'word-2'] },
      grading_status: 'GRADED', score: 1, is_correct: true, feedback: null,
    }] }))
    renderAt('/assessment-attempts/attempt-1/result')
    const submitted = await screen.findByText('Submitted order: 世界 你好')
    const review = submitted.closest('article') as HTMLElement
    expect(within(review).getByText('Correct order: 你好 世界')).toBeInTheDocument()
    expect(within(review).getByText('Correct')).toBeInTheDocument()
    expect(review).not.toHaveTextContent('word-1')
  })

  it('still shows backend-public correct review when a Matching or Reorder answer is missing', async () => {
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADED', answers: [
      {
        question_id: 'q-match', type: 'matching', prompt: 'Match these', answer: null,
        config: { left_items: [{ id: 'left-1', text: '你好' }], right_items: [{ id: 'right-1', text: 'Hello' }], correct_pairs: [{ left_id: 'left-1', right_id: 'right-1' }] },
        grading_status: 'GRADED', score: 0, is_correct: false, feedback: null,
      },
      {
        question_id: 'q-order', type: 'reorder_sentence', prompt: 'Order these words', answer: null,
        config: { items: [{ id: 'word-1', text: '你好' }], correct_order: ['word-1'] },
        grading_status: 'GRADED', score: 0, is_correct: false, feedback: null,
      },
    ] }))
    renderAt('/assessment-attempts/attempt-1/result')
    expect(await screen.findByText('你好 → Hello')).toBeInTheDocument()
    expect(screen.getByText('Correct order: 你好')).toBeInTheDocument()
    expect(screen.getAllByText('No pairs were recorded.')).toHaveLength(1)
    expect(screen.getByText('Submitted order: No order was recorded.')).toBeInTheDocument()
  })

  it('does not invent a correct MCQ option in result review', async () => {
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADED', answers: [{
      question_id: 'q-mc', type: 'multiple_choice', prompt: 'Choose one', answer: { option_id: 'private-option-id' },
      config: null, grading_status: 'GRADED', score: 1, is_correct: true, feedback: null,
    }] }))
    renderAt('/assessment-attempts/attempt-1/result')
    const submitted = await screen.findByText('Selected option recorded.')
    const review = submitted.closest('article') as HTMLElement
    expect(within(review).getByText('Correct')).toBeInTheDocument()
    expect(review).not.toHaveTextContent('private-option-id')
    expect(review).not.toHaveTextContent('Correct option')
  })

  it('renders UNCERTAIN neutrally, explains it was not counted, and shows backend feedback', async () => {
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADED', score: null, passed: null, answers: [{
      question_id: 'q-1', type: 'translate_vi_zh', prompt: 'Translate', answer: { text: '你好' }, grading_status: 'UNCERTAIN',
      score: null, is_correct: null, feedback: 'Needs review', reference_answer: '你好', rubric: null,
    }] }))
    renderAt('/assessment-attempts/attempt-1/result')
    expect(await screen.findByText('Uncertain · Needs review')).toBeInTheDocument()
    expect(screen.getByText('This item was not counted in your score.')).toBeInTheDocument()
    expect(screen.getByText('Feedback: Needs review')).toBeInTheDocument()
    expect(screen.queryByText(/^Score: 0/)).not.toBeInTheDocument()
    expect(screen.queryByText('Incorrect')).not.toBeInTheDocument()
  })

  it('keeps partial points visible while using the backend is_correct=false status', async () => {
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADED', score: null, passed: null, answers: [{
      question_id: 'q-1', type: 'sentence_writing', prompt: 'Write', answer: { text: '你好' }, grading_status: 'GRADED',
      score: 1.5, is_correct: false, feedback: 'Partly correct', reference_answer: null, rubric: null,
    }] }))
    renderAt('/assessment-attempts/attempt-1/result')
    const review = (await screen.findByText('Feedback: Partly correct')).closest('article') as HTMLElement
    expect(within(review).getByText('Incorrect')).toBeInTheDocument()
    expect(within(review).getByText('Score: 1.5')).toBeInTheDocument()
    expect(screen.getByText('Score: Not available')).toBeInTheDocument()
    expect(screen.getByText('Pass state not available')).toBeInTheDocument()
  })

  it('renders FAILED without inventing correctness', async () => {
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADING_FAILED', answers: [{
      question_id: 'q-1', type: 'sentence_writing', prompt: 'Write', answer: { text: '你好' }, grading_status: 'FAILED',
      score: null, is_correct: null, feedback: null,
    }] }))
    renderAt('/assessment-attempts/attempt-1/result')
    expect(await screen.findByText('Grading could not be completed for this answer.')).toBeInTheDocument()
    expect(screen.queryByText('Incorrect')).not.toBeInTheDocument()
  })

  it('shows passed-result Continue only for the backend Dashboard target', async () => {
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADED', score: 100, passed: true }))
    vi.mocked(getDashboard).mockResolvedValue(dashboardFixture({
      type: 'LESSON', section_id: null, code: null, lesson_id: 'lesson-next', assessment_id: null,
    }))
    renderAt('/assessment-attempts/attempt-1/result')
    expect(await screen.findByRole('link', { name: 'Continue Learning' })).toHaveAttribute('href', '/lessons/lesson-next')
    expect(getDashboard).toHaveBeenCalledTimes(1)
  })

  it('does not invent a Continue target when the backend returns null', async () => {
    vi.mocked(getAttempt).mockResolvedValue(attemptFixture({ status: 'GRADED', score: 100, passed: true }))
    vi.mocked(getDashboard).mockResolvedValue(dashboardFixture(null))
    renderAt('/assessment-attempts/attempt-1/result')
    expect(await screen.findByText('Passed')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Continue Learning' })).not.toBeInTheDocument()
  })
})

describe('Step 4.3 curriculum, progress, and Continue Learning', () => {
  it('resolves HSK by level number, shows Periodic Tests, and keeps LOCKED units non-actionable', async () => {
    vi.mocked(getCurriculum).mockResolvedValue({ hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' }, units: [
      { id: 'locked-unit', order_index: 1, unit_type: 'LESSON', state: 'LOCKED', lesson: { id: 'locked-lesson', lesson_number: 1, title: 'Locked lesson', status: 'PUBLISHED' }, assessment: null },
      { id: 'periodic-unit', order_index: 2, unit_type: 'PERIODIC_TEST', state: 'AVAILABLE', lesson: null, assessment: { id: 'periodic-1', title: 'HSK 1 Test', type: 'PERIODIC_TEST', status: 'PUBLISHED' } },
    ] })
    renderAt('/hsk/1')
    expect(await screen.findByRole('heading', { name: 'HSK 1 Curriculum' })).toBeInTheDocument()
    expect(getHskLevels).toHaveBeenCalled()
    await waitFor(() => expect(getCurriculum).toHaveBeenCalledWith('hsk-1'))
    expect(screen.getByRole('heading', { name: /Locked lesson/ }).closest('li')).toHaveTextContent('Locked')
    expect(screen.queryByRole('link', { name: 'Open Lesson' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Periodic Test' })).toHaveAttribute('href', '/assessments/periodic-1')
  })

  it('renders backend progress percentages verbatim and includes Periodic Test units', async () => {
    vi.mocked(getHskProgress).mockResolvedValue({ hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' }, progress_percentage: 12.34,
      units: [{ id: 'periodic-unit', order_index: 4, unit_type: 'PERIODIC_TEST', state: 'LOCKED', lesson: null,
        assessment: { id: 'periodic-1', title: 'Periodic checkpoint', type: 'PERIODIC_TEST', status: 'PUBLISHED' } }] })
    renderAt('/progress')
    expect(await screen.findByText('Overall progress: 37.25%')).toBeInTheDocument()
    expect(screen.getByText('12.34%')).toBeInTheDocument()
    expect(screen.getByText('State: AVAILABLE')).toBeInTheDocument()
    expect(screen.getByText('Periodic Test 4: Periodic checkpoint')).toBeInTheDocument()
    expect(screen.queryByText('12%')).not.toBeInTheDocument()
  })

  it.each([
    [{ type: 'PRONUNCIATION', section_id: 'section-1', code: 'pinyin', lesson_id: null, assessment_id: null }, '/pronunciation'],
    [{ type: 'LESSON', section_id: null, code: null, lesson_id: 'lesson-1', assessment_id: null }, '/lessons/lesson-1'],
    [{ type: 'PERIODIC_TEST', section_id: null, code: null, lesson_id: null, assessment_id: 'assessment-1' }, '/assessments/assessment-1'],
  ] as const)('routes Continue Learning from the backend target %s', async (target, href) => {
    vi.mocked(getDashboard).mockResolvedValue(dashboardFixture(target))
    renderAt('/dashboard')
    expect(await screen.findByRole('link', { name: 'Continue Learning' })).toHaveAttribute('href', href)
    expect(screen.getByText('37.25%')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('shows no fabricated target when the backend Continue Learning target is null', async () => {
    vi.mocked(getDashboard).mockResolvedValue(dashboardFixture(null))
    renderAt('/dashboard')
    expect(await screen.findByText('There is no current Continue Learning target.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Continue Learning' })).not.toBeInTheDocument()
  })
})

describe('TanStack Query page errors and background refresh', () => {
  it('renders Dashboard error and retries the backend read', async () => {
    vi.mocked(getDashboard).mockRejectedValueOnce(new Error('temporary failure'))
    renderAt('/dashboard')
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load your learning overview')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('37.25%')).toBeInTheDocument()
    expect(getDashboard).toHaveBeenCalledTimes(2)
  })

  it('renders curriculum error and retries level lookup before loading its curriculum', async () => {
    vi.mocked(getHskLevels).mockRejectedValueOnce(new Error('temporary failure'))
    renderAt('/hsk/1')
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load this curriculum')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Follow the unit order and availability returned by your learning plan.')).toBeInTheDocument()
    expect(getCurriculum).toHaveBeenCalledWith('hsk-1')
  })

  it('renders Lesson error and retries without starting Progress before Lesson succeeds', async () => {
    vi.mocked(getLesson).mockRejectedValueOnce(new Error('temporary failure'))
    renderAt('/lessons/lesson-1')
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load lesson content')
    expect(getLessonProgress).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByRole('heading', { name: 'Lesson 1: Greetings' })).toBeInTheDocument()
    expect(getLessonProgress).toHaveBeenCalledTimes(1)
  })

  it('renders Assessment and Attempt result errors with explicit Retry actions', async () => {
    vi.mocked(getAssessment).mockRejectedValueOnce(new Error('temporary failure'))
    const assessmentRender = renderAt('/assessments/assessment-1')
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load assessment')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByRole('heading', { name: 'Greetings practice' })).toBeInTheDocument()
    assessmentRender.unmount()

    vi.mocked(getAttempt).mockRejectedValueOnce(new Error('temporary failure'))
    renderAt('/assessment-attempts/attempt-1/result')
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load assessment result')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Attempt: 1')).toBeInTheDocument()
  })

  it('renders Progress error and retries its Overview read', async () => {
    vi.mocked(getProgressOverview).mockRejectedValueOnce(new Error('temporary failure'))
    renderAt('/progress')
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load learning progress')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Overall progress: 37.25%')).toBeInTheDocument()
  })

  it('keeps cached Dashboard content visible after a failed background refetch', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    queryClient.setQueryData(queryKeys.dashboard, dashboardFixture())
    vi.mocked(getDashboard).mockRejectedValueOnce(new Error('refresh failed'))
    renderAt('/dashboard', queryClient)
    expect(await screen.findByText(/Could not refresh learning overview/)).toBeInTheDocument()
    expect(screen.getByText('37.25%')).toBeInTheDocument()
  })
})
