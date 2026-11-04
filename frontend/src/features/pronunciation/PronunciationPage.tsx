import { useQueries, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Alert, Button, LoadingState, PageHeader, StatusBadge, Surface } from '../../components/ui'
import { queryKeys } from '../../app/query/keys'
import { getHskLevels } from '../curriculum/api'
import { getHskProgress, getProgressOverview } from '../progress/api'
import type { components } from '../../types/api.generated'
import { getPronunciationLesson } from './api'
import { HeaderArtwork, SceneIllustration } from '../../components/academy/AcademyArtwork'

export function PronunciationPage() {
  const lesson = useQuery({ queryKey: queryKeys.pronunciationLesson, queryFn: getPronunciationLesson })
  const levels = useQuery({ queryKey: queryKeys.curriculumLevels, queryFn: getHskLevels })
  const overview = useQuery({ queryKey: queryKeys.progressOverview, queryFn: getProgressOverview })
  const levelProgress = useQueries({ queries: (levels.data ?? []).map((level) => ({ queryKey: queryKeys.progressHsk(level.id), queryFn: () => getHskProgress(level.id) })) })
  const complete = Boolean(lesson.data?.completed_at)
  const completedSections = lesson.data?.sections.filter((section) => section.completed_at).length ?? 0

  return <section className="learner-page pronunciation-page learning-hub screen" aria-labelledby="page-title">
    <div className="pronunciation-intro academy-path-hero">
      <PageHeader title="Hành trình học" titleId="page-title" description="Học phát âm, khám phá HSK và theo dõi tiến độ của bạn ở cùng một nơi." artwork={<HeaderArtwork scene="path" pose={complete?'celebrate':'guide'}/>} />
    </div>

    <Surface as="section" className="learning-hub__overview" aria-labelledby="learning-overview-title">
      <div><h2 id="learning-overview-title">Tổng quan học tập</h2></div>
      {overview.isPending && <LoadingState>Đang tải tiến độ…</LoadingState>}
      {overview.isError && !overview.data && <Alert role="alert" tone="error" action={<Button onClick={() => void overview.refetch()}>Thử lại</Button>}>Không thể tải tiến độ học tập.</Alert>}
      {overview.data && <div className="learning-hub__overview-content">
        <div className="learning-hub__overview-score"><strong>{overview.data.progress_percentage}%</strong><span>tiến độ học tập</span></div>
        <progress aria-label="Tiến độ học tập tổng quan" max={100} value={overview.data.progress_percentage} />
        <p>HSK hiện tại: <strong>{overview.data.current_hsk ?? 'Chưa bắt đầu'}</strong></p>
        {overview.isError && <p role="status">Không thể cập nhật; đang hiển thị tiến độ đã tải trước đó.</p>}
      </div>}
    </Surface>

    {lesson.isPending && <LoadingState>Đang tải tiến độ phát âm…</LoadingState>}
    {lesson.isError && !lesson.data && <Alert role="alert" tone="error" action={<Button onClick={() => void lesson.refetch()}>Thử lại</Button>}>Không thể tải bài học phát âm.</Alert>}
    {lesson.data && <Surface as="section" className="learning-hub__pronunciation" aria-labelledby="pronunciation-block-title">
      <div>
        <h2 id="pronunciation-block-title">Bài học phát âm</h2>
        <p>Học lần lượt thanh mẫu, vận mẫu và thanh điệu để mở HSK 1.</p>
        <p className="learning-hub__progress">{completedSections} / 3 phần hoàn thành</p>
      </div>
      <div className="learning-hub__action">
        <StatusBadge tone={complete ? 'success' : 'info'}>{complete ? 'Đã hoàn thành' : 'Bắt đầu học'}</StatusBadge>
        <Link className="learner-link-action" to="/pronunciation/lesson">{complete ? 'Học lại bài phát âm' : 'Mở bài học'}<span aria-hidden="true"> →</span></Link>
      </div>
    </Surface>}

    <section className="learning-hub__levels" aria-labelledby="learning-hsk-title">
      <div><h2 id="learning-hsk-title">Các cấp độ HSK</h2></div>
      {levels.isPending && <LoadingState>Đang tải các cấp độ HSK…</LoadingState>}
      {levels.isError && !levels.data && <Alert role="alert" tone="error" action={<Button onClick={() => void levels.refetch()}>Thử lại</Button>}>Không thể tải các cấp độ HSK.</Alert>}
      {levels.data?.length === 0 && <p>Chưa có cấp độ HSK nào.</p>}
      {levels.data && <ol className="learning-hub__level-list">{levels.data.map((level, index) => {
        const locked = level.state === 'LOCKED'
        const progress = levelProgress[index]
        return <li key={level.id}><Surface as="section" className="learning-hub__level"><SceneIllustration scene="path"/>
          <div><p className="learning-hub__eyebrow">CẤP ĐỘ {level.level_number}</p><h3>{level.title ?? `HSK ${level.level_number}`}</h3>
            {locked && <p>{level.level_number === 1 && !complete ? 'Hoàn thành bài phát âm để mở khóa.' : 'Cấp độ này chưa có bài học khả dụng hoặc chưa đủ điều kiện mở khóa.'}</p>}</div>
          {locked ? <StatusBadge>Đã khóa</StatusBadge> : <Link className="learner-link-action learner-link-action--secondary" to={`/hsk/${level.level_number}`}>Mở HSK {level.level_number}</Link>}
          <div className="learning-hub__level-progress">
            {progress?.isPending && <p role="status">Đang tải tiến độ cấp độ…</p>}
            {progress?.isError && !progress.data && <Alert role="alert" tone="error" action={<Button onClick={() => void progress.refetch()}>Thử lại</Button>}>Không thể tải chi tiết tiến độ.</Alert>}
            {progress?.data && <><div className="learning-hub__level-progress-heading"><span>Tiến độ cấp độ</span><strong>{progress.data.progress_percentage}%</strong></div>
              <progress aria-label={`Tiến độ HSK ${level.level_number}`} max={100} value={progress.data.progress_percentage} />
              <details className="learning-hub__unit-details"><summary>Chi tiết bài học ({progress.data.units.length})</summary>
                {progress.data.units.length ? <ol className="progress-units">{[...progress.data.units].sort((a, b) => a.order_index - b.order_index).map((unit) => <LearningUnit key={unit.id} unit={unit} />)}</ol> : <p>Chưa có bài học trong cấp độ này.</p>}
              </details>
              {progress.isError && <p role="status">Không thể cập nhật; đang hiển thị thông tin đã tải trước đó.</p>}</>}
          </div>
        </Surface></li>
      })}</ol>}
    </section>
  </section>
}

