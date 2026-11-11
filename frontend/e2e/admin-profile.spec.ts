import { expect, test } from '@playwright/test'

const api = 'http://127.0.0.1:8000/api/v1'
const email = 'step81-profile-admin@example.invalid'
const password = process.env.STEP81_TEST_PASSWORD
if (!password) throw new Error('Guarded E2E setup must supply a test password')

test('admin profile saves identity and revokes other sessions on password change and logout-all', async ({ page, browser }) => {
  test.setTimeout(120_000)
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password!)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  await expect(page).toHaveURL(/\/admin$/)
  const other = await browser.newContext()
  try {
    const secondLogin = await other.request.post(api + '/auth/login', { data: { email, password } })
    expect(secondLogin.ok()).toBe(true)
    await page.getByRole('navigation', { name: 'Điều hướng quản trị' }).getByRole('link', { name: 'Hồ sơ', exact: true }).click()
    await expect(page).toHaveURL(/\/admin\/profile$/)
    await expect(page.getByLabel('Email', { exact: true })).toHaveAttribute('readonly', '')
    await page.getByLabel('Họ và tên', { exact: true }).fill('Quản trị kiểm tra hồ sơ')
    await page.getByRole('button', { name: 'Lưu thông tin', exact: true }).click()
    await expect(page.getByText('Đã cập nhật thông tin tài khoản.', { exact: true })).toBeVisible()
    await page.reload()
    await expect(page.getByLabel('Họ và tên', { exact: true })).toHaveValue('Quản trị kiểm tra hồ sơ')
    await page.getByLabel('Mật khẩu hiện tại', { exact: true }).fill('incorrect-password')
    const newPassword = password! + '-changed'
    await page.getByLabel('Mật khẩu mới', { exact: true }).fill(newPassword)
    await page.getByLabel('Xác nhận mật khẩu mới', { exact: true }).fill(newPassword)
    await page.getByRole('button', { name: 'Đổi mật khẩu', exact: true }).click()
    await expect(page.getByText('Mật khẩu hiện tại chưa chính xác.', { exact: true })).toBeVisible()
    await page.getByLabel('Mật khẩu hiện tại', { exact: true }).fill(password!)
    await page.getByRole('button', { name: 'Đổi mật khẩu', exact: true }).click()
    await expect(page).toHaveURL(/\/login$/)
    expect((await other.request.get(api + '/auth/me')).status()).toBe(401)
    expect((await other.request.post(api + '/auth/refresh')).status()).toBe(401)
    expect((await other.request.post(api + '/auth/login', { data: { email, password } })).status()).toBe(401)
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Mật khẩu', { exact: true }).fill(newPassword)
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
    await expect(page).toHaveURL(/\/admin$/)
    expect((await other.request.post(api + '/auth/login', { data: { email, password: newPassword } })).ok()).toBe(true)
    await page.goto('/admin/profile')
    await page.getByRole('button', { name: 'Đăng xuất tất cả thiết bị', exact: true }).click()
    await page.getByRole('button', { name: 'Hủy', exact: true }).click()
    expect((await other.request.get(api + '/auth/me')).status()).toBe(200)
    await page.getByRole('button', { name: 'Đăng xuất tất cả thiết bị', exact: true }).click()
    await page.getByRole('button', { name: 'Đăng xuất tất cả', exact: true }).click()
    await expect(page).toHaveURL(/\/login$/)
    expect((await other.request.get(api + '/auth/me')).status()).toBe(401)
  } finally { await other.close() }
})
