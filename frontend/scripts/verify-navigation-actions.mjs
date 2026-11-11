import assert from 'node:assert/strict'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const fixture = JSON.parse(await readFile('../tmp/hsk1-drafts-02-05-fixture.json', 'utf8'))
const bundle = Object.values(fixture.lessons).find(item => item.lesson.lesson_number === 2)
const origin = 'http://127.0.0.1:5173', folder = resolve('../.impeccable/review/navigation-actions')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch(), captures = [], errors = [], unexpected = []
const readyState = { sections: ['INITIALS', 'FINALS', 'TONES', 'SANDHI'].map((code, index) => ({ id: code, code, total_steps: [21, 36, 5, 12][index], completed_at: null })), current_section: 'INITIALS', step_index: 0, total_steps: 21, completed_at: null, can_finish: false }
const pageOf = items => ({ items, total: items.length, page: 1, page_size: 20 })
const periodic = { ...bundle.exercises.items[0], id: 'periodic', title: 'Kiểm tra tổng hợp HSK 1', type: 'PERIODIC_TEST', lesson_id: null }

try {
  for (const width of [1440, 390, 320]) {
    for (const role of [null, 'LEARNER', 'ADMIN']) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: 'reduce' })
      await context.route('**/api/v1/**', async route => {
        const request = route.request(), path = new URL(request.url()).pathname.split('/api/v1')[1]
        const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', 'access-control-allow-headers': 'content-type' }
        const reply = (json, status = 200) => route.fulfill({ json, status, headers })
        if (request.method() === 'OPTIONS' || path === '/auth/logout') return route.fulfill({ status: 204, headers })
        if (path === '/auth/refresh') return reply({ error: { code: 'INVALID_REFRESH_TOKEN', message: 'Fixture only' } }, 401)
        if (request.method() !== 'GET') { unexpected.push(`${request.method()} ${path}`); return reply({}, 405) }
        if (path === '/auth/me') return role ? reply({ id: 'fixture', role, full_name: 'Nguyễn An', email: 'fixture@example.invalid' }) : reply({ error: { code: 'AUTH_REQUIRED', message: 'Fixture only' } }, 401)
        if (path === '/pronunciation/lesson') return reply(readyState)
        if (path === '/hsk-levels') return reply(fixture.levels.map(level => ({ ...level, state: 'AVAILABLE' })))
        if (path === '/me/dashboard') return reply({ current_hsk: { id: bundle.lesson.hsk_level_id, level_number: 1, title: 'HSK 1' }, current_lesson: { ...bundle.lesson }, current_unit: null, progress_percentage: 0, continue_learning: { type: 'LESSON', lesson_id: bundle.lesson.id } })
        if (path === `/lessons/${bundle.lesson.id}`) return reply({ ...bundle.lesson, vocabulary: [], grammar: [], readings: [], assessment_ids: [] })
        if (path === `/me/progress/lessons/${bundle.lesson.id}`) return reply({ lesson_id: bundle.lesson.id, started_at: null, theory_completed_at: null, completed_at: null, vocabulary: [], grammar: [], readings: [] })
        if (path === '/admin/stats') return reply({ total_users: 8, users_by_current_hsk: [], average_exercise_score: null })
        if (path === '/admin/hsk-levels') return reply(fixture.levels)
        if (path === '/admin/lessons') return reply(pageOf([bundle.lesson]))
        if (path === '/admin/assessments') return reply(pageOf([periodic]))
        if (path === '/admin/assessments/periodic') return reply(periodic)
        if (path === '/admin/assessments/periodic/questions') return reply(bundle.questions[bundle.exercises.items[0].id])
        if (path === '/admin/documents') return reply(pageOf([]))
        if (path === `/admin/lessons/${bundle.lesson.id}`) return reply(bundle.lesson)
        for (const kind of ['vocabulary', 'grammar', 'readings']) if (path === `/admin/lessons/${bundle.lesson.id}/${kind}`) return reply(kind === 'readings' ? [] : bundle[kind])
        if (path.startsWith('/admin/hsk-levels/') && path.endsWith('/curriculum')) return reply(fixture.curriculum)
        unexpected.push(path); return reply({}, 404)
      })
      const page = await context.newPage()
      page.on('pageerror', error => errors.push(error.message))
      const routes = role === 'ADMIN' ? [
        ['/admin', '.admin-workbench-panel-footer', 'admin-home'],
        ['/admin/stats', '.admin-stats-grid', 'admin-stats'],
        ['/admin/assessments', '.admin-library', 'admin-tests'],
        [`/admin/lessons/${bundle.lesson.id}`, '.admin-lesson-hero', 'admin-editor'],
      ] : role === 'LEARNER' ? [
        ['/dashboard', '.academy-study-context', 'student-home'],
        ['/companions', '.academy-cast-main', 'companions'],
        ['/pronunciation/lesson', '.pronunciation-section-grid', 'pronunciation-overview'],
        ['/pronunciation/lesson/thanh-mau', '.pronunciation-session__symbol', 'pronunciation-part'],
        [`/lessons/${bundle.lesson.id}/grammar`, '.lesson-part-navigation', 'lesson-grammar'],
      ] : [
        ['/login', '.public-login-help-row', 'login'],
        ['/register', '.public-auth-links', 'register'],
        ['/forgot-password', '.public-auth-links', 'forgot-password'],
      ]
      for (const [path, selector, name] of routes.filter(route => !process.env.BO_REVIEW_PAGE || route[2] === process.env.BO_REVIEW_PAGE)) {
        await page.goto(origin + path)
        await page.locator(selector).first().waitFor()
        await page.evaluate(async () => {
          await document.fonts.ready
          await Promise.all([...document.images].map(image => image.decode().catch(() => {})))
          const assets = new Set([...document.querySelectorAll('*')].flatMap(node => [...getComputedStyle(node).backgroundImage.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(match => match[1])))
          await Promise.all([...assets].map(async src => { const image = new Image(); image.src = src; await image.decode() }))
        })
        const metrics = await page.evaluate(() => {
          const links = [...document.querySelectorAll('a')].filter(node => node.getClientRects().length && getComputedStyle(node).visibility !== 'hidden')
          return { viewport: innerWidth, scroll: document.documentElement.scrollWidth,
            underlined: links.filter(node => !node.matches('.public-login-help-row a[href="/forgot-password"]') && getComputedStyle(node).textDecorationLine.includes('underline')).map(node => ({ text: node.textContent.trim(), href: node.getAttribute('href') })),
            back: [...document.querySelectorAll('.lesson-header__back,.ui-page-header__context a,.admin-stats-detail-heading > a')].map(node => ({ height: node.getBoundingClientRect().height, border: getComputedStyle(node).borderTopWidth })) }
        })
        assert.deepEqual(metrics.underlined, [], `${name}: underlined navigation`)
        assert(metrics.scroll <= width + 1, `${name}: overflow`)
        for (const back of metrics.back) assert(back.height >= 44 && parseFloat(back.border) >= 1, `${name}: missing button surface`)
        if (name === 'login') {
          assert.equal(await page.getByText('Mừng bạn quay lại.', { exact: true }).count(), 0)
          const help = page.locator('.public-login-help-row a')
          assert.equal(await help.getAttribute('href'), '/forgot-password')
          const helpMetrics = await help.evaluate(node => ({ border: getComputedStyle(node).borderTopWidth, right: node.getBoundingClientRect().right, rowRight: node.parentElement.getBoundingClientRect().right, left: node.getBoundingClientRect().left, rowLeft: node.parentElement.getBoundingClientRect().left, direction: getComputedStyle(node.parentElement).flexDirection }))
          assert.equal(parseFloat(helpMetrics.border), 0)
          assert(Math.abs(helpMetrics.direction === 'column' ? helpMetrics.left - helpMetrics.rowLeft : helpMetrics.right - helpMetrics.rowRight) < 1)
          const password = await page.getByLabel('Mật khẩu', { exact: true }).boundingBox()
          const helpBox = await help.boundingBox()
          assert(helpBox.y + helpBox.height <= password.y, 'Password help must be above the input')
          assert(parseFloat(await page.locator('.public-login-register a').evaluate(node => getComputedStyle(node).borderTopWidth)) >= 1)
        }
        const back = page.locator('.lesson-header__back,.ui-page-header__context a,.admin-stats-detail-heading > a').first()
        if (await back.count()) {
          await back.hover()
          assert.equal(await back.evaluate(node => getComputedStyle(node).textDecorationLine), 'none')
          await back.focus()
          assert(parseFloat(await back.evaluate(node => getComputedStyle(node).outlineWidth)) >= 2)
        }
        await page.screenshot({ path: `${folder}/${name}-${width}.png`, fullPage: false, animations: 'disabled' })
        captures.push({ name, width, ...metrics })
        if (name === 'login') {
          await page.locator('.public-login-help-row a').click()
          await page.waitForURL('**/forgot-password')
          await page.locator('.public-auth-links').waitFor()
        }
      }
      await context.close()
    }
  }
  assert.deepEqual(errors, []); assert.deepEqual(unexpected, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/verification${process.env.BO_REVIEW_PAGE ? '-' + process.env.BO_REVIEW_PAGE : ''}.json`, JSON.stringify({ fixture: 'All APIs intercepted; no live account, content or progress writes', captures, errors, unexpected }, null, 2))
}
console.log(`PASS: ${captures.length} page/viewport checks; no underlined actions, button surfaces and focus verified.`)
