import assert from 'node:assert/strict'
import {mkdir} from 'node:fs/promises'
import {chromium} from 'playwright'
import {installJourneyFixture} from './journey-fixture.mjs'

const origin=process.argv[2]??'http://localhost:5174'
const folder=new URL('../../.impeccable/review/hsk-selection/',import.meta.url)
await mkdir(folder,{recursive:true})
const browser=await chromium.launch()
try {
 for(const width of [1440,390]) {
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'})
  const writes=[],unexpected=[],errors=[]
  await installJourneyFixture(context,{writes,unexpected})
  const page=await context.newPage()
  page.on('pageerror',error=>errors.push(error.message))
  await page.goto(origin+'/dashboard')
  await page.locator('.lc-hsk-card').last().waitFor()
  assert.equal(await page.locator('.lc-hsk-card').count(),3)
  assert.equal(await page.locator('.lc-lesson-grid,a[href="/measure-words"]').count(),0)
  await page.evaluate(()=>document.fonts.ready)
  assert(await page.locator('.lc-hsk-art').first().evaluate(e=>e.getBoundingClientRect().height>150))
  await page.evaluate(()=>new Promise(resolve=>{const image=new Image();image.onload=resolve;image.src='/academy/curriculum-v2/covers.png'}))
  await page.screenshot({path:new URL(`selection-${width}.png`,folder).pathname.replace(/^\/(\w:)/,'$1'),fullPage:true})
  await page.getByRole('link',{name:'HSK 1',exact:true}).click()
  await page.locator('.lc-lesson-grid').waitFor()
  assert.equal(await page.locator('.lc-foundation-card').count(),1)
  assert.equal(await page.locator('.lc-lesson-grid > li').count(),15)
  await page.screenshot({path:new URL(`hsk1-${width}.png`,folder).pathname.replace(/^\/(\w:)/,'$1')})
  await page.locator('a.lc-inline-button[href="/pronunciation"]').click()
  await page.getByRole('link',{name:'HSK 2',exact:true}).click()
  await page.waitForFunction(()=>document.querySelectorAll('.lc-lesson-grid > li').length===10)
  assert.equal(await page.locator('.lc-foundation-card').count(),0)
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await page.goto(origin+'/measure-words')
  await page.locator('.lc-hsk-card').last().waitFor()
  assert.deepEqual({writes,unexpected,errors},{writes:[],unexpected:[],errors:[]})
  await context.close()
 }
 console.log('HSK selection verified at 1440px and 390px; no data writes or browser errors.')
} finally {await browser.close()}
