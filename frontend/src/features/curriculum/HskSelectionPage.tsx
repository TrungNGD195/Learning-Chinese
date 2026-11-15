import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Companion } from '../../components/academy/Companion'
import { Alert, Button, LoadingState } from '../../components/ui'
import { getHskLevels } from './api'
import { CurriculumCover } from './CurriculumCover'
import type { CoverTopic } from './curriculumCoverData'
import { plannedLessonCounts } from '../journey/journeyData'
import '../../styles/academy-curriculum.css'

const descriptions: Record<number, { title: string; description: string; cover: CoverTopic }> = {
  1: { title: 'Bắt đầu từ nền tảng', description: 'Học phát âm trước, rồi làm quen với những bài học đầu tiên.', cover: 'greetings' },
  2: { title: 'Mở rộng giao tiếp', description: 'Chọn cấp độ để xem bài học và tiếp tục rèn luyện.', cover: 'dates-food' },
  3: { title: 'Tiến xa cùng tiếng Trung', description: 'Chọn cấp độ để khám phá các bài học tiếp theo.', cover: 'journey' },
}

export function HskSelectionPage() {
  const levels = useQuery({ queryKey: queryKeys.curriculumLevels, queryFn: getHskLevels })
  return <section className="learning-curriculum lc-selection screen" aria-labelledby="page-title">
    <header className="lc-heading lc-heading--bo-left"><Companion pose="guide" decorative/><div><h1 id="page-title">Giáo trình của bạn</h1><p>Chọn cấp độ phù hợp để bắt đầu hoặc tiếp tục học.</p></div></header>
    {levels.isPending && <LoadingState>Đang tải các cấp độ HSK…</LoadingState>}
    {levels.isError && <Alert tone="error" action={<Button onClick={() => void levels.refetch()}>Thử lại</Button>}>Chưa tải được các cấp độ HSK.</Alert>}
    <nav className="lc-hsk-grid" aria-label="Chọn cấp độ HSK">{[...(levels.data ?? [])].sort((a,b) => a.level_number-b.level_number).map(level => {
      const details = descriptions[level.level_number] ?? { title: level.title, description: 'Chọn cấp độ để xem các bài học.', cover: 'study' as CoverTopic }
      return <Link className="lc-hsk-card" key={level.id} to={`/hsk/${level.level_number}`} aria-label={`HSK ${level.level_number}`}>
        <div className="lc-hsk-art" aria-hidden="true"><CurriculumCover topic={details.cover}/><span>HSK {level.level_number}</span></div>
        <div className="lc-hsk-copy"><h2>{details.title}</h2><p>{details.description}</p><div className="lc-hsk-action"><span>{plannedLessonCounts[level.level_number]} bài học{level.level_number === 1 ? ' · Có phát âm nền tảng' : ''}</span><strong>Xem giáo trình <AcademyIcon name="arrow" size={20}/></strong></div></div>
      </Link>
    })}</nav>
  </section>
}
