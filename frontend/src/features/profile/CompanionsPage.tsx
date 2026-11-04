import { useState } from 'react'
import { Link } from 'react-router'
import { Companion, type CompanionPose } from '../../components/academy/Companion'
import { PageHeader } from '../../components/ui'

export function CompanionsPage(){
  const [pose,setPose]=useState<CompanionPose>('welcome')
  return <section className="learner-page academy-companions-page screen"><PageHeader title="Bo và những người bạn" description="Mỗi bạn đồng hành có một vai trò, xuất hiện đúng lúc bạn cần."/><div className="academy-cast-main"><div><Companion pose={pose}/></div><section><h2>Bo · Người dẫn đường</h2><p>Chào bạn khi quay lại, cùng suy nghĩ khi gặp điều mới và chúc mừng mỗi bước bạn hoàn thành.</p><div className="academy-expressions" role="group" aria-label="Biểu cảm của Bo">{([['welcome','Chào đón'],['guide','Hướng dẫn'],['think','Suy nghĩ'],['encourage','Động viên'],['celebrate','Ăn mừng'],['rest','Nghỉ ngơi']] as const).map(([value,label])=><button type="button" key={value} aria-pressed={pose===value} onClick={()=>setPose(value)}>{label}</button>)}</div></section></div><div className="academy-cast-helpers"><section><Companion pose="truc"/><div><h2>Trúc · Người giải thích</h2><p>Nhắc khẩu hình, chỉ ra âm dễ nhầm và gỡ rối cách dùng từ.</p><Link className="academy-text-link" to="/pronunciation/lesson">Học phát âm cùng Trúc →</Link></div></section><section><Companion pose="but"/><div><h2>Bút · Người cùng luyện</h2><p>Cùng bạn xem lại những điều đã học và cổ vũ khi bạn luyện tập.</p><Link className="academy-text-link" to="/pronunciation">Về hành trình học →</Link></div></section></div></section>
}
