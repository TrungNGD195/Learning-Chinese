import {useState} from 'react'
import {useLocation} from 'react-router'
import {Companion,type CompanionPose} from '../../components/academy/Companion'

export function CompanionGuide(){
 const {hash}=useLocation()
 const [pose,setPose]=useState<CompanionPose>('welcome')
 return <details className="profile-companions" id="companions" open={hash==='#companions'||undefined}>
  <summary>Bạn đồng hành<span>Bo · Trúc · Bút</span></summary>
  <p className="profile-companions-intro">Ba người bạn, ba vai trò. Gặp nhau ngay trong những hoạt động học của bạn.</p>
  <div className="profile-companion-row"><Companion pose={pose} decorative/><div><h3>Bo · Người dẫn đường</h3><p>Giúp bạn tiếp tục bài đang học và chúc mừng khi hoàn thành một bài.</p><div className="profile-bo-poses" role="group" aria-label="Biểu cảm của Bo">{([['welcome','Chào đón'],['guide','Hướng dẫn'],['think','Suy nghĩ'],['encourage','Động viên'],['celebrate','Ăn mừng'],['rest','Nghỉ ngơi']] as const).map(([value,label])=><button key={value} type="button" aria-pressed={value===pose} onClick={()=>setPose(value)}>{label}</button>)}</div></div></div>
  <div className="profile-companion-row"><Companion pose="truc" decorative/><div><h3>Trúc · Người giải thích</h3><p>Giải thích khẩu hình, điểm dễ nhầm, cách dùng từ, ngữ pháp và lượng từ.</p></div></div>
  <div className="profile-companion-row"><Companion pose="but" decorative/><div><h3>Bút · Người cùng luyện</h3><p>Hướng dẫn luyện tập, đọc lại câu và gợi ý cách ôn sau khi xem kết quả.</p></div></div>
 </details>
}
