import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = 'http://127.0.0.1:5173'
const folder = resolve('../.impeccable/review/open-hsk-levels')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch()
const errors = [], unexpected = [], captures = []
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' })
    const state = { content: false }
    await context.route('**/api/v1/**', async route => {
      const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'content-type' }
      const reply = json => route.fulfill({ json, headers })
      if (request.method() === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
      if (request.method() !== 'GET') { unexpected.push(`${request.method()} ${path}`); return route.fulfill({ status: 405, headers }) }
      if (path === '/auth/me') return reply({ id: 'fixture', full_name: 'Nguyễn An', email: 'fixture@example.invalid', role: 'LEARNER' })
      if (path === '/hsk-levels') return reply([1, 2, 3].map(level => ({ id: `hsk-${level}`, level_number: level, title: `HSK ${level}`, description: null, state: level === 1 ? 'LOCKED' : 'AVAILABLE' })))
      if (path === '/pronunciation/lesson') return reply({ sections: [], current_section: 'INITIALS', step_index: 0, total_steps: 21, completed_at: null, can_finish: false })
      if (path === '/me/progress') return reply({ current_hsk: 1, pronunciation_complete: false, progress_percentage: 0, hsk_levels: [] })
      const match = path.match(/^\/hsk-levels\/hsk-([123])\/curriculum$/)
      if (match) {
        const level = Number(match[1])
        return reply({ hsk: { id: `hsk-${level}`, level_number: level, title: `HSK ${level}` }, units: state.content && level > 1 ? [1, 2].map(index => ({ id: `unit-${level}-${index}`, order_index: index, unit_type: 'LESSON', state: index === 1 ? 'AVAILABLE' : 'LOCKED', lesson: { id: `lesson-${level}-${index}`, lesson_number: index, title: `Bài học HSK ${level}`, status: 'PUBLISHED' }, assessment: null })) : [] })
      }
      unexpected.push(path); return route.fulfill({ status: 404, headers })
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    async function capture(name) {
      await page.locator('.wall-map__art').waitFor()
      await page.evaluate(async () => {
        await document.fonts.ready
        await Promise.all([...document.images].map(image => image.decode().catch(() => {})))
        const assets = new Set([...document.querySelectorAll('*')].flatMap(node => [...getComputedStyle(node).backgroundImage.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(match => match[1])))
        await Promise.all([...assets].map(async src => { const image = new Image(); image.src = src; await image.decode() }))
        window.scrollTo({ top: 0, behavior: 'instant' })
      })
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${name}: overflow`)
      await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: false, animations: 'disabled' })
      captures.push({ name, width })
    }
    await page.goto(origin + '/pronunciation')
    await page.getByRole('link', { name: 'Mở HSK 2', exact: true }).click()
    await page.waitForURL('**/hsk/2')
    await page.getByText('Lộ trình này chưa có nội dung học.', { exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: /Điều kiện mở HSK [23]/ }).count(), 0)
    await capture('hsk2-empty-open')
    await page.getByRole('link', { name: 'Mở HSK 3', exact: true }).click()
    await page.waitForURL('**/hsk/3')
    await page.getByText('Lộ trình này chưa có nội dung học.', { exact: true }).waitFor()
    await capture('hsk3-empty-open')
    state.content = true
    for (const level of [3, 2]) {
      await page.goto(`${origin}/hsk/${level}`)
      const first = page.locator(`.wall-stop[data-unit-id="unit-${level}-1"] a`)
      await first.waitFor()
      assert.equal(await first.getAttribute('href'), `/lessons/lesson-${level}-1`)
      assert.equal(await page.locator(`.wall-stop[data-unit-id="unit-${level}-2"] a`).count(), 0)
      assert.equal(await page.locator('.wall-stop[data-unit-id="phat-am"]').count(), 0)
      await capture(`hsk${level}-direct-entry`)
    }
    await context.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/verification.json`, JSON.stringify({ fixture: 'All API requests intercepted; no live learner/content writes', captures, errors, unexpected }, null, 2))
}
console.log(`PASS: HSK2/3 navigation, empty catalogs and direct lesson entry; ${captures.length} captures.`)
