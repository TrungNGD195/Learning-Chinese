import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { getCurriculum, getHskLevels } from './api'

export function HskCurriculumPage() {
  const { hskLevel } = useParams()
  const levelsQuery = useQuery({ queryKey: queryKeys.curriculumLevels, queryFn: getHskLevels })
  const level = levelsQuery.data?.find((item) => String(item.level_number) === hskLevel)
  const curriculumQuery = useQuery({
    queryKey: queryKeys.curriculumHsk(level?.id ?? hskLevel ?? ''),
    queryFn: () => getCurriculum(level!.id),
    enabled: !!level,
  })
  const curriculum = curriculumQuery.data
  const title = curriculum?.hsk.title ?? level?.title ?? `HSK ${hskLevel ?? ''}`
  const loading = levelsQuery.isPending || (!!level && curriculumQuery.isPending)
  const failed = (levelsQuery.isError && !levelsQuery.data) || (!!level && curriculumQuery.isError && !curriculumQuery.data)

  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">{title} Curriculum</h1>
    {loading && <p role="status">Loading curriculum…</p>}
    {failed && <><p role="alert">Could not load this curriculum.</p><button className="secondary-action" type="button" onClick={() => void (levelsQuery.isError ? levelsQuery.refetch() : curriculumQuery.refetch())}>Retry</button></>}
    {!failed && (levelsQuery.isError || curriculumQuery.isError) && <p role="status">Could not refresh curriculum. Showing the last loaded information.</p>}
    {!loading && !failed && !level && <p role="alert">This HSK level was not found.</p>}
    {curriculum && <>
      {curriculumQuery.isFetching && <p role="status">Refreshing curriculum…</p>}
      <p>Follow the unit order and availability returned by your learning plan.</p>
      <ol className="unit-list">
        {[...curriculum.units].sort((a, b) => a.order_index - b.order_index).map((unit) => {
          const label = unit.unit_type === 'LESSON' ? 'Lesson' : 'Periodic Test'
          const titleText = unit.lesson?.title ?? unit.assessment?.title ?? `${label} ${unit.order_index}`
          const destination = unit.unit_type === 'LESSON' ? `/lessons/${unit.lesson?.id}` : `/assessments/${unit.assessment?.id}`
          const actionable = unit.state !== 'LOCKED' && (unit.unit_type === 'LESSON' ? unit.lesson !== null : unit.assessment !== null)
          return <li className="unit-card" key={unit.id}><div><span className="status-label">{unit.state}</span><h2>{label} {unit.order_index}: {titleText}</h2></div>
            {actionable ? <Link className="secondary-action" to={destination}>Open {label}</Link> : <span aria-label={`${label} locked`}>{unit.state === 'LOCKED' ? 'Locked' : 'Unavailable'}</span>}
          </li>
        })}
      </ol>
    </>}
  </section>
}
