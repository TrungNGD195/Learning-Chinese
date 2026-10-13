import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import type { components } from '../../types/api.generated'
import { queryKeys } from '../../app/query/keys'
import { getDashboard } from '../dashboard/api'
import { continueLearningPath } from '../dashboard/continueLearning'
import { getAttempt } from './api'

type AnswerResult = components['schemas']['AttemptDetailResponse']['answers'][number]

function matchingItemText(id: string, items: components['schemas']['MatchItemResponse'][] | undefined) { return items?.find((item) => item.id === id)?.text ?? 'Unavailable item' }
function MatchingReview({ answer }: { answer: Extract<AnswerResult, { type: 'matching' }> }) {
  const readablePair = (pair: { left_id: string; right_id: string }) => `${matchingItemText(pair.left_id, answer.config?.left_items)} → ${matchingItemText(pair.right_id, answer.config?.right_items)}`
  return <><h4>Your submitted pairs</h4>{answer.answer?.pairs.length ? <ul>{answer.answer.pairs.map((pair, index) => <li key={`${pair.left_id}-${pair.right_id}-${index}`}>{readablePair(pair)}</li>)}</ul> : <p>No pairs were recorded.</p>}
    {answer.config && <><h4>Correct pairs</h4>{answer.config.correct_pairs.length ? <ul>{answer.config.correct_pairs.map((pair, index) => <li key={`${pair.left_id}-${pair.right_id}-${index}`}>{readablePair(pair)}</li>)}</ul> : <p>No correct pairs are available.</p>}</>}</>
}
function reorderItemText(id: string, items: components['schemas']['ReorderItemResponse'][] | undefined) { return items?.find((item) => item.id === id)?.text ?? 'Unavailable item' }
function AnswerText({ answer }: { answer: AnswerResult }) {
  switch (answer.type) {
    case 'multiple_choice': return <p>{answer.answer ? 'Selected option recorded.' : 'No answer was recorded.'}</p>
    case 'fill_blank': return <p>{answer.answer ? `Your answer: ${answer.answer.text}` : 'No answer was recorded.'}</p>
    case 'matching': return <MatchingReview answer={answer} />
    case 'reorder_sentence': return <><p>Submitted order: {answer.answer?.item_ids.map((id) => reorderItemText(id, answer.config?.items)).join(' ') || 'No order was recorded.'}</p>{answer.config && <p>Correct order: {answer.config.correct_order.map((id) => reorderItemText(id, answer.config?.items)).join(' ') || 'No correct order is available.'}</p>}</>
    case 'translate_vi_zh':
    case 'translate_zh_vi':
    case 'sentence_writing': return <p>{answer.answer ? `Your answer: ${answer.answer.text}` : 'No answer was recorded.'}</p>
  }
}
function GradingLabel({ answer }: { answer: AnswerResult }) {
  switch (answer.grading_status) {
    case 'UNCERTAIN': return <><p className="result-neutral">Uncertain · Needs review</p><p className="result-neutral">This item was not counted in your score.</p></>
    case 'FAILED': return <p className="result-neutral">Grading could not be completed for this answer.</p>
    case 'PENDING': return <p className="result-neutral">Awaiting grading.</p>
    case 'GRADED': return <p className={answer.is_correct === true ? 'result-good' : answer.is_correct === false ? 'result-bad' : 'result-neutral'}>{answer.is_correct === true ? 'Correct' : answer.is_correct === false ? 'Incorrect' : 'Graded'}</p>
  }
}

export function AssessmentResultPage() {
  const { attemptId } = useParams()
  const attemptQuery = useQuery({ queryKey: queryKeys.attempt(attemptId ?? ''), queryFn: () => getAttempt(attemptId!), enabled: !!attemptId })
  const attempt = attemptQuery.data
  const dashboardQuery = useQuery({ queryKey: queryKeys.dashboard, queryFn: getDashboard, enabled: !!attempt && attempt.status === 'GRADED' && attempt.passed === true })
  const continuePath = dashboardQuery.data?.continue_learning ? continueLearningPath(dashboardQuery.data.continue_learning) : null
  if (attemptQuery.isPending) return <section className="screen"><h1 id="page-title">Assessment Result</h1><p role="status">Loading result…</p></section>
  if ((attemptQuery.isError && !attempt) || !attempt) return <section className="screen"><h1 id="page-title">Assessment Result</h1><p role="alert">Could not load assessment result.</p><button className="secondary-action" type="button" onClick={() => void attemptQuery.refetch()}>Retry</button></section>
  const canRetry = attempt.status === 'GRADING_FAILED' || attempt.passed === false
  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">Assessment Result</h1>
    {attemptQuery.isFetching && <p role="status">Refreshing result…</p>}
    {attemptQuery.isError && <p role="status">Could not refresh result. Showing the last loaded result.</p>}
    {dashboardQuery.isError && <p role="status">Continue Learning is temporarily unavailable. <button type="button" onClick={() => void dashboardQuery.refetch()}>Retry</button></p>}
    <section className="learning-card result-summary"><p>Attempt: {attempt.attempt_number}</p><p>Status: <strong>{attempt.status}</strong></p>
      {attempt.status === 'GRADING_FAILED' && <p role="status">Answers were saved, but grading could not be completed.</p>}
      {attempt.status === 'GRADED' && <><p>Score: {attempt.score === null ? 'Not available' : `${attempt.score}%`}</p><p>{attempt.passed === true ? 'Passed' : attempt.passed === false ? 'Not passed' : 'Pass state not available'}</p></>}
      {!['GRADED', 'GRADING_FAILED'].includes(attempt.status) && <p>This attempt does not have a final result yet.</p>}
      {canRetry && <Link className="primary-action" to={`/assessments/${encodeURIComponent(attempt.assessment_id)}`}>Retry</Link>}
      {attempt.status === 'GRADED' && attempt.passed === true && continuePath && <Link className="primary-action" to={continuePath}>Continue Learning</Link>}
    </section>
    <section className="learning-section" aria-labelledby="answer-review-title"><h2 id="answer-review-title">Answer review</h2>
      {attempt.answers.length === 0 ? <p>No answer details are available.</p> : <div className="section-grid">{attempt.answers.map((answer, index) => <article className="learning-card" key={`${answer.question_id}-${index}`}>
        <h3>Question {index + 1}</h3><p>{answer.prompt}</p><AnswerText answer={answer} /><GradingLabel answer={answer} />
        {answer.score !== null && <p>Score: {answer.score}</p>}{answer.feedback && <p>Feedback: {answer.feedback}</p>}{answer.reference_answer && <p>Reference answer: {answer.reference_answer}</p>}{answer.rubric && <p>Rubric: {answer.rubric}</p>}
      </article>)}</div>}
    </section>
  </section>
}
