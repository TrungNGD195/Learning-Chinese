import { Link } from 'react-router'

const destinations = [
  ['/admin/curriculum', 'Curriculum', 'Edit HSK display metadata and order existing units.'],
  ['/admin/lessons', 'Lessons', 'Manage lessons and their vocabulary and grammar.'],
  ['/admin/assessments', 'Assessments', 'Manage assessments, questions, and lifecycle.'],
  ['/admin/stats', 'Stats', 'View backend user and exercise aggregates.'],
] as const

export function AdminDashboardPage() {
  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">Admin Dashboard</h1>
    <div className="section-grid admin-link-grid">
      {destinations.map(([to, title, description]) => <Link className="structural-card" to={to} key={to}>
        <h2>{title}</h2><p>{description}</p>
      </Link>)}
    </div>
  </section>
}
