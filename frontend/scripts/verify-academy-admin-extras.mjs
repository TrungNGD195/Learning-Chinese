import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = 'http://127.0.0.1:5173', api = 'http://127.0.0.1:8001/api/v1'
const folder = resolve('../.impeccable/review/academy-visuals-vi/admin-extras')
await mkdir(folder, { recursive: true })
assert(process.env.ADMIN_STUDIO_REVIEW_TOKEN)
const browser = await chromium.launch({ executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true })
const errors = [], realMutations = [], captures = [], checks = []
async function context(width, height = 1000) {
  const c = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce' })
  await c.addCookies([{ name: 'access_token', value: process.env.ADMIN_STUDIO_REVIEW_TOKEN, url: origin, httpOnly: true, sameSite: 'Lax' }])
  await c.route('**/api/v1/**', (route) => ['GET', 'HEAD', 'OPTIONS'].includes(route.request().method()) ? route.continue() : route.abort('blockedbyclient'))
  return c
}
function watch(page, fixture = false) {
  page.on('pageerror', (e) => errors.push(e.message))
  if (!fixture) page.on('request', (r) => { if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(r.method())) realMutations.push(new URL(r.url()).pathname) })
}
async function json(c, path) { const r = await c.request.get(api + path); assert.equal(r.status(), 200, path); return r.json() }
async function capture(page, name) {
  await page.evaluate(async () => {
    await document.fonts.ready
    await Promise.all([...document.images].map((i) => i.decode()))
    const urls = new Set([...document.querySelectorAll('*')].flatMap((e) => [...getComputedStyle(e).backgroundImage.matchAll(/url\("?([^"\)]+)"?\)/g)].map((m) => m[1])))
    await Promise.all([...urls].map((src) => { const i = new Image(); i.src = src; return i.decode() }))
    scrollTo({ top: 0, behavior: 'instant' })
  })
  const metrics = await page.evaluate(() => ({ viewport: innerWidth, width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight }))
  assert(metrics.width <= metrics.viewport, `${name} horizontal overflow: ${metrics.width}`)
  await page.screenshot({ path: `${folder}/${name}.png`, fullPage: true })
  captures.push({ name, ...metrics })
}
async function load(page, path, selector) { await page.goto(origin + path); await page.locator('main[data-layout="admin"]').waitFor(); await page.locator(selector === '.ui-page-state' ? '.ui-page-state:has(h2)' : selector).first().waitFor() }
try {
 for (const width of [1440,390]) {
  const c=await context(width),page=await c.newPage();watch(page)
  for (const [name,path,selector] of [
   ['statistics','/admin/stats','.admin-stats-value'],
   ['create-lesson','/admin/lessons?create=1','.admin-form-grid'],
   ['ai-generation','/admin/assessments?generate=1','.admin-ai-generation-form']
  ]) {
   await load(page,path,selector);await capture(page,name+'-'+width)
   const visibleCopy=await page.locator('button:visible,label:visible,th:visible').allTextContents()
   const leftovers=visibleCopy.filter(text=>/\b(?:Lesson|Vocabulary|Grammar|Assessment|Draft|Published|Status|Title|Description|Save|Cancel|Delete|Upload|Loading|Retry|Previous|Next|Logout|metadata|Curriculum|Documents|Question|Options|Source|Processing|Review)\b/.test(text))
   assert.deepEqual(leftovers,[],name+' untranslated control copy')
  }
  await c.close()
 }
 assert.deepEqual(errors,[]);assert.deepEqual(realMutations,[])
 await writeFile(folder+'/verification.json',JSON.stringify({captures,errors,realMutations,checks:['Statistics, create lesson and AI generation forms at desktop/mobile; Vietnamese control copy; no API writes']},null,2))
 console.log(JSON.stringify({captures:captures.length,errors,realMutations}))
} finally {await browser.close()}
