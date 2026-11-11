import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5174'
const folder = resolve('../.impeccable/review/student-study-blocks')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ headless: true })
const captures = [], errors = [], unexpected = []
const time = '2026-11-05T10:00:00Z'
const description = 'Làm quen với lời chào 你好 và các chữ đầu tiên. Bài khóa: A: 你好！ Học cách nhận mặt chữ, hiểu nghĩa và dùng các cụm từ ngắn.'
const codes = ['INITIALS', 'FINALS', 'TONES', 'SANDHI']
const names = ['thanh mẫu', 'vận mẫu', 'thanh điệu', 'biến điệu']
const slugs = ['thanh-mau', 'van-mau', 'thanh-dieu', 'bien-dieu']
const totals = [21, 36, 5, 12]
function install(context) {
  const state = { index: 3, step: 0, writes: [], legacy: true }
  context.route('**/api/v1/**', route => {
    const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET,POST,OPTIONS' }
    const reply = (json, status = 200) => route.fulfill({ json, status, headers })
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    if (path === '/auth/logout' && request.method() === 'POST') return route.fulfill({ status: 204, headers })
    if (request.method() !== 'GET') state.writes.push({ path, body: request.postDataJSON() })
    const payload = () => ({ sections: codes.map((code, index) => ({ id: code, code, total_steps: totals[index], completed_at: index < state.index ? time : null })), current_section: codes[state.index] ?? null, step_index: state.step, total_steps: totals[state.index] ?? 0, completed_at: state.legacy ? time : null, can_finish: state.index === 4 && !state.legacy })
    if (path === '/auth/me') return reply({ id: 'student', full_name: 'Nguyễn An', email: 'review@example.invalid', role: 'LEARNER' })
    if (path === '/me/dashboard') return reply({ current_hsk: { id: 'hsk', level_number: 1, title: 'HSK 1' }, current_lesson: { id: 'lesson', lesson_number: 1, title: '你好 · Xin chào', description }, current_unit: { id: 'unit', order_index: 1, unit_type: 'LESSON', state: 'AVAILABLE', lesson: { id: 'lesson', lesson_number: 1, title: '你好 · Xin chào', status: 'PUBLISHED' }, assessment: null }, progress_percentage: 25, continue_learning: { type: 'LESSON', lesson_id: 'lesson' } })
    if (path === '/hsk-levels') return reply([{ id: 'hsk', level_number: 1, title: 'HSK 1', description: null, state: 'AVAILABLE' }])
    if (path === '/lessons/lesson') return reply({ id: 'lesson', hsk_level_id: 'hsk', lesson_number: 1, title: '你好 · Xin chào', description, vocabulary: [], grammar: [], readings: [], assessment_ids: [] })
    if (path === '/me/progress/lessons/lesson') return reply({ lesson_id: 'lesson', started_at: time, theory_completed_at: null, completed_at: null, vocabulary: [], grammar: [], readings: [] })
    if (path === '/pronunciation/lesson') return reply(payload())
    if (path === '/pronunciation/lesson/advance') { assert.equal(request.postDataJSON().section_code, codes[state.index]); state.step++; return reply(payload()) }
    if (path === '/pronunciation/SANDHI/complete') { state.index = 4; state.step = 0; return reply({ completed_at: time }) }
    unexpected.push({ path, method: request.method() }); return reply({}, 404)
  })
  return state
}
async function capture(page, name, width) {
  await page.evaluate(async () => {
    await document.fonts.ready
    const sources = new Set([...document.querySelectorAll('*')].flatMap(element => [...getComputedStyle(element).backgroundImage.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(match => match[1])))
    await Promise.all([...sources].map(async src => { const image = new Image(); image.src = src; await image.decode() }))
  })
  const metrics = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, viewport: innerWidth }))
  assert(metrics.scroll <= metrics.viewport + 1, `${name}: overflow at ${width}`)
  await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: true, animations: 'disabled' })
  captures.push({ name, width, ...metrics })
}
try {
  for (const width of (process.env.BO_REVIEW_WIDTHS || '1440,1024,768,390').split(',').map(Number)) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    const state = install(context), page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(origin + '/dashboard')
    await page.locator('.academy-overview-item').last().waitFor()
    assert.equal(await page.getByText(description, { exact: true }).count(), 0)
    await capture(page, 'dashboard-icon-layout', width)
    await page.goto(origin + '/lessons/lesson')
    await page.getByRole('heading', { name: 'Bài học 1: 你好 · Xin chào', exact: true }).waitFor()
    assert.equal(await page.getByText(description, { exact: true }).count(), 0)
    await capture(page, 'lesson-no-description', width)
    assert.deepEqual(state.writes, [])
    await page.goto(origin + '/pronunciation/lesson')
    const grid = page.getByRole('list', { name: 'Các phần của bài học' })
    await grid.getByRole('link', { name: 'Học biến điệu', exact: true }).waitFor()
    assert.equal(await page.getByText(/quyền học HSK được giữ nguyên/).count(), 0)
    const columns = await grid.evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length)
    assert.equal(columns, width > 600 ? 2 : 1)
    await capture(page, 'pronunciation-section-blocks', width)
    for (let index = 0; index < 3; index++) {
      const block = page.getByRole('link', { name: 'Ôn ' + names[index], exact: true })
      assert.equal(await block.evaluate(element => getComputedStyle(element).textDecorationLine), 'none')
      await block.click({ position: { x: 16, y: 16 } })
      assert.equal(new URL(page.url()).pathname, '/pronunciation/lesson/' + slugs[index])
      await page.locator('#pronunciation-step-title').waitFor()
      assert.equal(await page.locator('.academy-source, .academy-pronunciation-reference').count(), 0)
      assert.equal(await page.locator('.pronunciation-session__review-note').count(), 0)
      const tipBefore = await page.locator('.academy-articulation-note p').innerText()
      assert.equal(await page.locator('.pronunciation-section-grid').count(), 0)
      assert.equal(await page.evaluate(() => scrollY), 0)
      assert.equal(await page.locator('#page-title').evaluate(element => element === document.activeElement), true)
      await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
      await page.waitForFunction(previous => document.querySelector('.academy-articulation-note p')?.textContent !== previous, tipBefore)
      assert.deepEqual(state.writes, [], 'Review must not mutate saved progress')
      if (index === 2) await capture(page, 'tone-review-page', width)
      await page.goBack()
      await grid.waitFor()
    }
    await page.getByRole('link', { name: 'Học biến điệu', exact: true }).click({ position: { x: 16, y: 16 } })
    assert.equal(new URL(page.url()).pathname, '/pronunciation/lesson/bien-dieu')
    await page.getByText('ní hǎo', { exact: true }).waitFor()
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByText('老师', { exact: true }).waitFor()
    assert.equal(state.step, 1)
    await page.reload(); await page.getByText('老师', { exact: true }).waitFor()
    await capture(page, 'sandhi-page-resume', width)
    for (let index = 1; index < 12; index++) {
      await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
      await page.waitForFunction(value => document.querySelector('progress').value === value, index + 1)
    }
    await page.getByRole('button', { name: 'Hoàn thành biến điệu', exact: true }).click()
    await page.getByRole('heading', { name: 'Che pinyin, thử tự đọc', exact: true }).waitFor()
    assert.equal(new URL(page.url()).pathname, '/pronunciation/lesson')
    await capture(page, 'completed-section-blocks', width)
    state.index = 0; state.step = 0; state.legacy = false
    await page.reload(); await page.getByRole('link', { name: 'Học thanh mẫu', exact: true }).waitFor()
    assert.equal(await grid.getByRole('link').count(), 1)
    await capture(page, 'new-learner-locked-blocks', width)
    await page.goto(origin + '/pronunciation/lesson/van-mau')
    await page.getByRole('heading', { name: 'Phần học này chưa mở', exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Tiếp theo', exact: true }).count(), 0)
    await capture(page, 'locked-direct-route', width)
    await context.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
  await writeFile(folder + '/verification.json', JSON.stringify({ origin, captures, errors, unexpected, scope: 'Isolated fixture APIs; no real lesson content or learner progress changed.' }, null, 2))
  console.log(JSON.stringify({ captures: captures.length, errors, unexpected }))
} finally { await browser.close() }
