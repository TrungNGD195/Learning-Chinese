import assert from 'node:assert/strict'
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://localhost:5173'
const directory = '../backend/content/curriculum-refresh'
const files = (await readdir(directory)).filter(name => /^hsk[12]-lesson-\d+\.json$/.test(name)).sort()
const firstLevels = await Promise.all(files.map(async name => {
  const { lesson } = JSON.parse(await readFile(`${directory}/${name}`, 'utf8'))
  return { id: name, hsk_level_id: `hsk-${lesson.hsk_level}`, lesson_number: lesson.lesson_number, title: lesson.title, description: null, status: 'PUBLISHED', published_at: '2026-11-21T00:00:00Z' }
}))
const thirdLevel = await Promise.all((await readdir('../backend/content/hsk3')).filter(name => /^lesson-\d+\.json$/.test(name)).sort().map(async name => {
  const { lesson } = JSON.parse(await readFile(`../backend/content/hsk3/${name}`, 'utf8'))
  return { id: `hsk3-${name}`, hsk_level_id: 'hsk-3', lesson_number: lesson.lesson_number, title: lesson.title, description: null, status: 'PUBLISHED', published_at: '2026-11-21T00:00:00Z' }
}))
const lessons = [...firstLevels, ...thirdLevel]
const output = '../.impeccable/review/lesson-covers'
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ headless: true })
const errors = [], unexpected = [], writes = []
try {
  for (const width of [1440, 390]) for (const role of ['LEARNER', 'ADMIN']) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    await context.route('**/api/v1/**', route => {
      const request = route.request(), url = new URL(request.url()), path = url.pathname.split('/api/v1')[1]
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
      const reply = json => route.fulfill({ json, headers })
      if (request.method() === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
      if (request.method() !== 'GET') writes.push(path)
      if (path === '/auth/me') return reply({ id: 'review', full_name: 'Bạn học', role, email: 'review@example.invalid' })
      if (['/hsk-levels', '/admin/hsk-levels'].includes(path)) return reply([1, 2, 3].map(n => ({ id: `hsk-${n}`, level_number: n, title: `HSK ${n}`, description: null, order_index: n, state: 'AVAILABLE' })))
      if (path === '/me/dashboard') return reply({ current_hsk: null, current_unit: null, current_lesson: null, progress_percentage: 0, continue_learning: null })
      if (path === '/me/progress') return reply({ current_hsk: 1, progress_percentage: 0, pronunciation_complete: true, hsk_levels: [] })
      if (path === '/pronunciation/lesson') return reply({ sections: [], completed_at: '2026-11-21T00:00:00Z', total_steps: 74, step_index: 0, current_section: null, can_finish: false })
      const match = path.match(/^\/hsk-levels\/hsk-(\d)\/curriculum$/)
      if (match) return reply({ hsk: { id: `hsk-${match[1]}`, level_number: Number(match[1]), title: `HSK ${match[1]}` }, units: lessons.filter(l => l.hsk_level_id === `hsk-${match[1]}`).map(l => ({ id: l.id, unit_type: 'LESSON', order_index: l.lesson_number, state: 'AVAILABLE', lesson: l, assessment: null })) })
      if (path === '/admin/lessons') {
        const page = Number(url.searchParams.get('page')), size = Number(url.searchParams.get('page_size'))
        assert.equal(size, 10)
        return reply({ items: lessons.slice((page - 1) * size, page * size), page, page_size: size, total: lessons.length })
      }
      if (/^\/admin\/lessons\/.+\/(vocabulary|grammar)$/.test(path)) return reply([])
      unexpected.push(path)
      return route.fulfill({ status: 404, json: {} })
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    const seen = new Set()
    const routes = role === 'LEARNER' ? ['/hsk/1', '/hsk/2', '/hsk/3'] : ['/admin/lessons']
    for (const route of routes) {
      await page.goto(origin + route)
      const selector = role === 'LEARNER' ? '.lc-lesson-cover .lc-painted-cover' : '.admin-book-cover .lc-painted-cover'
      for (let batch = 1; batch <= (role === 'ADMIN' ? 4 : 1); batch++) {
        await page.locator(selector).first().waitFor()
        await page.evaluate(async () => {
          await document.fonts.ready
          await Promise.all([...new Set([...document.querySelectorAll('.lc-painted-cover')].map(el => getComputedStyle(el).backgroundImage.match(/url\(["']?(.*?)["']?\)/)?.[1]).filter(Boolean))].map(async src => { const img = new Image(); img.src = src; await img.decode(); if (!img.naturalWidth) throw new Error('Empty image') }))
        })
        const covers = await page.locator(selector).evaluateAll(nodes => nodes.map(el => ({ topic: el.dataset.coverTopic, width: el.getBoundingClientRect().width, height: el.getBoundingClientRect().height })))
        assert.equal(covers.length, role === 'ADMIN' ? 10 : route.endsWith('/2') ? 10 : 15)
        for (const cover of covers) { assert.notEqual(cover.topic, 'study'); assert.ok(cover.width > 100 && cover.height > 80); seen.add(cover.topic) }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
        await page.screenshot({ path: `${output}/${role}-${width}-${role === 'LEARNER' ? `hsk${route.slice(-1)}` : batch}.png` })
        if (role === 'ADMIN' && batch < 4) { await page.getByRole('button', { name: 'Tiếp', exact: true }).click(); await page.getByText(`Trang ${batch + 1}`, { exact: true }).waitFor() }
      }
    }
    assert.equal(seen.size, 40)
    await context.close()
  }
  assert.deepEqual({ errors, unexpected, writes }, { errors: [], unexpected: [], writes: [] })
  await writeFile(`${output}/result.json`, JSON.stringify({ lessons: 40, roles: ['LEARNER', 'ADMIN'], widths: [1440, 390], errors, unexpected, writes }, null, 2))
  console.log('All 40 lesson covers loaded in both roles at 1440px/390px; admin pages 10 each; no overflow or data writes.')
} finally { await browser.close() }
