import { StudyItemIndex } from '../../components/academy/StudyItemIndex'
import { pronunciationContent } from './pronunciationData'
import { Link } from 'react-router'
import type { PronunciationLessonState } from './api'
import type { PronunciationCode } from './pronunciationData'
import { pronunciationSections, pronunciationSectionPath } from './sectionRoutes'

export function PronunciationStudyHeader({ state, code }: { state?: PronunciationLessonState; code?: PronunciationCode }) {
  const completed = state?.sections.filter(section => section.completed_at).length ?? 0
  return <header className="lesson-header pronunciation-study-header">
    <div className="lesson-header__identity">
      <Link className="lesson-header__back" to={code ? '/pronunciation/lesson' : '/pronunciation'}>{code ? '← Các phần phát âm' : '← Về giáo trình'}</Link>
      <h1 id="page-title">{code ? pronunciationSections[code].title : 'Bài học phát âm'}</h1>
    </div>
    <div className="lesson-header__progress"><p>{state?.completed_at ? 'Đã hoàn thành' : 'Nền tảng phát âm'}</p><div>
      <progress aria-label="Tiến độ toàn bài phát âm" max={state?.sections.length || 4} value={completed}/><span>{completed}/{state?.sections.length || 4} phần</span>
    </div></div>
  </header>
}

export function PronunciationSectionNav({ state, active }: { state: PronunciationLessonState; active: PronunciationCode }) {
  return <nav className="lesson-sequence-nav pronunciation-sections-nav" aria-label="Các phần phát âm">
    {state.sections.map((section, index) => {
      const available = Boolean(section.completed_at) || state.current_section === section.code
      const label = `${section.completed_at ? 'Ôn' : 'Học'} ${pronunciationSections[section.code].title.toLocaleLowerCase('vi')}`
      const content = <><span aria-hidden="true">{index + 1}</span><span>{pronunciationSections[section.code].title}<small>{section.completed_at ? 'Đã xong' : state.current_section === section.code ? 'Đang học' : 'Chưa mở'}</small></span></>
      return available ? <Link key={section.code} to={pronunciationSectionPath(section.code)} aria-label={label} aria-current={active === section.code ? 'page' : undefined}>{content}</Link>
        : <span className="pronunciation-section-locked" key={section.code} aria-disabled="true">{content}</span>
    })}
  </nav>
}


export function PronunciationSoundList({ code, step, pending, onSelect }: {
  code: PronunciationCode; step: number; pending: boolean; onSelect: (step: number) => void
}) {
  const groups = pronunciationContent[code].groups
  return <StudyItemIndex title="Nội dung phát âm" className="pronunciation-sound-index"
    count={`${groups.reduce((total, group) => total + group.sounds.length, 0)} ${code === 'SANDHI' ? 'ví dụ' : 'âm'}`}
    groups={groups.map((group, groupIndex) => {
      const start = groups.slice(0, groupIndex).reduce((total, previous) => total + previous.sounds.length, 0)
      return { title: group.title, items: group.sounds.map((sound, index) => ({ id: sound.symbol, number: start + index + 1,
        text: sound.hanzi || sound.symbol, pinyin: sound.pinyin, active: step === start + index,
        label: `Chọn ${sound.symbol}`, disabled: pending, onSelect: () => onSelect(start + index) })) }
    })}/>
}
