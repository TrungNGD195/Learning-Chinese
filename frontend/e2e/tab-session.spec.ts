import { expect, test } from '@playwright/test'

const password = process.env.STEP81_TEST_PASSWORD
if (!password) throw new Error('The guarded test setup must provide an ephemeral password')

for (const [role, email, landing] of [
  ['student', 'step81-learner@example.invalid', '/pronunciation'],
  ['admin', 'step81-admin@example.invalid', '/admin'],
] as const) {
  test(`${role}: reload and SPA navigation retain login, closing and reopening the tab clears login`, async ({ page, context }) => {
    await page.goto('/login')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Mật khẩu').fill(password)
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
    await expect(page).toHaveURL(new RegExp(landing + '$'))
    let logouts = 0
    page.on('request', request => { if (new URL(request.url()).pathname.endsWith('/auth/logout')) logouts++ })
    await page.reload()
    await expect(page).toHaveURL(new RegExp(landing + '$'))
    const protectedLayout = role === 'student' ? 'learner' : 'admin'
    await expect(page.locator(`[data-layout="${protectedLayout}"]`)).toBeVisible()
    expect(logouts).toBe(0)
    await page.getByRole('link', { name: role === 'student' ? 'Hồ sơ' : 'Bài học', exact: true }).first().click()
    await expect(page).toHaveURL(new RegExp(role === 'student' ? '/profile$' : '/admin/lessons$'))
    await expect(page.locator(`[data-layout="${protectedLayout}"]`)).toBeVisible()
    await context.clearCookies({ name: 'access_token' })
    await page.reload()
    await expect(page.locator(`[data-layout="${protectedLayout}"]`)).toBeVisible()
    expect(logouts).toBe(0)
    expect((await context.cookies()).some(cookie => cookie.name === 'refresh_token')).toBe(true)
    await page.close()
    const reopened = await context.newPage()
    await reopened.goto(landing)
    await expect(reopened).toHaveURL(/\/login$/)
    await expect(reopened.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible()
    expect((await context.cookies()).some(cookie => ['access_token', 'refresh_token'].includes(cookie.name))).toBe(false)
    await reopened.reload()
    await expect(reopened).toHaveURL(/\/login$/)
  })
}
