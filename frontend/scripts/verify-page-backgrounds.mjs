import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium } from 'playwright'
import { installJourneyFixture } from './journey-fixture.mjs'

const origin = process.argv[2] || process.env.BO_FRONTEND_ORIGIN || 'http://localhost:5173'
const folder = '../.impeccable/review/page-backgrounds'
await mkdir(folder, { recursive: true })
const browser = await chromium.launch(), captures = [], errors = [], unexpected = [], writes = []
try {
  for (const width of [1440, 390]) {
    for (const role of ['student', 'admin', 'public']) {
      const context = await browser.newContext({ viewport: { width, height: 1000 }, reducedMotion: 'reduce' })
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-allow-headers': 'content-type' }
      await installJourneyFixture(context, { writes, unexpected, headers })
      if (role !== 'student') await context.route('**/api/v1/auth/me', route => route.fulfill({ headers, status: role === 'public' ? 401 : 200, json: role === 'public' ? { error: { code: 'AUTHENTICATION_REQUIRED', message: 'Fixture' } } : { id: 'admin', role: 'ADMIN', full_name: 'Nguyễn An', email: 'review@example.invalid' } }))
      if (role === 'public') await context.route('**/api/v1/auth/refresh', route => route.fulfill({ headers, status: 401, json: { error: { code: 'INVALID_REFRESH_TOKEN', message: 'Fixture' } } }))
      const page = await context.newPage()
      page.on('pageerror', error => errors.push(error.message))
      const paths = role === 'student' ? ['/pronunciation', '/hsk/1', '/pronunciation/lesson', '/lessons/lesson-1-1/readings', '/profile'] : role === 'admin' ? ['/admin/profile'] : ['/login', '/register']
      for (const path of paths) {
        await page.goto(origin + path)
        await page.locator('h1').first().waitFor()
        await page.waitForLoadState('networkidle')
        await page.evaluate(() => document.fonts.ready)
        const metrics = await page.evaluate(() => {
          const selectors = ['.bo-shell', '.academy-workspace', '.learning-curriculum', '.admin-main', '.public-shell']
          const canvases = selectors.flatMap(selector => [...document.querySelectorAll(selector)].map(node => ({ selector, background: getComputedStyle(node).backgroundImage })))
          return { canvases, width: innerWidth, scroll: document.documentElement.scrollWidth }
        })
        assert(metrics.canvases.length > 0, `${path}: missing page canvas`)
        for (const canvas of metrics.canvases) assert.equal(canvas.background, 'none', `${path}: scenery behind content in ${canvas.selector}`)
        assert(metrics.scroll <= metrics.width + 1, `${path}: horizontal overflow`)
        if (path === '/profile') assert.equal(await page.locator('.profile-page').evaluate(node => getComputedStyle(node, '::before').backgroundImage), 'none')
        const name = `${role}-${path.replaceAll('/', '-')}-${width}`
        await page.screenshot({ path: `${folder}/${name}.png`, fullPage: path === '/pronunciation' })
        captures.push({ path, role, width, ...metrics })
      }
      await context.close()
    }
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(unexpected, [])
  assert.deepEqual(writes, [])
  await writeFile(`${folder}/verification.json`, JSON.stringify({ captures, errors, unexpected, writes }, null, 2))
  console.log(JSON.stringify({ captures: captures.length, errors, unexpected, writes }))
} finally { await browser.close() }
