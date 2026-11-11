import assert from 'node:assert/strict'
import {mkdir,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import {chromium} from 'playwright'
import {installJourneyFixture} from './journey-fixture.mjs'

const folder=resolve('../.impeccable/review/spatial-great-wall/final-gate-fix')
await mkdir(folder,{recursive:true})
const browser=await chromium.launch({args:['--enable-unsafe-swiftshader']})
const checks=[],errors=[],unexpected=[],writes=[]
async function settle(page){await page.waitForTimeout(140);await page.waitForFunction(()=>!document.querySelector('.forward-viewport')?.dataset.cameraMoving,undefined,{timeout:60000});await page.waitForTimeout(360)}
async function move(page,p){await page.evaluate(p=>{const track=document.querySelector('.forward-track'),view=document.querySelector('.forward-viewport'),count=Number(view.dataset.pathCount),step=(track.offsetHeight-view.clientHeight)/(count-1),start=track.getBoundingClientRect().top+scrollY-parseFloat(getComputedStyle(view).top);scrollTo({top:start+(count-1-p)*step,behavior:'instant'})},p);await page.waitForFunction(p=>Math.abs(Number(document.querySelector('.forward-viewport').dataset.progress)-p)<.0001,p,{timeout:60000});await settle(page)}
const snapshot=page=>page.locator('.forward-viewport').evaluate(view=>({progress:Number(view.dataset.progress),distance:Number(view.dataset.worldDistance),eye:JSON.parse(view.dataset.worldPosition),boHeight:parseFloat(view.querySelector('.bo-journey-avatar').style.height),gates:JSON.parse(view.dataset.gateStages)}))
async function capture(page,name,width){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:`${folder}/${name}-${width}.png`})}
try{
  for(const width of [1440,390]){
    const context=await browser.newContext({viewport:{width,height:920}});await installJourneyFixture(context,{unexpected,writes})
    const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message))
    await page.goto('http://127.0.0.1:5173/hsk/1',{waitUntil:'domcontentloaded'})
    await page.locator('.forward-viewport[data-ready=true]').waitFor({timeout:60000});await page.evaluate(()=>document.fonts.ready);await settle(page)
    await move(page,14);const previous=await snapshot(page);await capture(page,'gate-14',width)
    await move(page,15);const last=await snapshot(page);await capture(page,'gate-15',width)
    assert(Math.abs(last.boHeight/previous.boHeight-1)<.04,'Lesson 15 keeps the same guide/camera scale as lesson 14')
    assert.equal(last.gates[15].opacity,1)
    await move(page,15.4);const crossing=await snapshot(page);await capture(page,'gate-15-before-passage',width)
    assert(crossing.boHeight/previous.boHeight>.94,'No zoom-out while still approaching the last gate')
    assert.equal(crossing.gates[15].opacity,1)
    await move(page,16);const tower=await snapshot(page);await capture(page,'single-arch-watchtower',width)
    await page.evaluate(()=>{
      window.textSamples=[]
      window.textTimer=setInterval(()=>{const cloud=document.querySelector('.journey-cloud-transition');window.textSamples.push({phase:cloud.dataset.phase,text:cloud.textContent,hasStatus:!!cloud.querySelector('p,[role="status"]')})},40)
    })
    await page.getByRole('button',{name:'Về bài đang học',exact:true}).click()
    await page.waitForFunction(()=>document.querySelector('.journey-cloud-transition').dataset.phase==='cover')
    await page.waitForTimeout(320);await capture(page,'cloud-without-text',width)
    await page.waitForFunction(()=>document.querySelector('.journey-cloud-transition').dataset.phase==='idle')
    const cloud=await page.evaluate(()=>{clearInterval(window.textTimer);return window.textSamples})
    assert(cloud.some(sample=>sample.phase==='cover')&&cloud.some(sample=>sample.phase==='reveal'))
    assert(cloud.every(sample=>sample.text===''&&!sample.hasStatus),'The cloud overlay contains no text at any transition phase')
    assert.equal(new URL(page.url()).pathname,'/hsk/1')
    checks.push({width,previous,last,crossing,tower,cloud});await context.close()
  }
  assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
}finally{await browser.close();await writeFile(`${folder}/verification.json`,JSON.stringify({checks,errors,unexpected,writes},null,2))}
console.log('PASS: normal last-gate scale, no premature camera pullback, single-arch tower and text-free cloud transition at desktop/mobile sizes.')
