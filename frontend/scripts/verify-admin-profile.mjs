import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5173'
const folder = resolve('../.impeccable/review/admin-profile')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch(), captures = [], errors = [], unexpected = []
try {
  for (const width of (process.env.BO_REVIEW_WIDTHS || '1440,1024,390,320').split(',').map(Number)) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' })
    const user = { id: 'fixture-admin', full_name: 'Nguyễn An', email: 'admin@example.invalid', role: 'ADMIN' }
    let signedOut = false, logoutCalls = 0, passwordCalls = 0
    await context.route('**/api/v1/**', async route => {
      const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'content-type' }
      const reply = (json, status = 200) => route.fulfill({ json, status, headers })
      if (request.method() === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
      if (path === '/auth/me' && request.method() === 'GET') return signedOut ? reply({ error: { code: 'AUTHENTICATION_REQUIRED', message: 'Fixture' } }, 401) : reply(user)
      if (path === '/auth/me' && request.method() === 'PATCH') { assert.deepEqual(Object.keys(request.postDataJSON()), ['full_name']); user.full_name = request.postDataJSON().full_name; return reply(user) }
      if (path === '/auth/change-password') { passwordCalls++; return reply({ error: { code: 'INVALID_CURRENT_PASSWORD', message: 'Fixture only' } }, 400) }
      if (path === '/auth/logout-all') { logoutCalls++; signedOut = true; return route.fulfill({ status: 204, headers }) }
      if (path === '/auth/refresh') return reply({ error: { code: 'INVALID_REFRESH_TOKEN', message: 'Fixture' } }, 401)
      unexpected.push(path); return reply({}, 404)
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    async function capture(name) {
      await page.evaluate(async () => document.fonts.ready)
      const metrics = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth }))
      assert(metrics.scroll <= width + 1, `${name}: overflow at ${width}`)
      await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: false, animations: 'disabled' })
      captures.push({ name, width, ...metrics })
    }
    await page.goto(origin + '/admin/profile')
    await page.getByRole('heading', { name: 'Hồ sơ', exact: true }).waitFor()
    assert.equal(await page.getByRole('navigation', { name: 'Điều hướng quản trị' }).getByRole('link', { name: 'Hồ sơ', exact: true }).getAttribute('aria-current'), 'page')
    const corners = await page.locator('.admin-sidebar .primary-nav').evaluate(nav => {
      const read = node => { const style = getComputedStyle(node); return [style.borderTopLeftRadius, style.borderTopRightRadius, style.borderBottomRightRadius, style.borderBottomLeftRadius] }
      return { profile: read(nav.querySelector('a[href="/admin/profile"]')), reference: read(nav.querySelector('a[href="/admin/lessons"]')) }
    })
    assert.deepEqual(corners.profile, corners.reference, 'Profile corners must match the other navigation items')
    assert(corners.profile.every(value => parseFloat(value) > 0))
    assert.equal(await page.getByLabel('Email', { exact: true }).getAttribute('readonly'), '')
    const visibilityControls = page.locator('.admin-profile-password-input button')
    assert.equal(await visibilityControls.locator('svg').count(), 3)
    assert.deepEqual(await visibilityControls.allTextContents(), ['', '', ''])
    await capture('profile')
    await page.getByLabel('Họ và tên', { exact: true }).fill('Trần Bình')
    await page.getByRole('button', { name: 'Lưu thông tin', exact: true }).click()
    await page.getByText('Đã cập nhật thông tin tài khoản.', { exact: true }).waitFor()
    assert.equal(user.full_name, 'Trần Bình')
    await page.getByLabel('Mật khẩu hiện tại', { exact: true }).fill('old-password')
    await page.getByLabel('Mật khẩu mới', { exact: true }).fill('new-password')
    await page.getByLabel('Xác nhận mật khẩu mới', { exact: true }).fill('mismatched')
    await page.getByRole('button', { name: 'Đổi mật khẩu', exact: true }).click()
    await page.getByText('Mật khẩu xác nhận chưa khớp.', { exact: true }).waitFor()
    assert.equal(passwordCalls, 0)
    await page.getByLabel('Xác nhận mật khẩu mới', { exact: true }).fill('new-password')
    await page.getByRole('button', { name: 'Đổi mật khẩu', exact: true }).click()
    await page.getByText('Mật khẩu hiện tại chưa chính xác.', { exact: true }).waitFor()
    await page.getByRole('button', { name: 'Hiện mật khẩu hiện tại', exact: true }).click()
    assert.equal(await page.getByLabel('Mật khẩu hiện tại', { exact: true }).getAttribute('type'), 'text')
    await page.locator('#admin-password-title').scrollIntoViewIfNeeded()
    await capture('password-error')
    await page.getByRole('button', { name: 'Đăng xuất tất cả thiết bị', exact: true }).click()
    await page.getByRole('dialog').waitFor()
    assert.equal(logoutCalls, 0)
    await capture('logout-confirmation')
    await page.getByRole('button', { name: 'Hủy', exact: true }).click()
    assert.equal(logoutCalls, 0)
    await page.getByRole('button', { name: 'Đăng xuất tất cả thiết bị', exact: true }).click()
    await page.getByRole('button', { name: 'Đăng xuất tất cả', exact: true }).click()
    await page.waitForURL('**/login')
    assert.equal(logoutCalls, 1)
    await context.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/verification.json`, JSON.stringify({ fixture: 'All API requests intercepted; no real account/password/session edits', captures, errors, unexpected }, null, 2))
}
console.log(`PASS: ${captures.length} captures; profile, password errors, visibility and logout confirmation verified.`)
