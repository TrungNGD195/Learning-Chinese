import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = 'http://127.0.0.1:5173'
const original = JSON.parse(await readFile('../tmp/admin-lesson-review-fixture.json', 'utf8'))
const folder = resolve('../.impeccable/review/admin-navigation')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch()
const captures = [], errors = [], unexpected = []

try {
  for (const width of [1440, 390]) {
    const data = structuredClone(original), requests = [], writes = []
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    await context.route('**/api/v1/**', async route => {
      const request = route.request(), url = new URL(request.url()), path = url.pathname.split('/api/v1')[1], method = request.method()
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,PATCH,OPTIONS', 'access-control-allow-headers': 'content-type' }
      const reply = (json, status = 200) => route.fulfill({ json, status, headers })
      if (method === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
      if (path === '/auth/me') return reply({ id: 'admin', role: 'ADMIN', full_name: 'Quản trị', email: 'review@example.invalid' })
      if (path === '/admin/hsk-levels') return reply(data.levels)
      if (path === '/admin/assessments' && method === 'GET') {
        requests.push(url.searchParams.get('assessment_type'))
        const items = url.searchParams.get('assessment_type') === 'PERIODIC_TEST' ? [] : data.exercises.items
        return reply({ items, total: items.length, page: 1, page_size: 100 })
      }
      if (path === '/admin/assessments' && method === 'POST') {
        const body = request.postDataJSON(); writes.push(body)
        const item = { ...data.exercises.items[0], ...body, id: 'inline-created-practice', status: 'DRAFT', published_at: null }
        data.exercises.items.push(item); data.questions[item.id] = []
        return reply(item, 201)
      }
      if (path === '/admin/assessments/generate-draft') {
        const body = request.postDataJSON(); writes.push(body)
        const item = { ...data.exercises.items[0], title: 'Bài luyện do AI tạo', id: 'inline-generated-practice', status: 'DRAFT' }
        data.questions[item.id] = data.questions[data.exercises.items[0].id].map((question, index) => ({ ...question, id: 'generated-question-' + index, assessment_id: item.id }))
        data.exercises.items.push(item)
        return reply({ assessment: item, questions: data.questions[item.id] }, 201)
      }
      if (path === `/admin/lessons/${data.lesson.id}`) return reply(data.lesson)
      for (const kind of ['vocabulary', 'grammar', 'readings']) if (path === `/admin/lessons/${data.lesson.id}/${kind}`) return reply(data[kind])
      for (const item of data.exercises.items) {
        if (path === `/admin/assessments/${item.id}`) return reply(item)
        if (path === `/admin/assessments/${item.id}/questions`) return reply(data.questions[item.id])
      }
      unexpected.push({ path, method }); return reply({ error: { code: 'NOT_FOUND', message: 'Fixture only', details: null } }, 404)
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    async function capture(name) {
      await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => image.decode().catch(() => {}))) })
      const scroll = await page.evaluate(() => document.documentElement.scrollWidth)
      assert(scroll <= width + 1, `${name}: overflow ${scroll}`)
      await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: true, animations: 'disabled' })
      captures.push({ name, width, scroll })
    }
    for (let attempt = 0; ; attempt++) {
      try { await page.goto(origin + '/admin/assessments'); break } catch (error) { if (attempt >= 4) throw error; await page.waitForTimeout(1000) }
    }
    await page.getByRole('heading', { name: 'Kiểm tra định kỳ', exact: true }).waitFor()
    const nav = page.getByRole('navigation', { name: 'Điều hướng quản trị' })
    assert.equal(await nav.getByRole('link', { name: 'Luyện tập', exact: true }).count(), 0)
    assert.equal(await nav.getByRole('link', { name: 'Kiểm tra định kỳ', exact: true }).count(), 1)
    assert(requests.length > 0 && requests.every(type => type === 'PERIODIC_TEST'))
    await capture('periodic-tests')
    await page.getByRole('button', { name: 'Tạo bài kiểm tra', exact: true }).click()
    assert.equal(await page.getByLabel('Loại', { exact: true }).count(), 0)
    await capture('periodic-create')
    await page.goto(`${origin}/admin/lessons/${data.lesson.id}?section=exercises`)
    await page.getByRole('button', { name: 'Thêm bài luyện tập', exact: true }).click()
    const create = page.getByRole('form', { name: 'Thêm bài luyện tập', exact: true })
    await create.getByLabel('Tiêu đề bài luyện tập', { exact: true }).fill('Luyện tập mới trong lesson')
    await capture('lesson-create')
    await create.getByRole('button', { name: 'Tạo bài luyện tập', exact: true }).click()
    await page.getByRole('heading', { name: 'Luyện tập mới trong lesson', exact: true }).waitFor()
    assert.equal(new URL(page.url()).pathname, `/admin/lessons/${data.lesson.id}`)
    assert.equal(writes[0].lesson_id, data.lesson.id)
    assert.equal(writes[0].pass_threshold, 80)
    await capture('lesson-created')
    await page.getByRole('button', { name: 'Tạo bản nháp bằng AI', exact: true }).click()
    const generation = page.locator('.admin-ai-generation-form')
    assert.equal(await generation.getByLabel('Loại bài luyện tập', { exact: true }).count(), 0)
    assert.equal(await generation.getByLabel('Bài học', { exact: true }).count(), 0)
    assert.equal(await generation.getByLabel('Số câu hỏi', { exact: true }).inputValue(), '30')
    await generation.getByRole('combobox', { name: 'Độ khó', exact: true }).selectOption('EASY')
    await capture('lesson-generation')
    await generation.getByRole('button', { name: 'Tạo bản nháp', exact: true }).click()
    await page.getByRole('heading', { name: 'Bài luyện do AI tạo', exact: true }).waitFor()
    assert.equal(writes[1].lesson_id, data.lesson.id)
    assert.equal(writes[1].question_count, 30)
    assert.equal(new URL(page.url()).pathname, `/admin/lessons/${data.lesson.id}`)
    await capture('lesson-generated')
    await context.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/verification.json`, JSON.stringify({ fixture: 'All API requests intercepted; no live content changed', captures, errors, unexpected }, null, 2))
}
console.log(`PASS: ${captures.length} captures; periodic-only library, inline creation and generation verified.`)
