import { useState } from 'react'
import { flushSync } from 'react-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useBeforeUnload, useBlocker, useNavigate, useParams } from 'react-router'
import type { components } from '../../types/api.generated'
import { Alert, Button, Dialog, LoadingState, PageHeader, StatusBadge, Surface } from '../../components/ui'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { getAssessment, startAttempt, submitAttempt } from './api'
import { QuestionRenderer, type DraftAnswer } from './QuestionRenderer'
import { createSubmitRequest, hasCompleteDraftAnswer } from './submission'
import { Companion } from '../../components/academy/Companion'

type Assessment = components['schemas']['AssessmentResponse']

export function AssessmentPage() {
  const { assessmentId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeAttemptId, setActiveAttemptId] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, DraftAnswer>>({})
  const [questionIndex, setQuestionIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [allowTerminalNavigation, setAllowTerminalNavigation] = useState(false)
  const assessmentQuery = useQuery({ queryKey: queryKeys.assessment(assessmentId ?? ''), queryFn: () => getAssessment(assessmentId!), enabled: !!assessmentId })
  const assessment: Assessment | undefined = assessmentQuery.data
  const dirty = !!activeAttemptId && Object.keys(drafts).length > 0 && !allowTerminalNavigation
  const blocker = useBlocker(dirty)
  useBeforeUnload((event) => {
    if (dirty) {
      event.preventDefault()
      event.returnValue = ''
    }
  })
  const startMutation = useMutation({ mutationFn: () => startAttempt(assessmentId!) })
  const submitMutation = useMutation({ mutationFn: ({ attemptId, body }: { attemptId: string; body: Parameters<typeof submitAttempt>[1] }) => submitAttempt(attemptId, body) })

  async function beginAttempt() {
    if (!assessmentId || startMutation.isPending) return
    setError(null)
    try {
      const started = await startMutation.mutateAsync()
      setActiveAttemptId(started.id)
    } catch {
      setError('Could not start or resume this assessment.')
    }
  }

  async function submit() {
    if (!activeAttemptId || !assessment || submitMutation.isPending) return
    const body = createSubmitRequest(assessment.questions, drafts)
    if (!body) {
      setError('Complete every question with a valid answer before submitting.')
      return
    }
    setError(null)
    try {
      const result = await submitMutation.mutateAsync({ attemptId: activeAttemptId, body })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.attempt(activeAttemptId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.attemptRoot }),
        queryClient.invalidateQueries({ queryKey: queryKeys.dashboard }),
        queryClient.invalidateQueries({ queryKey: queryKeys.progressOverview }),
        queryClient.invalidateQueries({ queryKey: queryKeys.curriculumLevels }),
        queryClient.invalidateQueries({ queryKey: queryKeys.curriculumHskRoot }),
        queryClient.invalidateQueries({ queryKey: queryKeys.progressHskRoot }),
        queryClient.invalidateQueries({ predicate: (query) => query.queryKey[0] === 'lesson' && query.queryKey[2] === 'progress' }),
      ])
      if (result.status === 'GRADED') {
        flushSync(() => setAllowTerminalNavigation(true))
        navigate(`/assessment-attempts/${encodeURIComponent(result.attempt_id)}/result`)
      }
    } catch (submissionError) {
      if (submissionError instanceof ApiError && submissionError.code === 'AI_GRADING_UNAVAILABLE') {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: queryKeys.attempt(activeAttemptId) }),
          queryClient.invalidateQueries({ queryKey: queryKeys.attemptRoot }),
        ])
        flushSync(() => setAllowTerminalNavigation(true))
        navigate(`/assessment-attempts/${encodeURIComponent(activeAttemptId)}/result`)
      } else setError('Could not submit assessment. Your answers are still here; you can try again when ready.')
    }
  }

  if (assessmentQuery.isPending && !assessment) return <section className="learner-page assessment-page screen" aria-labelledby="page-title">
    <PageHeader title="Assessment" titleId="page-title" />
    <LoadingState>Loading assessment…</LoadingState>
  </section>
  if (assessmentQuery.error instanceof ApiError && assessmentQuery.error.code==='THEORY_INCOMPLETE') return <section className="learner-page assessment-page screen" aria-labelledby="page-title"><PageHeader title="Hoàn thành lý thuyết trước" titleId="page-title"/><Alert tone="info">Bạn cần xem hết từ vựng và ngữ pháp bắt buộc của bài học trước khi mở luyện tập.</Alert><Link className="learner-link-action" to="/dashboard">Tiếp tục bài học</Link></section>
  if ((assessmentQuery.isError && !assessment) || !assessment) return <section className="learner-page assessment-page screen" aria-labelledby="page-title">
    <PageHeader title="Assessment" titleId="page-title" />
    <Alert role="alert" tone="error" action={<Button onClick={() => void assessmentQuery.refetch()}>Retry</Button>}>Could not load assessment.</Alert>
  </section>

  const activeQuestion = activeAttemptId ? assessment.questions[questionIndex] : undefined
  const completeResponseCount = assessment.questions.filter((question) => hasCompleteDraftAnswer(question, drafts[question.id])).length
  const questionCount = assessment.questions.length
  return <section className="learner-page assessment-page screen assessment-screen" aria-labelledby="page-title">
    {assessmentQuery.isFetching && <LoadingState>Refreshing assessment…</LoadingState>}
    {assessmentQuery.isError && <Alert role="status" tone="warning">Could not refresh assessment. Showing the last loaded information.</Alert>}
    <Surface as="section" className="learner-surface">
      <PageHeader title={assessment.title} titleId="page-title" eyebrow={assessment.type === 'LESSON_EXERCISE' ? 'Lesson Exercise' : 'Periodic Test'} description={assessment.description ?? undefined} />
      {!activeAttemptId && <div className="assessment-page__meta"><span>{questionCount} questions</span><StatusBadge tone="info">Ready</StatusBadge></div>}
    </Surface>
    {error && <Alert role="alert" tone="error">{error}</Alert>}
    {!activeAttemptId && <Surface as="section" className="learner-surface assessment-panel">
      <div className="academy-practice-buddy"><Companion pose="but"/><p>Bút cùng bạn luyện tập. Đọc kỹ câu hỏi và làm theo nhịp của bạn.</p></div>
      <h2>Ready when you are</h2>
      <p>Your assessment attempt begins only when you choose to start.</p>
      <Button variant="primary" disabled={startMutation.isPending} onClick={() => void beginAttempt()}>{startMutation.isPending ? 'Starting…' : 'Start / Resume Assessment'}</Button>
    </Surface>}
    {activeAttemptId && activeQuestion && <Surface as="section" className="learner-surface assessment-panel assessment-question">
      <div className="academy-practice-buddy"><Companion pose="think"/><p>Bo đang suy nghĩ cùng bạn. Bạn có thể xem lại các câu trước khi nộp bài.</p></div>
      <div className="assessment-progress">
        <p>Question {questionIndex + 1} of {questionCount}</p>
        <progress aria-label={`Question ${questionIndex + 1} of ${questionCount}`} max={questionCount} value={questionIndex + 1} />
        <p className="assessment-progress__complete">Responses complete: {completeResponseCount} / {questionCount}</p>
      </div>
      <QuestionRenderer question={activeQuestion} draft={drafts[activeQuestion.id]} onChange={(answer) => setDrafts((current) => ({ ...current, [activeQuestion.id]: answer }))} />
      <div className="assessment-question__navigation">
        <Button disabled={questionIndex === 0 || submitMutation.isPending} onClick={() => setQuestionIndex((index) => index - 1)}>Previous</Button>
        {questionIndex < questionCount - 1 && <Button variant="primary" disabled={submitMutation.isPending} onClick={() => setQuestionIndex((index) => index + 1)}>Next</Button>}
        {questionIndex === questionCount - 1 && <Button variant="primary" disabled={submitMutation.isPending} onClick={() => void submit()}>{submitMutation.isPending ? 'Submitting…' : 'Submit Assessment'}</Button>}
      </div>
    </Surface>}
    {activeAttemptId && !activeQuestion && <Surface as="section" className="learner-surface"><p>This assessment has no questions to display.</p></Surface>}
    <Dialog open={blocker.state === 'blocked'} title="Unsaved assessment answers" cancelLabel="Stay" confirmLabel="Leave"
      onCancel={() => blocker.reset?.()} onConfirm={() => blocker.proceed?.()}>
      <p>You have unsaved assessment answers.</p>
    </Dialog>
  </section>
}
