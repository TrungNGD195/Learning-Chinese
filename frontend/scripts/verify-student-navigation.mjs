import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5174'
const folder = resolve('../.impeccable/review/student-sidebar')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ headless: true })
const captures = [], errors = [], unexpected = []
const time = '2026-11-04T10:00:00Z'
const levels = [1, 2, 3].map(n => ({ id: `hsk-${n}`, level_number: n, title: `HSK ${n}`, description: null, state: n === 1 ? 'AVAILABLE' : 'LOCKED' }))
const units = ['你好 · Xin chào', 'Gia đình và những người thân yêu', 'Một ngày của bạn', 'Thời gian và những cuộc hẹn', 'Hỏi đường trong thành phố', 'Ôn tập cuối chặng'].map((title, i) => ({
  id: `unit-${i}`, order_index: i + 1, unit_type: i === 5 ? 'PERIODIC_TEST' : 'LESSON', state: i === 0 ? 'COMPLETED' : i === 1 ? 'AVAILABLE' : 'LOCKED',
  lesson: i === 5 ? null : { id: `lesson-${i}`, title, lesson_number: i + 1, status: 'PUBLISHED' },
  assessment: i === 5 ? { id: 'assessment-1', title, type: 'PERIODIC_TEST', status: 'PUBLISHED' } : null,
}))

function install(context) {
  const state = { done: true, empty: false, fail: false, authenticated: true, failLogout: true, writes: [] }
  context.route('**/api/v1/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
    const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
    const reply = (json, status = 200) => route.fulfill({ json, status, headers })
    const failure = { error: { code: 'FIXTURE_FAILURE', message: 'Isolated review fixture', details: null } }
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers })
    if (!['GET', 'HEAD'].includes(request.method())) state.writes.push(path)
    if (path === '/auth/me') return state.authenticated ? reply({ id: 'student', email: 'student@example.invalid', full_name: 'Nguyễn Minh Anh', role: 'LEARNER' }) : reply(failure, 401)
    if (path === '/auth/refresh') return reply(failure, 401)
    if (path === '/auth/logout') { if (state.failLogout) return reply(failure, 503); state.authenticated = false; return route.fulfill({ status: 204, headers }) }
    if (path === '/hsk-levels') return reply(levels.map(level => ({ ...level, state: !state.done ? 'LOCKED' : level.state })))
    if (path === '/pronunciation/lesson') return reply({ sections: ['INITIALS', 'FINALS', 'TONES', 'SANDHI'].map((code, i) => ({ id: code, code, total_steps: [21, 36, 5, 12][i], completed_at: state.done ? time : null })), current_section: state.done ? null : 'INITIALS', step_index: 0, total_steps: state.done ? 0 : 21, completed_at: state.done ? time : null, can_finish: false })
    if (path === '/me/progress') return reply({ current_hsk: state.done ? 1 : null, progress_percentage: state.done ? 16.67 : 0, pronunciation_complete: state.done, hsk_levels: levels })
    if (/^\/me\/progress\/hsk\//.test(path) || /^\/hsk-levels\/[^/]+\/curriculum$/.test(path)) {
      if (state.fail) return reply(failure, 503)
      const n = Number(path.match(/hsk-(\d)/)?.[1] ?? 1)
      return reply({ hsk: levels[n - 1], progress_percentage: n === 1 && state.done ? 16.67 : 0, units: state.empty || n !== 1 ? [] : units.map(unit => ({ ...unit, state: state.done ? unit.state : 'LOCKED' })) })
    }
    unexpected.push({ path, method: request.method() })
    return reply(failure, 404)
  })
  return state
}

async function capture(page, name, width) {
  await page.evaluate(async () => {
    await document.fonts.ready
    const sources = new Set(Array.from(document.querySelectorAll('*')).flatMap(element => Array.from(getComputedStyle(element).backgroundImage.matchAll(/url\("?([^"\)]+)"?\)/g), match => match[1])))
    await Promise.all(Array.from(sources, async src => { const img = new Image(); img.src = src; await img.decode() }))
  })
  const metrics = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: innerWidth }))
  assert(metrics.width <= width + 1, `${name} horizontal overflow`)
  captures.push({ name, width, ...metrics })
  await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: true, animations: 'disabled' })
}

