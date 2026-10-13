import { describe, expect, it } from 'vitest'

const sourceModules = import.meta.glob<string>('../**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default',
})

function applicationSources() {
  return Object.entries(sourceModules).filter(([path]) =>
    !path.endsWith('.test.ts') &&
    !path.endsWith('.test.tsx') &&
    !path.endsWith('/types/api.generated.ts'),
  )
}

describe('frontend API security and transport boundary', () => {
  it('keeps browser fetch in the central client only', async () => {
    for (const [path, contents] of applicationSources()) {
      if (path.endsWith('/lib/api/client.ts')) continue
      expect(contents, path).not.toMatch(/\bfetch\s*\(/)
    }
  })

  it('contains no Bearer token, token storage, or manual JWT decoding', async () => {
    const combined = applicationSources().map(([, contents]) => contents).join('\n')
    expect(combined).not.toMatch(/Authorization\s*[:=].{0,40}Bearer/i)
    expect(combined).not.toMatch(/localStorage|sessionStorage/i)
    expect(combined).not.toMatch(/\batob\s*\(|jwtDecode|decodeJwt|jwt-decode/i)
  })

  it('keeps API URLs out of component pages and limits Document wrappers to the Step 5.8 contract', async () => {
    const featureSources = applicationSources().filter(([path]) => path.startsWith('../features/'))
    const pages = featureSources.filter(([path]) => path.endsWith('.tsx'))
    for (const [path, contents] of pages) {
      expect(contents, path).not.toMatch(/https?:\/\/|\/api\/v1|\bfetch\s*\(/)
    }
    const adminApi = featureSources.find(([path]) => path === '../features/admin/api.ts')?.[1] ?? ''
    expect(adminApi).toContain("const documentsPath = '/api/v1/admin/documents'")
    expect(adminApi).not.toMatch(/\/admin\/(?:ingestion|chunks|embeddings)|\/documents\/\{document_id\}\/(?:parse|transform|chunk|reprocess|activate)/i)
  })

  it('uses TanStack Query for server state without adding another state library', async () => {
    const combined = applicationSources().map(([, contents]) => contents).join('\n')
    expect(combined).toMatch(/@tanstack\/react-query/)
    expect(combined).toMatch(/\buseQuery\s*\(/)
    expect(combined).not.toMatch(/from\s+['"]redux['"]|from\s+['"]zustand['"]|@tanstack\/react-query-devtools/)
    expect(combined).not.toMatch(/markTheoryComplete|localStorage|sessionStorage/)
    expect(combined).not.toMatch(/calculateScore|calculatePass|calculateCorrectness/)
  })

  it('keeps Conversation UI on existing wrappers with bounded Query pagination and no streaming additions', () => {
    const conversationSources = Object.entries(sourceModules).filter(([path]) =>
      path.includes('/features/conversation/') && !path.endsWith('.test.ts') && !path.endsWith('.test.tsx'),
    )
    const combined = conversationSources.map(([, contents]) => contents).join('\n')
    expect(combined).toMatch(/createConversation/)
    expect(combined).toMatch(/listConversations/)
    expect(combined).toMatch(/getMessages/)
    expect(combined).toMatch(/retryAssistantMessage/)
    expect(combined).not.toMatch(/\bfetch\s*\(|VITE_[A-Z_]*(?:AI|LLM|OPENAI)|OpenAI|Anthropic|EventSource|WebSocket|setInterval|ReadableStream/)
    expect(combined).not.toMatch(/rehype-raw|remark-gfm|@mdx-js|rehype|remark-/)
  })
})
