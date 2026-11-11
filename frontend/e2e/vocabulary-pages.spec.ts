import { expect, test } from '@playwright/test'

const api = 'http://127.0.0.1:8000/api/v1'
const lessonId = '0e63a248-4b5a-5c14-aad6-dadd22b8a91d'
const password = process.env.STEP81_TEST_PASSWORD
if (!password) throw new Error('The guarded E2E setup must provide a temporary test password')

test('vocabulary pages save only visited words and preserve theory gates across next, back and refresh', async ({ page, browser }) => {
  test.setTimeout(120_000)
  await page.goto('/login')
  await page.getByLabel('Email').fill('step81-admin@example.invalid')
  await page.getByLabel('Mật khẩu').fill(password!)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  await expect(page).toHaveURL(/\/admin$/)
  const existing = await (await page.request.get(`${api}/admin/lessons/${lessonId}/vocabulary`)).json()
  const nextOrder = Math.max(...existing.map(word => word.order_index)) + 1
  for (const [index, word] of [
    { hanzi: '不', pinyin: 'bù', vietnamese_meaning: 'không', part_of_speech: 'phó từ', example: '我不喝茶。Wǒ bù hē chá. Tôi không uống trà.', note: 'Trước thanh 4, 不 thường đọc thành bú.' },
    { hanzi: '一', pinyin: 'yī', vietnamese_meaning: 'một', part_of_speech: 'số từ', example: '我有一个朋友。Wǒ yǒu yí ge péngyou. Tôi có một người bạn.', note: null },
  ].entries()) {
    const response = await page.request.post(`${api}/admin/lessons/${lessonId}/vocabulary`, { data: { ...word, order_index: nextOrder + index } })
    expect(response.ok()).toBe(true)
  }
  const context = await browser.newContext({ viewport: { width: 390, height: 900 } })
  try {
    const student = await context.newPage()
    await student.goto('/login')
    await expect(student.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible()
    const registration = await student.request.post(`${api}/auth/register`, { data: { full_name: 'Word page learner', email: `word-pages-${Date.now()}@example.invalid`, password } })
    expect(registration.ok()).toBe(true)
    const phonetics = await (await student.request.get(`${api}/pronunciation/lesson`)).json()
    for (const section of phonetics.sections) {
      for (let step = 0; step < section.total_steps; step++) {
        const response = await student.request.post(`${api}/pronunciation/lesson/advance`, { data: { section_code: section.code, step_index: step } })
        expect(response.ok()).toBe(true)
      }
      expect((await student.request.post(`${api}/pronunciation/${section.id}/complete`)).ok()).toBe(true)
    }
    expect((await student.request.post(`${api}/pronunciation/lesson/complete`)).ok()).toBe(true)
    await student.goto(`/lessons/${lessonId}`)
    const readProgress = async () => (await student.request.get(`${api}/me/progress/lessons/${lessonId}`)).json()
    const words = (await (await student.request.get(`${api}/lessons/${lessonId}`)).json()).vocabulary.sort((a, b) => a.order_index - b.order_index)
    expect(words).toHaveLength(3)
    await expect(student.getByRole('heading', { name: '你好', exact: true })).toBeVisible()
    await expect(student.getByRole('button', { name: 'Quay lại', exact: true })).toBeDisabled()
    await expect(student.getByRole('button', { name: 'Tiếp theo', exact: true })).toBeEnabled()
    await expect.poll(async () => (await readProgress()).vocabulary.filter(row => row.viewed).length).toBe(1)
    await expect(student.getByRole('heading', { name: 'Ví dụ', exact: true })).toBeVisible()
    await expect(student.getByRole('button', { name: 'Xem chi tiết', exact: true })).toHaveCount(0)
    for (let index = 1; index < words.length; index++) {
      await student.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
      await student.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
      await expect(student).toHaveURL(new RegExp(`/vocabulary/${words[index].id}$`))
      await expect(student.getByRole('heading', { name: words[index].item.hanzi, exact: true })).toBeVisible()
      await expect.poll(async () => student.evaluate(() => {
        const heading = document.querySelector('.vocabulary-study-card__identity h2')!.getBoundingClientRect()
        const header = document.querySelector('.lesson-header')!.getBoundingClientRect()
        const menu = document.querySelector('.lesson-sequence-nav')!.getBoundingClientRect()
        return heading.top >= Math.max(header.bottom, menu.bottom) - 2 && heading.top < 600
      })).toBe(true)
      await expect.poll(async () => (await readProgress()).vocabulary.filter(row => row.viewed).length).toBe(index + 1)
      if (index === 1) await expect(student.getByRole('heading', { name: 'Lưu ý khi dùng', exact: true })).toBeVisible()
      else await expect(student.getByRole('heading', { name: 'Lưu ý khi dùng', exact: true })).toHaveCount(0)
    }
    await student.reload()
    await expect(student.getByRole('heading', { name: '一', exact: true })).toBeVisible()
    await student.getByRole('button', { name: 'Quay lại', exact: true }).click()
    await expect(student.getByRole('heading', { name: '不', exact: true })).toBeVisible()
    await student.goBack()
    await expect(student.getByRole('heading', { name: '一', exact: true })).toBeVisible()
    await student.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await expect(student).toHaveURL(new RegExp(`/lessons/${lessonId}/grammar$`))
    await expect(student.getByRole('heading', { name: /^Ngữ pháp/ })).toBeInViewport()
    await expect(student.locator('.vocabulary-study-card')).toHaveCount(0)
    await student.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    await expect(student.getByRole('button', { name: 'Mở luyện tập 1', exact: true })).toBeDisabled()
    expect((await readProgress()).theory_completed_at).toBeNull()
    await student.getByRole('link', { name: 'Ngữ pháp', exact: true }).click()
    await student.getByRole('button', { name: 'Xem chi tiết', exact: true }).click()
    await student.getByRole('link', { name: 'Bài khóa', exact: true }).click()
    for (const reading of (await (await student.request.get(`${api}/lessons/${lessonId}`)).json()).readings ?? []) {
      await student.getByRole('link', { name: 'Luyện tập', exact: true }).click()
      await expect(student.getByRole('button', { name: 'Mở luyện tập 1', exact: true })).toBeDisabled()
      await student.getByRole('link', { name: 'Bài khóa', exact: true }).click()
      await student.getByRole('button', { name: `Hoàn thành bài khóa: ${reading.title}`, exact: true }).click()
    }
    await student.getByRole('link', { name: 'Luyện tập', exact: true }).click()
    await expect(student.getByRole('link', { name: 'Mở luyện tập 1', exact: true })).toBeVisible()
    const sizes = await student.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }))
    expect(sizes.content).toBeLessThanOrEqual(sizes.viewport + 1)
  } finally { await context.close() }
})
