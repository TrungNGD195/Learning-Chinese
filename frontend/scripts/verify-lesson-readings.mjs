import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5174'
const folder = resolve('../.impeccable/review/lesson-readings')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ headless: true })
const captures = [], errors = [], unexpected = []
const time = '2026-11-05T10:00:00Z'
const first = { id: 'reading-1', order_index: 1, title: 'Chào hỏi · 你好', content: 'A：你好！\nB：你好！', pinyin: 'A: Nǐ hǎo!\nB: Nǐ hǎo!', vietnamese_translation: 'A: Xin chào!\nB: Xin chào!', source_reference: 'Giáo trình HSK1 3.0 Hanu 24.6.26, bài 1, trang in 1 (trang PDF 3).', version: 1 }
const second = { ...first, id: 'reading-2', order_index: 2, title: 'Hội thoại để kiểm tra khả năng hiển thị khi tiêu đề bài khóa dài hơn bình thường', content: 'A：你好吗？\nB：我很好。你呢？\nA：我也很好。', pinyin: null, vietnamese_translation: null, source_reference: null }
function install(context, admin = false) {
  const state = { readings: [first, second], done: new Set(), failed: false, stale: false, writes: [] }
  context.route('**/api/v1/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,PUT,DELETE,OPTIONS', 'access-control-allow-headers': 'content-type' }
    const reply = (json, status = 200) => route.fulfill({ json, status, headers })
    const failure = (code = 'FIXTURE_FAILURE') => ({ error: { code, message: 'Isolated fixture', details: null } })
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    if (path === '/auth/logout' && request.method() === 'POST') return route.fulfill({ status: 204, headers })
    if (request.method() !== 'GET') state.writes.push({ path, method: request.method(), body: request.postDataJSON() })
    if (path === '/auth/me') return reply({ id: 'user', full_name: 'Nguyễn An', email: 'review@example.invalid', role: admin ? 'ADMIN' : 'LEARNER' })
    if (path === '/hsk-levels' || path === '/admin/hsk-levels') return reply([{ id: 'hsk', level_number: 1, title: 'HSK 1', order_index: 1, description: null, state: 'AVAILABLE' }])
    if (path === '/lessons/lesson') return reply({ id: 'lesson', hsk_level_id: 'hsk', lesson_number: 1, title: '你好 · Xin chào', description: 'Làm quen với lời chào bằng tiếng Trung.', vocabulary: [], grammar: [], readings: state.readings, assessment_ids: ['practice'] })
    if (path === '/me/progress/lessons/lesson') return reply({ lesson_id: 'lesson', started_at: time, theory_completed_at: state.readings.every(row => state.done.has(row.id)) ? time : null, completed_at: null, vocabulary: [], grammar: [], readings: state.readings.map(row => ({ id: row.id, completed: state.done.has(row.id), completed_at: state.done.has(row.id) ? time : null })) })
    if (path.startsWith('/lessons/lesson/theory/readings/')) {
      if (state.failed) return reply(failure(), 503)
      if (state.stale) { state.stale = false; state.readings = state.readings.map(row => ({ ...row, version: 2 })); return reply(failure('READING_VERSION_CHANGED'), 409) }
      state.done.add(path.split('/readings/')[1].split('/')[0])
      return reply({ completed_at: time, theory_completed_at: state.done.size === state.readings.length ? time : null })
    }
    if (path === '/me/dashboard') return reply({ current_hsk: null, current_lesson: null, current_unit: null, progress_percentage: 0, continue_learning: null })
    if (path === '/me/progress') return reply({ current_hsk: 1, progress_percentage: 0, pronunciation_complete: true, hsk_levels: [] })
    if (path === '/admin/lessons/lesson') return reply({ id: 'lesson', hsk_level_id: 'hsk', lesson_number: 1, title: '你好 · Xin chào', description: 'Lời chào đầu tiên.', status: 'DRAFT', published_at: null })
    if (path === '/admin/lessons/lesson/vocabulary' || path === '/admin/lessons/lesson/grammar') return reply([])
    if (path === '/admin/assessments') return reply({ items: [], total: 0, page: 1, page_size: 20 })
    if (path === '/admin/lessons/lesson/readings') return reply(state.readings)
    if (path.startsWith('/admin/lessons/lesson/readings/')) return reply(failure('READING_ORDER_CONFLICT'), 409)
    unexpected.push({ path, method: request.method() }); return reply(failure(), 404)
  })
  return state
}

