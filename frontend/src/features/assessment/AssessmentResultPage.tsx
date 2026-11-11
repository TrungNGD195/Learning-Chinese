import {Companion} from '../../components/academy/Companion'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import type { components } from '../../types/api.generated'
import { Alert, Button, LoadingState, PageHeader, StatusBadge, Surface } from '../../components/ui'
import { queryKeys } from '../../app/query/keys'
import { getDashboard } from '../dashboard/api'
import { continueLearningPath } from '../dashboard/continueLearning'
import { getAttempt } from './api'
import { learnerLabel } from '../../lib/learnerLabels'

type AnswerResult = components['schemas']['AttemptDetailResponse']['answers'][number]

function matchingItemText(id: string, items: components['schemas']['MatchItemResponse'][] | undefined) { return items?.find((item) => item.id === id)?.text ?? "Nội dung không còn khả dụng" }
function MatchingReview({ answer }: { answer: Extract<AnswerResult, { type: 'matching' }> }) {
  const readablePair = (pair: { left_id: string; right_id: string }) => `${matchingItemText(pair.left_id, answer.config?.left_items)} → ${matchingItemText(pair.right_id, answer.config?.right_items)}`
  return <><h4>Các cặp bạn đã ghép</h4>{answer.answer?.pairs.length ? <ul>{answer.answer.pairs.map((pair, index) => <li key={`${pair.left_id}-${pair.right_id}-${index}`}>{readablePair(pair)}</li>)}</ul> : <p>Chưa ghi nhận cặp ghép nào.</p>}
    {answer.config && <><h4>Các cặp đúng</h4>{answer.config.correct_pairs.length ? <ul>{answer.config.correct_pairs.map((pair, index) => <li key={`${pair.left_id}-${pair.right_id}-${index}`}>{readablePair(pair)}</li>)}</ul> : <p>Chưa có thông tin về các cặp đúng.</p>}</>}</>
}
function reorderItemText(id: string, items: components['schemas']['ReorderItemResponse'][] | undefined) { return items?.find((item) => item.id === id)?.text ?? "Nội dung không còn khả dụng" }
function AnswerText({ answer }: { answer: AnswerResult }) {
  switch (answer.type) {
    case 'multiple_choice': return <p>{answer.selected_option_text ? `Bạn đã chọn: ${answer.selected_option_text}` : answer.answer ? "Đã ghi nhận lựa chọn của bạn." : "Chưa ghi nhận câu trả lời."}</p>
    case 'fill_blank': return <p>{answer.answer ? `Câu trả lời của bạn: ${answer.answer.text}` : "Chưa ghi nhận câu trả lời."}</p>
    case 'matching': return <MatchingReview answer={answer} />
    case 'reorder_sentence': return <><p>Thứ tự đã nộp: {answer.answer?.item_ids.map((id) => reorderItemText(id, answer.config?.items)).join(' ') || "Chưa ghi nhận thứ tự sắp xếp."}</p>{answer.config && <p>Thứ tự đúng: {answer.config.correct_order.map((id) => reorderItemText(id, answer.config?.items)).join(' ') || "Chưa có thông tin về thứ tự đúng."}</p>}</>
    case 'translate_vi_zh':
    case 'translate_zh_vi':
    case 'sentence_writing': return <p>{answer.answer ? `Câu trả lời của bạn: ${answer.answer.text}` : "Chưa ghi nhận câu trả lời."}</p>
  }
}
function GradingLabel({ answer }: { answer: AnswerResult }) {
  switch (answer.grading_status) {
    case 'UNCERTAIN': return <><StatusBadge tone="neutral">Chưa xác định · Cần xem lại</StatusBadge><p>Câu này không được tính vào điểm của bạn.</p></>
    case 'FAILED': return <><StatusBadge tone="warning">Chấm điểm không thành công</StatusBadge><p>Chưa thể chấm điểm câu trả lời này.</p></>
    case 'PENDING': return <StatusBadge tone="neutral">Đang chờ chấm điểm</StatusBadge>
    case 'GRADED': return <StatusBadge tone={answer.is_correct === true ? 'success' : answer.is_correct === false ? 'danger' : 'neutral'}>{answer.is_correct === true ? "Đúng" : answer.is_correct === false ? "Chưa đúng" : "Đã chấm điểm"}</StatusBadge>
  }
}

