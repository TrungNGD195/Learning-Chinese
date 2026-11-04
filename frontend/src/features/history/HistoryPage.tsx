import { EmptyState, PageHeader } from '../../components/ui'
import cloudGuideThinking from '../../assets/cloud-guide-dragon-thinking.png'

export function HistoryPage() {
  return (
    <section className="screen history-page" aria-labelledby="page-title">
      <PageHeader title="History" titleId="page-title" eyebrow="学习记录 · LEARNING JOURNEY" />
      <div className="history-illustrated">
        <div className="history-illustrated__art" aria-hidden="true"><img src={cloudGuideThinking} alt="" loading="lazy" /></div>
        <EmptyState className="history-unavailable" title="History is not available yet">
          Historical assessment attempts and results will be shown here.
        </EmptyState>
      </div>
    </section>
  )
}
