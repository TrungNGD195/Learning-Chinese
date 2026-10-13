import { useQueries, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import type { components } from '../../types/api.generated'
import { queryKeys } from '../../app/query/keys'
import { getHskProgress, getProgressOverview } from './api'

export function ProgressPage() {
  const overviewQuery = useQuery({ queryKey: queryKeys.progressOverview, queryFn: getProgressOverview })
  const levels = overviewQuery.data?.hsk_levels ?? []
  const hskQueries = useQueries({ queries: levels.map((level) => ({ queryKey: queryKeys.progressHsk(level.id), queryFn: () => getHskProgress(level.id) })) })
  if (overviewQuery.isPending) return <section className="screen"><h1 id="page-title">Progress</h1><p role="status">Loading progress…</p></section>
  if (overviewQuery.isError && !overviewQuery.data) return <section className="screen"><h1 id="page-title">Progress</h1><p role="alert">Could not load learning progress.</p><button className="secondary-action" type="button" onClick={() => void overviewQuery.refetch()}>Retry</button></section>
  if (hskQueries.some((query) => query.isPending)) return <section className="screen"><h1 id="page-title">Progress</h1><p role="status">Loading progress…</p></section>
  if (hskQueries.some((query) => query.isError && !query.data)) return <section className="screen"><h1 id="page-title">Progress</h1><p role="alert">Could not load learning progress.</p><button className="secondary-action" type="button" onClick={() => { void overviewQuery.refetch(); hskQueries.forEach((query) => { if (query.isError) void query.refetch() }) }}>Retry</button></section>
  const overview = overviewQuery.data!
  const hskProgress = hskQueries.map((query) => query.data!)
  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">Progress</h1>
    {(overviewQuery.isFetching || hskQueries.some((query) => query.isFetching)) && <p role="status">Refreshing progress…</p>}
    {(overviewQuery.isError || hskQueries.some((query) => query.isError)) && <p role="status">Could not refresh progress. Showing the last loaded information.</p>}
    <section className="learning-card"><h2>Pronunciation Foundations</h2><p>{overview.pronunciation_complete ? 'Complete' : 'In progress'}</p><p>Current HSK: {overview.current_hsk ?? 'Not started'}</p><p>Overall progress: {overview.progress_percentage}%</p></section>
    {hskProgress.map((curriculum) => <section className="learning-section" key={curriculum.hsk.id}>
      <div className="section-heading"><h2><Link to={`/hsk/${curriculum.hsk.level_number}`}>{curriculum.hsk.title ?? `HSK ${curriculum.hsk.level_number}`}</Link></h2>
        <span>State: {overview.hsk_levels.find((level) => level.id === curriculum.hsk.id)?.state ?? 'Unavailable'}</span><span>{curriculum.progress_percentage}%</span></div>
      <progress aria-label={`${curriculum.hsk.title ?? `HSK ${curriculum.hsk.level_number}`} progress`} max={100} value={curriculum.progress_percentage} />
      <ol className="unit-list">{[...curriculum.units].sort((a, b) => a.order_index - b.order_index).map((unit) => <ProgressUnit key={unit.id} unit={unit} />)}</ol>
    </section>)}
  </section>
}

function ProgressUnit({ unit }: { unit: components['schemas']['UnitProgress'] }) {
  const label = unit.unit_type === 'LESSON' ? 'Lesson' : 'Periodic Test'
  const title = unit.lesson?.title ?? unit.assessment?.title ?? `${label} ${unit.order_index}`
  const target = unit.unit_type === 'LESSON' ? unit.lesson?.id : unit.assessment?.id
  const href = target ? (unit.unit_type === 'LESSON' ? `/lessons/${target}` : `/assessments/${target}`) : null
  return <li className="unit-card"><div><span className="status-label">{unit.state}</span><h3>{label} {unit.order_index}: {title}</h3></div>
    {unit.state !== 'LOCKED' && href ? <Link className="secondary-action" to={href}>Open {label}</Link> : <span>{unit.state === 'LOCKED' ? 'Locked' : 'Unavailable'}</span>}</li>
}
