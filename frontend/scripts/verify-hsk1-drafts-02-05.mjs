import assert from 'node:assert/strict'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const fixture = JSON.parse(await readFile('../tmp/hsk1-drafts-02-05-fixture.json', 'utf8'))
const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5173'
const folder = resolve('../.impeccable/review/hsk1-drafts-02-05')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch()
const errors = [], unexpected = [], writes = [], captures = []
const bundles = Object.values(fixture.lessons)
const lesson = number => bundles.find(bundle => bundle.lesson.lesson_number === number)

try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    await context.route('**/api/v1/**', async route => {
      const request = route.request(), url = new URL(request.url()), path = url.pathname.split('/api/v1')[1]
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
      const reply = json => route.fulfill({ json, headers })
      if (request.method() === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
      if (request.method() !== 'GET') writes.push(path)
      if (path === '/auth/me') return reply({ id: 'review-admin', role: 'ADMIN', full_name: 'Quản trị', email: 'review@example.invalid' })
      if (path === '/admin/hsk-levels') return reply(fixture.levels)
      if (path === '/admin/lessons') {
        const items = bundles.map(bundle => bundle.lesson).filter(item => !url.searchParams.get('status') || item.status === url.searchParams.get('status'))
        return reply({ items, total: items.length, page: 1, page_size: 20 })
      }
      if (path.includes('/admin/hsk-levels/') && path.endsWith('/curriculum')) return reply(fixture.curriculum)
      for (const bundle of bundles) {
        if (path === `/admin/lessons/${bundle.lesson.id}`) return reply(bundle.lesson)
        for (const kind of ['vocabulary', 'grammar', 'readings']) if (path === `/admin/lessons/${bundle.lesson.id}/${kind}`) return reply(bundle[kind])
        for (const item of bundle.exercises.items) {
          if (path === `/admin/assessments/${item.id}`) return reply(item)
          if (path === `/admin/assessments/${item.id}/questions`) return reply(bundle.questions[item.id])
        }
      }
      if (path === '/admin/assessments') {
        const bundle = fixture.lessons[url.searchParams.get('lesson_id')]
        return reply(bundle ? bundle.exercises : { items: [], total: 0, page: 1, page_size: 20 })
      }
      unexpected.push(path)
      return route.fulfill({ status: 404, json: { error: { code: 'NOT_FOUND', message: 'Fixture only' } }, headers })
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    async function capture(name) {
      await page.evaluate(async () => {
        await document.fonts.ready
        const backgrounds = [...document.querySelectorAll('.academy-word-illustration')].filter(node => node.getClientRects().length)
        await Promise.all(backgrounds.map(async node => {
          const match = getComputedStyle(node).backgroundImage.match(/url\(["']?(.*?)["']?\)/)
          if (match) { const image = new Image(); image.src = match[1]; await image.decode() }
        }))
      })
      const metrics = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, headings: [...document.querySelectorAll('h1')].filter(item => item.getClientRects().length).length }))
      assert(metrics.scroll <= width + 1, `${name}: horizontal overflow`)
      assert.equal(metrics.headings, 1)
      await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: true, animations: 'disabled' })
      captures.push({ name, ...metrics })
    }
    for (let attempt = 0; ; attempt++) {
      try { await page.goto(origin + '/admin/lessons'); break } catch (error) { if (attempt >= 4) throw error; await page.waitForTimeout(1000) }
    }
    await page.locator('.admin-library-card').first().waitFor()
    const nav = page.getByRole('navigation', { name: 'Điều hướng quản trị' })
    assert.equal(await nav.getByRole('link', { name: 'Lộ trình', exact: true }).count(), 0)
    assert.equal(await nav.getByRole('link').count(), 5)
    await capture('draft-library')
    await page.getByRole('link', { name: 'Sắp xếp HSK', exact: true }).click()
    await page.getByRole('heading', { name: 'Sắp xếp HSK', exact: true }).waitFor()
    await page.getByRole('heading', { name: 'Lộ trình hiện tại', exact: true }).waitFor()
    await capture('ordering-inside-lessons')
    await page.goto(origin + '/admin/curriculum')
    await page.waitForURL('**/admin/lessons?view=curriculum')
    for (const number of [2, 3, 4, 5]) {
      const bundle = lesson(number)
      assert.equal(bundle.lesson.status, 'DRAFT')
      await page.goto(`${origin}/admin/lessons/${bundle.lesson.id}`)
      await page.getByRole('heading', { name: `Từ vựng · ${bundle.vocabulary.length}`, exact: true }).waitFor()
      if (width <= 640) await page.getByRole('button', { name: 'Xem trước', exact: true }).click()
      assert.equal(await page.locator('.vocabulary-study-card .academy-word-illustration:visible, .vocabulary-study-card .academy-numeral-illustration:visible').count(), 1)
      await capture(`lesson-${number}-vocabulary`)
      if (number === 4) {
        const positions = new Set()
        for (const word of ['爸爸', '妈妈', '爷爷', '奶奶', '外公', '外婆']) {
          await page.getByRole('navigation', { name: 'Danh sách từ vựng', exact: true }).getByRole('button').filter({ hasText: word }).click()
          if (width <= 640) await page.getByRole('button', { name: 'Xem trước', exact: true }).click()
          const picture = page.locator('.vocabulary-study-card [data-illustration="chibi-family"]:visible')
          await picture.waitFor()
          positions.add(await picture.evaluate(node => node.style.backgroundPosition))
          await capture(`lesson-4-family-${word}`)
        }
        assert.equal(positions.size, 6)
      }
      if (number === 3 || number === 5) {
        const word = number === 3 ? '中国' : '饺子'
        await page.getByRole('navigation', { name: 'Danh sách từ vựng', exact: true }).getByRole('button').filter({ hasText: word }).click()
        if (width <= 640) await page.getByRole('button', { name: 'Xem trước', exact: true }).click()
        await capture(`lesson-${number}-specific-art`)
      }
      if (number === 2) {
        await page.getByRole('button', { name: 'Ngữ pháp', exact: true }).click()
        await page.getByRole('heading', { name: `Ngữ pháp · ${bundle.grammar.length}`, exact: true }).waitFor()
        await capture('lesson-2-grammar')
        await page.getByRole('button', { name: 'Bài khóa', exact: true }).click()
        await page.getByRole('heading', { name: 'Bài khóa · 4', exact: true }).waitFor()
        await capture('lesson-2-readings')
      }
      await page.getByRole('button', { name: 'Duyệt xuất bản', exact: true }).click()
      const publish = page.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ', exact: true })
      await publish.waitFor()
      await page.waitForFunction(() => [...document.querySelectorAll('button')].some(button => button.textContent === 'Xác nhận xuất bản toàn bộ' && !button.disabled))
      assert.equal(await publish.isEnabled(), true)
      assert.equal(await page.getByText('30/30 câu · 4 dạng bài · Điểm đạt 80%', { exact: true }).count(), 1)
      await capture(`lesson-${number}-review`)
    }
    await context.close()
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(unexpected, [])
  assert.deepEqual(writes, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/verification.json`, JSON.stringify({ fixture: 'Read-only export; all API requests intercepted; no publish or content writes', captures, errors, unexpected, writes }, null, 2))
}
console.log(`PASS: ${captures.length} captures; drafts and embedded ordering reviewed without publishing.`)
