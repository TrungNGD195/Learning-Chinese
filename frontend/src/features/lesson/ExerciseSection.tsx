import { Link } from 'react-router'
import { EmptyState } from '../../components/ui'

export function ExerciseSection({ assessmentIds, theoryCompleted }: { assessmentIds: string[]; theoryCompleted: boolean }) {
  return <section className="lesson-section" id="exercise" aria-labelledby="exercise-title">
    <div className="lesson-section__heading">
      <div><h2 id="exercise-title">Exercise <span lang="zh-Hans" className="academy-section-chinese" aria-hidden="true">练习</span></h2></div>
    </div>
    {!theoryCompleted && assessmentIds.length>0 && <p role="status">Xem hết từ vựng và ngữ pháp của bài để mở luyện tập. Tiến độ của bạn được lưu tự động.</p>}
    {assessmentIds.length === 0 ? <EmptyState title="No exercises yet">No exercises are available in this lesson.</EmptyState> : <ol className="lesson-exercises">
      {assessmentIds.map((assessmentId, index) => <li key={assessmentId}>
        <span>Exercise {index + 1}</span>{theoryCompleted?<Link className="learner-link-action learner-link-action--secondary" to={`/assessments/${encodeURIComponent(assessmentId)}`}>Open Exercise {index + 1}</Link>:<button type="button" className="ui-button" disabled>Open Exercise {index+1}</button>}
      </li>)}
    </ol>}
  </section>
}