function LearningUnit({ unit }: { unit: components['schemas']['UnitProgress'] }) {
  const label = unit.unit_type === 'LESSON' ? 'Bài học' : 'Bài kiểm tra'
  const title = unit.lesson?.title ?? unit.assessment?.title ?? `${label} ${unit.order_index}`
  const target = unit.unit_type === 'LESSON' ? unit.lesson?.id : unit.assessment?.id
  const href = target ? (unit.unit_type === 'LESSON' ? `/lessons/${target}` : `/assessments/${target}`) : null
  const state = unit.state === 'COMPLETED' ? 'Đã hoàn thành' : unit.state === 'AVAILABLE' ? 'Có thể học' : 'Đã khóa'
  return <li className="progress-unit"><div className="progress-unit__content"><StatusBadge tone={unit.state === 'COMPLETED' ? 'success' : unit.state === 'AVAILABLE' ? 'info' : 'neutral'}>{state}</StatusBadge><h4>{label} {unit.order_index}: {title}</h4></div>
    {unit.state !== 'LOCKED' && href ? <Link className="secondary-action progress-unit__action" to={href}>Mở {label.toLowerCase()}</Link> : <span className="progress-unit__availability">{unit.state === 'LOCKED' ? 'Đã khóa' : 'Chưa khả dụng'}</span>}</li>
}
