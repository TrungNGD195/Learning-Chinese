import {LessonEntryLink as Link} from '../journey/LessonEntryLink'
import { EmptyState } from '../../components/ui'

export function ExerciseSection({ assessmentIds, theoryCompleted }: { assessmentIds: string[]; theoryCompleted: boolean }) {
  return <section className="lesson-section" id="exercise" aria-labelledby="exercise-title">
    <div className="lesson-section__heading">
      <div><h2 id="exercise-title">Luyện tập <span lang="zh-Hans" className="academy-section-chinese" aria-hidden="true">练习</span></h2></div>
    </div>
    {!theoryCompleted && assessmentIds.length>0 && <p role="status">Xem hết từ vựng, ngữ pháp và hoàn thành tất cả bài khóa để mở luyện tập. Tiến độ của bạn được lưu theo từng mục.</p>}
    {assessmentIds.length === 0 ? <EmptyState title="Chưa có bài luyện tập">Bài học này chưa có bài luyện tập.</EmptyState> : <ol className="lesson-exercises">
      {assessmentIds.map((assessmentId, index) => <li key={assessmentId}>
        <span>Luyện tập {index + 1}</span>{theoryCompleted?<Link className="learner-link-action learner-link-action--secondary" to={`/assessments/${encodeURIComponent(assessmentId)}`}>Mở luyện tập {index + 1}</Link>:<button type="button" className="ui-button" disabled>Mở luyện tập {index+1}</button>}
      </li>)}
    </ol>}
  </section>
}
