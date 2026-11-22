import { Link } from 'react-router'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Companion } from '../../components/academy/Companion'
import '../../styles/exam-entry-card.css'

type Props = { level: number; unlocked: boolean; completed: number; total: number }

export function ExamEntryCard({ level, unlocked, completed, total }: Props) {
  const content = <>
    <div className="lc-exam-entry__content">
      <h2>Thi thử HSK {level}</h2>
      <p className="lc-exam-entry__description">Thử sức với một đề thi trọn vẹn theo cấu trúc HSK 3.0.</p>
      <p className="lc-exam-entry__skills">Nghe hiểu · Đọc hiểu{level > 1 ? ' · Viết' : ''}</p>
      {unlocked ? <>
        <span className="lc-exam-entry__action">Vào phòng thi <AcademyIcon name="arrow" size={22}/></span>
        <p className="lc-exam-entry__note">Có kết quả, đáp án và giải thích sau khi nộp bài.</p>
      </> : <>
        <div className="lc-exam-entry__progress"><span>{completed}/{total} bài đã hoàn thành</span><progress aria-label="Tiến độ mở bài thi" value={completed} max={total || 1}/></div>
        <p className="lc-exam-entry__lock"><AcademyIcon name="lock" size={19}/><span>Hoàn thành tất cả bài học để mở bài thi.</span></p>
      </>}
    </div>
    <div className="lc-exam-entry__art" aria-hidden="true"><Companion pose="but" decorative/></div>
  </>
  return unlocked
    ? <Link className="lc-exam-entry" to={`/hsk/${level}/exam`}>{content}</Link>
    : <div className="lc-exam-entry lc-exam-entry--locked" role="group" aria-label={`Thi thử HSK ${level}, chưa mở`}>{content}</div>
}
