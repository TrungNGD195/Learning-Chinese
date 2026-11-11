import assert from 'node:assert/strict'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const source = JSON.parse(await readFile('../tmp/hsk1-drafts-02-05-fixture.json', 'utf8'))
const bundle = Object.values(source.lessons).find(item => item.lesson.lesson_number === 2)
const words = bundle.vocabulary.slice(0, 3)
const grammar = bundle.grammar.slice(0, 1)
const authored = JSON.parse(await readFile('../backend/content/hsk1/lesson-02.json', 'utf8'))
// The ignored administrative export can contain ORM reprs for readings. Use
// the authored content with explicit fixture IDs, never an empty reading card.
const readings = authored.readings.slice(0, 1).map((reading, index) => ({ ...reading, id: `fixture-reading-${index}`, version: 1 }))
const lessonId = bundle.lesson.id
const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5173'
const folder = resolve('../.impeccable/review/lesson-workspace')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch()
const errors = [], unexpected = [], captures = [], positions = []
const time = '2026-11-06T10:00:00Z'

try {
  for (const width of [1440, 768, 390, 320]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' })
    const state = { seen: new Set(), grammar: false, reading: false, fail: false, delay: 0 }
    const ready = () => state.seen.size === words.length && state.grammar && state.reading
    await context.route('**/api/v1/**', async route => {
      const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
      const reply = (json, status = 200) => route.fulfill({ json, status, headers })
      if (request.method() === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
      if (path === '/auth/me') return reply({ id: 'learner', role: 'LEARNER', full_name: 'Nguyễn An', email: 'fixture@example.invalid' })
      if (path === '/hsk-levels') return reply([{ id: bundle.lesson.hsk_level_id, level_number: 1, title: 'HSK 1', state: 'AVAILABLE' }])
      if (path === `/lessons/${lessonId}`) return reply({ ...bundle.lesson, vocabulary: words.map(word => ({ id: word.id, order_index: word.order_index, note: word.note, example: word.example, item: { id: word.vocabulary_id, hanzi: word.hanzi, pinyin: word.pinyin, vietnamese_meaning: word.vietnamese_meaning, part_of_speech: word.part_of_speech } })), grammar: grammar.map(item => ({ id: item.id, order_index: item.order_index, note: item.note, example: item.example, item: { id: item.grammar_id, name: item.name, structure: item.structure, explanation: item.explanation, usage: item.usage } })), readings, assessment_ids: ['practice'] })
      if (path === `/me/progress/lessons/${lessonId}`) return reply({ lesson_id: lessonId, started_at: time, theory_completed_at: ready() ? time : null, completed_at: null, vocabulary: words.map(word => ({ id: word.id, viewed: state.seen.has(word.id) })), grammar: grammar.map(item => ({ id: item.id, viewed: state.grammar })), readings: readings.map(item => ({ id: item.id, completed: state.reading, completed_at: state.reading ? time : null })) })
      const view = path.match(/\/theory\/vocabulary\/([^/]+)\/view$/)
      if (view) {
        if (state.fail) return reply({ error: { code: 'FIXTURE_FAILURE', message: 'Fixture only' } }, 503)
        if (state.delay) await new Promise(resolve => setTimeout(resolve, state.delay))
        state.seen.add(view[1]); return reply({ viewed_at: time, theory_completed_at: ready() ? time : null })
      }
      if (path.includes('/theory/grammar/')) { state.grammar = true; return reply({ viewed_at: time, theory_completed_at: ready() ? time : null }) }
      if (path.includes('/theory/readings/')) { state.reading = true; return reply({ completed_at: time, theory_completed_at: ready() ? time : null }) }
      unexpected.push(path); return reply({}, 404)
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    async function capture(name) {
      await page.evaluate(async () => {
        await document.fonts.ready
        for (const node of document.querySelectorAll('.academy-word-illustration')) {
          if (!node.getClientRects().length) continue
          const match = getComputedStyle(node).backgroundImage.match(/url\(["']?(.*?)["']?\)/)
          if (match) { const image = new Image(); image.src = match[1]; await image.decode() }
        }
      })
      const metrics = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, headerHeight: document.querySelector('.lesson-header').getBoundingClientRect().height }))
      assert(metrics.scroll <= width + 1, `${name}: overflow at ${width}`)
      assert(metrics.headerHeight <= 145, `${name}: header grew to ${metrics.headerHeight}`)
      await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: false, animations: 'disabled' })
      captures.push({ name, ...metrics })
    }
    async function aligned(name) {
      await page.waitForFunction(() => {
        const content = document.querySelector('#lesson-study-content')?.getBoundingClientRect()
        const header = document.querySelector('.lesson-header')?.getBoundingClientRect()
        return content && header && content.top >= header.bottom - 2
      })
      const value = await page.evaluate(() => {
        const header = document.querySelector('.lesson-header').getBoundingClientRect()
        const nav = document.querySelector('.lesson-sequence-nav').getBoundingClientRect()
        const content = document.querySelector('#lesson-study-content').getBoundingClientRect()
        const heading = document.querySelector('.vocabulary-study-card__identity h2') ?? document.querySelector('#lesson-study-content h2')
        return { scroll: scrollY, content: content.top, header: header.bottom, nav: nav.bottom, heading: heading?.getBoundingClientRect().top, focus: document.activeElement === heading }
      })
      const limit = width <= 800 ? Math.max(value.header, value.nav) : value.header
      assert(value.heading >= limit - 2 && value.heading < 650, `${name}: heading covered or too far down: ${JSON.stringify(value)}`)
      positions.push({ width, name, ...value })
    }
    await page.goto(`${origin}/lessons/${lessonId}`)
    await page.getByRole('heading', { name: words[0].hanzi, exact: true }).waitFor()
    await page.waitForFunction(() => ![...document.querySelectorAll('button')].find(button => button.textContent.includes('Tiếp theo'))?.disabled)
    assert.equal(await page.locator('.lesson-header .academy-header-art').count(), 0)
    assert.equal(await page.getByText('Đã bắt đầu: Có', { exact: true }).count(), 0)
    if (width <= 800) assert.equal(await page.getByRole('button', { name: 'Luyện viết nét', exact: true }).getAttribute('aria-expanded'), 'false')
    await capture('first-word')
    state.fail = true
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByRole('heading', { name: words[1].hanzi, exact: true }).waitFor()
    await page.getByRole('alert').waitFor()
    assert.equal(await page.getByRole('button', { name: 'Tiếp theo', exact: true }).isDisabled(), true)
    await aligned('next-word-save-error')
    await capture('save-error')
    state.fail = false; state.delay = 500
    await page.getByRole('button', { name: 'Thử lưu lại', exact: true }).click()
    await page.evaluate(() => window.scrollTo(0, Math.min(200, document.documentElement.scrollHeight - innerHeight)))
    const during = await page.evaluate(() => scrollY)
    await page.waitForFunction(() => ![...document.querySelectorAll('button')].find(button => button.textContent.includes('Tiếp theo'))?.disabled)
    const after = await page.evaluate(() => scrollY)
    assert(Math.abs(after - during) <= 3, `Saving progress moved reading position: ${during} -> ${after}`)
    state.delay = 0
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByRole('heading', { name: words[2].hanzi, exact: true }).waitFor()
    await aligned('third-word')
    if (width <= 800) {
      await page.getByRole('button', { name: 'Luyện viết nét', exact: true }).click()
      assert.equal(await page.getByRole('button', { name: 'Luyện viết nét', exact: true }).getAttribute('aria-expanded'), 'true')
      await capture('writing-open')
      await page.getByRole('button', { name: 'Luyện viết nét', exact: true }).click()
    }
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByRole('heading', { name: /^Ngữ pháp/ }).waitFor()
    await aligned('grammar')
    await capture('grammar')
    await page.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    assert.equal(await page.getByRole('button', { name: 'Mở luyện tập 1', exact: true }).isDisabled(), true)
    await page.getByRole('link', { name: 'Ngữ pháp', exact: true }).click()
    await page.getByRole('button', { name: 'Xem chi tiết', exact: true }).click()
    await page.getByRole('link', { name: 'Tiếp: Bài khóa', exact: true }).click()
    await page.getByRole('heading', { name: /^Bài khóa/ }).waitFor()
    assert.equal(await page.locator('.lesson-reading-text__hanzi').textContent(), readings[0].content)
    await aligned('readings')
    await capture('readings')
    await page.getByRole('button', { name: 'Hoàn thành bài khóa: ' + readings[0].title, exact: true }).click()
    await page.getByRole('link', { name: 'Đến luyện tập', exact: true }).click()
    await page.getByRole('link', { name: 'Mở luyện tập 1', exact: true }).waitFor()
    await aligned('practice')
    await capture('practice-open')
    assert.equal(state.seen.size, 3)
    await context.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/verification.json`, JSON.stringify({ fixture: 'All requests intercepted; no live progress/content writes', captures, positions, errors, unexpected }, null, 2))
}
console.log(`PASS: ${captures.length} captures; route scroll, save stability, writing and practice gates verified.`)
