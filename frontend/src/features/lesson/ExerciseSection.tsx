import { Link } from 'react-router'

export function ExerciseSection({ assessmentIds }: { assessmentIds: string[] }) {
  return <section className="learning-section" aria-labelledby="exercise-title">
    <h2 id="exercise-title">Exercise</h2>
    {assessmentIds.length === 0 ? <p>No exercises are available in this lesson.</p> : <ol className="exercise-list">
      {assessmentIds.map((assessmentId, index) => <li key={assessmentId}>
        <span>Exercise {index + 1}</span><Link className="secondary-action" to={`/assessments/${encodeURIComponent(assessmentId)}`}>Open Exercise {index + 1}</Link>
      </li>)}
    </ol>}
  </section>
}
