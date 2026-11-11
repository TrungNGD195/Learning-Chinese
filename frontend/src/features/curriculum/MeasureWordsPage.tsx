import {useRef} from 'react'
import {useSearchParams} from 'react-router'
import {AcademyIcon} from '../../components/academy/AcademyIcon'
import {VocabularyAudio} from '../lesson/VocabularyAudio'
import {LessonEntryLink} from '../journey/LessonEntryLink'
import {Companion} from '../../components/academy/Companion'
import {measureWords} from './measureWordsData'
import '../../styles/academy-curriculum.css'

export function MeasureWordsPage(){
 const [params,setParams]=useSearchParams()
 const content=useRef<HTMLElement>(null)
 const raw=Number(params.get('word')??1)
 const index=Number.isInteger(raw)?Math.max(0,Math.min(measureWords.length-1,raw-1)):0
 const word=measureWords[index]
 const spokenPhrase=word.pairs[0].split(' · ')[0]
 const go=(next:number)=>{
  setParams({word:String(next+1)})
  content.current?.scrollIntoView({block:'start',behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})
 }
 return <section className="learning-curriculum measure-words-page screen" aria-labelledby="page-title">
  <LessonEntryLink className="lc-inline-button mw-back" to="/pronunciation"><AcademyIcon name="book" size={17}/>Về giáo trình</LessonEntryLink>
  <header className="mw-heading"><div><h1 id="page-title">Lượng từ</h1><p>Đếm đúng, nói tự nhiên hơn. Học từng lượng từ qua những cụm quen thuộc.</p></div><span>Mục {index+1}/{measureWords.length}</span></header>
  <div className="mw-layout"><aside className="mw-outline"><h2>10 lượng từ thông dụng</h2><nav aria-label="Chọn lượng từ">{measureWords.map((item,i)=><button key={item.hanzi} type="button" aria-pressed={index===i} onClick={()=>go(i)}><strong lang="zh-Hans">{item.hanzi}</strong><span>{item.pinyin}</span></button>)}</nav><p>Bạn có thể học chuyên đề này bất cứ lúc nào.</p></aside>
   <article ref={content} className="mw-content" aria-label={`Lượng từ ${word.hanzi}`}>
    <div className="mw-word"><div><h2 lang="zh-Hans">{word.hanzi}</h2><p className="mw-pinyin">{word.pinyin}</p></div><div><h3>{word.meaning}</h3><p>{word.usage}</p></div></div>
    <div className="mw-audio"><VocabularyAudio key={word.hanzi} hanzi={spokenPhrase}/><p>Nghe theo cụm: <span lang="zh-Hans">{spokenPhrase}</span></p></div>
    <section className="mw-rule"><h3>Cách ghép</h3><p>Số + <strong>lượng từ</strong> + danh từ</p><p>Dùng 两 khi đếm hai người hoặc vật trước lượng từ, chẳng hạn <span lang="zh-Hans">两本书</span>.</p></section>
    <section className="mw-pairs"><h3>Nhớ theo cụm</h3>{word.pairs.map(pair=><p key={pair}><span lang="zh-Hans">{pair.split(' · ')[0]}</span><span>{pair.split(' · ')[1]}</span></p>)}</section>
    <section className="mw-example"><h3>Dùng trong một câu</h3><p lang="zh-Hans">{word.sentence}</p><p className="mw-pinyin">{word.reading}</p><p>{word.translation}</p></section>
    <section className="mw-note"><Companion pose="truc" decorative/><div><h3>Trúc nhắc nhỏ</h3><p>{word.note}</p></div></section>
    <footer className="mw-pagination"><button className="lc-inline-button" type="button" disabled={index===0} onClick={()=>go(index-1)}>Quay lại</button><span>{index+1} / {measureWords.length}</span><button className="lc-inline-button" type="button" disabled={index===measureWords.length-1} onClick={()=>go(index+1)}>Tiếp theo<AcademyIcon name="arrow" size={16}/></button></footer>
   </article>
  </div>
 </section>
}
