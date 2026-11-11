import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5174'
const folder = resolve('../.impeccable/review/student-vietnamese')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ headless: true })
const captures = [], errors = [], unexpected = []
const time = '2026-11-04T10:00:00Z'
const questions = [
  { id: 'choice', type: 'multiple_choice', prompt: 'Chọn lời chào phù hợp.', config: {}, options: [{ id: 'hello', option_text: '你好' }] },
  { id: 'fill', type: 'fill_blank', prompt: 'Điền từ còn thiếu: 你__。', config: {} },
  { id: 'match', type: 'matching', prompt: 'Ghép chữ Hán với nghĩa.', config: { left_items: [{ id: 'left', text: '你好' }], right_items: [{ id: 'right', text: 'xin chào' }] } },
  { id: 'order', type: 'reorder_sentence', prompt: 'Sắp xếp thành câu.', config: { items: [{ id: 'you', text: '你' }, { id: 'good', text: '好' }] } },
  { id: 'vi-zh', type: 'translate_vi_zh', prompt: 'Dịch sang tiếng Trung: Xin chào.', config: {} },
  { id: 'zh-vi', type: 'translate_zh_vi', prompt: 'Dịch sang tiếng Việt: 你好。', config: {} },
  { id: 'write', type: 'sentence_writing', prompt: 'Viết một câu chào bằng tiếng Trung.', config: {} },
].map((question, index) => ({ ...question, points: 1, order_index: index + 1 }))
const lesson = { id: 'lesson', hsk_level_id: 'hsk', lesson_number: 1, title: '你好 · Xin chào', description: 'Những lời chào đầu tiên.', vocabulary: [{ id: 'vocabulary', order_index: 1, example: '你好！', note: 'Hai thanh 3 liên tiếp: thanh đầu đọc gần thanh 2.', item: { id: 'word', hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', part_of_speech: 'phrase' } }], grammar: [], assessment_ids: ['practice'] }
const conversation = { id: 'conversation', scope: 'LESSON', lesson_id: 'lesson', title: null, created_at: time, updated_at: time }
const message = (id, sequence, status, content) => ({ id, sequence_number: sequence, role: 'ASSISTANT', conversation_id: 'conversation', reply_to_message_id: null, status, content, created_at: time, citations: [] })
const messages = [
  { ...message('answer', 1, 'COMPLETED', '你好 có nghĩa là **xin chào**.'), citations: [{ label: 'S1', source_kind: 'EXTERNAL_URL', title: 'Tài liệu tham khảo', url: 'https://example.invalid/reference', domain: 'example.invalid', source_type: null, section: null, page_number: null }] },
  message('pending', 2, 'PENDING', null), message('failed', 3, 'FAILED', null),
]

function install(context) {
  const state = { authenticated: true, result: 'GRADED', writes: [] }
  context.route('**/api/v1/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
    const reply = (json, status = 200) => route.fulfill({ json, status, headers })
    const failure = { error: { code: 'FIXTURE_FAILURE', message: 'Isolated fixture only', details: null } }
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    if (path === '/auth/logout' && request.method() === 'POST') return route.fulfill({ status: 204, headers })
    if (!['GET', 'HEAD'].includes(request.method())) state.writes.push(path)
    if (path === '/auth/me') return state.authenticated ? reply({ id: 'student', full_name: 'Nguyễn Minh Anh', email: 'student@example.invalid', role: 'LEARNER' }) : reply(failure, 401)
    if (path === '/auth/refresh') return reply(failure, 401)
    if (path === '/auth/password/forgot') return reply({ message: 'Acknowledged' })
    if (path === '/hsk-levels') return reply([{ id: 'hsk', level_number: 1, title: 'HSK 1', state: 'AVAILABLE', description: null }])
    if (path === '/me/progress') return reply({ current_hsk: 1, progress_percentage: 25, pronunciation_complete: true, hsk_levels: [] })
    if (path === '/me/dashboard') return reply({ current_hsk: null, current_unit: null, current_lesson: null, progress_percentage: 25, continue_learning: null })
    if (path === '/lessons/lesson') return reply(lesson)
    if (path === '/me/progress/lessons/lesson') return reply({ lesson_id: 'lesson', started_at: time, theory_completed_at: time, completed_at: null, vocabulary: [{ id: 'vocabulary', viewed: true }], grammar: [] })
    if (path === '/assessments/practice') return reply({ id: 'practice', type: 'LESSON_EXERCISE', title: 'Luyện tập lời chào', description: null, pass_threshold: 80, questions })
    if (path === '/assessments/practice/attempts') return reply({ id: 'attempt', assessment_id: 'practice', attempt_number: 1, status: 'IN_PROGRESS', score: null, passed: null, submitted_at: null, answers: [] })
    if (path === '/me/assessment-attempts/attempt') return reply({ id: 'attempt', assessment_id: 'practice', attempt_number: 1, status: state.result, score: state.result === 'GRADED' ? 80 : null, passed: state.result === 'GRADED' ? true : null, submitted_at: time, answers: [{ question_id: 'fill', type: 'fill_blank', prompt: 'Điền từ còn thiếu.', answer: { text: '好' }, grading_status: 'GRADED', is_correct: true, score: 1, feedback: 'Bạn đã trả lời đúng.', reference_answer: null, rubric: null }] })
    if (path === '/me/conversations') return reply({ items: [conversation], total: 1, page: 1, page_size: 20 })
    if (path === '/conversations/conversation/messages') return reply({ items: messages, total: messages.length, page: 1, page_size: 50 })
    if (path === '/conversations/conversation') return reply(conversation)
    unexpected.push({ path, method: request.method() })
    return reply(failure, 404)
  })
  return state
}

async function capture(page, name, width) {
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(img => img.decode())) })
  const metrics = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth }))
  assert(metrics.width <= width + 1, `${name} overflow`)
  const copy = await page.locator('body').innerText()
  assert(!/\b(?:Show details|Open Exercise|Lesson Exercise|Choose a match|Use this order|GRADING_FAILED|GRADED|AVAILABLE|LOCKED|AI is thinking|Passwords do not match|opens in a new tab)\b/.test(copy), `${name} contains untranslated interface text`)
  if (name === 'chat-states') {
    assert(await page.locator('.chat-composer button').evaluate(element => {
      const rect = element.getBoundingClientRect()
      return element.contains(document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2))
    }), 'Chat send control must remain above the mobile navigation')
  }
  captures.push({ name, ...metrics })
  await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: !name.startsWith('chat-'), animations: 'disabled' })
}

