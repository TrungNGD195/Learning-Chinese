import { useEffect, useRef, useState } from 'react'
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
import { QuestionMedia } from './QuestionMedia'
import { questionForAttempt, skillLabels, difficultyLabels } from './practicePresentation'
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
  const questionNavigation = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const nav = questionNavigation.current
    const active = nav?.querySelector<HTMLElement>('[aria-current=step]')
    if (nav && active && nav.scrollWidth > nav.clientWidth) nav.scrollLeft = active.offsetLeft - nav.offsetLeft - nav.clientWidth / 2 + active.clientWidth / 2
  }, [questionIndex, activeAttemptId])
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
      setError("Không thể bắt đầu hoặc tiếp tục bài luyện tập.")
    }
  }

  async function submit() {
    if (!activeAttemptId || !assessment || submitMutation.isPending) return
    const body = createSubmitRequest(assessment.questions, drafts)
    if (!body) {
      setError("Vui lòng trả lời đầy đủ các câu hỏi trước khi nộp bài.")
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
      } else setError("Không thể nộp bài. Câu trả lời được giữ lại để bạn thử lại khi sẵn sàng.")
    }
  }

  if (assessmentQuery.isPending && !assessment) return <section className="learner-page assessment-page screen" aria-labelledby="page-title">
    <PageHeader title="Luyện tập" titleId="page-title" />
    <LoadingState>Đang tải bài luyện tập…</LoadingState>
  </section>
  if (assessmentQuery.error instanceof ApiError && assessmentQuery.error.code==='THEORY_INCOMPLETE') return <section className="learner-page assessment-page screen" aria-labelledby="page-title"><PageHeader title="Hoàn thành lý thuyết trước" titleId="page-title"/><Alert tone="info">Bạn cần xem hết từ vựng, ngữ pháp và hoàn thành tất cả bài khóa trước khi mở luyện tập.</Alert><Link className="learner-link-action" to="/dashboard">Tiếp tục bài học</Link></section>
  if ((assessmentQuery.isError && !assessment) || !assessment) return <section className="learner-page assessment-page screen" aria-labelledby="page-title">
    <PageHeader title="Luyện tập" titleId="page-title" />
    <Alert role="alert" tone="error" action={<Button onClick={() => void assessmentQuery.refetch()}>Thử lại</Button>}>Không thể tải bài luyện tập.</Alert>
  </section>

  const activeQuestion = activeAttemptId && assessment.questions[questionIndex] ? questionForAttempt(assessment.questions[questionIndex], activeAttemptId) : undefined
  const completeResponseCount = assessment.questions.filter((question) => hasCompleteDraftAnswer(question, drafts[question.id])).length
  const questionCount = assessment.questions.length
  return <section className="learner-page assessment-page screen assessment-screen practice-workspace" aria-labelledby="page-title">
    {assessmentQuery.isFetching && <LoadingState>Đang cập nhật bài luyện tập…</LoadingState>}
    {assessmentQuery.isError && <Alert role="status" tone="warning">Chưa cập nhật được bài luyện tập. Đang hiển thị thông tin đã tải.</Alert>}
    <Surface as="section" className="learner-surface">
      <PageHeader title={assessment.title} titleId="page-title" artwork={false} />
      {!activeAttemptId && <div className="assessment-page__meta"><span>{questionCount} câu hỏi</span><StatusBadge tone="info">Sẵn sàng</StatusBadge></div>}
    </Surface>
    {error && <Alert role="alert" tone="error">{error}</Alert>}
    {!activeAttemptId && <Surface as="section" className="learner-surface assessment-panel">
      <Companion pose="but" decorative/>
      <h2>Bắt đầu khi bạn sẵn sàng</h2>
      <p>{assessment.description || 'Luyện từng câu, xem lại lỗi sai và tiếp tục tiến bộ.'}</p><p>Điểm đạt: <strong>{assessment.pass_threshold}%</strong>. Bạn có thể quay lại các câu trước khi nộp.</p>
      <Button variant="primary" disabled={startMutation.isPending} onClick={() => void beginAttempt()}>{startMutation.isPending ? "Đang bắt đầu…" : "Bắt đầu / Tiếp tục luyện tập"}</Button>
    </Surface>}
    {activeAttemptId && activeQuestion && <div className="practice-layout"><aside className="practice-overview" aria-label="Tiến độ làm bài"><h2>Các câu hỏi</h2><p>Đã trả lời {completeResponseCount}/{questionCount}</p><div className="practice-question-grid" ref={questionNavigation}>{assessment.questions.map((question, index) => <button type="button" key={question.id} aria-label={`Câu ${index + 1}${hasCompleteDraftAnswer(question, drafts[question.id]) ? ', đã trả lời' : ', chưa trả lời'}`} aria-current={index === questionIndex ? 'step' : undefined} data-answered={hasCompleteDraftAnswer(question, drafts[question.id])} disabled={submitMutation.isPending} onClick={() => setQuestionIndex(index)}>{index + 1}</button>)}</div><p className="practice-overview-hint">Chọn số để chuyển câu. Câu đã trả lời được tô xanh.</p></aside><Surface as="section" className="learner-surface assessment-panel assessment-question">
      <div className="assessment-progress">
        <p>Câu hỏi {questionIndex + 1} / {questionCount}</p>
        <progress aria-label={`Câu hỏi ${questionIndex + 1} / ${questionCount}`} max={questionCount} value={questionIndex + 1} />
        <p className="assessment-progress__complete">Đã trả lời: {completeResponseCount} / {questionCount}</p>
      </div>
      {activeQuestion.config.presentation && <div className="practice-question-tags"><span>{skillLabels[activeQuestion.config.presentation.skill]}</span><span>{difficultyLabels[activeQuestion.config.presentation.difficulty]}</span>{activeQuestion.config.presentation.review && <span>Ôn bài trước</span>}</div>}
      <QuestionMedia key={activeQuestion.id} question={activeQuestion}/>
      <QuestionRenderer question={activeQuestion} draft={drafts[activeQuestion.id]} onChange={(answer) => setDrafts((current) => ({ ...current, [activeQuestion.id]: answer }))} />
      <div className="assessment-question__navigation">
        <Button disabled={questionIndex === 0 || submitMutation.isPending} onClick={() => setQuestionIndex((index) => index - 1)}>Trước</Button>
        {questionIndex < questionCount - 1 && <Button variant="primary" disabled={submitMutation.isPending} onClick={() => setQuestionIndex((index) => index + 1)}>Tiếp theo</Button>}
        {questionIndex === questionCount - 1 && <Button variant="primary" disabled={submitMutation.isPending} onClick={() => void submit()}>{submitMutation.isPending ? "Đang nộp bài…" : "Nộp bài"}</Button>}
      </div>
      <p className="practice-save-hint">Câu trả lời được giữ khi chuyển câu. Nộp bài để lưu kết quả và xem giải thích.</p>
    </Surface></div>}
    {activeAttemptId && !activeQuestion && <Surface as="section" className="learner-surface"><p>Bài luyện tập này chưa có câu hỏi.</p></Surface>}
    <Dialog open={blocker.state === 'blocked'} title="Câu trả lời chưa được lưu" cancelLabel="Ở lại" confirmLabel="Rời trang"
      onCancel={() => blocker.reset?.()} onConfirm={() => blocker.proceed?.()}>
      <p>Bạn còn câu trả lời chưa được lưu. Rời trang sẽ mất nội dung đang làm.</p>
    </Dialog>
  </section>
}
