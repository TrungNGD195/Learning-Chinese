import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

// Intercept every API request. The fixture copies lesson content read-only;
// publication, question edits and unpublication below never reach the live DB.
const fixture = JSON.parse(await readFile(resolve('../tmp/admin-lesson-review-fixture.json'), 'utf8'))
const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5173'
const folder = resolve('../.impeccable/review/lesson-studio')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ headless: true })
const captures = [], errors = [], unexpected = []
const lessonId = fixture.lesson.id

async function install(context) {
  const data = structuredClone(fixture)
  const writes = []
  let failPublish = false
  await context.route('**/api/v1/**', async (route) => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname.split('/api/v1')[1]
    const method = request.method()
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,PATCH,PUT,DELETE,OPTIONS', 'access-control-allow-headers': 'content-type' }
    const reply = (json, status = 200) => route.fulfill({ json, status, headers })
    if (method === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
    if (method !== 'GET') writes.push({ path, method })
    if (path === '/auth/me') return reply({ id: 'review-admin', email: 'admin@example.invalid', role: 'ADMIN', full_name: 'Quản trị' })
    if (path === '/admin/hsk-levels') return reply(data.levels)
    if (path === `/admin/lessons/${lessonId}`) return reply(data.lesson)
    for (const kind of ['vocabulary', 'grammar', 'readings']) if (path === `/admin/lessons/${lessonId}/${kind}`) return reply(data[kind])
    if (path === '/admin/assessments') return reply(data.exercises)
    if (path === `/admin/lessons/${lessonId}/publish-package`) {
      if (failPublish) return reply({ error: { code: 'TEMPORARY', message: 'Fixture failure', details: null } }, 503)
      data.lesson.status = 'PUBLISHED'
      for (const item of data.exercises.items) if (item.status !== 'ARCHIVED') item.status = 'PUBLISHED'
      return reply(data.lesson)
    }
    if (path === `/admin/lessons/${lessonId}/unpublish`) { data.lesson.status = 'DRAFT'; return reply(data.lesson) }
    for (const item of data.exercises.items) {
      if (path === `/admin/assessments/${item.id}`) return reply(item)
      if (path === `/admin/assessments/${item.id}/questions`) return reply(data.questions[item.id])
      for (const question of data.questions[item.id]) if (path === `/admin/assessments/${item.id}/questions/${question.id}` && method === 'PATCH') {
        Object.assign(question, request.postDataJSON()); return reply(question)
      }
    }
    unexpected.push({ path, method }); return reply({ error: { code: 'NOT_FOUND', message: 'Unexpected fixture request', details: null } }, 404)
  })
  return { writes, data, failPublication: value => { failPublish = value } }
}

async function capture(page, name, width) {
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => image.decode().catch(() => {}))) })
  const metrics = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, headings: [...document.querySelectorAll('h1')].filter(node => node.getClientRects().length).length }))
  assert(metrics.scroll <= width + 1, `${name} overflow at ${width}: ${metrics.scroll}`)
  assert.equal(metrics.headings, 1)
  await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: true, animations: 'disabled' })
  captures.push({ name, ...metrics })
}

try {
  for (const width of [1440, 768, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    const state = await install(context), page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    for (let attempt = 0; ; attempt++) {
      try { await page.goto(`${origin}/admin/lessons/${lessonId}`); break } catch (error) {
        if (attempt >= 4) throw error
        await page.waitForTimeout(1000)
      }
    }
    await page.getByRole('heading', { name: /^Từ vựng · 13$/ }).waitFor()
    await capture(page, 'vocabulary', width)
    await page.getByRole('button', { name: 'Luyện tập', exact: true }).click()
    const prompt = page.getByLabel('Nội dung câu hỏi', { exact: true }).filter({ visible: true })
    await prompt.waitFor().catch(async (error) => { await writeFile(`${folder}/debug.txt`, await page.locator('body').innerText()); await page.screenshot({ path: `${folder}/debug.png`, fullPage: true }); throw error })
    await capture(page, 'practice', width)
    const original = await prompt.inputValue()
    await prompt.fill(original + ' · Bản chỉnh sửa')
    await page.getByRole('button', { name: 'Từ vựng', exact: true }).click()
    await page.getByRole('button', { name: 'Duyệt xuất bản', exact: true }).click()
    assert.equal(await page.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ', exact: true }).isDisabled(), true)
    await page.getByText('Lưu các thay đổi ở từng mục trước khi xuất bản.', { exact: true }).waitFor()
    await capture(page, 'review-unsaved', width)
    await page.getByRole('button', { name: 'Luyện tập', exact: true }).click()
    assert.equal(await prompt.inputValue(), original + ' · Bản chỉnh sửa')
    await page.getByRole('button', { name: 'Lưu câu hỏi', exact: true }).click()
    await page.getByText('Chọn một mục để biên soạn và xem trước', { exact: false }).waitFor()
    await page.getByRole('button', { name: 'Duyệt xuất bản', exact: true }).click()
    await capture(page, 'review', width)
    state.failPublication(true)
    await page.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ', exact: true }).click()
    await page.getByRole('alert').filter({ hasText: 'Có sự cố tạm thời' }).waitFor()
    await capture(page, 'review-error', width)
    state.failPublication(false)
    await page.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ', exact: true }).click()
    await page.getByRole('button', { name: 'Đã xuất bản toàn bộ', exact: true }).waitFor()
    await capture(page, 'published', width)
    await page.getByRole('button', { name: 'Hủy xuất bản', exact: true }).click()
    await page.getByRole('dialog', { name: 'Hủy xuất bản bài học?' }).waitFor()
    await capture(page, 'unpublish-confirmation', width)
    await page.getByRole('dialog').getByRole('button', { name: 'Hủy xuất bản', exact: true }).click()
    await page.getByText('Trạng thái: Bản nháp', { exact: true }).waitFor()
    assert.equal(new URL(page.url()).pathname, `/admin/lessons/${lessonId}`)
    assert(state.writes.every(write => /questions\/|publish-package|unpublish/.test(write.path)))
    await context.close()
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(unexpected, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/verification.json`, JSON.stringify({ fixture: 'Read-only copy of Lesson 1; all API traffic intercepted', captures, errors, unexpected }, null, 2))
}
console.log(`Verified ${captures.length} captures; no errors or horizontal overflow.`)
