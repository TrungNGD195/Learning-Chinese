import { useRef, useState } from 'react'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Companion, VocabularyIllustration } from '../../components/academy/Companion'
import { vocabularyDiscovery } from '../lesson/vocabularyDiscoveries'
import './culture-preview.css'

const dumplingDiscovery = vocabularyDiscovery({ hanzi: '饺子', pinyin: 'jiǎozi', vietnamese_meaning: 'sủi cảo' })!
const source = dumplingDiscovery.sources[0]
const words = [
  {hanzi:'米饭',pinyin:'mǐfàn',meaning:'cơm',example:'我喜欢吃米饭。',examplePinyin:'Wǒ xǐhuan chī mǐfàn.',translation:'Tôi thích ăn cơm.'},
  {hanzi:'饺子',pinyin:'jiǎozi',meaning:'sủi cảo',example:'我喜欢吃饺子。',examplePinyin:'Wǒ xǐhuan chī jiǎozi.',translation:'Tôi thích ăn sủi cảo.'},
  {hanzi:'面条',pinyin:'miàntiáo',meaning:'mì sợi',example:'我喜欢吃面条。',examplePinyin:'Wǒ xǐhuan chī miàntiáo.',translation:'Tôi thích ăn mì sợi.'},
]

export function CultureLessonPreview() {
  const [section,setSection]=useState<'vocabulary'|'readings'>('vocabulary')
  const [wordIndex,setWordIndex]=useState(1)
  const discovery=useRef<HTMLDialogElement>(null)
  const word=words[wordIndex]
  return <div className="cp-shell bo-shell">
    <aside className="cp-sidebar" aria-label="Điều hướng bản xem thử">
      <a className="cp-brand" href="/pronunciation"><span lang="zh-Hans">中</span>Hanfolio</a>
      <p>Chậm một chút.<br/>Hiểu thêm một điều.</p>
      <a href="/pronunciation" className="cp-sidebar-active"><AcademyIcon name="book"/>Giáo trình</a>
      <div className="cp-sidebar-friend"><Companion pose="truc" decorative/><p>Cùng Trúc hiểu thêm<br/>về điều vừa học.</p></div>
      <small>Bản xem thử giao diện<br/>Không lưu tiến độ học</small>
    </aside>
    <main className="cp-main">
      <div className="cp-preview-toolbar"><span>Bản test · Khám phá văn hóa</span><div><button aria-pressed={section==='vocabulary'} onClick={()=>setSection('vocabulary')}>Block từ vựng</button><button aria-pressed={section==='readings'} onClick={()=>setSection('readings')}>Cấu trúc bài học</button></div></div>
      <header className="cp-header"><div><a href="/hsk/1">← Về danh sách bài</a><h1>Bài 5 · Hôm nay ăn gì?</h1><p>HSK 1 · Nội dung minh họa để duyệt bố cục</p></div><Companion pose="guide" decorative/></header>
      <nav className="cp-sections" aria-label="Các phần bài học">
        <button aria-current={section==='vocabulary'?'page':undefined} onClick={()=>setSection('vocabulary')}><span>1</span><strong>Từ vựng<small>Chọn từ để học</small></strong></button>
        <button disabled title="Không nằm trong nội dung bản test"><span>2</span><strong>Ngữ pháp<small>Bản test chưa mô phỏng</small></strong></button>
        <button aria-current={section==='readings'?'page':undefined} onClick={()=>setSection('readings')}><span>3</span><strong>Bài khóa<small>Luyện đọc hội thoại</small></strong></button>
        <button disabled title="Bản test không ghi nhận hoàn thành lý thuyết"><span>4</span><strong>Luyện tập<small>Sau lý thuyết bắt buộc</small></strong></button>
      </nav>
      <div className="cp-workspace">
        <aside className="cp-index" aria-label={section==='vocabulary'?'Danh sách từ':'Danh sách bài khóa'}><h2>{section==='vocabulary'?'Từ trong bản test':'Bài khóa'}</h2>
          {section==='vocabulary'?<ol>{words.map((item,index)=><li key={item.hanzi}><button aria-current={wordIndex===index?'true':undefined} onClick={()=>setWordIndex(index)}><span>{index+1}</span><span><strong lang="zh-Hans">{item.hanzi}</strong><small>{item.pinyin}</small></span></button></li>)}</ol>:<ol><li><button aria-current="true"><span>1</span><span><strong lang="zh-Hans">吃什么？</strong><small>Chī shénme?</small></span></button></li></ol>}
          <p>{section==='vocabulary'?'Mỗi lần tập trung vào một từ.':'Đọc thành tiếng để luyện cách dùng từ trong câu.'}</p>
        </aside>
        <div className="cp-content">
          {section==='vocabulary'?<>
            <article className="cp-word" aria-label={`Từ vựng ${word.hanzi}`}><p className="cp-word-count">Từ {wordIndex+1} / 3</p>
              <div className="cp-word-top"><div className="cp-word-art"><VocabularyIllustration hanzi={word.hanzi}/></div><div className="cp-word-identity"><h2 lang="zh-Hans">{word.hanzi}</h2><p className="cp-pinyin">{word.pinyin}</p><p className="cp-meaning">{word.meaning} <small>Danh từ</small></p></div></div>
              <div className="cp-word-details" data-discovery={wordIndex===1}><div className="cp-word-theory">
              <section className="cp-example"><h3>Ví dụ</h3><p lang="zh-Hans">{word.example}</p><p>{word.examplePinyin}</p><p>{word.translation}</p></section>
              <section className="cp-note"><h3>Lưu ý sử dụng</h3><p>{wordIndex===1?'子 trong 饺子 đọc thanh nhẹ: jiǎozi. Giữ âm tiết cuối nhẹ và ngắn hơn âm đầu.':'Dùng 吃 khi nói về việc ăn món này: 吃'+word.hanzi+'.'}</p></section>
              </div>{wordIndex===1&&<aside className="cp-word-discovery" aria-label="Khám phá văn hóa"><Companion pose="truc" decorative/><div><p>Sủi cảo có<br className="cp-desktop-break"/> câu chuyện gì?</p><button className="cp-discover-button" aria-label="Khám phá thêm" aria-haspopup="dialog" onClick={()=>discovery.current?.showModal()}><span>Khám phá thêm</span><AcademyIcon name="arrow" size={17}/></button></div></aside>}</div>
            </article>
            <div className="cp-pagination"><button disabled={wordIndex===0} onClick={()=>setWordIndex(i=>i-1)}>← Quay lại</button><span>{wordIndex+1} / 3 từ</span><button onClick={()=>wordIndex===2?setSection('readings'):setWordIndex(i=>i+1)}>{wordIndex===2?'Xem bài khóa':'Tiếp theo'} →</button></div>
          </>:<>
            <article className="cp-reading"><div className="cp-reading-title"><h2 lang="zh-Hans">吃什么？</h2><span>Ăn gì?</span></div><p className="cp-reading-description">Đọc đoạn hội thoại ngắn về món ăn yêu thích.</p>
              <div className="cp-dialogue"><span>A</span><div><p lang="zh-Hans">你喜欢吃什么？</p><small>Nǐ xǐhuan chī shénme?</small><p>Bạn thích ăn gì?</p></div></div>
              <div className="cp-dialogue"><span>B</span><div><p lang="zh-Hans">我喜欢吃饺子。你呢？</p><small>Wǒ xǐhuan chī jiǎozi. Nǐ ne?</small><p>Tôi thích ăn sủi cảo. Còn bạn?</p></div></div>
              <div className="cp-reading-status"><AcademyIcon name="book"/><span>Bài khóa minh họa · Không ghi nhận hoàn thành</span></div>
            </article>
          </>}
        </div>
      </div>
    </main>
    <dialog ref={discovery} className="cp-discovery-modal" aria-labelledby="cp-discovery-title" onClick={event=>{const rect=event.currentTarget.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)discovery.current?.close()}}>
      <div className="cp-modal-heading"><div><Companion pose="truc" decorative/><span>Khám phá thêm cùng Trúc</span></div><button autoFocus aria-label="Đóng khám phá" onClick={()=>discovery.current?.close()}>Đóng ×</button></div>
      <div className="cp-modal-intro"><div className="cp-modal-art"><VocabularyIllustration hanzi="饺子"/></div><div><h2 id="cp-discovery-title">Sủi cảo trong dịp Tết</h2><p><span lang="zh-Hans">饺子</span> · jiǎozi · sủi cảo</p></div></div>
      <p className="cp-modal-story">{dumplingDiscovery.text}</p>
      <details className="cp-sources"><summary>Nguồn tham khảo</summary><a href={source.url} target="_blank" rel="noreferrer">{source.label} ↗</a><p>Nội dung minh họa diễn giải từ nguồn bên ngoài, không trích nguyên văn giáo trình.</p></details>
      <button className="cp-back-to-word" onClick={()=>discovery.current?.close()}>Quay lại từ đang học<AcademyIcon name="arrow" size={18}/></button>
    </dialog>
  </div>
}
