import { useParams } from 'react-router'
import { GreatWallJourneyPage } from '../journey/GreatWallJourneyPage'

export function HskCurriculumPage() {
  const { hskLevel } = useParams()
  return <GreatWallJourneyPage key={hskLevel} requestedLevel={hskLevel}/>
}
