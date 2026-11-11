import type { CSSProperties } from 'react'
import { lessonVocabularyScenes, countryIllustrations, foodIllustrations, familyIllustrations } from './lessonVocabularyArt'
import { CountryVocabularyIllustration } from './CountryVocabularyIllustration'

export type CompanionPose='welcome'|'guide'|'think'|'encourage'|'celebrate'|'rest'|'truc'|'but'|'but-happy'
const poses:Record<CompanionPose,[number,string]>={welcome:[0,'Bo vẫy tay chào bạn'],guide:[1,'Bo hướng dẫn bài học'],think:[2,'Bo suy nghĩ cùng bạn'],encourage:[3,'Bo động viên bạn thử lại'],celebrate:[4,'Bo chúc mừng bạn hoàn thành'],rest:[5,'Bo nghỉ ngơi và đợi bạn quay lại'],truc:[6,'Trúc giải thích lưu ý'],but:[7,'Bút đồng hành luyện tập'],'but-happy':[8,'Bút vui mừng cùng bạn']}
export function Companion({pose='welcome',className='',decorative=false}:{pose?:CompanionPose;className?:string;decorative?:boolean}){
  const [cell,label]=poses[pose]
  return <span className={`academy-companion ${className}`} role={decorative?undefined:'img'} aria-label={decorative?undefined:label} aria-hidden={decorative||undefined} style={{backgroundPosition:`${cell%3*50}% ${Math.floor(cell/3)*50}%`} as CSSProperties}/>
}
const illustrations:Record<string,[number,string]>={'茶':[0,'trà'],'喝':[0,'đồ uống: trà'],'水':[1,'nước'],'书':[2,'sách'],'山':[3,'núi'],'人':[4,'người'],'朋友':[5,'bạn bè']}
const hskIllustrations:Record<string,[number,string]>={'口':[0,'miệng'],'马':[1,'ngựa'],'女':[2,'phụ nữ'],'大':[3,'to, lớn'],'白':[4,'màu trắng'],'你好':[5,'chào hỏi']}
const numerals:Record<string,number>={'零':0,'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'百':100,'千':1000,'万':10000}
const extraIllustrations:Record<string,[number,string]>={'你':[0,'người đang được nói chuyện cùng'],'好':[1,'tốt, được'],'不':[2,'không, từ chối']}
const pandaWords = new Set(['人', '朋友', '口', '女', '你好', '你', '好', '不'])
export function VocabularyIllustration({hanzi,partOfSpeech}:{hanzi:string;partOfSpeech?:string|null}){
  const key=hanzi.trim()
  if(key in numerals)return <figure className="academy-numeral-illustration" aria-label={'Minh họa số '+numerals[key]}>{numerals[key] > 10 || numerals[key] === 0 ? <strong>{numerals[key].toLocaleString('vi-VN')}</strong> : Array.from({length:numerals[key]},(_,index)=><i key={index} aria-hidden="true"/>)}<figcaption>{key} · {numerals[key].toLocaleString('vi-VN')}</figcaption></figure>
  if (countryIllustrations[key]) return <CountryVocabularyIllustration hanzi={key}/>
  const family = familyIllustrations[key]
  if (family) return <span className="academy-word-illustration" data-illustration="chibi-family" role="img" aria-label={family[1]} style={{backgroundImage:"url('/academy/chibi-family-v1.png')", backgroundSize:'400% 400%', backgroundPosition:`${family[0]%4*100/3}% ${Math.floor(family[0]/4)*100/3}%`}}/>
  const food = foodIllustrations[key]
  if (food) return <span className="academy-word-illustration" data-illustration="food" role="img" aria-label={food[1]} style={{backgroundImage:"url('/academy/hsk1-food-drinks-v1.png')", backgroundSize:'300% 300%', backgroundPosition:`${food[0]%3*50}% ${Math.floor(food[0]/3)*50}%`}}/>
  const scene = key === '口' && partOfSpeech !== 'lượng từ' ? undefined : lessonVocabularyScenes[key]
  if (scene) return <span className="academy-word-illustration" data-illustration="panda-context" role="img" aria-label={scene[1]} style={{backgroundImage:"url('/academy/panda-lessons-02-05-v1.png')", backgroundSize:'400% 400%', backgroundPosition:`${scene[0]%4*100/3}% ${Math.floor(scene[0]/4)*100/3}%`}}/>
  const extra=extraIllustrations[key]
  if(extra)return <span className="academy-word-illustration" data-illustration="panda" role="img" aria-label={`Gấu trúc minh họa ${extra[1]}`} style={{backgroundImage:"url('/academy/panda-hsk1-extra-v3.png')",backgroundSize:'300% 100%',backgroundPosition:`${extra[0]*50}% 0`}}/>
  const hsk=hskIllustrations[key]
  const illustration=hsk??illustrations[key]
  if(!illustration)return null
  const [index,meaning]=illustration
  return <span className="academy-word-illustration" data-illustration={pandaWords.has(key) ? 'panda' : 'object'} role="img" aria-label={`${pandaWords.has(key) ? 'Gấu trúc minh họa' : 'Minh họa'} ${meaning}`} style={{...(hsk?{backgroundImage:"url('/academy/panda-hsk1-v3.png')"}:{}),backgroundPosition:`${index%3*50}% ${Math.floor(index/3)*100}%`}}/>
}
