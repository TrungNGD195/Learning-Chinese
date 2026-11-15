import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const origin=process.argv[2]??'http://127.0.0.1:5173'
const folder=new URL('../../.impeccable/review/culture/',import.meta.url)
await mkdir(folder,{recursive:true})
const browser=await chromium.launch()
try {
 for (const width of [1440,390]) {
  const height=width===390?740:900
  const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce'})
  const page=await context.newPage(),errors=[],apiCalls=[]
  page.on('pageerror',error=>errors.push(error.message))
  await page.route('**/api/**',route=>{apiCalls.push(route.request().url());return route.abort()})
  await page.goto(origin+'/culture-preview.html')
  await page.getByRole('button',{name:'Block từ vựng',exact:true}).click()
  await page.getByRole('heading',{name:'饺子',exact:true}).waitFor()
  await page.evaluate(()=>document.fonts.ready)
  await page.evaluate(()=>Promise.all([...new Set([...document.querySelectorAll('.academy-word-illustration,.academy-companion,.lc-painted-cover')].map(e=>getComputedStyle(e).backgroundImage).filter(s=>s.startsWith('url(')))].map(s=>new Promise(resolve=>{const image=new Image();image.onload=resolve;image.onerror=resolve;image.src=s.slice(5,-2)}))))
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await page.screenshot({path:fileURLToPath(new URL(`vocabulary-${width}.png`,folder)),fullPage:true})
  const trigger=page.getByRole('button',{name:'Khám phá thêm',exact:true})
  const initialTrigger=await trigger.boundingBox()
  assert(await page.evaluate(()=>window.scrollY===0))
  assert(initialTrigger.y>=0&&initialTrigger.y+initialTrigger.height<height,'Discovery must be visible without scrolling')
  await trigger.click()
  const popup=page.getByRole('dialog')
  await popup.waitFor()
  const bounds=await popup.boundingBox()
  assert(bounds.width<width-20)
  assert(bounds.height<height-20)
  assert(Math.abs(bounds.x+bounds.width/2-width/2)<2)
  assert(Math.abs(bounds.y+bounds.height/2-height/2)<2)
  assert.equal(await popup.getByRole('button').count(),2)
  await page.screenshot({path:fileURLToPath(new URL(`culture-${width}.png`,folder))})
  await page.keyboard.press('Escape')
  assert.equal(await page.getByRole('dialog').count(),0)
  assert(await trigger.evaluate(e=>document.activeElement===e))
  await trigger.click()
  await page.locator('.cp-sources summary').click()
  assert(await page.locator('.cp-sources a').isVisible())
  await page.getByRole('button',{name:'Quay lại từ đang học',exact:true}).click()
  await page.getByRole('button',{name:'Cấu trúc bài học',exact:true}).click()
  assert.equal(await page.getByRole('button',{name:'Khám phá thêm',exact:true}).count(),0)
  await page.evaluate(()=>window.scrollTo(0,0))
  await page.screenshot({path:fileURLToPath(new URL(`lesson-${width}.png`,folder)),fullPage:true})
  assert.equal(await page.locator('.cp-discovery,.cp-story,.cp-culture-check').count(),0)
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  assert.deepEqual({errors,apiCalls},{errors:[],apiCalls:[]})
  await context.close()
 }
 console.log('Culture preview verified at 1440px and 390px: optional vocabulary button, compact centered popup, no quiz, no discovery in readings, focus restoration, source toggle, no API calls or browser errors.')
} finally {await browser.close()}