async function capture(page, name, width) {
  assert.equal(await page.locator('.lesson-reading-text__source').count(), 0)
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => image.decode())) })
  const metrics = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, viewport: innerWidth }))
  assert(metrics.scroll <= metrics.viewport + 1, `${name} overflow at ${width}`)
  captures.push({ name, width, ...metrics })
  await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: true, animations: 'disabled' })
}
try {
  for (const width of [1440, 768, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    const state = install(context), page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(origin + '/lessons/lesson/readings')
    await page.getByRole('heading', { name: first.title, exact: true }).waitFor()
    await page.locator('#readings').scrollIntoViewIfNeeded()
    await capture(page, 'student-required', width)
    assert.equal(state.writes.length, 0, 'Reading the page must not mark it complete')
    state.failed = true
    await page.getByRole('button', { name: 'Hoàn thành bài khóa: ' + first.title, exact: true }).click()
    await page.getByRole('alert').waitFor(); await capture(page, 'student-save-error', width)
    state.failed = false; state.stale = true
    await page.getByRole('button', { name: 'Hoàn thành bài khóa: ' + first.title, exact: true }).click()
    await page.getByText('Bài khóa vừa được cập nhật. Hãy đọc lại nội dung mới rồi bấm hoàn thành.', { exact: true }).waitFor()
    await capture(page, 'student-version-changed', width)
    await page.getByRole('button', { name: 'Hoàn thành bài khóa: ' + first.title, exact: true }).click()
    await page.getByRole('button', { name: 'Đã hoàn thành bài khóa: ' + first.title, exact: true }).waitFor()
    await page.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    assert.equal(await page.getByRole('button', { name: 'Mở luyện tập 1', exact: true }).isDisabled(), true)
    await page.getByRole('link', { name: 'Bài khóa', exact: true }).click()
    await page.getByRole('button', { name: 'Hoàn thành bài khóa: ' + second.title, exact: true }).click()
    await page.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    await page.getByRole('link', { name: 'Mở luyện tập 1', exact: true }).waitFor()
    await capture(page, 'student-completed', width)
    await page.reload(); await page.getByRole('link', { name: 'Mở luyện tập 1', exact: true }).waitFor()
    await page.getByRole('link', { name: 'Bài khóa', exact: true }).click()
    await page.evaluate(() => document.documentElement.style.setProperty('--reader-font-size', '23px'))
    await page.locator('#readings').scrollIntoViewIfNeeded(); await capture(page, 'student-large-text', width)
    state.readings = []; await page.reload(); await page.getByRole('heading', { name: 'Chưa có bài khóa', exact: true }).waitFor(); await capture(page, 'student-empty', width)
    await context.close()

    const adminContext = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    install(adminContext, true)
    const admin = await adminContext.newPage(); admin.on('pageerror', error => errors.push(error.message))
    await admin.goto(origin + '/admin/lessons/lesson')
    await admin.getByRole('button', { name: 'Bài khóa', exact: true }).click()
    await admin.getByRole('heading', { name: 'Biên soạn bài khóa', exact: true }).waitFor()
    await capture(admin, 'admin-reading-editor', width)
    await admin.getByLabel('Tiêu đề bài khóa', { exact: true }).first().fill('Chào hỏi đã chỉnh sửa')
    await admin.getByRole('button', { name: 'Lưu bài khóa', exact: true }).click()
    await admin.getByRole('alert').waitFor(); await capture(admin, 'admin-order-error', width)
    await admin.getByRole('button', { name: 'Xóa bài khóa', exact: true }).click()
    await admin.getByRole('dialog', { name: 'Xóa bài khóa này?' }).waitFor(); await capture(admin, 'admin-delete-confirm', width)
    await admin.getByRole('dialog').getByRole('button', { name: 'Hủy', exact: true }).click()
    await adminContext.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
  await writeFile(folder + '/verification.json', JSON.stringify({ origin, captures, errors, unexpected, scope: 'Isolated fixture APIs; no real user data or publishing.' }, null, 2))
  console.log(JSON.stringify({ captures: captures.length, errors, unexpected }))
} finally { await browser.close() }
