import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { Alert, Button, LoadingState, PageHeader, StatusBadge, Surface } from '../../components/ui'
import { queryKeys } from '../../app/query/keys'
import { getCurriculum, getHskLevels } from './api'
import { SceneIllustration, sceneForTitle } from '../../components/academy/AcademyArtwork'

function stateTone(state: string) {
  if (state === 'COMPLETED') return 'success'
  if (state === 'AVAILABLE') return 'info'
  return 'neutral'
}

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
  const retry = () => void (levelsQuery.isError ? levelsQuery.refetch() : curriculumQuery.refetch())

  return <section className="learner-page curriculum-page screen" aria-labelledby="page-title">
    <div className="curriculum-hero academy-path-hero">
      <PageHeader title={`${title} Curriculum`} titleId="page-title" />
      {curriculum && <p className="curriculum-intro">Follow the unit order and availability returned by your learning plan.</p>}
    </div>
    {loading && <LoadingState>Loading curriculum…</LoadingState>}
    {failed && <Alert role="alert" tone="error" action={<Button onClick={retry}>Retry</Button>}>Could not load this curriculum.</Alert>}
    {!failed && (levelsQuery.isError || curriculumQuery.isError) && <Alert role="status" tone="warning">Could not refresh curriculum. Showing the last loaded information.</Alert>}
    {!loading && !failed && !level && <Alert role="alert" tone="error">This HSK level was not found.</Alert>}
    {curriculum && <>
      {curriculumQuery.isFetching && <LoadingState>Refreshing curriculum…</LoadingState>}
      {curriculum.units.length === 0 ? <Surface as="section" className="learner-surface curriculum-empty-state"><p>No units are available in this learning path yet.</p></Surface> : <ol className="curriculum-path">
        {[...curriculum.units].sort((a, b) => a.order_index - b.order_index).map((unit) => {
          const label = unit.unit_type === 'LESSON' ? 'Lesson' : 'Periodic Test'
          const titleText = unit.lesson?.title ?? unit.assessment?.title ?? `${label} ${unit.order_index}`
          const destination = unit.unit_type === 'LESSON' ? `/lessons/${unit.lesson?.id}` : `/assessments/${unit.assessment?.id}`
          const actionable = unit.state !== 'LOCKED' && (unit.unit_type === 'LESSON' ? unit.lesson !== null : unit.assessment !== null)
          return <li className="learner-surface curriculum-unit" key={unit.id}>
            <SceneIllustration scene={unit.unit_type === 'LESSON' ? sceneForTitle(titleText) : 'practice'}/><div className="curriculum-unit__content">
              <div className="curriculum-unit__heading"><span className="curriculum-unit__type">{label} · Unit {unit.order_index}</span><h2>{label} {unit.order_index}: {titleText}</h2></div>
              <StatusBadge tone={stateTone(unit.state)}>{unit.state}</StatusBadge>
              {!actionable && <span aria-label={unit.state === 'LOCKED' ? `${label} locked` : `${label} unavailable`} className="curriculum-unit__locked">{unit.state === 'LOCKED' ? 'Locked' : 'Unavailable'}</span>}
            </div>
            {actionable && <Link className="learner-link-action learner-link-action--secondary curriculum-unit__action" to={destination}>Open {label}</Link>}
          </li>
        })}
      </ol>}
    </>}
  </section>
}
