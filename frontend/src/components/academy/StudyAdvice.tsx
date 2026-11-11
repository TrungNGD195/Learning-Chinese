import { useId } from 'react'
import { Companion, type CompanionPose } from './Companion'

const advice = {
  recall: {
    title: 'Tự nhắc lại trước khi học mới',
    text: 'Trước khi mở bài tiếp theo, thử nói lại một từ và một câu của bài trước mà không nhìn tài liệu. Chỗ nào chưa nhớ, hãy xem lại ví dụ rồi thử thêm lần nữa.',
    pose: 'guide',
  },
  pronunciation: {
    title: 'Che pinyin, thử tự đọc',
    text: 'Chọn một ví dụ đã học, che pinyin và tự đọc chữ Hán. Sau đó mở lại pinyin để đối chiếu, rồi đọc lại cả cụm.',
    pose: 'truc',
  },
  INITIALS: {
    title: 'Luyện theo cặp âm',
    text: 'Chọn hai thanh mẫu dễ nhầm trong bài. Đọc luân phiên từng âm, chú ý vị trí môi, lưỡi và luồng hơi; sau đó đọc lại các từ ví dụ.',
    pose: 'truc',
  },
  FINALS: {
    title: 'Đọc chậm để nghe rõ âm cuối',
    text: 'Chọn hai vận mẫu bạn dễ nhầm. Đọc chậm từng vần, chú ý phần kết thúc, rồi ghép lại với thanh mẫu trong ví dụ.',
    pose: 'truc',
  },
  TONES: {
    title: 'Vẽ đường thanh bằng tay',
    text: 'Nhìn đường thanh trong bài và dùng tay đi theo khi đọc. Sau đó thử đọc lại mà không nhìn hình, rồi đối chiếu với hướng dẫn.',
    pose: 'truc',
  },
  SANDHI: {
    title: 'Tập biến điệu trong cả cụm',
    text: 'Chọn một ví dụ và đọc liền cả cụm theo cách đọc trong bài. Thử dùng cụm đó trong một câu ngắn thay vì chỉ lặp lại từng âm riêng lẻ.',
    pose: 'truc',
  },
  'practice-start': {
    title: 'Thử nhớ lại trước khi bắt đầu',
    text: 'Tự nhẩm vài từ và mẫu câu vừa học mà không mở tài liệu. Sau lượt làm, dùng kết quả để chọn phần cần ôn lại.',
    pose: 'but',
  },
  'practice-active': {
    title: 'Đọc lại cả câu',
    text: 'Với câu điền từ hoặc sắp xếp, đọc lại cả câu để kiểm tra nghĩa và thứ tự từ.',
    pose: 'but',
  },
  'review-passed': {
    title: 'Dùng lại điều vừa học',
    text: 'Chọn một từ hoặc mẫu câu trong bài làm và đặt một câu mới về bản thân. Thử nói câu đó mà không nhìn đáp án.',
    pose: 'but-happy',
  },
  'review-retry': {
    title: 'Hiểu chỗ sai trước khi thử lại',
    text: 'Chọn một câu chưa đúng bên dưới. Xem đáp án và nhận xét nếu có, tự giải thích điểm khác biệt, rồi thử làm lại câu đó trước khi bắt đầu lượt mới.',
    pose: 'but',
  },
} satisfies Record<string, { title: string; text: string; pose: CompanionPose }>

export type StudyAdviceTopic = keyof typeof advice

export function StudyAdvice({ topic, inline = false }: { topic: StudyAdviceTopic; inline?: boolean }) {
  const titleId = useId()
  const item = advice[topic]
  const Heading = inline ? 'h3' : 'h2'
  return <aside className={`study-advice${inline ? ' study-advice--inline' : ''}`} data-topic={topic} aria-labelledby={titleId}>
    <Companion pose={item.pose} decorative/>
    <div className="study-advice__copy"><Heading id={titleId}>{item.title}</Heading><p>{item.text}</p></div>
  </aside>
}
