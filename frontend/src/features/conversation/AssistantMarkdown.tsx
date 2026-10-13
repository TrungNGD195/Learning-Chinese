import Markdown from 'react-markdown'

const allowedElements = ['p', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'br'] as const

export function AssistantMarkdown({ content }: { content: string }) {
  return <div className="chat-assistant-markdown">
    <Markdown skipHtml allowedElements={[...allowedElements]} unwrapDisallowed>
      {content}
    </Markdown>
  </div>
}
