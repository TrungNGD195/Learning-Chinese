import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { getDashboard } from './api'
import { continueLearningPath } from './continueLearning'

export function DashboardPage() {
  const dashboardQuery = useQuery({ queryKey: queryKeys.dashboard, queryFn: getDashboard })
  const dashboard = dashboardQuery.data

  if (dashboardQuery.isPending) return <section className="screen"><h1 id="page-title">Dashboard</h1><p role="status">Loading learning overview…</p></section>
  if ((dashboardQuery.isError && !dashboard) || !dashboard) return <section className="screen"><h1 id="page-title">Dashboard</h1><p role="alert">Could not load your learning overview.</p>
    <button className="secondary-action" type="button" onClick={() => void dashboardQuery.refetch()}>Retry</button></section>

  const continuePath = dashboard.continue_learning ? continueLearningPath(dashboard.continue_learning) : null
  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">Dashboard</h1>
    {dashboardQuery.isError && <p role="status">Could not refresh learning overview. Showing the last loaded information.</p>}
    {dashboardQuery.isFetching && <p role="status">Refreshing learning overview…</p>}
    <div className="section-grid">
      <section className="learning-card"><h2>Current HSK</h2>{dashboard.current_hsk ? <Link to={`/hsk/${dashboard.current_hsk.level_number}`}>{dashboard.current_hsk.title ?? `HSK ${dashboard.current_hsk.level_number}`}</Link> : <p>No current HSK level.</p>}</section>
      <section className="learning-card"><h2>Current curriculum unit</h2>{dashboard.current_unit ? <><p>{dashboard.current_unit.unit_type === 'LESSON' ? 'Lesson' : 'Periodic Test'} · {dashboard.current_unit.state}</p><p>Unit {dashboard.current_unit.order_index}</p><p>{dashboard.current_unit.lesson?.title ?? dashboard.current_unit.assessment?.title ?? 'Title unavailable'}</p></> : <p>No current curriculum unit.</p>}</section>
      <section className="learning-card"><h2>Current lesson</h2>{dashboard.current_lesson ? <><h3>{dashboard.current_lesson.title}</h3><p>Lesson {dashboard.current_lesson.lesson_number}</p><p>{dashboard.current_lesson.description}</p></> : <p>No current lesson.</p>}</section>
      <section className="learning-card"><h2>Overall progress</h2><p className="progress-value">{dashboard.progress_percentage}%</p><progress aria-label="Overall progress" max={100} value={dashboard.progress_percentage} /></section>
      <section className="learning-card"><h2>Continue Learning</h2>{continuePath ? <Link className="primary-action" to={continuePath}>Continue Learning</Link> : <p>There is no current Continue Learning target.</p>}</section>
    </div>
  </section>
}