try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    const state = install(context), page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(origin + '/lessons/lesson')
    await page.getByText('Loại từ: cụm từ', { exact: true }).waitFor()
    await capture(page, 'lesson-details', width)
    assert.equal(await page.locator('.lesson-chat-entry, .chat-panel').count(), 0)
    await page.goto(origin + '/assessments/practice')
    await page.getByRole('button', { name: 'Bắt đầu / Tiếp tục luyện tập', exact: true }).click()
    for (let index = 0; index < questions.length; index++) {
      await page.getByRole('progressbar', { name: `Câu hỏi ${index + 1} / 7`, exact: true }).waitFor()
      await capture(page, 'question-' + questions[index].type, width)
      if (index < questions.length - 1) await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    }
    for (const status of ['GRADED', 'GRADING_FAILED', 'IN_PROGRESS']) {
      state.result = status
      await page.goto(origin + '/assessment-attempts/attempt/result')
      await page.locator('.assessment-result-summary').waitFor()
      await capture(page, 'result-' + status.toLowerCase(), width)
    }
    await page.goto(origin + '/profile')
    await page.getByRole('button', { name: 'Đổi mật khẩu', exact: true }).click()
    await page.getByText('Vui lòng điền đầy đủ các trường mật khẩu.', { exact: true }).waitFor()
    await capture(page, 'profile-validation', width)
    assert.deepEqual(state.writes, ['/assessments/practice/attempts'])
    await context.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
  await writeFile(folder + '/verification.json', JSON.stringify({ origin, captures, errors, unexpected, scope: 'Isolated API fixtures only; no real learner data or credentials used.' }, null, 2))
  console.log(JSON.stringify({ captures: captures.length, errors, unexpected }))
} finally { await browser.close() }
