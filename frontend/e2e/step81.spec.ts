import { expect, test, type Page } from '@playwright/test'

// Guarded global setup resets/seeds only chinese_learning_test. The test ASGI
// server substitutes deterministic AI providers; no production data is used.
const password = process.env.STEP81_TEST_PASSWORD
if (!password) throw new Error('Playwright global setup must provide its ephemeral test password')
const learnerEmail = 'step81-learner@example.invalid'
const adminEmail = 'step81-admin@example.invalid'
const lessonA = '0e63a248-4b5a-5c14-aad6-dadd22b8a91d'
const periodic = 'c997aaf0-15e3-514e-92bc-a1d55eb6a57b'
const api = 'http://127.0.0.1:8000/api/v1'

async function login(page: Page, email: string) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel("Mật khẩu").fill(password!)
  await page.getByRole('button', { name: "Đăng nhập", exact: true }).click()
  await expect(page).toHaveURL(email === adminEmail ? /\/admin$/ : /\/pronunciation$/)
}

async function noOverflow(page: Page) {
  await page.evaluate(() => document.fonts.ready)
  const size = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
  expect(size.scroll).toBeLessThanOrEqual(size.client + 1)
}

async function get(page: Page, path: string) {
  const response = await page.request.get(api + path)
  expect(response.ok(), `${path}: ${response.status()}`).toBe(true)
  return response.json()
}

async function createLesson(page: Page, number: string, title: string) {
  await page.goto('/admin/lessons?create=1')
  const form = page.locator('form.admin-form-grid')
  const levels = await get(page, '/admin/hsk-levels')
  await form.getByRole('combobox', { name: 'HSK', exact: true }).selectOption(levels.find(level => level.level_number === 1).id)
  await form.getByLabel('Số thứ tự bài học').fill(number)
  await form.getByLabel('Tiêu đề', { exact: true }).fill(title)
  await form.getByRole('button', { name: 'Tạo bài học', exact: true }).click()
  await expect(page.getByRole('heading', { name: `Bài ${number} · ${title}`, exact: true })).toBeVisible()
  return new URL(page.url()).pathname.split('/').at(-1)!
}

async function createPractice(page: Page, lessonId: string) {
  const created = await page.request.post(`${api}/admin/assessments`, { data: { type: 'LESSON_EXERCISE', lesson_id: lessonId, title: 'Luyện tập duyệt chung', pass_threshold: 80 } })
  expect(created.ok()).toBe(true)
  const assessment = await created.json()
  for (let index = 0; index < 30; index++) {
    const response = await page.request.post(`${api}/admin/assessments/${assessment.id}/questions`, { data: { type: ['fill_blank', 'translate_zh_vi', 'sentence_writing'][index % 3], prompt: `Câu hỏi ${index + 1}`, reference_answer: '你好', order_index: index + 1, points: 1 } })
    expect(response.ok()).toBe(true)
  }
  return assessment.id
}

