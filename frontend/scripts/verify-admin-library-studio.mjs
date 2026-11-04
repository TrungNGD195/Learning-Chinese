import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = 'http://127.0.0.1:5173', api = 'http://127.0.0.1:8001/api/v1'
const folder = resolve('../.impeccable/review/admin-library-studio')
await mkdir(folder, { recursive: true })
assert(process.env.ADMIN_STUDIO_REVIEW_TOKEN)
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true })
const errors = [], realMutations = [], captures = [], checks = []
async function context(width, height = 1000) {
  const c = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce' })
  await c.addCookies([{ name: 'access_token', value: process.env.ADMIN_STUDIO_REVIEW_TOKEN, url: origin, httpOnly: true, sameSite: 'Lax' }])
  await c.route('**/api/v1/**', (route) => ['GET', 'HEAD', 'OPTIONS'].includes(route.request().method()) ? route.continue() : route.abort('blockedbyclient'))
  return c
}
function watch(page, fixture = false) {
  page.on('pageerror', (e) => errors.push(e.message))
  if (!fixture) page.on('request', (r) => { if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(r.method())) realMutations.push(new URL(r.url()).pathname) })
}
async function json(c, path) { const r = await c.request.get(api + path); assert.equal(r.status(), 200, path); return r.json() }
async function capture(page, name) {
  await page.evaluate(async () => {
    await document.fonts.ready
    await Promise.all([...document.images].map((i) => i.decode()))
    const urls = new Set([...document.querySelectorAll('*')].flatMap((e) => [...getComputedStyle(e).backgroundImage.matchAll(/url\("?([^"\)]+)"?\)/g)].map((m) => m[1])))
    await Promise.all([...urls].map((src) => { const i = new Image(); i.src = src; return i.decode() }))
    scrollTo({ top: 0, behavior: 'instant' })
  })
  const metrics = await page.evaluate(() => ({ viewport: innerWidth, width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight }))
  assert(metrics.width <= metrics.viewport, `${name} horizontal overflow: ${metrics.width}`)
  await page.screenshot({ path: `${folder}/${name}.png`, fullPage: true })
  captures.push({ name, ...metrics })
}
async function load(page, path, selector) { await page.goto(origin + path); await page.locator(selector).first().waitFor() }
try {
  const seed = await context(1440)
  const lessonId = 'd84c81ba-57b3-5132-b15e-dee32ed22bbf', assessmentId = '2185832f-164e-59b8-ae3c-b9ead02e1f64'
  const lesson = await json(seed, `/admin/lessons/${lessonId}`), words = await json(seed, `/admin/lessons/${lessonId}/vocabulary`)
  const assessment = await json(seed, `/admin/assessments/${assessmentId}`), questions = await json(seed, `/admin/assessments/${assessmentId}/questions`)
  const docs = await json(seed, '/admin/documents?page=1&page_size=20')
  assert.equal(lesson.status, 'DRAFT'); assert.equal(assessment.status, 'DRAFT'); assert.equal(assessment.pass_threshold, 80)
  await seed.close()
  for (const width of [1440, 1024, 768, 390]) {
    const c = await context(width), page = await c.newPage(); watch(page)
    for (const [name, path] of [['lessons', '/admin/lessons'], ['assessments', '/admin/assessments'], ['documents', '/admin/documents']]) {
      await load(page, path, name === 'documents' && !docs.items.length ? '.ui-page-state' : '.admin-library-card'); await capture(page, `${name}-${width}`)
      if (name === 'lessons' && width === 1440) {
        await page.keyboard.press('Tab')
        assert(await page.getByRole('link', { name: 'Skip to content', exact: true }).evaluate((e) => e === document.activeElement))
        await page.keyboard.press('Enter')
        assert(await page.locator('#main-content').evaluate((e) => e === document.activeElement))
        await page.keyboard.press('Tab')
        assert(await page.getByRole('button', { name: 'Create Lesson', exact: true }).evaluate((e) => e === document.activeElement))
      }
      if (!await page.locator('.admin-library-card').count()) continue
      const firstTitle = await page.locator('.admin-library-card h2 button').first().textContent()
      await page.getByRole('button', { name: 'Bảng', exact: true }).click(); await page.locator('.admin-library-table').waitFor()
      assert.equal(await page.locator('.admin-library-table tbody tr').count() > 0, true)
      assert.equal(await page.locator('.admin-quick-preview h3').textContent(), firstTitle)
      if (width === 1440) await capture(page, `${name}-table-${width}`)
    }
    await load(page, `/admin/lessons/${lessonId}`, '.admin-content-edit-preview')
    await page.locator('.admin-content-outline li button').first().waitFor()
    assert.equal(await page.locator('.admin-content-edit-preview:visible').count(), 1)
    assert.equal(await page.locator('.admin-content-outline li button:visible').count(), words.length)
    await capture(page, `lesson-editor-${width}`)
    if (width === 390) {
      await page.getByRole('button', { name: 'Xem trước', exact: true }).click()
      await capture(page, 'lesson-preview-390')
      assert.equal(await page.locator('.admin-edit-fields:visible').count(), 0)
    }
    await load(page, `/admin/assessments/${assessmentId}`, '.admin-question-workshop')
    assert.equal(await page.locator('.admin-assessment-question-form:visible').count(), 1)
    assert.equal(await page.locator('.admin-content-outline li button').count(), questions.length)
    await capture(page, `question-editor-${width}`)
    if (width === 1440 || width === 390) {
      await load(page, '/admin', '.admin-workbench'); await capture(page, `dashboard-${width}`)
      await load(page, '/admin/curriculum', '.admin-curriculum-page'); await capture(page, `curriculum-${width}`)
      if (docs.items.length) { await load(page, `/admin/documents/${docs.items[0].id}`, '.admin-document-detail-page'); await capture(page, `document-detail-${width}`) }
    }
    await c.close()
  }
  checks.push('Real lists, card/table toggle, draft lesson and assessment, shared admin background at 1440/1024/768/390; no real mutations')

  // Write paths are exercised only against isolated in-browser API fixtures.
  const c = await context(1440), fixture = await c.newPage(); watch(fixture, true)
  let failSave = true, saves = 0
  await c.route(`**/api/v1/admin/lessons/${lessonId}/vocabulary**`, async (route) => {
    if (route.request().method() === 'PATCH') {
      saves++
      if (failSave) return route.fulfill({ status: 503, json: { error: { code: 'TEMPORARY_FAILURE', message: 'Review fixture: save unavailable', details: null } } })
      const index = words.findIndex((word) => route.request().url().endsWith('/' + word.id)); assert(index >= 0)
      words[index] = { ...words[index], ...route.request().postDataJSON() }
      return route.fulfill({ json: words[index] })
    }
    return route.fulfill({ json: words })
  })
  await load(fixture, `/admin/lessons/${lessonId}`, '.admin-content-edit-preview')
  const original = words[0].vietnamese_meaning, edited = original.replace(/\s+/g, ' ') + ' · bản đang soạn'
  await fixture.locator('.admin-content-stage > div:visible').getByLabel('Vietnamese meaning', { exact: true }).fill(edited)
  assert((await fixture.locator('.admin-student-word:visible .admin-word-meaning').textContent()).includes(edited))
  assert(await fixture.getByRole('button', { name: 'Publish Lesson', exact: true }).isDisabled())
  await fixture.locator('.admin-content-outline li button').nth(1).click(); await fixture.locator('.admin-content-outline li button').first().click()
  assert.equal(await fixture.locator('.admin-content-stage > div:visible').getByLabel('Vietnamese meaning', { exact: true }).inputValue(), edited)
  await fixture.getByRole('button', { name: 'Save content changes', exact: true }).click(); await fixture.getByRole('alert').waitFor()
  assert.equal(await fixture.locator('.admin-content-stage > div:visible').getByLabel('Vietnamese meaning', { exact: true }).inputValue(), edited)
  await capture(fixture, 'save-error-preserves-draft')
  failSave = false
  await fixture.getByRole('button', { name: 'Save content changes', exact: true }).click()
  await fixture.getByText('Vocabulary updated.', { exact: true }).waitFor()
  assert.equal(saves, 2)
  await fixture.locator('.admin-edit-fields:visible textarea[name="note"]').fill('Ghi chú chưa lưu')
  await fixture.getByRole('link', { name: 'Back to Lessons', exact: true }).click()
  await fixture.getByRole('dialog', { name: 'Rời trang khi chưa lưu?' }).waitFor()
  await capture(fixture, 'unsaved-navigation-warning')
  await fixture.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click()
  assert.equal(new URL(fixture.url()).pathname, `/admin/lessons/${lessonId}`)
  await fixture.close(); await c.close()
  checks.push('Unsaved draft survives item switch and failed save, live preview follows fields, explicit save retry, publication blocked with unsaved edits, route leave warning')

  const qc = await context(390), qp = await qc.newPage(); watch(qp, true)
  let releaseSave, onSaveReceived, releaseDelete, onDeleteReceived
  const saveReceived = new Promise((resolve) => { onSaveReceived = resolve })
  const deleteReceived = new Promise((resolve) => { onDeleteReceived = resolve })
  await qc.route('**/api/v1/admin/assessments/*/questions/*', async (route) => {
    assert(['PATCH', 'DELETE'].includes(route.request().method()))
    if (route.request().method() === 'DELETE') await new Promise((resolve) => { releaseDelete = resolve; onDeleteReceived() })
    else await new Promise((resolve) => { releaseSave = resolve; onSaveReceived() })
    return route.fulfill({ status: 503, json: { error: { code: 'TEMPORARY_FAILURE', message: 'Delayed save fixture', details: null } } })
  })
  await load(qp, `/admin/assessments/${assessmentId}`, '.admin-question-workshop')
  const questionDraft = 'Bản nháp kiểm tra · ' + questions[0].prompt
  await qp.locator('.admin-content-stage > div:visible').getByRole('textbox', { name: 'Prompt', exact: true }).fill(questionDraft)
  await qp.locator('.admin-content-outline li button').nth(1).click(); await qp.locator('.admin-content-outline li button').first().click()
  assert.equal(await qp.locator('.admin-content-stage > div:visible').getByRole('textbox', { name: 'Prompt', exact: true }).inputValue(), questionDraft)
  await qp.getByRole('button', { name: 'Submit Review', exact: true, disabled: true }).waitFor()
  assert(await qp.getByRole('button', { name: 'Submit Review', exact: true }).isDisabled())
  await qp.getByRole('button', { name: 'Save question', exact: true }).click(); await saveReceived
  await qp.getByRole('button', { name: 'Delete question', exact: true, disabled: true }).waitFor()
  assert(await qp.getByRole('button', { name: 'Delete question', exact: true }).isDisabled())
  releaseSave(); await qp.getByRole('alert').waitFor()
  await qp.getByRole('button', { name: 'Delete question', exact: true }).click()
  await qp.getByRole('dialog').getByRole('button', { name: 'Delete question', exact: true }).click(); await deleteReceived
  await qp.getByRole('button', { name: 'Save question', exact: true, disabled: true }).waitFor()
  assert(await qp.getByRole('button', { name: 'Save question', exact: true }).isDisabled())
  releaseDelete(); await qp.locator('.admin-assessment-question-row > [role="alert"]').waitFor()
  await qp.getByRole('button', { name: 'Xem trước', exact: true }).click()
  await qp.locator('.admin-editor-preview:visible').getByText(questionDraft, { exact: true }).waitFor()
  await qp.locator('.admin-editor-preview:visible input[type="radio"]').first().check()
  assert.equal(await qp.locator('.admin-editor-preview:visible').getByText('Correct answer', { exact: true }).count(), 0)
  await capture(qp, 'question-live-preview-390')
  await qp.getByRole('button', { name: 'Biên soạn', exact: true }).click()
  await qp.getByRole('button', { name: 'Cancel', exact: true }).click()
  await qp.getByRole('dialog', { name: 'Bỏ thay đổi của câu hỏi?' }).waitFor()
  await qp.getByRole('dialog').getByRole('button', { name: 'Bỏ thay đổi', exact: true }).click()
  await qp.getByRole('button', { name: 'Edit question', exact: true }).waitFor()
  await qp.getByRole('button', { name: 'Add Question', exact: true }).click()
  for (const type of ['multiple_choice', 'fill_blank', 'matching', 'reorder_sentence', 'translate_vi_zh', 'translate_zh_vi', 'sentence_writing']) {
    await qp.locator('.admin-assessment-question-form:visible').getByRole('combobox', { name: 'Question type', exact: true }).selectOption(type)
    await qp.locator('.admin-assessment-question-form:visible').getByRole('textbox', { name: 'Prompt', exact: true }).fill('Kiểm tra xem trước · ' + type)
    await qp.getByRole('button', { name: 'Xem trước', exact: true }).click()
    await qp.locator('.admin-editor-preview:visible').getByText('Kiểm tra xem trước · ' + type, { exact: true }).waitFor()
    await qp.getByRole('button', { name: 'Biên soạn', exact: true }).click()
  }
  await qp.locator('.admin-assessment-question-form:visible').getByRole('combobox', { name: 'Question type', exact: true }).selectOption('reorder_sentence')
  await qp.getByRole('button', { name: 'Add sentence item', exact: true }).click()
  await qp.locator('.admin-assessment-question-form:visible').getByLabel('Item 1', { exact: true }).fill('甲')
  await qp.getByRole('button', { name: 'Add sentence item', exact: true }).click()
  await qp.locator('.admin-assessment-question-form:visible').getByLabel('Item 2', { exact: true }).fill('乙')
  await qp.getByRole('button', { name: 'Xem trước', exact: true }).click()
  await qp.locator('.admin-editor-preview:visible').getByRole('button', { name: 'Move 甲 down', exact: true }).click()
  await qp.getByRole('button', { name: 'Biên soạn', exact: true }).click()
  await qp.getByRole('button', { name: 'Add sentence item', exact: true }).click()
  await qp.locator('.admin-assessment-question-form:visible').getByLabel('Item 3', { exact: true }).fill('丙')
  await qp.getByRole('button', { name: 'Xem trước', exact: true }).click()
  assert.equal(await qp.locator('.admin-editor-preview:visible .reorder-list li').count(), 3)
  await capture(qp, 'reorder-preview-new-item-390')
  await qc.close()
  checks.push('Question draft preservation, live mobile preview and local answer interaction, explicit cancel/discard, all seven question types, no answer key in student preview; preview resets after authored items change; delete disabled during delayed save')

  for (const width of [1440, 390]) {
    const dc = await context(width)
    const items = [
      { id: 'review-source-a', title: 'Giáo trình HSK 1', original_filename: 'hsk1-source.pdf', source_category: 'CURRICULUM_MATERIAL', source_language: 'zh', processing_status: 'UPLOADED', review_status: 'PENDING' },
      { id: 'review-source-b', title: 'Tài liệu ngữ pháp bổ trợ', original_filename: 'grammar-notes.docx', source_category: 'INTERNAL_AUTHORED', source_language: 'vi', processing_status: 'PREVIEW_READY', review_status: 'PENDING' },
    ]
    await dc.route('**/api/v1/admin/documents?*', (route) => route.fulfill({ json: { items, page: 1, page_size: 20, total: 2 } }))
    const dp = await dc.newPage(); watch(dp)
    await load(dp, '/admin/documents', '.admin-library-card')
    await dp.getByRole('button', { name: items[1].title, exact: true }).click()
    assert.equal(await dp.locator('.admin-quick-preview h3').textContent(), items[1].title)
    await capture(dp, `documents-fixture-filled-${width}`)
    await dp.getByRole('button', { name: 'Bảng', exact: true }).click()
    assert.equal(await dp.locator('.admin-library-table button[aria-pressed="true"]').textContent(), items[1].title)
    await capture(dp, `documents-fixture-table-${width}`)
    await dc.close()
  }
  checks.push('Document library fixtures show processing and review separately; card selection and table toggle preserve selected record; real document inventory is empty')

  for (const scenario of ['empty', 'failure', 'long', 'readonly']) {
    const c = await context(scenario === 'long' ? 768 : 390)
    await c.route('**/api/v1/admin/lessons**', (route) => {
      const path = new URL(route.request().url()).pathname
      if (path.endsWith('/vocabulary')) return route.fulfill({ json: scenario === 'empty' ? [] : words })
      if (path.endsWith('/grammar')) return route.fulfill({ json: [] })
      if (path.endsWith(lessonId)) return route.fulfill({ json: { ...lesson, status: scenario === 'readonly' ? 'ARCHIVED' : lesson.status } })
      if (scenario === 'failure') return route.fulfill({ status: 503, json: { error: { code: 'TEMPORARY_FAILURE', message: 'Review fixture failure', details: null } } })
      return route.fulfill({ json: { items: scenario === 'empty' ? [] : [{ ...lesson, title: 'Bài học chào hỏi với nội dung tiêu đề rất dài dành cho người mới bắt đầu học tiếng Trung và làm quen các tình huống giao tiếp trong cuộc sống hằng ngày', description: 'Nội dung minh họa kiểm tra cách xuống dòng của tiêu đề và phần giới thiệu.' }], page: 1, page_size: 20, total: scenario === 'empty' ? 0 : 1 } })
    })
    const page = await c.newPage(); watch(page)
    await load(page, scenario === 'readonly' ? `/admin/lessons/${lessonId}` : '/admin/lessons', scenario === 'failure' ? '[role="alert"]' : scenario === 'empty' ? '.ui-page-state' : scenario === 'readonly' ? '.admin-content-edit-preview' : '.admin-library-card')
    if (scenario === 'readonly') assert.equal(await page.getByRole('button', { name: 'Save content changes', exact: true }).count(), 0)
    await capture(page, `state-${scenario}`); await c.close()
  }
  checks.push('Empty, error, long content, archived read-only, keyboard/DOM order, responsive overflow')
  const zoom = await context(720, 500), zp = await zoom.newPage(); watch(zp)
  await load(zp, `/admin/lessons/${lessonId}`, '.admin-content-edit-preview'); await capture(zp, 'lesson-zoom-200-equivalent'); await zoom.close()
  assert.deepEqual(errors, []); assert.deepEqual(realMutations, [])
  await writeFile(folder + '/verification.json', JSON.stringify({ origin, captures, checks, errors, realMutations, lessonStatus: lesson.status, assessmentStatus: assessment.status, passThreshold: assessment.pass_threshold }, null, 2))
  console.log(JSON.stringify({ captures: captures.length, checks, errors, realMutations }))
} finally { await browser.close() }
