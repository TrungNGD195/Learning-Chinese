import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = 'http://127.0.0.1:5173'
const baseline = process.env.BO_CAPTURE_BASELINE === '1'
const folder = resolve('../.impeccable/review/pronunciation-workspace')
const codes = ['INITIALS', 'FINALS', 'TONES', 'SANDHI'], totals = [21, 36, 5, 12]
const time = '2026-11-07T10:00:00Z'
await mkdir(folder, { recursive: true })
const browser = await chromium.launch()
const captures = [], errors = [], unexpected = []
try {
  for (const width of (baseline ? [1440, 390] : [1440, 768, 390, 320])) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' })
    const state = { current: 0, step: 0, fail: false, advances: 0 }
    const payload = () => ({ sections: codes.map((code, index) => ({ id: code, code, total_steps: totals[index], completed_at: index < state.current ? time : null })), current_section: codes[state.current] ?? null, step_index: state.step, total_steps: totals[state.current] ?? 0, completed_at: null, can_finish: state.current === 4 })
    await context.route('**/api/v1/**', async route => {
      const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'content-type' }
      const reply = (json, status = 200) => route.fulfill({ json, status, headers })
      if (request.method() === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
      if (path === '/auth/me') return reply({ id: 'fixture', role: 'LEARNER', full_name: 'Nguyễn An', email: 'fixture@example.invalid' })
      if (path === '/pronunciation/lesson') return reply(payload())
      if (path === '/pronunciation/lesson/advance') {
        state.advances++
        assert.deepEqual(request.postDataJSON(), { section_code: codes[state.current], step_index: state.step })
        if (state.fail) return reply({ error: { code: 'FIXTURE_FAILURE', message: 'Fixture only' } }, 503)
        state.step++; return reply(payload())
      }
      if (/^\/pronunciation\/[A-Z]+\/complete$/.test(path)) { state.current++; state.step = 0; return reply({ completed_at: time }) }
      unexpected.push(path); return reply({}, 404)
    })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    async function capture(name) {
      await page.evaluate(async () => {
        await document.fonts.ready
        await Promise.all([...document.images].map(image => image.decode().catch(() => {})))
        const assets = new Set([...document.querySelectorAll('*')].flatMap(node => [...getComputedStyle(node).backgroundImage.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(match => match[1])))
        await Promise.all([...assets].map(async src => { const image = new Image(); image.src = src; await image.decode() }))
      })
      const metrics = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth, header: document.querySelector('.lesson-header')?.getBoundingClientRect().height }))
      assert(metrics.scroll <= width + 1, `${name}: overflow`)
      if (!baseline) assert(metrics.header < 130, `${name}: header too tall`)
      if (!baseline && width <= 800 && await page.locator('.pronunciation-session__navigation').count()) {
        const footer = await page.locator('.pronunciation-session__navigation').boundingBox()
        assert(footer.x >= 10 && footer.x + footer.width <= width - 10, `${name}: footer outside viewport`)
      }
      await page.screenshot({ path: `${folder}/${baseline ? 'before-' : ''}${name}-${width}.png`, fullPage: false, animations: 'disabled' })
      captures.push({ name, width, ...metrics })
    }
    await page.goto(origin + '/pronunciation/lesson/thanh-mau')
    await page.locator('.pronunciation-session__symbol').filter({ hasText: /^b$/ }).waitFor()
    await capture('initials')
    if (baseline) { await context.close(); continue }
    assert.equal(await page.locator('.pronunciation-sections-nav [aria-disabled="true"]').count(), 3)
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.locator('.pronunciation-session__symbol').filter({ hasText: /^p$/ }).waitFor()
    const position = await page.locator('.pronunciation-session__symbol').evaluate(node => node.getBoundingClientRect().top)
    assert(position > 0 && position < 650, `New sound outside main viewport: ${position}`)
    await page.getByRole('button', { name: 'Quay lại', exact: true }).click()
    await page.locator('.pronunciation-session__symbol').filter({ hasText: /^b$/ }).waitFor()
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    assert.equal(state.advances, 1, 'Reviewing a saved sound must not write progress')
    state.fail = true
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.getByRole('alert').waitFor()
    await capture('save-error')
    state.fail = false
    await page.getByRole('button', { name: 'Tiếp theo', exact: true }).click()
    await page.locator('.pronunciation-session__symbol').filter({ hasText: /^m$/ }).waitFor()
    state.current = 1; state.step = 0
    await page.goto(origin + '/pronunciation/lesson/van-mau')
    await page.locator('.pronunciation-session__symbol').filter({ hasText: /^a$/ }).waitFor()
    await capture('finals')
    state.current = 2; state.step = 0
    await page.goto(origin + '/pronunciation/lesson/thanh-dieu')
    await page.locator('.academy-tone-diagram').waitFor()
    await capture('tones')
    state.current = 3; state.step = 0
    await page.goto(origin + '/pronunciation/lesson/bien-dieu')
    await page.locator('.sandhi-example').waitFor()
    await capture('sandhi')
    state.current = 0; state.step = 0
    await page.goto(origin + '/pronunciation/lesson/van-mau')
    await page.getByRole('heading', { name: 'Phần học này chưa mở' }).waitFor()
    assert.equal(await page.getByRole('button', { name: 'Tiếp theo', exact: true }).count(), 0)
    state.step = 21
    await page.goto(origin + '/pronunciation/lesson/thanh-mau')
    await page.getByRole('button', { name: 'Hoàn thành thanh mẫu', exact: true }).waitFor()
    await capture('section-finish')
    await page.getByRole('button', { name: 'Hoàn thành thanh mẫu', exact: true }).click()
    await page.waitForURL('**/pronunciation/lesson')
    await page.getByRole('link', { name: 'Học vận mẫu', exact: true }).waitFor()
    await capture('overview')
    await context.close()
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/${baseline ? 'before-' : ''}verification.json`, JSON.stringify({ fixture: 'All API requests intercepted; no live progress writes', captures, errors, unexpected }, null, 2))
}
console.log(`PASS: ${captures.length} captures; pronunciation layout and navigation verified.`)
