import assert from 'node:assert/strict'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://localhost:5173'
const folder = '../.impeccable/review/reading-illustrations'
await mkdir(folder, { recursive: true })
const readings = []
for (let lesson = 1; lesson <= 5; lesson++) {
  const data = JSON.parse(await readFile(`../backend/content/hsk1/lesson-${String(lesson).padStart(2, '0')}.json`, 'utf8'))
  readings.push(...data.readings.map(reading => ({ ...reading, id: `reading-${readings.length + reading.order_index}`, version: 1 })))
}
const errors = [], unexpected = [], writes = []
const browser = await chromium.launch({ headless: true })
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    await context.route('**/api/v1/**', route => {
      const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
      const reply = json => route.fulfill({ json, headers })
      if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
      if (path === '/auth/logout' && request.method() === 'POST') return route.fulfill({ status: 204, headers })
      if (request.method() !== 'GET') { writes.push(path); return route.fulfill({ status: 409, json: {} }) }
      if (path === '/auth/me') return reply({ id: 'review', full_name: 'Bạn học', email: 'review@example.invalid', role: 'LEARNER' })
      if (path === '/hsk-levels') return reply([{ id: 'hsk-1', level_number: 1, title: 'HSK 1', description: null, state: 'AVAILABLE' }])
      if (path === '/lessons/review') return reply({ id: 'review', hsk_level_id: 'hsk-1', lesson_number: 1, title: 'Minh họa bài khóa', description: null, vocabulary: [], grammar: [], readings, assessment_ids: [] })
      if (path === '/me/progress/lessons/review') return reply({ lesson_id: 'review', started_at: '2026-11-15T00:00:00Z', theory_completed_at: null, completed_at: null, vocabulary: [], grammar: [], readings: readings.map(reading => ({ id: reading.id, completed: false, completed_at: null })) })
      unexpected.push(path)
      return route.fulfill({ status: 404, json: {} })
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(`${origin}/lessons/review/readings`)
    try { await page.locator('.lesson-reading-card').last().waitFor({ timeout: 10000 }) }
    catch (error) {
      await writeFile(`${folder}/failure.json`, JSON.stringify({ url: page.url(), text: await page.locator('body').innerText(), errors, unexpected, writes }, null, 2))
      throw error
    }
    await page.evaluate(async () => {
      await document.fonts.ready
      const image = new Image()
      image.src = '/academy/but-reading-scenes-v1.webp'
      await image.decode()
    })
    assert.equal(await page.locator('.lesson-reading-card').count(), 14)
    assert.equal(await page.locator('.lesson-reading-scene').count(), 14)
    assert.deepEqual(await page.locator('.lesson-reading-scene').evaluateAll(nodes => nodes.map(node => Number(node.dataset.scene))), Array.from({ length: 14 }, (_, index) => index))
    assert.equal(await page.locator('.lesson-word-index, .lesson-reading-companion').count(), 0)
    assert(await page.locator('.bo-shell, .academy-workspace').evaluateAll(nodes => nodes.every(node => getComputedStyle(node).backgroundImage === 'none')))
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
    const layout = await page.locator('.lesson-reading-card').evaluateAll(cards => cards.map(card => {
      const copy = card.querySelector('.lesson-reading-text__copy').getBoundingClientRect()
      const hanzi = card.querySelector('.lesson-reading-text__hanzi').getBoundingClientRect()
      const image = card.querySelector('.lesson-reading-scene').getBoundingClientRect()
      const translations = card.querySelector('.lesson-reading-text__translations').getBoundingClientRect()
      const supports = [...card.querySelectorAll('.lesson-reading-text__support')].map(node => node.getBoundingClientRect())
      return { copy: { right: copy.right, bottom: copy.bottom, center: copy.y + copy.height / 2 }, hanziBottom: hanzi.bottom, translationTop: translations.top, supports: supports.map(rect => ({ x: rect.x, y: rect.y })), image: { x: image.x, y: image.y, width: image.width, center: image.y + image.height / 2 } }
    }))
    for (const item of layout) {
      assert(item.translationTop >= item.hanziBottom + 15)
      assert(item.image.width <= (width < 700 ? 240 : 380) + 1)
      assert(item.supports[1].y > item.supports[0].y)
      assert(Math.abs(item.supports[0].x - item.supports[1].x) <= 1)
      if (width >= 700) { assert(item.image.x > item.copy.right); assert(Math.abs(item.image.center - item.copy.center) <= 1) }
      else assert(item.image.y >= item.copy.bottom)
    }
    for (const index of [0, 3, 7, 9, 12, 13]) {
      const card = page.locator('.lesson-reading-card').nth(index)
      await card.scrollIntoViewIfNeeded()
      if (width < 700) {
        await card.evaluate(node => {
          const headerHeight = document.querySelector('.lesson-header')?.getBoundingClientRect().height ?? 0
          window.scrollTo({ top: window.scrollY + node.getBoundingClientRect().top - headerHeight - 16, behavior: 'instant' })
        })
        await page.screenshot({ path: `${folder}/scene-${index}-${width}.png` })
      } else await card.screenshot({ path: `${folder}/scene-${index}-${width}.png` })
    }
    await context.close()
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(unexpected, [])
  assert.deepEqual(writes, [])
  const report = { readings: 14, widths: [1440, 390], captures: 12, errors, unexpected, writes, scope: 'Mock API only; no real learner data or content writes.' }
  await writeFile(`${folder}/verification.json`, JSON.stringify(report, null, 2))
  console.log(JSON.stringify(report))
} finally { await browser.close() }
