import type { CSSProperties } from 'react'

export type CompanionPose='welcome'|'guide'|'think'|'encourage'|'celebrate'|'rest'|'truc'|'but'|'but-happy'
const poses:Record<CompanionPose,[number,string]>={welcome:[0,'Bo vẫy tay chào bạn'],guide:[1,'Bo hướng dẫn bài học'],think:[2,'Bo suy nghĩ cùng bạn'],encourage:[3,'Bo động viên bạn thử lại'],celebrate:[4,'Bo chúc mừng bạn hoàn thành'],rest:[5,'Bo nghỉ ngơi và đợi bạn quay lại'],truc:[6,'Trúc giải thích lưu ý'],but:[7,'Bút đồng hành luyện tập'],'but-happy':[8,'Bút vui mừng cùng bạn']}
export function Companion({pose='welcome',className='',decorative=false}:{pose?:CompanionPose;className?:string;decorative?:boolean}){
  const [cell,label]=poses[pose]
  return <span className={`academy-companion ${className}`} role={decorative?undefined:'img'} aria-label={decorative?undefined:label} aria-hidden={decorative||undefined} style={{backgroundPosition:`${cell%3*50}% ${Math.floor(cell/3)*50}%`} as CSSProperties}/>
}
const illustrations:Record<string,[number,string]>={'茶':[0,'trà'],'水':[1,'nước'],'书':[2,'sách'],'山':[3,'núi'],'人':[4,'người'],'朋友':[5,'bạn bè']}
const hskIllustrations:Record<string,[number,string]>={'口':[0,'miệng'],'马':[1,'ngựa'],'女':[2,'phụ nữ'],'大':[3,'to, lớn'],'白':[4,'màu trắng'],'你好':[5,'chào hỏi']}
const numerals:Record<string,number>={'一':1,'五':5,'八':8}
const extraIllustrations:Record<string,[number,string]>={'你':[0,'người đang được nói chuyện cùng'],'好':[1,'tốt, được'],'不':[2,'không, từ chối']}
export function VocabularyIllustration({hanzi}:{hanzi:string}){
  const key=hanzi.trim()
  if(numerals[key])return <figure className="academy-numeral-illustration" aria-label={'Minh họa số '+numerals[key]}>{Array.from({length:numerals[key]},(_,index)=><i key={index} aria-hidden="true"/>)}<figcaption>{key} · {numerals[key]}</figcaption></figure>
  const extra=extraIllustrations[key]
  if(extra)return <span className="academy-word-illustration" role="img" aria-label={`Minh họa ${extra[1]}`} style={{backgroundImage:"url('/academy/vocabulary-hsk1-extra.png')",backgroundSize:'300% 100%',backgroundPosition:`${extra[0]*50}% 0`}}/>
  const hsk=hskIllustrations[key]
  const illustration=hsk??illustrations[key]
  if(!illustration)return null
  const [index,meaning]=illustration
  return <span className="academy-word-illustration" role="img" aria-label={`Minh họa ${meaning}`} style={{...(hsk?{backgroundImage:"url('/academy/vocabulary-hsk1.png')"}:{}),backgroundPosition:`${index%3*50}% ${Math.floor(index/3)*100}%`}}/>
}
