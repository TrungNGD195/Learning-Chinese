import assert from 'node:assert/strict'
import {mkdir,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import {chromium} from 'playwright'
import {installJourneyFixture} from './journey-fixture.mjs'

const folder=resolve('../.impeccable/review/spatial-great-wall/tower-entry-realism')
await mkdir(folder,{recursive:true})
const browser=await chromium.launch({args:['--enable-unsafe-swiftshader']})
const errors=[],unexpected=[],writes=[],checks=[],assets=[]
async function settle(page){await page.waitForTimeout(140);await page.waitForFunction(()=>!document.querySelector('.forward-viewport')?.dataset.cameraMoving,undefined,{timeout:60000});await page.waitForTimeout(360)}
async function ready(page,level){await page.locator(`.forward-viewport[data-level="${level}"][data-ready=true]`).waitFor({timeout:60000});await page.evaluate(()=>document.fonts.ready);await settle(page);await page.waitForFunction(()=>document.querySelector('.journey-cloud-transition').dataset.phase==='idle')}
const snapshot=page=>page.locator('.forward-viewport').evaluate(view=>({progress:Number(view.dataset.progress),distance:Number(view.dataset.worldDistance),eye:JSON.parse(view.dataset.worldPosition),avatar:{opacity:Number(view.querySelector('.bo-journey-avatar').style.opacity),filter:view.querySelector('.bo-journey-avatar').style.filter,facing:view.querySelector('.bo-journey-avatar').dataset.facing},graphics:JSON.parse(view.dataset.graphics)}))
async function capture(page,name,width){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:`${folder}/${name}-${width}.png`})}
async function milestone(page,level){await page.getByRole('button',{name:'Xem toàn bộ lộ trình',exact:true}).click();await page.getByRole('button',{name:`Đến tháp canh HSK ${level}`,exact:true}).click();await ready(page,level)}
async function enter(page,level,width){
  const before=await snapshot(page)
  await page.evaluate(()=>{
    window.entryTrace=[]
    window.entryObserver=new MutationObserver(()=>{const view=document.querySelector('.forward-viewport'),bo=view.querySelector('.bo-journey-avatar'),cloud=document.querySelector('.journey-cloud-transition');window.entryTrace.push({at:performance.now(),amount:Number(view.dataset.chapterEntry),opacity:Number(bo.style.opacity),filter:bo.style.filter,eye:JSON.parse(view.dataset.worldPosition),facing:bo.dataset.facing,cloud:cloud.dataset.phase})})
    window.entryObserver.observe(document.querySelector('.forward-viewport'),{attributes:true,attributeFilter:['data-chapter-entry']})
  })
  await page.getByRole('link',{name:`Đi đến HSK ${level+1}`,exact:true}).click()
  await page.waitForFunction(()=>Number(document.querySelector('.forward-viewport')?.dataset.chapterEntry)>.25)
  await capture(page,'chapter-departure-hsk'+level,width)
  await page.waitForFunction(()=>window.entryTrace.some(frame=>frame.opacity===0),undefined,{timeout:10000})
  const trace=await page.evaluate(()=>{window.entryObserver.disconnect();return window.entryTrace})
  const vanished=trace.find(frame=>frame.opacity===0)
  assert(trace.some(frame=>frame.amount>0&&frame.amount<1),'Bo visibly advances into the door before leaving the chapter')
  assert(trace.some(frame=>frame.opacity>0&&frame.opacity<1),'Bo fades at the dark threshold')
  assert(trace.every(frame=>frame.facing==='away'))
  assert(trace.every(frame=>Math.hypot(frame.eye.x-before.eye.x,frame.eye.y-before.eye.y,frame.eye.z-before.eye.z)<.001),'Camera holds the tower while Bo walks inside')
  assert.equal(vanished.cloud,'idle','Bo disappears before the clouds gather')
  await page.waitForURL(`**/hsk/${level+1}`,{timeout:20000});await ready(page,level+1)
  const after=await snapshot(page)
  assert.equal(after.progress,.5,'Portal arrives on the first lesson approach with clouds ahead and no old tower')
  assert.equal(after.avatar.opacity,1)
  assert.equal(after.avatar.facing,'away')
  assert.equal(after.avatar.filter,'brightness(1)')
  assert.equal(await page.locator('.journey-cloud-transition').textContent(),'')
  await capture(page,'first-lesson-hsk'+(level+1),width)
  return {before,trace,vanished,after}
}
try{
  for(const width of [1440,390]){
    const context=await browser.newContext({viewport:{width,height:920}});await installJourneyFixture(context,{unexpected,writes})
    const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));page.on('console',m=>{if(m.type()==='error'&&/THREE|Shader Error/.test(m.text()))errors.push(m.text())})
    page.on('response',response=>{if(response.url().includes('/realistic-v1/'))assets.push({path:new URL(response.url()).pathname,status:response.status()})})
    await page.goto('http://127.0.0.1:5173/hsk/1',{waitUntil:'domcontentloaded'});await ready(page,1)
    await capture(page,'realistic-walking-view',width)
    await milestone(page,1);await capture(page,'grounded-black-door-tower',width)
    if(width===1440){
      await page.getByRole('link',{name:'Đi đến HSK 2',exact:true}).click()
      await page.waitForFunction(()=>Number(document.querySelector('.forward-viewport')?.dataset.chapterEntry)>.1)
      await page.keyboard.press('Escape');await settle(page)
      const cancelled=await snapshot(page)
      assert.equal(new URL(page.url()).pathname,'/hsk/1');assert.equal(cancelled.progress,16);assert.equal(cancelled.avatar.opacity,1)
      assert.equal(await page.locator('.journey-cloud-transition').getAttribute('data-phase'),'idle')
    }
    const hsk2=await enter(page,1,width)
    let hsk3
    if(width===1440){await milestone(page,2);await capture(page,'grounded-tower-hsk2',width);hsk3=await enter(page,2,width)}
    checks.push({width,hsk2,hsk3});await context.close()
  }
  assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
  assert(assets.some(asset=>asset.path.endsWith('/masonry.webp')&&asset.status===200))
  assert(assets.some(asset=>asset.path.endsWith('/pines.webp')&&asset.status===200))
}finally{await browser.close();await writeFile(`${folder}/verification.json`,JSON.stringify({checks,assets,errors,unexpected,writes},null,2))}
console.log('PASS: grounded dark tower, Bo walks/disappears before cloud cover, Escape restores pose, first-lesson arrivals in HSK2/3, new realistic assets and desktop/mobile rendering.')
