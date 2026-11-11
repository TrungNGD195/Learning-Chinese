import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { chromium, request } from 'playwright'

// Real local API, isolated short-lived learner; no existing account is changed.
const api = await request.newContext({ baseURL: 'http://127.0.0.1:8001/api/v1/' })
const browser = await chromium.launch()
const email = `auth-transport-${randomUUID()}@example.com`
const password = `Smoke!${randomUUID()}`
let user
try {
  const registration = await api.post('auth/register', { data: { email, password, full_name: 'Local auth transport smoke' } })
  assert.equal(registration.status(), 201, 'Create isolated smoke learner')
  user = await registration.json()
  for (const host of process.env.AUTH_EXPECT_BLOCKED ? ['127.0.0.1'] : ['127.0.0.1', 'localhost']) {
    const context = await browser.newContext()
    const page = await context.newPage()
    const statuses = [], blockedReasons = []
    page.on('response', response => {
      const path = new URL(response.url()).pathname
      if (/\/auth\/(login|me|refresh)$/.test(path)) statuses.push({ path, status: response.status() })
    })
    const cdp = await context.newCDPSession(page)
    await cdp.send('Network.enable')
    cdp.on('Network.responseReceivedExtraInfo', event => {
      for (const cookie of event.blockedCookies ?? []) blockedReasons.push(...cookie.blockedReasons)
    })
    await page.goto(`http://${host}:5173/login`, { waitUntil: 'networkidle' })
    await page.locator('input[name=email]').fill(email)
    await page.locator('input[name=password]').fill(password)
    const login = page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/auth/login') && response.request().method() === 'POST')
    await page.locator('form button[type=submit]').click()
    assert.equal((await login).status(), 200, 'Credentials accepted by actual backend')
    if (process.env.AUTH_EXPECT_BLOCKED) {
      await page.waitForTimeout(1500)
      assert(new URL(page.url()).pathname === '/login')
      assert(statuses.some(item => item.path.endsWith('/auth/me') && item.status === 401))
      assert(blockedReasons.length, 'Browser explicitly blocks the cross-site cookies')
      console.log(JSON.stringify({ host, reproduced: true, statuses, blockedReasons }))
    } else {
      await page.waitForURL('**/dashboard', { timeout: 20000 })
      await page.locator('[data-layout=learner]').waitFor()
      const cookies = await context.cookies()
      assert(cookies.some(cookie => cookie.name === 'access_token' && cookie.httpOnly && cookie.domain === host))
      assert(cookies.some(cookie => cookie.name === 'refresh_token' && cookie.httpOnly && cookie.domain === host))
      await page.reload({ waitUntil: 'networkidle' })
      await page.locator('[data-layout=learner]').waitFor()
      assert.equal(new URL(page.url()).pathname, '/dashboard', 'Reload retains login')
      const me = await page.evaluate(async () => (await fetch('/api/v1/auth/me', { credentials: 'include' })).status)
      assert.equal(me, 200)
      await context.clearCookies({ name: 'access_token' })
      await page.reload({ waitUntil: 'networkidle' })
      await page.locator('[data-layout=learner]').waitFor()
      assert.equal(new URL(page.url()).pathname, '/dashboard', 'Refresh cookie restores session')
      assert((await context.cookies()).some(cookie => cookie.name === 'access_token'))
      await page.close()
      const reopened = await context.newPage()
      await reopened.goto(`http://${host}:5173/dashboard`, { waitUntil: 'networkidle' })
      await reopened.waitForURL('**/login')
      assert(!(await context.cookies()).some(cookie => ['access_token', 'refresh_token'].includes(cookie.name)))
      console.log(JSON.stringify({ host, login: 'pass', reload: 'pass', refresh: 'pass', newTabLogout: 'pass', blockedReasons }))
    }
    await context.close()
  }
} finally {
  await browser.close()
  await api.dispose()
  if (user) {
    // Both generated UUID and exact generated email must match before deletion.
    const cleanup = `import asyncio,sys\nfrom uuid import UUID\nfrom sqlalchemy import delete\nfrom app.database.session import SessionFactory\nfrom app.database.models import User\nasync def main():\n async with SessionFactory() as s:\n  result=await s.execute(delete(User).where(User.id==UUID(sys.argv[1]),User.email==sys.argv[2],User.full_name=='Local auth transport smoke'))\n  assert result.rowcount==1\n  await s.commit()\nasyncio.run(main())`
    execFileSync('docker', ['compose', '-f', 'compose.yaml', '-f', 'compose.app.yaml', 'exec', '-T', 'backend', 'python', '-c', cleanup, user.id, email], { cwd: '..', stdio: ['ignore', 'pipe', 'pipe'] })
    console.log('Temporary smoke learner removed.')
  }
}
