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
  await page.getByLabel('Password').fill(password!)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL(email === adminEmail ? /\/admin$/ : /\/dashboard$/)
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

test('B1 every pronunciation step and explicit finish are required; theory gates practice', async ({ page }) => {
  test.setTimeout(180_000)
  await page.goto('/register')
  await page.getByLabel('Full name').fill('New Academy Learner')
  await page.getByLabel('Email').fill(`step81-new-${Date.now()}@example.invalid`)
  await page.getByLabel('Password', { exact: true }).fill(password!)
  await page.getByLabel('Confirm password').fill(password!)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  expect((await page.request.get(`${api}/lessons/${lessonA}`)).status()).toBe(403)
  await page.goto('/pronunciation/lesson')
  for (const [name, count] of [['thanh mẫu', 21], ['vận mẫu', 36], ['thanh điệu', 5]] as const) {
    await expect(page.locator('#pronunciation-step-title')).toHaveText(name)
    await expect(page.getByRole('button', { name: `Hoàn thành ${name}`, exact: true })).toHaveCount(0)
    for (let index = 0; index < count; index++) {
      const response = page.waitForResponse(r => r.url().endsWith('/pronunciation/lesson/advance') && r.request().method() === 'POST')
      await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
      expect((await response).status()).toBe(200)
      await expect(page.getByRole('progressbar', { name: `Tiến độ ${name}`, exact: true })).toHaveAttribute('value', String(index + 1))
    }
    await page.getByRole('button', { name: `Hoàn thành ${name}`, exact: true }).click()
  }
  await expect(page.getByRole('heading', { name: 'Đã hoàn thành ba phần' })).toBeVisible()
  expect((await get(page, '/pronunciation/lesson')).completed_at).toBeNull()
  expect((await page.request.get(`${api}/lessons/${lessonA}`)).status()).toBe(403)
  await page.getByRole('button', { name: 'Hoàn thành bài học', exact: true }).click()
  await expect(page).toHaveURL(/\/pronunciation$/)
  expect((await get(page, '/pronunciation/lesson')).completed_at).toBeTruthy()
  await page.goto(`/lessons/${lessonA}`)
  await expect(page.getByRole('button', { name: 'Open Exercise 1', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Show details', exact: true }).first().click()
  expect((await get(page, `/me/progress/lessons/${lessonA}`)).theory_completed_at).toBeNull()
  await page.getByRole('button', { name: 'Show details', exact: true }).click()
  await expect.poll(async () => (await get(page, `/me/progress/lessons/${lessonA}`)).theory_completed_at).toBeTruthy()
  await expect(page.getByRole('link', { name: 'Open Exercise 1', exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('link', { name: 'Open Exercise 1', exact: true })).toBeVisible()
})

test('D-120 forbidden routes preserve separate learner and administrator sessions', async ({ page, browser }) => {
  await page.goto('/admin')
  await expect(page).toHaveURL(/\/login$/)
  await login(page, learnerEmail)
  await page.goto('/admin')
  await expect(page.getByTestId('admin-forbidden')).toBeVisible()
  await page.getByRole('link', { name: 'Quay lại góc học tập' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  const context = await browser.newContext()
  try {
    const admin = await context.newPage()
    await login(admin, adminEmail)
    await admin.goto('/dashboard')
    await expect(admin.getByTestId('learner-forbidden')).toBeVisible()
    await admin.getByRole('link', { name: 'Go to Admin Dashboard' }).click()
    await expect(admin.getByRole('heading', { name: 'Quản trị học liệu', exact: true })).toBeVisible()
  } finally { await context.close() }
})

test('B3 lesson chat is lesson scoped and persists across refresh', async ({ page }) => {
  await login(page, learnerEmail)
  await page.goto(`/lessons/${lessonA}`)
  await page.getByRole('button', { name: 'Open AI chat' }).click()
  await page.getByRole('button', { name: 'Start a conversation' }).click()
  await page.getByRole('textbox', { name: 'Message', exact: true }).fill('What does 你好 mean?')
  await page.getByRole('button', { name: 'Send', exact: true }).click()
  await expect(page.getByText('Hiện tại mình chưa có đủ nguồn đáng tin cậy để trả lời câu hỏi này.')).toBeVisible()
  await page.reload()
  await page.getByRole('button', { name: 'Open AI chat' }).click()
  await expect(page.getByText('What does 你好 mean?')).toBeVisible()
  await expect(page.getByText('Hiện tại mình chưa có đủ nguồn đáng tin cậy để trả lời câu hỏi này.')).toBeVisible()
})

test('B2 failed periodic attempt stays gated; retry passes and both results persist', async ({ page }) => {
  await login(page, learnerEmail)
  await page.goto(`/assessments/${periodic}`)
  await page.getByRole('button', { name: 'Start / Resume Assessment' }).click()
  await page.getByLabel('你好', { exact: true }).check()
  await page.getByRole('button', { name: 'Submit Assessment' }).click()
  await expect(page.getByText('Not passed', { exact: true })).toBeVisible()
  const failedPath = new URL(page.url()).pathname
  await page.goto('/hsk/2')
  await expect(page.getByLabel('Lesson locked')).toBeVisible()
  await page.goto(failedPath)
  await page.getByRole('link', { name: 'Retry', exact: true }).click()
  await page.getByRole('button', { name: 'Start / Resume Assessment' }).click()
  await page.getByLabel('再见', { exact: true }).check()
  await page.getByRole('button', { name: 'Submit Assessment' }).click()
  await expect(page.getByText('Passed', { exact: true })).toBeVisible()
  const passedPath = new URL(page.url()).pathname
  expect(passedPath).not.toBe(failedPath)
  await page.goto('/hsk/2')
  await expect(page.getByText('AVAILABLE', { exact: true })).toBeVisible()
  await page.goto(failedPath)
  await expect(page.getByText('Not passed', { exact: true })).toBeVisible()
  await page.goto(passedPath)
  await expect(page.getByText('Passed', { exact: true })).toBeVisible()
})

test('B4 draft visibility, publication and curriculum membership stay explicit', async ({ page, browser }) => {
  await login(page, adminEmail)
  const lesson = await createLesson(page, '840001', 'Lifecycle lesson')
  await expect(page.getByText('Trạng thái: Bản nháp', { exact: true })).toBeVisible()
  const context = await browser.newContext()
  try {
    const learner = await context.newPage()
    await login(learner, learnerEmail)
    expect((await learner.request.get(`${api}/lessons/${lesson}`)).status()).toBe(404)
    await page.getByRole('button', { name: 'Thông tin bài học', exact: true }).click()
    await page.getByLabel('Tiêu đề', { exact: true }).fill('Published lifecycle lesson')
    await expect(page.getByRole('button', { name: 'Xuất bản bài học', exact: true })).toBeDisabled()
    await page.getByRole('button', { name: 'Lưu thông tin', exact: true }).click()
    await page.getByRole('button', { name: 'Xuất bản bài học', exact: true }).click()
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

test('B5 AI draft defaults to 80 percent and needs review before publishing', async ({ page, browser }) => {
  await login(page, adminEmail)
  await page.goto('/admin/assessments?generate=1')
  await page.getByRole('combobox', { name: 'Bài học', exact: true }).selectOption(lessonA)
  await page.getByRole('combobox', { name: 'Độ khó', exact: true }).selectOption('EASY')
  await expect(page.getByLabel('Điểm đạt (%)', { exact: true })).toHaveValue('80')
  await page.getByRole('button', { name: 'Tạo bản nháp', exact: true }).click()
  await expect(page.getByText('Trạng thái: Bản nháp', { exact: true })).toBeVisible()
  const assessmentId = new URL(page.url()).pathname.split('/').at(-1)!
  const context = await browser.newContext()
  try {
    const learner = await context.newPage()
    await login(learner, learnerEmail)
    expect((await learner.request.get(`${api}/assessments/${assessmentId}`)).status()).toBe(404)
    await page.getByRole('button', { name: 'Gửi duyệt', exact: true }).click()
    await expect(page.getByText('Trạng thái: Chờ duyệt', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Xuất bản bài luyện tập', exact: true }).click()
    await expect(page.getByText('Trạng thái: Đã xuất bản', { exact: true })).toBeVisible()
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
    await expect(nav.getByRole('link')).toHaveText(['Tổng quan', 'Lộ trình', 'Bài học', 'Luyện tập', 'Tài liệu'])
    for (const link of await nav.getByRole('link').all()) { await link.focus(); await expect(link).toBeFocused() }
    for (const [path, title] of [
      ['/admin', 'Quản trị học liệu'], ['/admin/curriculum', 'Lộ trình HSK'],
      ['/admin/lessons', 'Bài học'], ['/admin/assessments', 'Luyện tập'],
      ['/admin/documents', 'Thư viện tài liệu'], ['/admin/stats', 'Thống kê'],
      [`/admin/lessons/${lessonA}`, 'Bài 1 · Step 8.1 Lesson A'],
    ]) {
      await page.goto(path)
      await expect(page.getByRole('heading', { name: title, level: 1, exact: true })).toBeVisible()
      if (path !== '/admin/stats') await expect(page.locator('.academy-header-art')).toBeVisible()
      await noOverflow(page)
      await expect(page.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
    }
    await page.goto('/admin/lessons')
    await expect(page.getByRole('complementary', { name: 'Xem nhanh nội dung' })).toBeVisible()
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
      ['/dashboard', 'Dashboard'], ['/pronunciation', 'Hành trình học'],
      ['/pronunciation/lesson', 'Bài học phát âm'], ['/hsk/1', 'HSK 1 Curriculum'],
      [`/lessons/${lessonA}`, 'Lesson 1: Step 8.1 Lesson A'], ['/history', 'History'],
      ['/profile', 'Profile'], ['/companions', 'Bo và những người bạn'],
      [`/assessments/${periodic}`, 'Step 8.1 Periodic Test'],
    ]) {
      await page.goto(path)
      await expect(page.getByRole('heading', { name: title, level: 1, exact: true })).toBeVisible()
      await noOverflow(page)
    }
    await page.goto(`/lessons/${lessonA}`)
    const opener = page.getByRole('button', { name: 'Open AI chat', exact: true })
    await opener.click()
    const dialog = page.getByRole('dialog', { name: 'AI Tutor Chat' })
    await expect(dialog.getByRole('button', { name: 'Close chat', exact: true })).toBeFocused()
    await noOverflow(page)
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(opener).toBeFocused()
  })

  test(`public auth forms remain keyboard accessible at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 })
    for (const [path, title] of [['/login', 'Login'], ['/register', 'Create an account'], ['/forgot-password', 'Forgot password']]) {
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
    await page.getByRole('button', { name: role === 'admin' ? 'Đăng xuất' : 'Logout', exact: true }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.locator(`main[data-layout="${role === 'admin' ? 'admin' : 'learner'}"]`)).toBeVisible()
    await page.unrouteAll()
    await page.getByRole('button', { name: role === 'admin' ? 'Thử đăng xuất lại' : 'Retry logout', exact: true }).click()
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
  await page.getByRole('button', { name: 'Xuất bản bài học', exact: true }).click()
  await page.getByRole('button', { name: 'Lưu trữ bài học', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Lưu trữ bài học', exact: true }).click()
  await expect(page.getByText('Trạng thái: Đã lưu trữ', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Tên', { exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Lưu nội dung', exact: true })).toHaveCount(0)
})

test('seven question types have learner previews and saved questions can be deleted explicitly', async ({ page }) => {
  await login(page, adminEmail)
  await page.goto('/admin/assessments')
  await page.getByRole('button', { name: 'Tạo bài luyện tập', exact: true }).click()
  const create = page.locator('form.admin-form-grid')
  await create.getByRole('combobox', { name: 'Bài học', exact: true }).selectOption(lessonA)
  await create.getByLabel('Tiêu đề', { exact: true }).fill('Question workshop')
  await expect(create.getByLabel('Điểm đạt (%)', { exact: true })).toHaveValue('80')
  await create.getByRole('button', { name: 'Tạo bài luyện tập', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Question workshop', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Thêm câu hỏi', exact: true }).click()
  const form = page.locator('.admin-assessment-question-form:visible')
  const preview = page.locator('.admin-editor-preview:visible')
  const prompt = form.getByRole('textbox', { name: 'Nội dung câu hỏi', exact: true })
  await prompt.fill('Chọn lời chào')
  for (const type of ['multiple_choice', 'fill_blank', 'matching', 'reorder_sentence', 'translate_vi_zh', 'translate_zh_vi', 'sentence_writing']) {
    await form.getByRole('combobox', { name: 'Dạng câu hỏi', exact: true }).selectOption(type)
    await expect(preview).toContainText('Chọn lời chào')
    await expect(preview.getByText('Đáp án đúng', { exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Gửi duyệt', exact: true })).toBeDisabled()
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
  await expect(page.getByRole('button', { name: 'Gửi duyệt', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: 'Xóa câu hỏi', exact: true }).click()
  await page.getByRole('dialog', { name: 'Xóa câu hỏi?' }).getByRole('button', { name: 'Xóa câu hỏi', exact: true }).click()
  await expect(page.getByText('Chưa có câu hỏi nào.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Gửi duyệt', exact: true })).toBeDisabled()
})

test('dashboard puts authoring first; reading preferences persist with accessible skip links', async ({ page }) => {
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
  await page.locator('.academy-reading-settings summary').click()
  await page.getByRole('button', { name: 'Rất lớn', exact: true }).click()
  await page.getByLabel('Hiện pinyin trong từ vựng').uncheck()
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-show-vocabulary-pinyin', 'false')
  expect(await page.locator('html').evaluate(element => element.style.getPropertyValue('--reader-font-size'))).toBe('23px')
  await noOverflow(page)
})

test('retired design prototypes stay outside the production application', async ({ page }) => {
  for (const path of ['/design-lab', '/design-lab/preview', '/journey-test.html']) {
    await page.goto(path)
    await expect(page.getByTestId('not-found')).toBeVisible()
  }
})
