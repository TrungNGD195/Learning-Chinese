import { useQuery } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'
import { getAdminStats } from './api'

export function AdminStatsPage() {
  const stats = useQuery({ queryKey: queryKeys.adminStats, queryFn: getAdminStats })
  if (stats.isPending && !stats.data) return <section className="screen"><h1>Admin Stats</h1><p role="status">Loading statistics…</p></section>
  if (stats.isError && !stats.data) return <section className="screen"><h1>Admin Stats</h1><p role="alert">Could not load statistics.</p><button type="button" onClick={() => void stats.refetch()}>Retry</button></section>
  if (!stats.data) return null
  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">Admin Stats</h1>
    {stats.isError && <p role="alert">Statistics could not be refreshed.</p>}
    <div className="section-grid">
      <section className="learning-card"><h2>Total Users</h2><p>{stats.data.total_users}</p></section>
      <section className="learning-card"><h2>Users by Current HSK</h2>
        {stats.data.users_by_current_hsk.length === 0
          ? <p>No learner HSK data yet.</p>
          : <table><thead><tr><th scope="col">HSK Level</th><th scope="col">Users</th></tr></thead><tbody>
            {stats.data.users_by_current_hsk.map((bucket) => <tr key={bucket.hsk_level}><th scope="row">HSK {bucket.hsk_level}</th><td>{bucket.users}</td></tr>)}
          </tbody></table>}
      </section>
      <section className="learning-card"><h2>Average Exercise Score</h2>
        <p>{stats.data.average_exercise_score === null ? 'No graded lesson-exercise attempts yet.' : `${stats.data.average_exercise_score}%`}</p>
      </section>
    </div>
    {stats.isFetching && <p role="status">Refreshing statistics…</p>}
    {stats.isError && <button type="button" onClick={() => void stats.refetch()}>Retry</button>}
  </section>
}