test('B1 every pronunciation step and explicit finish are required; theory gates practice', async ({ page }) => {
  test.setTimeout(180_000)
  await page.goto('/register')
  await page.getByLabel("Họ và tên").fill('New Academy Learner')
  await page.getByLabel('Email').fill(`step81-new-${Date.now()}@example.invalid`)
  await page.getByLabel("Mật khẩu", { exact: true }).fill(password!)
  await page.getByLabel("Xác nhận mật khẩu").fill(password!)
  await page.getByRole('button', { name: "Tạo tài khoản" }).click()
  await expect(page).toHaveURL(/\/pronunciation$/)
  expect((await page.request.get(`${api}/lessons/${lessonA}`)).status()).toBe(403)
  await page.goto('/pronunciation/lesson')
  await expect(page.locator('.pronunciation-section-grid').getByRole('link')).toHaveCount(1)
  await page.goto('/pronunciation/lesson/van-mau')
  await expect(page.getByRole('heading', { name: 'Phần học này chưa mở', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Chọn phần đang học', exact: true }).click()
  for (const [name, count, slug] of [['thanh mẫu', 21, 'thanh-mau'], ['vận mẫu', 36, 'van-mau'], ['thanh điệu', 5, 'thanh-dieu'], ['biến điệu', 12, 'bien-dieu']] as const) {
    await page.getByRole('link', { name: `Học ${name}`, exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`/pronunciation/lesson/${slug}$`))
    await expect(page.locator('#pronunciation-step-title')).toHaveText(name)
    await expect(page.getByRole('button', { name: `Hoàn thành ${name}`, exact: true })).toHaveCount(0)
    for (let index = 0; index < count; index++) {
      const response = page.waitForResponse(r => r.url().endsWith('/pronunciation/lesson/advance') && r.request().method() === 'POST')
      await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
      expect((await response).status()).toBe(200)
      await expect(page.getByRole('progressbar', { name: `Tiến độ ${name}`, exact: true })).toHaveAttribute('value', String(index + 1))
    }
    await page.getByRole('button', { name: `Hoàn thành ${name}`, exact: true }).click()
    await expect(page).toHaveURL(/\/pronunciation\/lesson$/)
  }
  await expect(page.getByRole('heading', { name: 'Đã hoàn thành bốn phần' })).toBeVisible()
  expect((await get(page, '/pronunciation/lesson')).completed_at).toBeNull()
  expect((await page.request.get(`${api}/lessons/${lessonA}`)).status()).toBe(403)
  await page.getByRole('button', { name: 'Hoàn thành bài học', exact: true }).click()
  await expect(page).toHaveURL(/\/pronunciation$/)
  expect((await get(page, '/pronunciation/lesson')).completed_at).toBeTruthy()
  await page.goto(`/lessons/${lessonA}`)
  await expect(page.getByRole('heading', { name: '你好', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Tiếp theo', exact: true })).toBeEnabled()
  await page.getByRole('link', { name: 'Luyện tập', exact: true }).click()
  await expect(page.getByRole('button', { name: "Mở luyện tập 1", exact: true })).toBeDisabled()
  await page.getByRole('link', { name: 'Từ vựng', exact: true }).click()
  await expect(page.getByRole('heading', { name: '你好', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
  expect((await get(page, `/me/progress/lessons/${lessonA}`)).theory_completed_at).toBeNull()
  await page.getByRole('button', { name: "Xem chi tiết", exact: true }).click()
  await expect.poll(async () => (await get(page, `/me/progress/lessons/${lessonA}`)).theory_completed_at).toBeTruthy()
  await page.getByRole('link', { name: 'Luyện tập', exact: true }).click()
  await expect(page.getByRole('link', { name: "Mở luyện tập 1", exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('link', { name: "Mở luyện tập 1", exact: true })).toBeVisible()
})

test('D-120 forbidden routes preserve separate learner and administrator sessions', async ({ page, browser }) => {
  await page.goto('/admin')
  await expect(page).toHaveURL(/\/login$/)
  await login(page, learnerEmail)
  await page.goto('/admin')
  await expect(page.getByTestId('admin-forbidden')).toBeVisible()
  await page.getByRole('link', { name: 'Quay lại góc học tập' }).click()
  await expect(page).toHaveURL(/\/pronunciation$/)
  const context = await browser.newContext()
  try {
    const admin = await context.newPage()
    await login(admin, adminEmail)
    await admin.goto('/dashboard')
    await expect(admin.getByTestId('learner-forbidden')).toBeVisible()
    await admin.getByRole('link', { name: "Về trang quản trị" }).click()
    await expect(admin.getByRole('heading', { name: 'Quản trị học liệu', exact: true })).toBeVisible()
  } finally { await context.close() }
})

test('B3 student lesson pages expose no AI assistant or conversation requests', async ({ page }) => {
  await login(page, learnerEmail)
  const assistantRequests: string[] = []
  page.on('request', request => { if (/\/conversations(?:[/?]|$)|\/messages\/[^/]+\/retry/.test(request.url())) assistantRequests.push(request.url()) })
  for (const part of ['', '/vocabulary', '/grammar', '/readings', '/practice']) {
    await page.goto(`/lessons/${lessonA}${part}`)
    await expect(page.getByRole('heading', { name: 'Bài học 1: Step 8.1 Lesson A', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Mở trợ lý AI' })).toHaveCount(0)
    await expect(page.locator('.lesson-chat-entry, .chat-panel')).toHaveCount(0)
  }
  expect(assistantRequests).toEqual([])
})

test('B2 HSK levels stay independently open; periodic retry and both results persist', async ({ page }) => {
  await login(page, learnerEmail)
  await page.goto(`/assessments/${periodic}`)
  await page.getByRole('button', { name: "Bắt đầu / Tiếp tục luyện tập" }).click()
  await page.getByLabel('你好', { exact: true }).check()
  await page.getByRole('button', { name: "Nộp bài" }).click()
  await expect(page.getByText("Chưa đạt", { exact: true })).toBeVisible()
  const failedPath = new URL(page.url()).pathname
  await page.goto('/hsk/2')
  await expect(page.locator('.lc-lesson-grid')).toBeVisible()
  await expect(page.locator('.lc-lesson-grid a.lc-lesson-card')).toHaveCount(1)
  await page.goto(failedPath)
  await page.getByRole('link', { name: "Thử lại", exact: true }).click()
  await page.getByRole('button', { name: "Bắt đầu / Tiếp tục luyện tập" }).click()
  await page.getByLabel('再见', { exact: true }).check()
  await page.getByRole('button', { name: "Nộp bài" }).click()
  await expect(page.getByText("Đạt", { exact: true })).toBeVisible()
  const passedPath = new URL(page.url()).pathname
  expect(passedPath).not.toBe(failedPath)
  await page.goto('/hsk/2')
  await expect(page.locator('.lc-lesson-grid > li[data-state="current"]')).toBeVisible()
  await expect(page.locator('.lc-lesson-grid a.lc-lesson-card')).toHaveCount(1)
  await page.goto(failedPath)
  await expect(page.getByText("Chưa đạt", { exact: true })).toBeVisible()
  await page.goto(passedPath)
  await expect(page.getByText("Đạt", { exact: true })).toBeVisible()
})

test('B4 draft visibility, publication and curriculum membership stay explicit', async ({ page, browser }) => {
  await login(page, adminEmail)
  const lesson = await createLesson(page, '840001', 'Lifecycle lesson')
  await createPractice(page, lesson)
  await page.reload()
  await expect(page.getByText('Trạng thái: Bản nháp', { exact: true })).toBeVisible()
  const context = await browser.newContext()
  try {
    const learner = await context.newPage()
    await login(learner, learnerEmail)
    expect((await learner.request.get(`${api}/lessons/${lesson}`)).status()).toBe(404)
    await page.getByRole('button', { name: 'Thông tin bài học', exact: true }).click()
    await page.locator('.admin-lesson-metadata-form').getByLabel('Tiêu đề', { exact: true }).fill('Published lifecycle lesson')
    await page.getByRole('button', { name: 'Duyệt xuất bản', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ', exact: true })).toBeDisabled()
    await page.getByRole('button', { name: 'Thông tin bài học', exact: true }).click()
    await page.getByRole('button', { name: 'Lưu thông tin', exact: true }).click()
    await page.getByRole('button', { name: 'Duyệt xuất bản', exact: true }).click()
    await page.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ', exact: true }).click()
    await expect(page.getByText('Trạng thái: Đã xuất bản', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Hủy xuất bản', exact: true }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Hủy xuất bản', exact: true }).click()
    await expect(page.getByText('Trạng thái: Bản nháp', { exact: true })).toBeVisible()
    expect((await learner.request.get(`${api}/lessons/${lesson}`)).status()).toBe(404)
    await page.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ', exact: true }).click()
    await expect(page.getByText('Trạng thái: Đã xuất bản', { exact: true })).toBeVisible()
    await learner.goto('/hsk/1')
    await expect(learner.getByText(/Published lifecycle lesson/)).toHaveCount(0)
    await page.goto('/admin/curriculum')
    await page.getByRole('button', { name: 'Thêm Published lifecycle lesson vào lộ trình', exact: true }).click()
    await page.setViewportSize({ width: 390, height: 844 })
    await page.getByRole('button', { name: 'Lưu lộ trình', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: 'Lưu thay đổi lộ trình?' })
    await expect(dialog).toBeVisible()
    await noOverflow(page)
    await dialog.getByRole('button', { name: 'Lưu lộ trình', exact: true }).click()
    await expect(dialog).not.toBeVisible()
    await learner.reload()
    await expect(learner.getByRole('heading', { name: /Published lifecycle lesson/ })).toBeVisible()
  } finally { await context.close() }
})

test('B5 AI draft has 30 varied questions at 80 percent and needs review before publishing', async ({ page, browser }) => {
  await login(page, adminEmail)
  await page.goto(`/admin/lessons/${lessonA}?section=exercises`)
  await page.getByRole('button', { name: 'Tạo bản nháp bằng AI', exact: true }).click()
  await page.getByRole('combobox', { name: 'Độ khó', exact: true }).selectOption('EASY')
  await expect(page.getByRole('spinbutton', { name: 'Điểm đạt (%)', exact: true })).toHaveValue('80')
  await expect(page.getByRole('spinbutton', { name: 'Số câu hỏi', exact: true })).toHaveValue('30')
  const generation = page.waitForResponse(response => response.url().endsWith('/admin/assessments/generate-draft') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Tạo bản nháp', exact: true }).click()
  await expect(page).toHaveURL(new RegExp(`/admin/lessons/${lessonA}\\?section=exercises$`))
  const generated = (await (await generation).json()).assessment
  const assessmentId = generated.id
  await expect(page.locator('.admin-embedded-assessment-heading:visible')).toContainText('Bản nháp')
  const questions = await get(page, `/admin/assessments/${assessmentId}/questions`)
  expect(questions).toHaveLength(30)
  expect(new Set(questions.map(question => question.type)).size).toBe(4)
  const context = await browser.newContext()
  try {
    const learner = await context.newPage()
    await login(learner, learnerEmail)
    expect((await learner.request.get(`${api}/assessments/${assessmentId}`)).status()).toBe(404)
    // The baseline one-question fixture predates the 30-question policy.
    // Archive it explicitly; the new draft is the lesson's active exercise.
    const existing = await get(page, `/admin/assessments?lesson_id=${lessonA}`)
    for (const item of existing.items.filter(item => item.id !== assessmentId && item.status === 'PUBLISHED')) {
      expect((await page.request.post(`${api}/admin/assessments/${item.id}/archive`)).ok()).toBe(true)
    }
    await page.goto(`/admin/lessons/${lessonA}?section=exercises&exercise=${assessmentId}`)
    await page.getByRole('button', { name: 'Duyệt xuất bản', exact: true }).click()
    await page.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ', exact: true }).click()
    await expect(page.getByText('Trạng thái: Đã xuất bản', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Luyện tập', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Lưu câu hỏi', exact: true })).toHaveCount(0)
    await learner.goto(`/assessments/${assessmentId}`)
    await expect(learner.getByRole('heading', { name: 'AI Draft — Step 8.1 Lesson A', exact: true })).toBeVisible()
  } finally { await context.close() }
})

test('vocabulary drafts survive section switches, failed saves and cancelled navigation', async ({ page }) => {
  await login(page, adminEmail)
  await page.goto(`/admin/lessons/${lessonA}`)
  const meaning = page.getByRole('textbox', { name: 'Nghĩa tiếng Việt', exact: true })
  await meaning.fill('xin chào — bản chỉnh sửa')
  await page.getByRole('button', { name: 'Ngữ pháp', exact: true }).click()
  await page.getByRole('button', { name: 'Từ vựng', exact: true }).click()
  await expect(meaning).toHaveValue('xin chào — bản chỉnh sửa')
  await page.getByRole('link', { name: 'Quay lại bài học', exact: true }).click()
  const warning = page.getByRole('dialog', { name: 'Rời trang khi chưa lưu?' })
  await expect(warning).toBeVisible()
  await warning.getByRole('button', { name: 'Hủy', exact: true }).click()
  await page.route(/\/admin\/lessons\/[^/]+\/vocabulary\/[^/]+$/, route => route.request().method() === 'PATCH'
    ? route.fulfill({ status: 503, json: { error: { code: 'TEMPORARY', message: 'Fixture failure', details: null } } }) : route.continue())
  await page.getByRole('button', { name: 'Lưu nội dung', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Có sự cố tạm thời')
  await expect(meaning).toHaveValue('xin chào — bản chỉnh sửa')
  await page.unrouteAll()
  await page.getByRole('button', { name: 'Lưu nội dung', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Lưu nội dung', exact: true })).toBeDisabled()
  await page.reload()
  await expect(meaning).toHaveValue('xin chào — bản chỉnh sửa')
})

for (const width of [390, 768, 1440]) {
  test(`admin navigation, library and authoring reflow at ${width}px`, async ({ page }) => {
    test.setTimeout(90_000)
    await page.setViewportSize({ width, height: 1000 })
    const brokenAssets: string[] = [], errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('response', response => { if (response.status() >= 400 && ['image', 'font'].includes(response.request().resourceType())) brokenAssets.push(response.url()) })
    await login(page, adminEmail)
    const nav = page.getByRole('navigation', { name: 'Điều hướng quản trị', exact: true })
    await expect(nav.getByRole('link')).toHaveText(['Tổng quan', 'Bài học', 'Kiểm tra định kỳ', 'Tài liệu', 'Hồ sơ'])
    for (const link of await nav.getByRole('link').all()) { await link.focus(); await expect(link).toBeFocused() }
    for (const [path, title] of [
      ['/admin', 'Quản trị học liệu'], ['/admin/curriculum', 'Sắp xếp HSK'],
      ['/admin/lessons', 'Bài học'], ['/admin/assessments', 'Kiểm tra định kỳ'],
      ['/admin/documents', 'Thư viện tài liệu'], ['/admin/stats', 'Thống kê'],
      [`/admin/lessons/${lessonA}`, 'Bài 1 · Step 8.1 Lesson A'],
    ]) {
      await page.goto(path)
      await expect(page.getByRole('heading', { name: title, level: 1, exact: true })).toBeVisible()
      if (path === '/admin') await expect(page.locator('.academy-header-art')).toBeVisible()
      await noOverflow(page)
      await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
    }
    await page.goto('/admin/lessons')
    await expect(page.locator('.admin-library-card').first()).toBeVisible()
    await page.getByRole('button', { name: 'Bảng', exact: true }).click()
    await expect(page.getByRole('region', { name: 'Bảng bài học', exact: true }).getByRole('table')).toBeVisible()
    await noOverflow(page)
    await page.getByRole('button', { name: 'Thẻ', exact: true }).click()
    await expect(page.locator('.admin-library-card').first()).toBeVisible()
    await page.goto('/admin/assessments?generate=1')
    await expect(page.getByRole('heading', { name: 'Tạo bản nháp bằng AI', exact: true })).toBeVisible()
    await noOverflow(page)
    expect(brokenAssets).toEqual([])
    expect(errors).toEqual([])
  })

  test(`student routes and chat containment at ${width}px`, async ({ page }) => {
    test.setTimeout(90_000)
    await page.setViewportSize({ width, height: 1000 })
    await login(page, learnerEmail)
    for (const [path, title] of [
      ['/dashboard', 'Giáo trình của bạn'], ['/pronunciation', 'Giáo trình của bạn'],
      ['/pronunciation/lesson', 'Bài học phát âm'], ['/hsk/1', 'Giáo trình của bạn'],
      [`/lessons/${lessonA}`, "Bài học 1: Step 8.1 Lesson A"],
      ['/profile', "Hồ sơ"], ['/companions', 'Hồ sơ'],
      [`/assessments/${periodic}`, 'Step 8.1 Periodic Test'],
    ]) {
      await page.goto(path)
      await expect(page.getByRole('heading', { name: title, level: 1, exact: true })).toBeVisible()
      await noOverflow(page)
    }
    await page.goto(`/lessons/${lessonA}`)
    await expect(page.locator('.lesson-chat-entry, .chat-panel')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /AI/ })).toHaveCount(0)
    await noOverflow(page)
  })

  test(`public auth forms remain keyboard accessible at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 })
    for (const [path, title] of [['/login', "Đăng nhập"], ['/register', "Tạo tài khoản"], ['/forgot-password', "Quên mật khẩu"]]) {
      await page.goto(path)
      await expect(page.getByRole('heading', { name: title, level: 1, exact: true })).toBeVisible()
      await page.getByLabel('Email', { exact: true }).focus()
      await expect(page.getByLabel('Email', { exact: true })).toBeFocused()
      await noOverflow(page)
    }
  })
}

test('Vietnamese list recovery and empty states remain actionable', async ({ page }) => {
  await login(page, adminEmail)
  let fail = true
  await page.route(/\/api\/v1\/admin\/lessons(?:\?.*)?$/, route => route.fulfill(fail
    ? { status: 503, json: { error: { code: 'TEMPORARY', message: 'Fixture failure', details: null } } }
    : { json: { items: [], total: 0, page: 1, page_size: 20 } }))
  await page.goto('/admin/lessons')
  await expect(page.getByRole('alert')).toContainText('Có sự cố tạm thời')
  fail = false
  await page.getByRole('button', { name: 'Thử lại', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Không có bài học phù hợp', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Tạo bài học', exact: true })).toBeVisible()
  await noOverflow(page)
})

test('curriculum metadata and ordering save independently; empty HSK states are usable', async ({ page }) => {
  await login(page, adminEmail)
  await page.goto('/admin/curriculum')
  const metadata = page.getByRole('button', { name: 'Lưu thông tin HSK', exact: true })
  const order = page.getByRole('button', { name: 'Lưu lộ trình', exact: true })
  await expect(metadata).toBeDisabled()
  await expect(order).toBeDisabled()
  await page.getByLabel('Tiêu đề', { exact: true }).fill('HSK 1 — metadata draft')
  await expect(metadata).toBeEnabled()
  await expect(order).toBeDisabled()
  await page.getByRole('button', { name: 'Đưa Step 8.1 Lesson A xuống', exact: true }).click()
  await expect(order).toBeEnabled()
  await order.click()
  await page.getByRole('dialog').getByRole('button', { name: 'Hủy', exact: true }).click()
  await expect(order).toBeEnabled()
  await expect(metadata).toBeEnabled()
  await page.goto('/admin/curriculum')
  const levels = await get(page, '/admin/hsk-levels')
  await page.getByRole('combobox', { name: 'Chọn HSK', exact: true }).selectOption(levels.find(level => level.level_number === 3).id)
  await expect(page.getByRole('heading', { name: 'Lộ trình chưa có nội dung', exact: true })).toBeVisible()
  await page.route(/\/api\/v1\/admin\/hsk-levels$/, route => route.fulfill({ json: [] }))
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Chưa có cấp độ HSK', exact: true })).toBeVisible()
})

for (const role of ['admin', 'student'] as const) {
  test(`${role} logout failure preserves session and explicit retry signs out`, async ({ page }) => {
    await login(page, role === 'admin' ? adminEmail : learnerEmail)
    await page.route('**/api/v1/auth/logout', route => route.fulfill({ status: 503, json: { error: { code: 'TEMPORARY', message: 'Fixture failure', details: null } } }))
    await page.getByRole('button', { name: role === 'admin' ? 'Đăng xuất' : "Đăng xuất", exact: true }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.locator(`main[data-layout="${role === 'admin' ? 'admin' : 'learner'}"]`)).toBeVisible()
    await page.unrouteAll()
    await page.getByRole('button', { name: role === 'admin' ? 'Thử đăng xuất lại' : "Thử đăng xuất lại", exact: true }).click()
    await expect(page).toHaveURL(/\/login$/)
    await page.goto(role === 'admin' ? '/admin' : '/dashboard')
    await expect(page).toHaveURL(/\/login$/)
  })
}

test('draft vocabulary and grammar can be managed; archival makes the editor read only', async ({ page }) => {
  await login(page, adminEmail)
  await createLesson(page, '840002', 'Content authoring lesson')
  await page.getByRole('button', { name: 'Thêm từ vựng', exact: true }).click()
  await page.getByLabel('Chữ Hán', { exact: true }).fill('谢谢')
  await page.getByLabel('Phiên âm', { exact: true }).fill('xièxie')
  await page.getByLabel('Nghĩa tiếng Việt', { exact: true }).fill('cảm ơn')
  await page.getByRole('button', { name: 'Tạo và thêm từ vựng', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Gỡ từ vựng', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Gỡ từ vựng', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Gỡ từ vựng', exact: true }).click()
  await expect(page.getByText('Bài học này chưa có từ vựng.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Ngữ pháp', exact: true }).click()
  await page.getByRole('button', { name: 'Thêm ngữ pháp', exact: true }).click()
  await page.getByLabel('Tên', { exact: true }).fill('Greeting structure')
  await page.getByLabel('Giải thích', { exact: true }).fill('A greeting example')
  await page.getByRole('button', { name: 'Tạo và thêm ngữ pháp', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Gỡ ngữ pháp', exact: true })).toBeVisible()
  const lessonId = new URL(page.url()).pathname.split('/').at(-1)!
  expect((await page.request.post(`${api}/admin/lessons/${lessonId}/publish`)).ok()).toBe(true)
  await page.reload()
  await page.getByRole('button', { name: 'Ngữ pháp', exact: true }).click()
  await page.getByRole('button', { name: 'Lưu trữ bài học', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Lưu trữ bài học', exact: true }).click()
  await expect(page.getByText('Trạng thái: Đã lưu trữ', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Tên', { exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Lưu nội dung', exact: true })).toHaveCount(0)
})

test('seven question types have learner previews and saved questions can be deleted explicitly', async ({ page }) => {
  await login(page, adminEmail)
  await page.goto(`/admin/lessons/${lessonA}?section=exercises`)
  await page.getByRole('button', { name: 'Thêm bài luyện tập', exact: true }).click()
  const create = page.getByRole('form', { name: 'Thêm bài luyện tập', exact: true })
  await create.getByLabel('Tiêu đề bài luyện tập', { exact: true }).fill("Câu hỏi workshop")
  await expect(create.getByLabel('Điểm đạt (%)', { exact: true })).toHaveValue('80')
  await create.getByRole('button', { name: 'Tạo bài luyện tập', exact: true }).click()
  await expect(page.getByRole('heading', { name: "Câu hỏi workshop", exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Thêm câu hỏi', exact: true }).click()
  const form = page.locator('.admin-assessment-question-form:visible')
  const preview = page.locator('.admin-editor-preview:visible')
  const prompt = form.getByRole('textbox', { name: 'Nội dung câu hỏi', exact: true })
  await prompt.fill('Chọn lời chào')
  for (const type of ['multiple_choice', 'fill_blank', 'matching', 'reorder_sentence', 'translate_vi_zh', 'translate_zh_vi', 'sentence_writing']) {
    await form.getByRole('combobox', { name: 'Dạng câu hỏi', exact: true }).selectOption(type)
    await expect(preview).toContainText('Chọn lời chào')
    await expect(preview.getByText('Đáp án đúng', { exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Gửi duyệt', exact: true })).toHaveCount(0)
  }
  await form.getByRole('combobox', { name: 'Dạng câu hỏi', exact: true }).selectOption('reorder_sentence')
  await form.getByRole('button', { name: 'Thêm mảnh câu', exact: true }).click()
  await form.getByLabel('Mảnh câu 1', { exact: true }).fill('你')
  await form.getByRole('button', { name: 'Thêm mảnh câu', exact: true }).click()
  await form.getByLabel('Mảnh câu 2', { exact: true }).fill('好')
  await preview.getByRole('button', { name: 'Đưa 好 lên', exact: true }).click()
  await form.getByRole('button', { name: 'Thêm mảnh câu', exact: true }).click()
  await form.getByLabel('Mảnh câu 3', { exact: true }).fill('吗')
  for (const word of ['你', '好', '吗']) await expect(preview.getByText(word, { exact: true })).toBeVisible()
  await form.getByRole('button', { name: 'Lưu câu hỏi', exact: true }).click()
  await page.getByRole('button', { name: 'Duyệt xuất bản', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Xác nhận xuất bản toàn bộ', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Luyện tập', exact: true }).click()
  await page.getByRole('button', { name: 'Xóa câu hỏi', exact: true }).click()
  await page.getByRole('dialog', { name: 'Xóa câu hỏi?' }).getByRole('button', { name: 'Xóa câu hỏi', exact: true }).click()
  await expect(page.getByText('Chưa có câu hỏi nào.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Gửi duyệt', exact: true })).toHaveCount(0)
})

test('dashboard puts authoring first; student reading uses one large size with accessible skip links', async ({ page }) => {
  await login(page, adminEmail)
  await expect(page.getByRole('link', { name: 'Tạo bài học', exact: true })).toBeVisible()
  const primary = await page.locator('.admin-workbench-primary').boundingBox()
  const stats = await page.locator('.admin-workbench-stats').boundingBox()
  expect(primary!.y).toBeLessThan(stats!.y)
  await page.getByRole('link', { name: 'Chuyển đến nội dung', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('#main-content')).toBeFocused()
  await page.getByRole('button', { name: 'Đăng xuất', exact: true }).click()
  await expect(page).toHaveURL(/\/login$/)
  await login(page, learnerEmail)
  await expect(page.locator('.academy-topbar, .academy-reading-settings')).toHaveCount(0)
  expect(await page.locator('.bo-shell').evaluate(element => getComputedStyle(element).getPropertyValue('--reader-font-size').trim())).toBe('21px')
  await page.reload()
  expect(await page.locator('.bo-shell').evaluate(element => getComputedStyle(element).getPropertyValue('--reader-font-size').trim())).toBe('21px')
  await noOverflow(page)
})

test('retired design prototypes stay outside the production application', async ({ page }) => {
  for (const path of ['/design-lab', '/design-lab/preview', '/journey-test.html']) {
    await page.goto(path)
    await expect(page.getByTestId('not-found')).toBeVisible()
  }
})

test('Great Wall journey opens real lessons and student logout stays in the sidebar', async ({ page }) => {
  await login(page, learnerEmail)
  await page.goto('/pronunciation')
  await expect(page.locator('.learning-hub__unit-details')).toHaveCount(0)
  await page.getByRole('link', { name: /^HSK 1/ }).click()
  await expect(page).toHaveURL(/\/hsk\/1$/)
  const units = page.getByRole('list', { name: 'Các bài trong cấp độ HSK' })
  await expect(units).toBeVisible()
  await units.getByRole('link', { name: /(?:Học|Ôn) Bài học 1: Step 8.1 Lesson A/ }).click()
  await expect(page).toHaveURL(new RegExp(`/lessons/${lessonA}$`))
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 900 })
    const opener = page.getByRole('button', { name: 'Mở menu học viên', exact: true })
    if (width <= 800) {
      await opener.click()
      await expect(page.getByRole('dialog', { name: 'Khu vực học viên' })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Đóng menu', exact: true })).toBeFocused()
    }
    await expect(page.locator('.academy-sidebar').getByRole('button', { name: "Đăng xuất", exact: true })).toBeVisible()
    await expect(page.locator('.academy-topbar .logout-action')).toHaveCount(0)
    await noOverflow(page)
    if (width <= 800) {
      await page.keyboard.press('Escape')
      await expect(opener).toBeFocused()
      await expect(page.locator('.academy-sidebar')).not.toBeVisible()
    }
  }
})

test('textbook readings require explicit completion before practice; admin edits invalidate the old completion', async ({ page, browser }) => {
  test.setTimeout(120_000)
  await login(page, adminEmail)
  await page.goto(`/admin/lessons/${lessonA}`)
  await page.getByRole('button', { name: 'Bài khóa', exact: true }).click()
  await page.getByRole('button', { name: 'Thêm bài khóa', exact: true }).click()
  await page.getByLabel('Tiêu đề bài khóa', { exact: true }).fill('Chào hỏi từ giáo trình')
  await page.getByLabel('Nội dung tiếng Trung', { exact: true }).fill('A：你好！\nB：你好！')
  await page.getByLabel('Phiên âm (không bắt buộc)', { exact: true }).fill('A: Nǐ hǎo!\nB: Nǐ hǎo!')
  await page.getByLabel('Nghĩa tiếng Việt (không bắt buộc)', { exact: true }).fill('A: Xin chào!\nB: Xin chào!')
  await page.getByRole('button', { name: 'Lưu bài khóa', exact: true }).click()
  await expect(page.getByRole('button', { name: '1. Chào hỏi từ giáo trình', exact: true })).toBeVisible()
  const readings = await get(page, `/admin/lessons/${lessonA}/readings`)
  const exercise = (await get(page, `/admin/assessments?lesson_id=${lessonA}`)).items.find(item => item.lesson_id === lessonA && item.type === 'LESSON_EXERCISE' && item.status === 'PUBLISHED')
  expect(readings).toHaveLength(1)
  expect(exercise).toBeTruthy()
  const learnerContext = await browser.newContext()
  try {
    const student = await learnerContext.newPage()
    await login(student, learnerEmail)
    await student.goto(`/lessons/${lessonA}`)
    await expect(student.getByRole('heading', { name: '你好', exact: true })).toBeVisible()
    await student.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await expect(student.getByRole('heading', { name: 'Bài học 1: Step 8.1 Lesson A', exact: true })).toBeVisible()
    await expect(student.getByRole('heading', { name: 'Ngữ pháp', exact: true })).toBeVisible()
    while (await student.getByRole('button', { name: 'Xem chi tiết', exact: true }).count()) await student.getByRole('button', { name: 'Xem chi tiết', exact: true }).first().click()
    await student.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    await expect(student.getByRole('button', { name: 'Mở luyện tập 1', exact: true })).toBeDisabled()
    expect((await student.request.get(`${api}/assessments/${exercise.id}`)).status()).toBe(403)
    await student.reload()
    await student.getByRole('link', { name: 'Bài khóa', exact: true }).click()
    await expect(student.getByRole('button', { name: 'Hoàn thành bài khóa: Chào hỏi từ giáo trình', exact: true })).toBeEnabled()
    await student.getByRole('button', { name: 'Hoàn thành bài khóa: Chào hỏi từ giáo trình', exact: true }).click()
    await student.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    await expect(student.getByRole('link', { name: 'Mở luyện tập 1', exact: true })).toBeVisible()
    await student.reload()
    await student.getByRole('link', { name: 'Bài khóa', exact: true }).click()
    await expect(student.getByRole('button', { name: 'Đã hoàn thành bài khóa: Chào hỏi từ giáo trình', exact: true })).toBeDisabled()
    await page.getByRole('textbox', { name: 'Nội dung tiếng Trung', exact: true }).fill('A：你好！\nB：你好吗？')
    await page.getByRole('button', { name: 'Lưu bài khóa', exact: true }).click()
    await expect(page.getByText('Đã lưu bài khóa.', { exact: true })).toBeVisible()
    expect((await student.request.post(`${api}/lessons/${lessonA}/theory/readings/${readings[0].id}/complete`, { data: { version: 1 } })).status()).toBe(409)
    await student.reload()
    await student.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    await expect(student.getByRole('button', { name: 'Mở luyện tập 1', exact: true })).toBeDisabled()
    await student.setViewportSize({ width: 390, height: 900 })
    await student.getByRole('link', { name: 'Bài khóa', exact: true }).click()
    await student.getByRole('button', { name: 'Hoàn thành bài khóa: Chào hỏi từ giáo trình', exact: true }).click()
    await student.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    await expect(student.getByRole('link', { name: 'Mở luyện tập 1', exact: true })).toBeVisible()
    await noOverflow(student)
  } finally { await learnerContext.close() }
})

test('real stroke data supports each character and earlier graduates can complete supplementary sandhi', async ({ page }) => {
  test.setTimeout(90_000)
  await login(page, learnerEmail)
  const before = await get(page, '/pronunciation/lesson')
  expect(before.completed_at).toBeTruthy()
  expect(before.current_section).toBe('SANDHI')
  await page.goto(`/lessons/${lessonA}`)
  const writer = page.locator('[data-character="你"]').first()
  await writer.scrollIntoViewIfNeeded()
  await expect(writer).toHaveAttribute('data-total-strokes', '7')
  await writer.getByRole('button', { name: 'Tạm dừng chữ 你', exact: true }).click()
  await writer.getByRole('button', { name: 'Bắt đầu lại chữ 你', exact: true }).click()
  await writer.getByRole('button', { name: 'Tạm dừng chữ 你', exact: true }).click()
  await writer.getByRole('button', { name: 'Nét tiếp theo của chữ 你' }).click()
  await expect(writer).toHaveAttribute('data-written-strokes', '1')
  await page.getByRole('button', { name: 'Chữ 好, vị trí 2', exact: true }).click()
  await expect(page.locator('[data-character="好"]')).toHaveAttribute('data-total-strokes', '6')
  await page.goto('/pronunciation/lesson')
  await page.getByRole('link', { name: 'Ôn thanh mẫu', exact: true }).click({ position: { x: 16, y: 16 } })
  await expect(page).toHaveURL(/\/pronunciation\/lesson\/thanh-mau$/)
  await expect(page.locator('.pronunciation-session__symbol')).toHaveText('b')
  await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
  await expect(page.locator('.pronunciation-session__symbol')).toHaveText('p')
  expect((await get(page, '/pronunciation/lesson')).step_index).toBe(before.step_index)
  await page.goBack()
  await page.getByRole('link', { name: 'Học biến điệu', exact: true }).click()
  await expect(page).toHaveURL(/\/pronunciation\/lesson\/bien-dieu$/)
  await expect(page.getByText(/quyền học HSK được giữ nguyên/)).toHaveCount(0)
  await expect(page.getByText('ní hǎo', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
  await expect(page.getByRole('progressbar', { name: 'Tiến độ biến điệu' })).toHaveAttribute('value', '1')
  await page.reload()
  await expect(page.getByRole('progressbar', { name: 'Tiến độ biến điệu' })).toHaveAttribute('value', '1')
  for (let index = 1; index < 12; index++) {
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await expect(page.getByRole('progressbar', { name: 'Tiến độ biến điệu' })).toHaveAttribute('value', String(index + 1))
  }
  await page.getByRole('button', { name: 'Hoàn thành biến điệu', exact: true }).click()
  await expect(page).toHaveURL(/\/pronunciation\/lesson$/)
  await expect(page.getByRole('link', { name: 'Ôn biến điệu', exact: true })).toBeVisible()
  const after = await get(page, '/pronunciation/lesson')
  expect(after.current_section).toBeNull()
  expect(after.completed_at).toBe(before.completed_at)
  expect(after.sections.every(section => section.completed_at)).toBe(true)
  expect((await page.request.get(`${api}/lessons/${lessonA}`)).status()).toBe(200)
})
