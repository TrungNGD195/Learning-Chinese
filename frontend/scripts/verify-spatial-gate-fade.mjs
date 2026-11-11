import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'
import { installJourneyFixture } from './journey-fixture.mjs'

const folder = resolve('../.impeccable/review/spatial-great-wall/gate-fade')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] })
const errors = [], unexpected = [], writes = [], checks = []
async function settle(page) {
  await page.waitForTimeout(150)
  await page.waitForFunction(() => !document.querySelector('.forward-viewport')?.dataset.cameraMoving, undefined, { timeout: 60000 })
  await page.waitForTimeout(260)
}
async function move(page, value) {
  await page.evaluate(value => {
    const track = document.querySelector('.forward-track'), view = document.querySelector('.forward-viewport')
    const count = Number(view.dataset.pathCount), step = (track.offsetHeight - view.clientHeight) / (count - 1)
    const start = track.getBoundingClientRect().top + scrollY - parseFloat(getComputedStyle(view).top)
    scrollTo({ top: start + (count - 1 - value) * step, behavior: 'instant' })
  }, value)
  await page.waitForFunction(value => Math.abs(Number(document.querySelector('.forward-viewport').dataset.progress) - value) < .006, value, { timeout: 60000 })
  await settle(page)
}
async function gate(page, index) {
  return page.locator('.forward-gate').nth(index).evaluate(node => ({ hidden: node.hidden, opacity: Number(node.style.opacity), inert: node.inert, pointerEvents: getComputedStyle(node).pointerEvents }))
}
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 920 } })
    await installJourneyFixture(context, { unexpected, writes })
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('http://127.0.0.1:5173/hsk/1', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await page.locator('.forward-viewport[data-ready=true]').waitFor({ timeout: 60000 })
    await page.evaluate(() => document.fonts.ready)
    await settle(page)
    const samples = []
    for (const p of [0, .3, .4, .5]) {
      if(p===.5)await page.evaluate(()=>{
        window.crossingSamples=[]
        window.crossingObserver=new MutationObserver(()=>{
          const view=document.querySelector('.forward-viewport'),gate=document.querySelector('.forward-gate')
          window.crossingSamples.push({progress:Number(view.dataset.progress),opacity:Number(gate.style.opacity),hidden:gate.hidden})
        })
        window.crossingObserver.observe(document.querySelector('.forward-viewport'),{attributes:true,attributeFilter:['data-progress']})
      })
      await move(page, p)
      samples.push({ p, ...await gate(page, 0) })
      await page.screenshot({ path: `${folder}/approach-${p}-${width}.png` })
    }
    assert(!samples[0].hidden && samples[0].opacity > .98, 'Gateway remains readable at its normal stop')
    for(const sample of samples.slice(0,3))assert(!sample.hidden && sample.opacity === 1, 'Arch and plaque remain fully readable before Bo crosses')
    assert(samples[3].hidden, 'Passed gateway clears after one crossing tread')
    const crossing=await page.evaluate(()=>{window.crossingObserver.disconnect();return window.crossingSamples})
    assert(crossing.some(frame=>frame.progress>.4&&frame.opacity>0&&frame.opacity<1&&!frame.hidden),'Fade happens during the actual crossing step')
    await move(page, .3)
    const reversed = await gate(page, 0)
    assert(!reversed.hidden && Math.abs(reversed.opacity - samples[1].opacity) < .025, 'Reverse restores the distance-based fade')
    await move(page, 1)
    const next = await gate(page, 1)
    assert(!next.hidden && next.opacity > .98, 'The next gate keeps its own full opacity')
    const link = page.locator('.forward-gate').nth(1).locator('a')
    const destination = await link.getAttribute('href')
    await link.click()
    await page.waitForURL(url => url.pathname.startsWith(destination), { timeout: 30000 })
    await page.goto('http://127.0.0.1:5173/hsk/1',{waitUntil:'domcontentloaded'})
    await page.locator('.forward-viewport[data-ready=true]').waitFor({timeout:60000})
    await settle(page)
    await move(page,10)
    const historyBefore=await page.evaluate(()=>{
      window.returnSamples=[]
      window.returnObserver=new MutationObserver(()=>{
        const view=document.querySelector('.forward-viewport'),cloud=document.querySelector('.journey-cloud-transition'),bo=document.querySelector('.bo-journey-avatar')
        window.returnSamples.push({progress:Number(view.dataset.progress),phase:cloud.dataset.phase,coverage:Number(getComputedStyle(cloud,'::before').opacity),moving:!!view.dataset.cameraMoving,motion:bo.dataset.motion,facing:bo.dataset.facing})
      })
      window.returnObserver.observe(document.querySelector('.forward-viewport'),{attributes:true,attributeFilter:['data-progress']})
      return history.length
    })
    await page.getByRole('button',{name:'Về bài đang học',exact:true}).click()
    await page.waitForFunction(()=>Number(document.querySelector('.forward-viewport').dataset.progress)===7,undefined,{timeout:15000})
    await page.waitForFunction(()=>document.querySelector('.journey-cloud-transition').dataset.phase==='idle')
    await settle(page)
    const returned=await page.evaluate(()=>{window.returnObserver.disconnect();return{samples:window.returnSamples,history:history.length,path:location.pathname}})
    assert(returned.samples.length>0)
    assert(returned.samples.every(frame=>frame.progress===10||frame.progress===7),'Return has no visible backwards travel through intermediate positions')
    const jump=returned.samples.find(frame=>frame.progress===7)
    assert(jump.phase==='cover'&&jump.coverage>.98,'Cloud fully covers the scene before its position changes')
    assert(!jump.moving&&jump.motion==='idle'&&jump.facing==='away','Bo returns standing forward without stale backward walking')
    assert.equal(returned.history,historyBefore,'In-scene return adds no router history entry')
    assert.equal(returned.path,'/hsk/1')
    await page.screenshot({path:`${folder}/return-current-${width}.png`})
    checks.push({ width, samples, crossing, reversed, next, destination,returned })
    await context.close()
  }
  assert.deepEqual(errors, [])
  assert.deepEqual(unexpected, [])
  assert.deepEqual(writes, [])
} finally {
  await browser.close()
  await writeFile(`${folder}/verification.json`, JSON.stringify({ checks, errors, unexpected, writes }, null, 2))
}
console.log('PASS: gateway stays solid until crossing, fades during passage, reverses, opens lesson; return to current gate jumps only under full cloud cover at 1440px / 390px.')
