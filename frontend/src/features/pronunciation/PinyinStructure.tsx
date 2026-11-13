import { useState } from 'react'
import { Companion } from '../../components/academy/Companion'

const examples = [
  { hanzi: '妈', pinyin: 'mā', meaning: 'mẹ', initial: 'm', final: 'a', tone: 'ˉ', toneName: 'Thanh 1', note: 'Ghép m với a, rồi đọc cao và ngang. Dấu thanh nằm trên a.' },
  { hanzi: '你', pinyin: 'nǐ', meaning: 'bạn', initial: 'n', final: 'i', tone: 'ˇ', toneName: 'Thanh 3', note: 'Ghép n với i và đọc thanh 3. Khi i mang dấu thanh, bỏ chấm trên i.' },
  { hanzi: '学', pinyin: 'xué', meaning: 'học', initial: 'x', final: 'üe', tone: 'ˊ', toneName: 'Thanh 2', note: 'x + üe + thanh 2 → xué. Sau j, q, x, bỏ hai chấm của ü trong chữ viết; cách phát âm vẫn là ü.' },
  { hanzi: '爱', pinyin: 'ài', meaning: 'yêu', initial: '—', final: 'ai', tone: 'ˋ', toneName: 'Thanh 4', note: 'ài không có thanh mẫu: vận mẫu ai đi cùng thanh 4. Không phải âm tiết nào cũng có đủ ba phần.' },
]

export function PinyinStructure() {
  const [index, setIndex] = useState(0)
  const example = examples[index]
  return <section className="pinyin-structure" aria-labelledby="pinyin-structure-title">
    <div className="pinyin-structure-heading"><div><h2 id="pinyin-structure-title">Một âm tiết Pinyin được tạo nên thế nào?</h2><p>Pinyin ghi lại cách phát âm. Một từ có thể có một hoặc nhiều âm tiết.</p></div><Companion pose="truc" decorative/></div>
    <div className="pinyin-example-choices" role="group" aria-label="Chọn ví dụ cấu tạo Pinyin">{examples.map((item, i) => <button key={item.pinyin} type="button" aria-pressed={i === index} onClick={() => setIndex(i)}><span lang="zh-Hans">{item.hanzi}</span> {item.pinyin}</button>)}</div>
    <div className="pinyin-equation" aria-live="polite" aria-atomic="true">
      <div className="pinyin-part" data-part="initial"><strong>{example.initial}</strong><span>Thanh mẫu</span><small>{index === 3 ? 'Không có âm đầu' : 'Phụ âm đầu'}</small></div>
      <span className="pinyin-operator" aria-hidden="true">+</span>
      <div className="pinyin-part" data-part="final"><strong>{example.final}</strong><span>Vận mẫu</span><small>Phần vần</small></div>
      <span className="pinyin-operator" aria-hidden="true">+</span>
      <div className="pinyin-part" data-part="tone"><strong>{example.tone}</strong><span>Thanh điệu</span><small>{example.toneName}</small></div>
      <span className="pinyin-operator" aria-hidden="true">=</span>
      <div className="pinyin-result"><strong>{example.pinyin}</strong><span><b lang="zh-Hans">{example.hanzi}</b> · {example.meaning}</span></div>
    </div>
    <p className="pinyin-structure-note">{example.note}</p>
    <p className="pinyin-structure-footnote">Thanh điệu thuộc về cả âm tiết. Thanh nhẹ không ghi dấu thanh.</p>
  </section>
}
