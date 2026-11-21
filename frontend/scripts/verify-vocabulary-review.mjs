import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://localhost:5173'
const output = '../.impeccable/review/vocabulary-review'
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ headless: true })
const errors = [], unexpected = []
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 950 }, reducedMotion: 'reduce' })
    let empty = false
    await context.route('**/api/v1/**', route => {
      const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
      const reply = json => route.fulfill({ json, headers })
      if (request.method() === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
      if (path === '/auth/me') return reply({ id: 'review', full_name: 'Bạn học', role: 'LEARNER', email: 'review@example.invalid' })
      if (path === '/me/vocabulary-review') return reply({ page: 1, page_size: 50, total: empty ? 0 : 2, items: empty ? [] : [
        { id: 'one', hanzi: '你', pinyin: 'nǐ', vietnamese_meaning: 'bạn', part_of_speech: 'đại từ', lessons: [{ lesson_id: 'one', hsk_level: 1, lesson_number: 1, title: 'Xin chào', note: '你 dùng khi nói với một người; 您 là cách xưng hô lịch sự.' }] },
        { id: 'two', hanzi: '好', pinyin: 'hǎo', vietnamese_meaning: 'tốt; khỏe', part_of_speech: 'tính từ', lessons: [{ lesson_id: 'one', hsk_level: 1, lesson_number: 1, title: 'Xin chào', note: null }] },
      ] })
      unexpected.push(path)
      return route.fulfill({ status: 404, json: {} })
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(`${origin}/vocabulary-review`)
    const card = page.getByRole('button', { name: 'Lật thẻ 你 để xem phiên âm và nghĩa' })
    await card.waitFor()
    await page.evaluate(() => document.fonts.ready)
    assert.equal(await page.getByText('nǐ', { exact: true }).count(), 0)
    await card.click()
    await page.getByText('nǐ', { exact: true }).waitFor()
    assert.ok(await page.getByRole('heading', { name: 'Lưu ý khi dùng' }).isVisible())
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
    await page.screenshot({ path: `${output}/${width}-answer.png`, fullPage: true })
    await page.getByRole('button', { name: 'Tiếp theo →' }).click()
    await page.getByRole('button', { name: 'Lật thẻ 好 để xem phiên âm và nghĩa' }).waitFor()
    empty = true
    await page.reload()
    await page.getByRole('heading', { name: 'Bắt đầu từ một bài học' }).waitFor()
    await page.screenshot({ path: `${output}/${width}-empty.png`, fullPage: true })
    await context.close()
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(unexpected, [])
  await writeFile(`${output}/result.json`, JSON.stringify({ widths: [1440, 390], errors, unexpected, passed: true }, null, 2))
  console.log('Vocabulary review: desktop/mobile, reveal, next, empty state and overflow passed.')
} finally { await browser.close() }
