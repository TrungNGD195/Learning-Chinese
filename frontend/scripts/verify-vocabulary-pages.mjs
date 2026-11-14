import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5174'
const folder = resolve(process.env.BO_REVIEW_FOLDER || '../.impeccable/review/vocabulary-pages')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ headless: true })
const captures = [], errors = [], unexpected = []
const time = '2026-11-05T10:00:00Z'
const words = [
  { id: 'greeting', order_index: 1, hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', part_of_speech: 'lời chào', example: '老师，你好！\nLǎoshī, nǐ hǎo!\nEm chào thầy/cô!', note: 'Hai thanh 3 liên tiếp: thanh đầu đọc gần thanh 2. Khi viết pinyin vẫn giữ nǐ hǎo.' },
  { id: 'one', order_index: 2, hanzi: '一', pinyin: 'yī', vietnamese_meaning: 'một', part_of_speech: 'số từ', example: '我有一个朋友。\nWǒ yǒu yí ge péngyou.\nTôi có một người bạn.', note: null },
  { id: 'negative', order_index: 3, hanzi: '不', pinyin: 'bù', vietnamese_meaning: 'không', part_of_speech: 'phó từ', example: '我不喝茶。\nWǒ bù hē chá.\nTôi không uống trà.', note: '不 thường đọc thành bú trước âm tiết thanh 4, ví dụ 不是 bú shì.' },
]
function install(context, admin = false) {
  const state = { seen: new Set(), failed: '', writes: [], grammar: false, reading: false }
  context.route('**/api/v1/**', route => {
    const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
    const reply = (json, status = 200) => route.fulfill({ json, headers, status })
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    if (path === '/auth/logout' && request.method() === 'POST') return route.fulfill({ status: 204, headers })
    if (request.method() !== 'GET') state.writes.push(path)
    if (path === '/auth/me') return reply({ id: 'student', full_name: 'Nguyễn An', email: 'review@example.invalid', role: admin ? 'ADMIN' : 'LEARNER' })
    if (path === '/hsk-levels' || path === '/admin/hsk-levels') return reply([{ id: 'hsk', level_number: 1, title: 'HSK 1', order_index: 1, description: null, state: 'AVAILABLE' }])
    if (path === '/lessons/lesson') return reply({ id: 'lesson', hsk_level_id: 'hsk', lesson_number: 1, title: '你好 · Xin chào', description: null, vocabulary: words.map(word => ({ id: word.id, order_index: word.order_index, example: word.example, note: word.note, item: { id: 'catalog-' + word.id, hanzi: word.hanzi, pinyin: word.pinyin, vietnamese_meaning: word.vietnamese_meaning, part_of_speech: word.part_of_speech } })), grammar: [{ id: 'grammar', order_index: 1, item: { id: 'grammar-item', name: 'Lời chào', explanation: 'Cách dùng lời chào.' }, note: null, example: null }], readings: [{ id: 'reading', order_index: 1, title: 'Chào hỏi', content: 'A：你好！\nB：你好！', pinyin: null, vietnamese_translation: null, source_reference: null, version: 1 }], assessment_ids: ['practice'] })
    if (path === '/me/progress/lessons/lesson') return reply({ lesson_id: 'lesson', started_at: time, theory_completed_at: state.seen.size === words.length && state.grammar && state.reading ? time : null, completed_at: null, vocabulary: words.map(word => ({ id: word.id, viewed: state.seen.has(word.id) })), grammar: [{ id: 'grammar', viewed: state.grammar }], readings: [{ id: 'reading', completed: state.reading, completed_at: state.reading ? time : null }] })
    if (path === '/lessons/lesson/theory/grammar/grammar/view') { state.grammar = true; return reply({ viewed_at: time, theory_completed_at: null }) }
    if (path === '/lessons/lesson/theory/readings/reading/complete') { assert.equal(request.postDataJSON().version, 1); state.reading = true; return reply({ completed_at: time, theory_completed_at: state.seen.size === words.length && state.grammar ? time : null }) }
    const visit = path.match(/^\/lessons\/lesson\/theory\/vocabulary\/([^/]+)\/view$/)
    if (visit) {
      if (visit[1] === state.failed) return reply({ error: { code: 'FIXTURE_FAILURE', message: 'Isolated error', details: null } }, 503)
      state.seen.add(visit[1]); return reply({ viewed_at: time, theory_completed_at: null })
    }
    if (path === '/admin/lessons/lesson') return reply({ id: 'lesson', hsk_level_id: 'hsk', lesson_number: 1, title: '你好 · Xin chào', description: null, status: 'DRAFT', published_at: null })
    if (path === '/admin/lessons/lesson/vocabulary') return reply(words)
    if (path === '/admin/lessons/lesson/grammar' || path === '/admin/lessons/lesson/readings') return reply([])
    if (path === '/admin/assessments') return reply({ items: [], total: 0, page: 1, page_size: 20 })
    unexpected.push({ path, method: request.method() }); return reply({}, 404)
  })
  return state
}
async function capture(page, name, width) {
  assert.equal(await page.locator('.hanzi-stroke-attribution, .vocabulary-study-card__attribution').count(), 0)
  assert.equal(await page.locator('.lesson-chat-entry, .chat-panel').count(), 0)
  for (const item of await page.locator('.academy-word-illustration').evaluateAll(nodes => nodes.map(node => ({ src: getComputedStyle(node).backgroundImage, kind: node.dataset.illustration })))) {
    assert(item.src.includes('/academy/panda-'), `${name}: legacy illustration remains`)
    assert(['panda', 'object'].includes(item.kind), `${name}: missing illustration kind`)
  }
  await page.evaluate(async () => {
    await document.fonts.ready
    const sources = new Set([...document.querySelectorAll('*')].flatMap(element => [...getComputedStyle(element).backgroundImage.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(match => match[1])))
    await Promise.all([...sources].map(async src => { const image = new Image(); image.src = src; await image.decode() }))
  })
  const metrics = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, viewport: innerWidth }))
  assert(metrics.scroll <= metrics.viewport + 1, `${name} overflow at ${width}`)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: true, animations: 'allow' })
  captures.push({ name, width, ...metrics })
}
try {
  for (const width of (process.env.BO_REVIEW_WIDTHS || '1440,1024,768,390,320').split(',').map(Number)) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    await context.addInitScript(() => {
      window.__vocabularySpeech = []
      window.__vocabularyUtterance = null
      window.SpeechSynthesisUtterance = class { constructor(text) { this.text = text } }
      Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
        getVoices: () => [{ lang: 'zh-CN', localService: true }],
        addEventListener() {}, removeEventListener() {},
        cancel() { window.__vocabularyUtterance?.onerror?.({ error: 'canceled' }); window.__vocabularyUtterance = null },
        speak(utterance) { window.__vocabularyUtterance = utterance; window.__vocabularySpeech.push({ text: utterance.text, lang: utterance.lang, rate: utterance.rate }) },
      } })
    })
    const state = install(context), page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(origin + '/lessons/lesson')
    await page.getByRole('heading', { name: '你好', exact: true }).waitFor()
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).waitFor({ state: 'visible' })
    await page.waitForFunction(() => ![...document.querySelectorAll('.vocabulary-page__navigation button')].at(-1).disabled)
    assert.equal(new URL(page.url()).pathname, '/lessons/lesson')
    assert.equal(await page.locator('.vocabulary-index').count(), 0)
    assert.equal(await page.locator('.lesson-sections-horizontal a[aria-current="page"]').getAttribute('href'), '/lessons/lesson/vocabulary')
    assert.equal(await page.locator('.lesson-word-index a').count(), words.length)
    assert.equal(await page.locator('.lesson-word-index a[aria-current="page"]').getAttribute('href'), '/lessons/lesson/vocabulary/greeting')
    assert.equal(await page.locator('#grammar, #readings, #exercise').count(), 0)
    assert.equal(await page.locator('.vocabulary-study-card').count(), 1)
    assert.equal(await page.getByRole('button', { name: 'Xem chi tiết', exact: true }).count(), 0)
    assert.equal(await page.getByRole('button', { name: 'Quay lại', exact: true }).isDisabled(), true)
    assert(await page.getByRole('heading', { name: 'Ví dụ', exact: true }).isVisible())
    assert(await page.getByRole('heading', { name: 'Lưu ý khi dùng', exact: true }).isVisible())
    assert.equal(state.seen.size, 1)
    assert.deepEqual(await page.evaluate(() => window.__vocabularySpeech), [])
    await page.getByRole('button', { name: 'Nghe phát âm 你好', exact: true }).click()
    assert.deepEqual(await page.evaluate(() => window.__vocabularySpeech), [{ text: '你好', lang: 'zh-CN', rate: 0.8 }])
    await page.evaluate(() => window.__vocabularyUtterance.onend({}))
    const artWidth = await page.locator('.vocabulary-study-card__summary .academy-word-illustration').evaluate(element => element.getBoundingClientRect().width)
    assert(artWidth >= 128)
    await capture(page, 'first-word-always-visible-theory', width)
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByRole('heading', { name: '一', exact: true }).waitFor()
    assert.equal(await page.evaluate(() => window.__vocabularySpeech.length), 1)
    await page.getByRole('button', { name: 'Nghe phát âm 一', exact: true }).click()
    assert.equal(await page.evaluate(() => window.__vocabularySpeech.at(-1).text), '一')
    await page.waitForFunction(() => ![...document.querySelectorAll('.vocabulary-page__navigation button')].at(-1).disabled)
    assert.equal(await page.getByRole('heading', { name: 'Lưu ý khi dùng', exact: true }).count(), 0)
    await capture(page, 'second-word-no-note', width)
    await page.goBack(); await page.getByRole('heading', { name: '你好', exact: true }).waitFor()
    assert.equal(state.writes.filter(path => path.includes('/greeting/view')).length, 1)
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByRole('heading', { name: '一', exact: true }).waitFor()
    await page.reload(); await page.getByRole('heading', { name: '一', exact: true }).waitFor()
    assert.equal(state.writes.filter(path => path.includes('/one/view')).length, 1)
    state.failed = 'negative'
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByRole('alert').waitFor()
    assert(await page.getByRole('button', { name: 'Tiếp theo', exact: true }).isDisabled())
    assert.equal(state.seen.size, 2)
    await capture(page, 'save-error-with-readable-theory', width)
    state.failed = ''
    await page.getByRole('button', { name: 'Thử lưu lại', exact: true }).click()
    await page.waitForFunction(() => ![...document.querySelectorAll('.vocabulary-page__navigation button')].at(-1).disabled)
    assert.equal(state.seen.size, 3)
    await capture(page, 'last-word-saved', width)
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByRole('heading', { name: 'Ngữ pháp', exact: true }).waitFor()
    assert.equal(new URL(page.url()).pathname, '/lessons/lesson/grammar')
    assert.equal(await page.locator('.vocabulary-study-card, #readings, #exercise').count(), 0)
    await page.getByRole('button', { name: 'Xem chi tiết', exact: true }).click()
    await page.getByText('Đã xem', { exact: true }).waitFor()
    await capture(page, 'grammar-separate-page', width)
    await page.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    assert(await page.getByRole('button', { name: 'Mở luyện tập 1', exact: true }).isDisabled())
    await capture(page, 'vocabulary-complete-other-theory-required', width)
    await page.getByRole('link', { name: 'Bài khóa', exact: true }).click()
    await page.getByRole('heading', { name: 'Chào hỏi', exact: true }).waitFor()
    assert.equal(await page.locator('.vocabulary-study-card, #grammar, #exercise').count(), 0)
    assert.equal(state.reading, false)
    await page.reload()
    await capture(page, 'reading-separate-page', width)
    assert.equal(state.reading, false)
    await page.getByRole('button', { name: 'Hoàn thành bài khóa: Chào hỏi', exact: true }).click()
    await page.getByRole('button', { name: 'Đã hoàn thành bài khóa: Chào hỏi', exact: true }).waitFor()
    await page.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    await page.getByRole('link', { name: 'Mở luyện tập 1', exact: true }).waitFor()
    assert.equal(await page.locator('.vocabulary-study-card, #grammar, #readings').count(), 0)
    await capture(page, 'practice-open-after-all-theory', width)
    const before = state.writes.length
    await page.goto(origin + '/lessons/lesson/vocabulary/not-in-lesson')
    await page.getByRole('alert').waitFor()
    assert.equal(state.writes.length, before)
    await capture(page, 'invalid-word-route', width)
    await context.close()

    const adminContext = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    const adminState = install(adminContext, true), admin = await adminContext.newPage()
    admin.on('pageerror', error => errors.push(error.message))
    await admin.goto(origin + '/admin/lessons/lesson')
    await admin.getByRole('button', { name: 'Từ vựng', exact: true }).click()
    if (width < 900) await admin.getByRole('button', { name: 'Xem trước', exact: true }).click()
    await admin.getByRole('complementary', { name: 'Xem trước nội dung bài học' }).filter({ visible: true }).locator('.vocabulary-study-card').waitFor()
    await capture(admin, 'admin-matching-preview', width)
    assert.deepEqual(adminState.writes, [])
    await adminContext.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
  await writeFile(folder + '/verification.json', JSON.stringify({ origin, captures, errors, unexpected, scope: 'Isolated API fixtures and real stroke assets; no real student progress or content changes.' }, null, 2))
  console.log(JSON.stringify({ captures: captures.length, errors, unexpected }))
} finally { await browser.close() }
