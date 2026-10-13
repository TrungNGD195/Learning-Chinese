import { useState } from 'react'
import { ChatPanel } from './ChatPanel'

export function LessonChatRegion({ lessonId, lessonNumber, hskLabel }: {
  lessonId: string
  lessonNumber: number
  hskLabel: string | null
}) {
  const [open, setOpen] = useState(false)
  return <>
    <section className="structural-card lesson-chat-entry" aria-labelledby="ai-chat-heading">
      <div>
        <h2 id="ai-chat-heading">AI Chat</h2>
        <p>{hskLabel ? `${hskLabel} · ` : ''}Lesson {lessonNumber}</p>
      </div>
      <button className="primary-action" type="button" onClick={() => setOpen(true)}>Open AI chat</button>
    </section>
    {open && <ChatPanel key={lessonId} lessonId={lessonId} lessonNumber={lessonNumber} hskLabel={hskLabel} onClose={() => setOpen(false)} />}
  </>
}
