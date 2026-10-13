import { useState } from 'react'
import { flushSync } from 'react-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useBeforeUnload, useBlocker, useNavigate, useParams } from 'react-router'
import type { components } from '../../types/api.generated'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { getAssessment, startAttempt, submitAttempt } from './api'
import { QuestionRenderer, type DraftAnswer } from './QuestionRenderer'
import { createSubmitRequest } from './submission'

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

  if (assessmentQuery.isPending) return <section className="screen"><h1 id="page-title">Assessment</h1><p role="status">Loading assessment…</p></section>
  if ((assessmentQuery.isError && !assessment) || !assessment) return <section className="screen"><h1 id="page-title">Assessment</h1><p role="alert">Could not load assessment.</p>
    <button className="secondary-action" type="button" onClick={() => void assessmentQuery.refetch()}>Retry</button></section>

  const activeQuestion = activeAttemptId ? assessment.questions[questionIndex] : undefined
  return <section className="screen assessment-screen" aria-labelledby="page-title">
    {assessmentQuery.isFetching && <p role="status">Refreshing assessment…</p>}
    {assessmentQuery.isError && <p role="status">Could not refresh assessment. Showing the last loaded information.</p>}
    <header className="learning-card"><p className="eyebrow">{assessment.type === 'LESSON_EXERCISE' ? 'Lesson Exercise' : 'Periodic Test'}</p><h1 id="page-title">{assessment.title}</h1>
      {assessment.description && <p>{assessment.description}</p>}{!activeAttemptId && <p>{assessment.questions.length} questions</p>}</header>
    {error && <p role="alert">{error}</p>}
    {!activeAttemptId && <section className="learning-card"><h2>Ready when you are</h2><p>Your assessment attempt begins only when you choose to start.</p>
      <button type="button" className="primary-action" disabled={startMutation.isPending} onClick={() => void beginAttempt()}>{startMutation.isPending ? 'Starting…' : 'Start / Resume Assessment'}</button></section>}
    {activeAttemptId && activeQuestion && <section className="learning-card question-card"><p>Question {questionIndex + 1} of {assessment.questions.length}</p>
      <QuestionRenderer question={activeQuestion} draft={drafts[activeQuestion.id]} onChange={(answer) => setDrafts((current) => ({ ...current, [activeQuestion.id]: answer }))} />
      <div className="question-navigation"><button type="button" className="secondary-action" disabled={questionIndex === 0 || submitMutation.isPending} onClick={() => setQuestionIndex((index) => index - 1)}>Previous</button>
        {questionIndex < assessment.questions.length - 1 && <button type="button" className="secondary-action" disabled={submitMutation.isPending} onClick={() => setQuestionIndex((index) => index + 1)}>Next</button>}
        {questionIndex === assessment.questions.length - 1 && <button type="button" className="primary-action" disabled={submitMutation.isPending} onClick={() => void submit()}>{submitMutation.isPending ? 'Submitting…' : 'Submit Assessment'}</button>}</div>
    </section>}
    {activeAttemptId && !activeQuestion && <section className="learning-card"><p>This assessment has no questions to display.</p></section>}
    {blocker.state === 'blocked' && <section className="learning-card" role="alertdialog" aria-label="Unsaved assessment answers">
      <p>You have unsaved assessment answers.</p><button type="button" className="secondary-action" onClick={() => blocker.reset?.()}>Stay</button>
      <button type="button" className="primary-action" onClick={() => blocker.proceed?.()}>Leave</button>
    </section>}
  </section>
}
