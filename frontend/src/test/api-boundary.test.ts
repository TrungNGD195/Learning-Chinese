import { describe, expect, it } from 'vitest'

const sourceModules = import.meta.glob<string>('../**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default',
})

function applicationSources() {
  return Object.entries(sourceModules).filter(([path]) =>
    !path.startsWith('../preview/') &&
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
    expect(combined).not.toMatch(/localStorage/i)
    const tabMarkerPath = '../features/auth/tabSession.ts'
    // These reviewed modules retain only tab-local visual route positions;
    // credentials remain HttpOnly cookies and never enter browser storage.
    const visualPositionPaths=new Set([
      '../features/journey/GreatWallMap.tsx',
      '../features/journey/ForwardWallJourney.tsx',
      '../features/journey/ReferenceWallJourney.tsx',
    ])
    for (const [path, contents] of applicationSources()) {
      if(visualPositionPaths.has(path)){
        expect(contents,path).not.toMatch(/access_token|refresh_token|password|Authorization|Bearer/i)
        expect(contents,path).toContain('bo-')
      } else if (path !== tabMarkerPath) expect(contents, path).not.toMatch(/sessionStorage/)
    }
    const tabMarker = sourceModules[tabMarkerPath]
    expect(tabMarker).toContain("tab.setItem(tabSessionMarker, 'ready')")
    expect(tabMarker).not.toMatch(/setItem\([^\n]*(?:access_token|refresh_token|password|JSON\.stringify)/)
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
    expect(combined).not.toMatch(/markTheoryComplete|localStorage/)
    expect(combined).not.toMatch(/calculateScore|calculatePass|calculateCorrectness/)
  })

  it('does not expose the retired student assistant or its API wrappers', () => {
    const conversationSources = Object.entries(sourceModules).filter(([path]) =>
      path.includes('/features/conversation/') && !path.endsWith('.test.ts') && !path.endsWith('.test.tsx'),
    )
    expect(conversationSources).toEqual([])
    const lesson = sourceModules['../features/lesson/LessonPage.tsx']
    expect(lesson).not.toMatch(/LessonChatRegion|ChatPanel/)
  })
})
