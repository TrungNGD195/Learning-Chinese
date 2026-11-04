import { useCallback, useRef, useState } from 'react'
import { ChatPanel } from './ChatPanel'
import { Surface } from '../../components/ui'

export function LessonChatRegion({ lessonId, lessonNumber, hskLabel }: {
  lessonId: string
  lessonNumber: number
  hskLabel: string | null
}) {
  const [open, setOpen] = useState(false)
  const openerRef = useRef<HTMLButtonElement>(null)
  const closeChat = useCallback(() => setOpen(false), [])
  return <>
    <Surface as="section" className="lesson-chat-entry" aria-labelledby="ai-chat-heading">
      <div>
        <h2 id="ai-chat-heading">AI Chat</h2>
        <p>{hskLabel ? `${hskLabel} · ` : ''}Lesson {lessonNumber}</p>
      </div>
      <button ref={openerRef} className="primary-action" type="button" onClick={() => setOpen(true)}>Open AI chat</button>
    </Surface>
    {open && <ChatPanel key={lessonId} lessonId={lessonId} lessonNumber={lessonNumber} hskLabel={hskLabel} openerRef={openerRef} onClose={closeChat} />}
  </>
}
