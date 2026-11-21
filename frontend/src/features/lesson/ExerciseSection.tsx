import { useState } from 'react'
import { EmptyState } from '../../components/ui'
import { AssessmentPage } from '../assessment/AssessmentPage'

export function ExerciseSection({ assessmentIds, theoryCompleted }: { assessmentIds: string[]; theoryCompleted: boolean }) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [attemptActive, setAttemptActive] = useState(false)
  const activeId = selectedId && assessmentIds.includes(selectedId) ? selectedId : assessmentIds[0]
  return <section className="lesson-section lesson-inline-practice" id="exercise" aria-label="Luyện tập">
    {(!theoryCompleted || !activeId) && <h2>Luyện tập</h2>}
    {!theoryCompleted && assessmentIds.length>0 && <p role="status">Xem hết từ vựng, ngữ pháp và hoàn thành tất cả bài khóa để mở luyện tập. Tiến độ của bạn được lưu theo từng mục.</p>}
    {assessmentIds.length === 0 ? <EmptyState title="Chưa có bài luyện tập">Bài học này chưa có bài luyện tập.</EmptyState> : !theoryCompleted && <ol className="lesson-exercises">
      {assessmentIds.map((assessmentId, index) => <li key={assessmentId}>
        <span>Luyện tập {index + 1}</span><button type="button" className="ui-button" disabled>Mở luyện tập {index+1}</button>
      </li>)}
    </ol>}
    {theoryCompleted && activeId && <>
      {assessmentIds.length > 1 && <nav className="lesson-practice-selector" aria-label="Chọn bài luyện tập">{assessmentIds.map((id, index) => <button key={id} type="button" className="ui-button" aria-pressed={activeId === id} disabled={attemptActive} onClick={() => setSelectedId(id)}>Luyện tập {index + 1}</button>)}</nav>}
      <AssessmentPage key={activeId} embeddedAssessmentId={activeId} onSessionChange={setAttemptActive}/>
    </>}
  </section>
}
