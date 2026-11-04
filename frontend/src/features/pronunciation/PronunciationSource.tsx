import type { PronunciationCode } from './pronunciationData'

import { pronunciationSourcePage } from './pronunciationSourceMetadata'

export function PronunciationSource({code,symbol}:{code:PronunciationCode;symbol?:string}){
  return <details className="academy-source"><summary>Nguồn bài học và cách sử dụng</summary><p>Biên soạn từ <strong>HSK1 3.0 Hanu 24.6.26.pdf</strong> — Trung tâm Ngôn ngữ & Văn hoá Trung Quốc, Đại học Hà Nội.</p><p>Phần đang học: {pronunciationSourcePage(code,symbol)}. Nội dung được diễn giải theo từng bước; ví dụ chữ Hán dùng để luyện âm, không phải một bài kiểm tra phát âm tự động.</p><p>Phần ngữ âm được tổng hợp từ các bài 1–3 của giáo trình để học trước HSK 1. Âm thanh, nếu có, là giọng đọc của thiết bị và có thể khác giọng giáo viên.</p></details>
}
