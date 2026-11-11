import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5174'
const folder = resolve('../.impeccable/review/study-content-focus/dashboard')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ headless: true })
const captures = [], errors = [], unexpected = []
const dashboard = { current_hsk: { id: 'hsk', level_number: 1, title: 'HSK 1' }, current_lesson: { id: 'lesson', lesson_number: 1, title: '你好 · Xin chào', description: 'Làm quen với lời chào bằng tiếng Trung.' }, current_unit: { id: 'unit', order_index: 1, unit_type: 'LESSON', state: 'AVAILABLE', lesson: { id: 'lesson', lesson_number: 1, title: '你好 · Xin chào', status: 'PUBLISHED' }, assessment: null }, progress_percentage: 25, continue_learning: { type: 'LESSON', lesson_id: 'lesson', assessment_id: null } }
try {
  for (const width of (process.env.BO_REVIEW_WIDTHS || '1440,1024,768,390').split(',').map(Number)) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    // An earlier small-size / hidden-pinyin preference must no longer affect reading.
    await context.addInitScript(() => localStorage.setItem('chinese-learning.reading.v1', JSON.stringify({ size: 19, pinyin: false })))
    let pronunciation = false
    await context.route('**/api/v1/**', route => {
      const path = new URL(route.request().url()).pathname.split('/api/v1')[1]
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'content-type' }
      const reply = json => route.fulfill({ json, headers })
      if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
      assert.equal(route.request().method(), 'GET', 'Visual checks must not write learner progress')
      if (path === '/auth/me') return reply({ id: 'student', full_name: 'Nguyễn An', email: 'review@example.invalid', role: 'LEARNER' })
      if (path === '/me/dashboard') return reply(pronunciation ? { ...dashboard, current_hsk: null, current_lesson: null, current_unit: null, progress_percentage: 0, continue_learning: { type: 'PRONUNCIATION', section_id: 'initials', code: 'INITIALS' } } : dashboard)
      if (path === '/hsk-levels') return reply([{ id: 'hsk', level_number: 1, title: 'HSK 1', description: null, state: 'AVAILABLE' }])
      if (path === '/lessons/lesson') return reply({ id: 'lesson', hsk_level_id: 'hsk', lesson_number: 1, title: '你好 · Xin chào', description: 'Lời chào đầu tiên.', vocabulary: [{ id: 'word', order_index: 1, example: '老师，你好！Lǎoshī, nǐ hǎo! Em chào thầy/cô!', note: null, item: { id: 'vocabulary', hanzi: '你好', pinyin: 'nǐ hǎo', vietnamese_meaning: 'xin chào', part_of_speech: 'lời chào' } }], grammar: [], readings: [], assessment_ids: [] })
      if (path === '/me/progress/lessons/lesson') return reply({ lesson_id: 'lesson', started_at: null, theory_completed_at: null, completed_at: null, vocabulary: [{ id: 'word', viewed: true }], grammar: [], readings: [] })
      unexpected.push(path); return route.fulfill({ status: 404, headers, json: {} })
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    const capture = async name => {
      await page.evaluate(async () => {
        await document.fonts.ready
        const sources = new Set([...document.querySelectorAll('*')].flatMap(element => [...getComputedStyle(element).backgroundImage.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(match => match[1])))
        await Promise.all([...sources].map(async src => { const image = new Image(); image.src = src; await image.decode() }))
      })
      const metrics = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth, reading: getComputedStyle(document.querySelector('.bo-shell')).getPropertyValue('--reader-font-size').trim() }))
      assert(metrics.scroll <= metrics.viewport + 1, `${name} overflow at ${width}`)
      assert.equal(metrics.reading, '21px')
      assert.equal(await page.locator('.academy-topbar, .academy-reading-settings').count(), 0)
      assert.equal(await page.getByText('Không gian nhỏ, hành trình lớn.', { exact: true }).count(), 0)
      await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: true, animations: 'disabled' })
      captures.push({ name, width, ...metrics })
    }
    await page.goto(origin + '/dashboard')
    await page.getByRole('region', { name: 'Tiếp tục học' }).waitFor()
    assert.equal(await page.locator('.academy-greeting').count(), 0)
    await capture('returning-learner')
    const top = await page.locator('.academy-home-grid').evaluate(element => element.getBoundingClientRect().top)
    assert(top < 240, 'Resume content should move to the first viewport')
    const toolbar = page.locator('.academy-mobile-toolbar')
    assert.equal(await toolbar.isVisible(), width <= 800)
    if (width <= 800) {
      await page.getByRole('button', { name: 'Mở menu học viên' }).click()
      const close = page.getByRole('button', { name: 'Đóng menu', exact: true })
      assert(await close.evaluate(element => element === document.activeElement))
      await page.keyboard.press('Escape')
      assert(await page.getByRole('button', { name: 'Mở menu học viên' }).evaluate(element => element === document.activeElement))
    }
    pronunciation = true
    await page.reload(); await page.getByRole('heading', { name: 'Nền tảng trước HSK 1' }).waitFor()
    await capture('new-learner')
    await page.goto(origin + '/lessons/lesson/vocabulary/word')
    await page.locator('.vocabulary-study-card__pinyin').waitFor()
    assert(await page.locator('.vocabulary-study-card__pinyin').isVisible())
    await capture('lesson-fixed-large-type')
    await context.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
  await writeFile(folder + '/verification.json', JSON.stringify({ origin, captures, errors, unexpected, scope: 'Isolated read-only API fixtures, including obsolete reading preferences.' }, null, 2))
  console.log(JSON.stringify({ captures: captures.length, errors, unexpected }))
} finally { await browser.close() }
