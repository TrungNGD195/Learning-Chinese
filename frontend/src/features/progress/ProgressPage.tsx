import { useQueries, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import type { components } from '../../types/api.generated'
import { queryKeys } from '../../app/query/keys'
import { Alert, Button, LoadingState, PageHeader, StatusBadge, Surface } from '../../components/ui'
import { getHskProgress, getProgressOverview } from './api'
import academyScene from '../../assets/bg02-academy-morning.png'
import cloudGuideWelcome from '../../assets/cloud-guide-dragon-welcome.png'
import cloudGuideCelebrating from '../../assets/cloud-guide-dragon-celebrating.png'
import { learnerLabel } from '../../lib/learnerLabels'

function progressTone(state: string) {
  if (state === 'COMPLETED') return 'success' as const
  if (state === 'AVAILABLE') return 'info' as const
  if (state === 'LOCKED') return 'neutral' as const
  return 'warning' as const
}

export function ProgressPage() {
  const overviewQuery = useQuery({ queryKey: queryKeys.progressOverview, queryFn: getProgressOverview })
  const levels = overviewQuery.data?.hsk_levels ?? []
  const hskQueries = useQueries({ queries: levels.map((level) => ({ queryKey: queryKeys.progressHsk(level.id), queryFn: () => getHskProgress(level.id) })) })
  if (overviewQuery.isPending) return <section className="screen progress-page"><PageHeader title="Tiến độ học tập" titleId="page-title" eyebrow="Tiến độ học tập · 学习进度" /><LoadingState>Đang tải tiến độ…</LoadingState></section>
  if (overviewQuery.isError && !overviewQuery.data) return <section className="screen progress-page"><PageHeader title="Tiến độ học tập" titleId="page-title" eyebrow="Tiến độ học tập · 学习进度" /><Alert role="alert" tone="error">Không thể tải tiến độ học tập.</Alert><Button className="secondary-action" onClick={() => void overviewQuery.refetch()}>Thử lại</Button></section>
  if (hskQueries.some((query) => query.isPending)) return <section className="screen progress-page"><PageHeader title="Tiến độ học tập" titleId="page-title" eyebrow="Tiến độ học tập · 学习进度" /><LoadingState>Đang tải tiến độ…</LoadingState></section>
  if (hskQueries.some((query) => query.isError && !query.data)) return <section className="screen progress-page"><PageHeader title="Tiến độ học tập" titleId="page-title" eyebrow="Tiến độ học tập · 学习进度" /><Alert role="alert" tone="error">Không thể tải tiến độ học tập.</Alert><Button className="secondary-action" onClick={() => { void overviewQuery.refetch(); hskQueries.forEach((query) => { if (query.isError) void query.refetch() }) }}>Thử lại</Button></section>
  const overview = overviewQuery.data!
  const hskProgress = hskQueries.map((query) => query.data!)
  return <section className="screen progress-page" aria-labelledby="page-title">
    <PageHeader title="Tiến độ học tập" titleId="page-title" eyebrow="Tiến độ học tập · 学习进度" description="Lộ trình và tiến độ dựa trên hoạt động học tập đã được ghi nhận." />
    {(overviewQuery.isFetching || hskQueries.some((query) => query.isFetching)) && <p role="status">Đang cập nhật tiến độ…</p>}
    {(overviewQuery.isError || hskQueries.some((query) => query.isError)) && <Alert role="status" tone="warning">Chưa cập nhật được tiến độ. Đang hiển thị thông tin đã tải.</Alert>}
    <Surface as="section" className="progress-overall" aria-labelledby="progress-overall-heading">
      <div className="progress-overall__summary">
        <div className="progress-overall__heading"><p className="progress-eyebrow">Tổng quan học tập của bạn</p><h2 id="progress-overall-heading">Tổng quan học tập</h2></div>
        <strong className="progress-overall__value">Tiến độ tổng quan: {overview.progress_percentage}%</strong>
      </div>
      <progress className="progress-overall__bar" aria-label="Tiến độ tổng quan" max={100} value={overview.progress_percentage} />
      <div className="progress-overall__facts">
        <div className="progress-overall__fact progress-overall__fact--hsk"><span>HSK hiện tại</span><strong>{overview.current_hsk ?? "Chưa bắt đầu"}</strong></div>
        <div className="progress-overall__fact progress-overall__fact--pronunciation"><span>Nền tảng phát âm</span><StatusBadge tone={overview.pronunciation_complete ? 'success' : 'info'}>{overview.pronunciation_complete ? "Đã hoàn thành" : "Đang học"}</StatusBadge></div>
      </div>
      <div className="progress-overall__art" aria-hidden="true">
        <img className="progress-overall__art-scene" src={academyScene} alt="" />
        <img className="progress-overall__art-dragon" src={overview.progress_percentage === 100 ? cloudGuideCelebrating : cloudGuideWelcome} alt="" />
      </div>
    </Surface>
    <section className="progress-levels" aria-labelledby="progress-levels-heading">
      <div className="progress-section-heading"><div><p className="progress-eyebrow">Lộ trình học · 学习路径</p><h2 id="progress-levels-heading">Lộ trình HSK</h2></div></div>
      <ol className="progress-hsk-list">
      {hskProgress.map((curriculum) => {
        const level = overview.hsk_levels.find((item) => item.id === curriculum.hsk.id)
        const title = curriculum.hsk.title ?? `HSK ${curriculum.hsk.level_number}`
        return <li className="progress-hsk-list__item" key={curriculum.hsk.id}><Surface as="section" className="progress-hsk" aria-label={title}>
          <div className="progress-hsk__heading">
            <div className="progress-hsk__identity"><p className="progress-hsk__eyebrow">Giai đoạn học</p><h3><Link to={`/hsk/${curriculum.hsk.level_number}`}>{title}</Link></h3></div>
            <div className="progress-hsk__status"><StatusBadge tone={progressTone(level?.state ?? 'UNAVAILABLE')}>Trạng thái: {learnerLabel(level?.state ?? 'UNAVAILABLE')}</StatusBadge><strong>{curriculum.progress_percentage}%</strong></div>
          </div>
          <progress aria-label={`Tiến độ ${title}`} max={100} value={curriculum.progress_percentage} />
          <ol className="progress-units">{[...curriculum.units].sort((a, b) => a.order_index - b.order_index).map((unit) => <ProgressUnit key={unit.id} unit={unit} />)}</ol>
        </Surface></li>
      })}
      </ol>
    </section>
  </section>
}

function ProgressUnit({ unit }: { unit: components['schemas']['UnitProgress'] }) {
  const label = unit.unit_type === 'LESSON' ? "Bài học" : "Kiểm tra định kỳ"
  const title = unit.lesson?.title ?? unit.assessment?.title ?? `${label} ${unit.order_index}`
  const target = unit.unit_type === 'LESSON' ? unit.lesson?.id : unit.assessment?.id
  const href = target ? (unit.unit_type === 'LESSON' ? `/lessons/${target}` : `/assessments/${target}`) : null
  return <li className="progress-unit">
    <div className="progress-unit__content"><StatusBadge tone={progressTone(unit.state)}>{learnerLabel(unit.state)}</StatusBadge><h4>{label} {unit.order_index}: {title}</h4></div>
    {unit.state !== 'LOCKED' && href ? <Link className="secondary-action progress-unit__action" to={href}>Mở {label.toLocaleLowerCase('vi-VN')}</Link> : <span className="progress-unit__availability">{unit.state === 'LOCKED' ? "Đã khóa" : "Chưa khả dụng"}</span>}
  </li>
}
