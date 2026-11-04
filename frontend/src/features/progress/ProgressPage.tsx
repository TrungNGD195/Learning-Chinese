import { useQueries, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import type { components } from '../../types/api.generated'
import { queryKeys } from '../../app/query/keys'
import { Alert, Button, LoadingState, PageHeader, StatusBadge, Surface } from '../../components/ui'
import { getHskProgress, getProgressOverview } from './api'
import academyScene from '../../assets/bg02-academy-morning.png'
import cloudGuideWelcome from '../../assets/cloud-guide-dragon-welcome.png'
import cloudGuideCelebrating from '../../assets/cloud-guide-dragon-celebrating.png'

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
  if (overviewQuery.isPending) return <section className="screen progress-page"><PageHeader title="Progress" titleId="page-title" eyebrow="学习进度 · LEARNING PROGRESS" /><LoadingState>Loading progress…</LoadingState></section>
  if (overviewQuery.isError && !overviewQuery.data) return <section className="screen progress-page"><PageHeader title="Progress" titleId="page-title" eyebrow="学习进度 · LEARNING PROGRESS" /><Alert role="alert" tone="error">Could not load learning progress.</Alert><Button className="secondary-action" onClick={() => void overviewQuery.refetch()}>Retry</Button></section>
  if (hskQueries.some((query) => query.isPending)) return <section className="screen progress-page"><PageHeader title="Progress" titleId="page-title" eyebrow="学习进度 · LEARNING PROGRESS" /><LoadingState>Loading progress…</LoadingState></section>
  if (hskQueries.some((query) => query.isError && !query.data)) return <section className="screen progress-page"><PageHeader title="Progress" titleId="page-title" eyebrow="学习进度 · LEARNING PROGRESS" /><Alert role="alert" tone="error">Could not load learning progress.</Alert><Button className="secondary-action" onClick={() => { void overviewQuery.refetch(); hskQueries.forEach((query) => { if (query.isError) void query.refetch() }) }}>Retry</Button></section>
  const overview = overviewQuery.data!
  const hskProgress = hskQueries.map((query) => query.data!)
  return <section className="screen progress-page" aria-labelledby="page-title">
    <PageHeader title="Progress" titleId="page-title" eyebrow="学习进度 · LEARNING PROGRESS" description="Your learning path and completion, based on recorded activity." />
    {(overviewQuery.isFetching || hskQueries.some((query) => query.isFetching)) && <p role="status">Refreshing progress…</p>}
    {(overviewQuery.isError || hskQueries.some((query) => query.isError)) && <Alert role="status" tone="warning">Could not refresh progress. Showing the last loaded information.</Alert>}
    <Surface as="section" className="progress-overall" aria-labelledby="progress-overall-heading">
      <div className="progress-overall__summary">
        <div className="progress-overall__heading"><p className="progress-eyebrow">Your learning overview</p><h2 id="progress-overall-heading">Overall learning</h2></div>
        <strong className="progress-overall__value">Overall progress: {overview.progress_percentage}%</strong>
      </div>
      <progress className="progress-overall__bar" aria-label="Overall progress" max={100} value={overview.progress_percentage} />
      <div className="progress-overall__facts">
        <div className="progress-overall__fact progress-overall__fact--hsk"><span>Current HSK</span><strong>{overview.current_hsk ?? 'Not started'}</strong></div>
        <div className="progress-overall__fact progress-overall__fact--pronunciation"><span>Pronunciation Foundations</span><StatusBadge tone={overview.pronunciation_complete ? 'success' : 'info'}>{overview.pronunciation_complete ? 'Complete' : 'In progress'}</StatusBadge></div>
      </div>
      <div className="progress-overall__art" aria-hidden="true">
        <img className="progress-overall__art-scene" src={academyScene} alt="" />
        <img className="progress-overall__art-dragon" src={overview.progress_percentage === 100 ? cloudGuideCelebrating : cloudGuideWelcome} alt="" />
      </div>
    </Surface>
    <section className="progress-levels" aria-labelledby="progress-levels-heading">
      <div className="progress-section-heading"><div><p className="progress-eyebrow">Curriculum · 学习路径</p><h2 id="progress-levels-heading">HSK progression</h2></div></div>
      <ol className="progress-hsk-list">
      {hskProgress.map((curriculum) => {
        const level = overview.hsk_levels.find((item) => item.id === curriculum.hsk.id)
        const title = curriculum.hsk.title ?? `HSK ${curriculum.hsk.level_number}`
        return <li className="progress-hsk-list__item" key={curriculum.hsk.id}><Surface as="section" className="progress-hsk" aria-label={title}>
          <div className="progress-hsk__heading">
            <div className="progress-hsk__identity"><p className="progress-hsk__eyebrow">Learning stage</p><h3><Link to={`/hsk/${curriculum.hsk.level_number}`}>{title}</Link></h3></div>
            <div className="progress-hsk__status"><StatusBadge tone={progressTone(level?.state ?? 'UNAVAILABLE')}>State: {level?.state ?? 'Unavailable'}</StatusBadge><strong>{curriculum.progress_percentage}%</strong></div>
          </div>
          <progress aria-label={`${title} progress`} max={100} value={curriculum.progress_percentage} />
          <ol className="progress-units">{[...curriculum.units].sort((a, b) => a.order_index - b.order_index).map((unit) => <ProgressUnit key={unit.id} unit={unit} />)}</ol>
        </Surface></li>
      })}
      </ol>
    </section>
  </section>
}

function ProgressUnit({ unit }: { unit: components['schemas']['UnitProgress'] }) {
  const label = unit.unit_type === 'LESSON' ? 'Lesson' : 'Periodic Test'
  const title = unit.lesson?.title ?? unit.assessment?.title ?? `${label} ${unit.order_index}`
  const target = unit.unit_type === 'LESSON' ? unit.lesson?.id : unit.assessment?.id
  const href = target ? (unit.unit_type === 'LESSON' ? `/lessons/${target}` : `/assessments/${target}`) : null
  return <li className="progress-unit">
    <div className="progress-unit__content"><StatusBadge tone={progressTone(unit.state)}>{unit.state}</StatusBadge><h4>{label} {unit.order_index}: {title}</h4></div>
    {unit.state !== 'LOCKED' && href ? <Link className="secondary-action progress-unit__action" to={href}>Open {label}</Link> : <span className="progress-unit__availability">{unit.state === 'LOCKED' ? 'Locked' : 'Unavailable'}</span>}
  </li>
}
