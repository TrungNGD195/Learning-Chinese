import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5174'
const folder = resolve(process.env.BO_REVIEW_FOLDER || '../.impeccable/review/pronunciation-sandhi-strokes')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ headless: true })
const captures = [], errors = [], unexpected = []
const time = '2026-11-05T10:00:00Z'
const words = [
  { id: 'v1', hanzi: '字', pinyin: 'zì', vietnamese_meaning: 'chữ', part_of_speech: 'danh từ', example: '这个字很大。Zhège zì hěn dà. Chữ này rất to.', note: null },
  { id: 'v2', hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', part_of_speech: 'lời chào', example: '老师，你好！Lǎoshī, nǐ hǎo! Em chào thầy/cô!', note: 'Khi nói liền hai thanh 3, thanh đầu đọc gần thanh 2.' },
  { id: 'v3', hanzi: '我', pinyin: 'wǒ', vietnamese_meaning: 'tôi', part_of_speech: 'đại từ', example: '我很好。Wǒ hěn hǎo. Tôi rất khỏe.', note: null },
]
function install(context, admin = false) {
  const state = { step: 0, done: false, writes: [] }
  context.route('**/api/v1/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
    const reply = (json, status = 200) => route.fulfill({ json, status, headers })
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    if (path === '/auth/logout' && request.method() === 'POST') return route.fulfill({ status: 204, headers })
    if (request.method() !== 'GET') state.writes.push(path)
    const pronunciation = () => ({ sections: ['INITIALS', 'FINALS', 'TONES', 'SANDHI'].map((code, i) => ({ id: code, code, total_steps: [21, 36, 5, 12][i], completed_at: i < 3 || state.done ? time : null })), current_section: state.done ? null : 'SANDHI', step_index: state.step, total_steps: state.done ? 0 : 12, completed_at: time, can_finish: false })
    if (path === '/auth/me') return reply({ id: 'user', full_name: 'Nguyễn An', email: 'review@example.invalid', role: admin ? 'ADMIN' : 'LEARNER' })
    if (path === '/hsk-levels' || path === '/admin/hsk-levels') return reply([{ id: 'hsk', level_number: 1, title: 'HSK 1', order_index: 1, description: null, state: 'AVAILABLE' }])
    if (path === '/lessons/lesson') return reply({ id: 'lesson', hsk_level_id: 'hsk', lesson_number: 1, title: '你好 · Xin chào', description: 'Làm quen với lời chào bằng tiếng Trung.', vocabulary: words.map((word, i) => ({ id: word.id, order_index: i + 1, example: word.example, note: word.note, item: { id: word.id, hanzi: word.hanzi, pinyin: word.pinyin, vietnamese_meaning: word.vietnamese_meaning, part_of_speech: word.part_of_speech } })), grammar: [], readings: [], assessment_ids: ['practice'] })
    if (path === '/me/progress/lessons/lesson') return reply({ lesson_id: 'lesson', started_at: time, theory_completed_at: null, completed_at: null, vocabulary: words.map(word => ({ id: word.id, viewed: true })), grammar: [], readings: [] })
    if (path === '/me/dashboard') return reply({ current_hsk: null, current_lesson: null, current_unit: null, progress_percentage: 0, continue_learning: null })
    if (path === '/me/progress') return reply({ current_hsk: 1, progress_percentage: 0, pronunciation_complete: true, hsk_levels: [] })
    if (path === '/pronunciation/lesson') return reply(pronunciation())
    if (path === '/pronunciation/lesson/advance') { assert.equal(request.postDataJSON().section_code, 'SANDHI'); state.step++; return reply(pronunciation()) }
    if (path === '/pronunciation/SANDHI/complete') { state.done = true; return reply({ completed_at: time }) }
    if (path === '/admin/lessons/lesson') return reply({ id: 'lesson', hsk_level_id: 'hsk', lesson_number: 1, title: '你好 · Xin chào', description: 'Lời chào đầu tiên.', status: 'DRAFT', published_at: null })
    if (path === '/admin/lessons/lesson/vocabulary') return reply(words.map((word, i) => ({ ...word, order_index: i + 1 })))
    if (path === '/admin/lessons/lesson/grammar' || path === '/admin/lessons/lesson/readings') return reply([])
    if (path === '/admin/assessments') return reply({ items: [], total: 0, page: 1, page_size: 20 })
    unexpected.push({ path, method: request.method() }); return reply({ error: { code: 'FIXTURE_FAILURE', message: 'Unexpected fixture API', details: null } }, 404)
  })
  return state
}
async function capture(page, name, width) {
  await page.evaluate(() => document.fonts.ready)
  const metrics = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, viewport: innerWidth }))
  assert(metrics.scroll <= metrics.viewport + 1, `${name}: overflow ${JSON.stringify(metrics)}`)
  captures.push({ name, width, ...metrics })
  await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: true, animations: 'allow' })
}
try {
  for (const width of (process.env.BO_REVIEW_WIDTHS || '1440,768,390').split(',').map(Number)) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'no-preference' })
    const state = install(context), page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(origin + '/lessons/lesson/vocabulary/v1')
    const player = page.locator('[data-character="字"]')
    await player.scrollIntoViewIfNeeded()
    await page.waitForFunction(() => Number(document.querySelector('[data-character="字"]')?.dataset.writtenStrokes) >= 1)
    await player.getByRole('button', { name: 'Tạm dừng chữ 字', exact: true }).click()
    assert.equal(await player.getAttribute('data-total-strokes'), '6')
    await player.getByRole('button', { name: 'Bắt đầu lại chữ 字' }).click()
    await player.getByRole('button', { name: 'Tạm dừng chữ 字', exact: true }).click()
    await player.getByRole('button', { name: 'Nét tiếp theo của chữ 字' }).click()
    await player.getByRole('button', { name: 'Nét tiếp theo của chữ 字' }).click()
    assert.equal(await player.getAttribute('data-written-strokes'), '2')
    await capture(page, 'student-writing', width)
    await player.locator('svg.hanzi-writing-square').screenshot({ path: `${folder}/writing-closeup-${width}.png`, animations: 'allow' })
    await player.getByRole('button', { name: 'Nét trước của chữ 字' }).click()
    assert.equal(await player.getAttribute('data-written-strokes'), '1')
    await player.getByLabel('Tốc độ viết chữ 字').selectOption('1.6')
    await player.getByRole('button', { name: 'Viết từng nét chữ 字', exact: true }).click()
    await player.scrollIntoViewIfNeeded()
    try {
      await page.waitForFunction(() => document.querySelector('[data-character="字"]')?.dataset.writtenStrokes === '6')
    } catch (error) {
      console.log(JSON.stringify(await player.evaluate(element => ({ width: innerWidth, visibility: document.visibilityState, position: element.getBoundingClientRect().toJSON(), viewport: innerHeight, stroke: element.dataset.writtenStrokes, button: element.querySelector('.hanzi-stroke-play')?.textContent, players: element.getAnimations({ subtree: true }).map(animation => ({ state: animation.playState, time: animation.currentTime, duration: animation.effect.getTiming().duration })) }))))
      await page.screenshot({ path: folder + '/animation-debug.png' })
      throw error
    }
    await player.getByRole('button', { name: 'Viết lại chữ 字', exact: true }).waitFor()
    await capture(page, 'student-finished', width)
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByRole('button', { name: 'Chữ 好, vị trí 2' }).click()
    const second = page.locator('[data-character="好"]')
    await second.scrollIntoViewIfNeeded()
    await second.getByRole('button', { name: 'Tạm dừng chữ 好', exact: true }).waitFor()
    assert.equal(await second.getAttribute('data-total-strokes'), '6')
    await second.getByRole('button', { name: 'Tạm dừng chữ 好', exact: true }).click()
    await capture(page, 'student-multiple-characters', width)
    assert.deepEqual(state.writes, [], 'Stroke controls must not mark theory as viewed')
    await page.goto(origin + '/pronunciation/lesson')
    await page.getByRole('link', { name: 'Học biến điệu', exact: true }).click()
    assert.equal(new URL(page.url()).pathname, '/pronunciation/lesson/bien-dieu')
    await page.getByText('ní hǎo', { exact: true }).waitFor()
    await capture(page, 'sandhi-third-tone', width)
    for (let i = 0; i < 3; i++) { await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click(); await page.waitForFunction(index => document.querySelector('progress').value === index, i + 1) }
    await page.getByText('yídìng', { exact: true }).waitFor()
    await capture(page, 'sandhi-yi', width)
    for (let i = 3; i < 12; i++) { await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click(); await page.waitForFunction(index => document.querySelector('progress').value === index, i + 1) }
    await page.getByRole('button', { name: 'Hoàn thành biến điệu', exact: true }).click()
    await page.getByRole('heading', { name: 'Che pinyin, thử tự đọc', exact: true }).waitFor()
    await capture(page, 'sandhi-completed', width)
    await context.close()

    const reduced = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    install(reduced)
    const manual = await reduced.newPage(); manual.on('pageerror', error => errors.push(error.message))
    await manual.goto(origin + '/lessons/lesson/vocabulary/v1')
    const reducedPlayer = manual.locator('[data-character="字"]')
    await reducedPlayer.scrollIntoViewIfNeeded()
    await reducedPlayer.getByText('Đã viết 0 / 6 nét', { exact: true }).waitFor()
    assert.equal(await reducedPlayer.getByRole('button', { name: /Tạm dừng/ }).count(), 0)
    await reducedPlayer.getByRole('button', { name: 'Nét tiếp theo của chữ 字' }).click()
    await capture(manual, 'student-reduced-motion', width)
    await reduced.close()

    const adminContext = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    const adminState = install(adminContext, true), admin = await adminContext.newPage()
    admin.on('pageerror', error => errors.push(error.message))
    await admin.goto(origin + '/admin/lessons/lesson')
    await admin.getByRole('button', { name: 'Từ vựng', exact: true }).click()
    if (width < 900) await admin.getByRole('button', { name: /Xem trước/, exact: true }).click()
    const preview = admin.getByRole('complementary', { name: 'Xem trước nội dung bài học' }).filter({ visible: true })
    await preview.locator('[data-character="字"]').scrollIntoViewIfNeeded()
    await preview.getByText('Đã viết 0 / 6 nét', { exact: true }).waitFor()
    await preview.getByRole('button', { name: 'Nét tiếp theo của chữ 字' }).click()
    await capture(admin, 'admin-word-preview', width)
    assert.deepEqual(adminState.writes, [])
    await adminContext.close()
  }
  const fallback = await browser.newContext({ viewport: { width: 390, height: 1000 } })
  const fallbackState = install(fallback)
  await fallback.route('**/hanzi-data/5b57.json', route => route.fulfill({ status: 503, body: '' }))
  const page = await fallback.newPage()
  await page.goto(origin + '/lessons/lesson/vocabulary/v1')
  const player = page.locator('[data-character="字"]'); await player.scrollIntoViewIfNeeded()
  await player.getByText(/Chưa tải được thứ tự nét/).waitFor()
  await capture(page, 'student-data-error', 390)
  await fallback.unroute('**/hanzi-data/5b57.json')
  await player.getByRole('button', { name: 'Thử lại' }).click()
  await page.waitForFunction(() => document.querySelector('[data-character="字"]')?.dataset.totalStrokes === '6')
  assert.deepEqual(fallbackState.writes, [])
  await fallback.close()
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
  await writeFile(folder + '/verification.json', JSON.stringify({ origin, captures, errors, unexpected, scope: 'Isolated API fixtures; real self-hosted stroke JSON. No real user data changed.' }, null, 2))
  console.log(JSON.stringify({ captures: captures.length, errors, unexpected }))
} finally { await browser.close() }