export function AssessmentResultPage() {
  const [onlyMistakes, setOnlyMistakes] = useState(false)
  const { attemptId } = useParams()
  const attemptQuery = useQuery({ queryKey: queryKeys.attempt(attemptId ?? ''), queryFn: () => getAttempt(attemptId!), enabled: !!attemptId })
  const attempt = attemptQuery.data
  const dashboardQuery = useQuery({ queryKey: queryKeys.dashboard, queryFn: getDashboard, enabled: !!attempt && attempt.status === 'GRADED' && attempt.passed === true })
  const continuePath = dashboardQuery.data?.continue_learning ? continueLearningPath(dashboardQuery.data.continue_learning) : null
  if (attemptQuery.isPending && !attempt) return <section className="learner-page assessment-result-page screen" aria-labelledby="page-title"><PageHeader title="Kết quả luyện tập" titleId="page-title" /><LoadingState>Đang tải kết quả…</LoadingState></section>
  if ((attemptQuery.isError && !attempt) || !attempt) return <section className="learner-page assessment-result-page screen" aria-labelledby="page-title"><PageHeader title="Kết quả luyện tập" titleId="page-title" />
    <Alert role="alert" tone="error" action={<Button onClick={() => void attemptQuery.refetch()}>Thử lại</Button>}>Không thể tải kết quả luyện tập.</Alert></section>

  const canRetry = attempt.status === 'GRADING_FAILED' || attempt.passed === false
  const isPassed = attempt.status === 'GRADED' && attempt.passed === true
  const isNotPassed = attempt.status === 'GRADED' && attempt.passed === false
  const outcome = isPassed ? "Đạt" : isNotPassed ? "Chưa đạt" : attempt.status === 'GRADING_FAILED' ? "Chưa thể chấm điểm" : "Đang chờ kết quả"
  const outcomeTone = isPassed ? 'success' : isNotPassed ? 'warning' : attempt.status === 'GRADING_FAILED' ? 'danger' : 'neutral'
  return <section className="learner-page assessment-result-page screen practice-results" aria-labelledby="page-title">
    <PageHeader title="Kết quả luyện tập" titleId="page-title" artwork={false} />
    {attemptQuery.isFetching && <LoadingState>Đang cập nhật kết quả…</LoadingState>}
    {attemptQuery.isError && <Alert role="status" tone="warning">Chưa cập nhật được kết quả. Đang hiển thị kết quả đã tải.</Alert>}
    {dashboardQuery.isError && <Alert role="status" tone="warning" action={<Button onClick={() => void dashboardQuery.refetch()}>Thử lại</Button>}>Chưa thể tải bước học tiếp theo. Vui lòng thử lại.</Alert>}
    <Surface as="section" className="learner-surface assessment-result-summary" aria-labelledby="assessment-outcome-title">
      {isPassed&&<Companion pose="celebrate" className="result-bo-celebrate" decorative/>}
      <h2 id="assessment-outcome-title">Kết quả bài làm</h2>
      <StatusBadge tone={outcomeTone}>{outcome}</StatusBadge>
      <p>Lần làm: {attempt.attempt_number}</p>
      <p>Trạng thái: <strong>{learnerLabel(attempt.status)}</strong></p>
      {attempt.status === 'GRADING_FAILED' && <p role="status">Câu trả lời đã được lưu, nhưng chưa thể chấm điểm.</p>}
      {attempt.status === 'GRADED' && <><p>Điểm: {attempt.score === null ? "Chưa có thông tin" : `${attempt.score}%`}</p>{attempt.passed === null && <p>Chưa xác định trạng thái đạt</p>}</>}
      {!['GRADED', 'GRADING_FAILED'].includes(attempt.status) && <p>Lần làm bài này chưa có kết quả cuối cùng.</p>}
      {canRetry && <Link className="learner-link-action learner-link-action--secondary assessment-result-summary__primary" to={`/assessments/${encodeURIComponent(attempt.assessment_id)}`}>Thử lại</Link>}
      {isPassed && <Link className="learner-link-action learner-link-action--secondary" to={`/assessments/${encodeURIComponent(attempt.assessment_id)}`}>Làm lại để ôn tập</Link>}
      {isPassed && continuePath && <Link className="learner-link-action assessment-result-summary__primary" to={continuePath}>Tiếp tục học</Link>}
      {isPassed && !continuePath && !dashboardQuery.isError && <p>Chưa có nội dung học tiếp theo.</p>}
    </Surface>
    <section className="assessment-answer-review" aria-labelledby="answer-review-title">
      <h2 id="answer-review-title">Xem lại bài làm</h2>
      <div className="practice-review-toolbar"><p>{attempt.answers.filter(answer => answer.is_correct === true).length}/{attempt.answers.length} câu đúng</p><button type="button" aria-pressed={onlyMistakes} onClick={() => setOnlyMistakes(!onlyMistakes)}>{onlyMistakes ? 'Xem tất cả câu' : 'Chỉ xem câu cần ôn'}</button></div>
      {onlyMistakes && !attempt.answers.some(answer => answer.is_correct !== true) && <p>Bạn đã trả lời đúng tất cả các câu.</p>}
      {attempt.answers.length === 0 ? <p>Chưa có thông tin chi tiết về câu trả lời.</p> : <div className="assessment-answer-list">{attempt.answers.map((answer, index) => onlyMistakes && answer.is_correct === true ? null : <Surface as="article" className="learner-surface assessment-answer-card" data-correct={answer.is_correct} key={`${answer.question_id}-${index}`}>
        <h3>Câu hỏi {index + 1}</h3><p>{answer.prompt}</p><h4>Câu trả lời đã nộp</h4><AnswerText answer={answer} /><GradingLabel answer={answer} />
        {answer.score !== null && <p>Điểm: {answer.score}</p>}{answer.reference_answer && <p className="practice-correct-answer">Đáp án tham khảo: {answer.reference_answer}</p>}{(answer.feedback || answer.rubric) && <div className="practice-explanation"><h4>{answer.is_correct === false ? 'Vì sao câu này chưa đúng?' : 'Ghi nhớ'}</h4><p>{answer.feedback || answer.rubric}</p></div>}
      </Surface>)}</div>}
    </section>
  </section>
}
