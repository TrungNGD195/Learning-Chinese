import {LessonEntryLink} from '../journey/LessonEntryLink'
import {AcademyIcon} from '../../components/academy/AcademyIcon'
import {CurriculumCover} from './CurriculumCover'

export function FoundationCards({completed,loading,unavailable}:{completed:boolean;loading:boolean;unavailable:boolean}){
 return <div className="lc-foundation-grid" aria-label="Các chuyên đề nền tảng">
  <LessonEntryLink className="lc-foundation-card lc-foundation-card--pronunciation" to="/pronunciation/lesson" aria-label={completed?'Ôn phát âm nền tảng':'Học phát âm nền tảng'}>
   <div className="lc-foundation-art" aria-hidden="true"><CurriculumCover topic="pronunciation"/></div>
   <div className="lc-foundation-copy"><h2>Phát âm nền tảng</h2><p>Thanh mẫu, vận mẫu, thanh điệu và biến điệu.</p><div><span>{loading?'Đang tải tiến độ…':unavailable?'Mở bài phát âm':completed?'Đã hoàn thành · Ôn lại':'Bắt đầu học · Mở khóa HSK 1'}</span><AcademyIcon name="arrow" size={18}/></div></div>
  </LessonEntryLink>
  <LessonEntryLink className="lc-foundation-card lc-foundation-card--supplement" to="/measure-words" aria-label="Học lượng từ">
   <div className="lc-foundation-art" aria-hidden="true"><CurriculumCover topic="measure-words"/></div>
   <div className="lc-foundation-copy"><h2>Lượng từ</h2><p>Chuyên đề bổ trợ. Học bất cứ lúc nào.</p><div><span>Học 10 lượng từ thông dụng</span><AcademyIcon name="arrow" size={18}/></div></div>
  </LessonEntryLink>
 </div>
}
