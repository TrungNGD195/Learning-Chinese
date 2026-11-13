import { AcademyIcon } from '../../components/academy/AcademyIcon'

export function LearningFlow({ completed, loading }: { completed: boolean; loading: boolean }) {
  return <section className="lc-learning-flow" aria-labelledby="learning-flow-title">
    <h2 id="learning-flow-title">{completed ? 'Từng bước chinh phục bài học' : 'Bắt đầu học từ đâu?'}</h2>
    <ol>
      <li data-completed={completed}>
        <span className="lc-flow-number" aria-hidden="true">{completed ? <AcademyIcon name="exercise" size={20}/> : '1'}</span>
        <div><h3>Phát âm nền tảng</h3><p>{loading ? 'Học cách đọc trước khi bắt đầu HSK 1.' : completed ? 'Đã hoàn thành. Bạn có thể học các bài HSK 1 bên dưới.' : 'Hoàn thành 4 phần phát âm để mở HSK 1.'}</p></div>
      </li>
      <li>
        <span className="lc-flow-number" aria-hidden="true">2</span>
        <div><h3>Học lý thuyết từng bài</h3><p>Học đủ từ vựng, ngữ pháp và bài khóa để mở luyện tập.</p></div>
      </li>
      <li>
        <span className="lc-flow-number" aria-hidden="true">3</span>
        <div><h3>Luyện tập &amp; tiến bước</h3><p>Đạt từ <strong>80%</strong> để mở bài tiếp theo. Được làm lại nhiều lần.</p></div>
      </li>
    </ol>
    <p className="lc-flow-note">Đã có nền tảng? Bạn có thể chọn học HSK 2 hoặc HSK 3 ngay.</p>
  </section>
}