try {
  for (const width of [1440, 1024, 768, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
    const state = install(context), page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(origin + '/pronunciation')
    await page.locator('.hsk-level-block').last().waitFor()
    assert.equal(await page.getByRole('link', { name: 'Lịch sử', exact: true }).count(), 0)
    await capture(page, 'hsk-blocks', width)
    await page.locator('.hsk-level-block').first().scrollIntoViewIfNeeded()
    const block = await page.locator('.hsk-level-block').first().boundingBox()
    await page.mouse.click(block.x + block.width - 30, block.y + 35)
    await page.waitForURL('**/hsk/1')
    await page.locator('.curriculum-unit').last().waitFor()
    assert.equal(await page.locator('.curriculum-unit').count(), 6)
    assert.equal(await page.locator('.curriculum-unit[data-state="LOCKED"] a').count(), 0)
    await capture(page, 'lesson-blocks', width)
    if (width > 800) {
      const mainBefore = await page.locator('#main-content').evaluate(element => element.getBoundingClientRect().width)
      const collapse = page.getByRole('button', { name: 'Thu gọn thanh bên', exact: true })
      await collapse.focus(); await page.keyboard.press('Enter')
      const expand = page.getByRole('button', { name: 'Mở rộng thanh bên', exact: true })
      assert.equal(await expand.getAttribute('aria-expanded'), 'false')
      assert.equal(await expand.evaluate(element => element === document.activeElement), true)
      assert.equal(await page.locator('.academy-sidebar').evaluate(element => element.getBoundingClientRect().width), 80)
      assert(await page.locator('#main-content').evaluate(element => element.getBoundingClientRect().width) > mainBefore + 80)
      await capture(page, 'sidebar-collapsed', width)
      await page.getByRole('navigation', { name: 'Điều hướng học viên', exact: true }).getByRole('link', { name: 'Hành trình', exact: true }).click()
      await page.getByRole('link', { name: 'Mở HSK 1', exact: true }).click()
      await page.locator('.curriculum-unit').last().waitFor()
      assert.equal(await page.locator('.bo-shell').getAttribute('data-sidebar-collapsed'), 'true')
      // Desktop preference must not hide the labels or controls in the mobile drawer.
      await page.setViewportSize({ width: 390, height: 1000 })
      await page.getByRole('button', { name: 'Mở menu học viên' }).click()
      const drawer = page.getByRole('dialog', { name: 'Khu vực học viên' })
      assert(await drawer.getByRole('link', { name: 'Hành trình', exact: true }).locator('span').isVisible())
      assert.equal(await drawer.getByRole('button', { name: 'Thu gọn thanh bên', exact: true }).isVisible(), false)
      await page.keyboard.press('Escape')
      await page.setViewportSize({ width, height: 1000 })
      await page.waitForFunction(() => document.querySelector('.bo-shell')?.getAttribute('data-sidebar-collapsed') === 'true')
      assert.equal(await page.locator('.bo-shell').getAttribute('data-sidebar-collapsed'), 'true')
      await expand.click()
      assert.equal(await page.getByRole('button', { name: 'Thu gọn thanh bên' }).getAttribute('aria-expanded'), 'true')
      await capture(page, 'sidebar-restored', width)
      await page.getByRole('button', { name: 'Thu gọn thanh bên' }).click()
    }
    if (width <= 800) {
      const opener = page.getByRole('button', { name: 'Mở menu học viên', exact: true })
      await opener.click()
      const sidebar = page.getByRole('dialog', { name: 'Khu vực học viên' })
      assert.equal(await sidebar.getByRole('button', { name: 'Đóng menu', exact: true }).evaluate(element => element === document.activeElement), true)
      await capture(page, 'sidebar-open', width)
      await sidebar.getByRole('button', { name: "Đăng xuất", exact: true }).focus()
      await page.keyboard.press('Tab')
      assert.equal(await sidebar.getByRole('button', { name: 'Đóng menu', exact: true }).evaluate(element => element === document.activeElement), true)
      await page.keyboard.press('Escape')
      assert.equal(await opener.evaluate(element => element === document.activeElement), true)
      await opener.click()
    }
    assert.equal(await page.locator('.academy-topbar .logout-action').count(), 0)
    await page.locator('.academy-sidebar').getByRole('button', { name: "Đăng xuất", exact: true }).click()
    await page.getByRole('alert').waitFor()
    await capture(page, 'logout-error', width)
    state.failLogout = false
    await page.getByRole('button', { name: "Thử đăng xuất lại", exact: true }).click()
    await page.waitForURL('**/login')
    assert(state.writes.every(path => ['/auth/logout', '/auth/refresh'].includes(path)), 'No learner progress mutations permitted')
    await context.close()

    const lockedContext = await browser.newContext({ viewport: { width, height: 1000 } })
    const locked = install(lockedContext), lockedPage = await lockedContext.newPage()
    locked.done = false
    await lockedPage.goto(origin + '/pronunciation')
    await lockedPage.locator('.hsk-level-block').last().waitFor()
    assert.equal(await lockedPage.locator('.hsk-level-block a').count(), 0)
    await capture(lockedPage, 'hsk-locked', width)
    locked.empty = true
    await lockedPage.goto(origin + '/hsk/1')
    await lockedPage.locator('.curriculum-empty-state').waitFor()
    await capture(lockedPage, 'lessons-empty', width)
    locked.fail = true
    await lockedPage.reload()
    await lockedPage.getByRole('alert').waitFor()
    await capture(lockedPage, 'lessons-error', width)
    await lockedContext.close()
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(unexpected, [])
  await writeFile(folder + '/verification.json', JSON.stringify({ origin, captures, errors, unexpected, scope: 'Isolated fixtures; no real accounts, credentials, progress, or attempts used.' }, null, 2))
  console.log(JSON.stringify({ captures: captures.length, errors, unexpected }))
} finally { await browser.close() }
