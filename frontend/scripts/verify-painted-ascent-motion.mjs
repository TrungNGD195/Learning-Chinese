import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'
import { installJourneyFixture } from './journey-fixture.mjs'

const folder=resolve('../.impeccable/review/continuous-painted-ascent')
await mkdir(folder,{recursive:true})
const browser=await chromium.launch()
const unexpected=[],writes=[],errors=[],results=[]
const origin=process.env.BO_FRONTEND_ORIGIN||'http://127.0.0.1:5173'
const settle=async page=>{
  await page.waitForTimeout(80)
  await page.waitForFunction(()=>!document.querySelector('.forward-viewport')?.dataset.cameraMoving&&document.querySelector('.bo-journey-avatar')?.dataset.motion==='idle',undefined,{timeout:30000})
  await page.waitForTimeout(180)
}
const sample=page=>page.evaluate(()=>{
  const view=document.querySelector('.forward-viewport'),canvas=view.querySelector('canvas'),ctx=canvas.getContext('2d')
  const pixels=(x,y)=>Array.from(ctx.getImageData(Math.round(canvas.width*x),Math.round(canvas.height*y),30,20).data)
  return {progress:Number(view.dataset.progress),foot:document.querySelector('.bo-journey-avatar').style.transform,ground:pixels(.4,.87),sky:pixels(.5,.12)}
})
const difference=(a,b)=>a.reduce((sum,value,i)=>sum+(i%4===3?0:Math.abs(value-b[i])),0)/(a.length*.75)
try {
  for(const width of [1440,390]) {
    const context=await browser.newContext({viewport:{width,height:920},recordVideo:{dir:`${folder}/video`,size:{width:width===1440?960:390,height:width===1440?614:920}}})
    await installJourneyFixture(context,{unexpected,writes})
    const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message))
    await page.goto(origin+'/hsk/1',{waitUntil:'domcontentloaded'})
    await page.locator('.forward-viewport[data-ready=true]').waitFor({timeout:30000})
    await page.evaluate(()=>document.fonts.ready)
    await page.locator('.forward-mountains').evaluate(img=>img.decode())
    await page.evaluate(async()=>Promise.all([...document.querySelectorAll('img[data-bo-preload]')].map(img=>img.decode())))
    await page.evaluate(()=>{
      const track=document.querySelector('.forward-track'),view=document.querySelector('.forward-viewport'),count=document.querySelectorAll('.forward-gate').length
      const step=(track.offsetHeight-view.clientHeight)/(count-1)
      const start=track.getBoundingClientRect().top+scrollY-parseFloat(getComputedStyle(view).top)
      scrollTo({top:start+(count-1-6.85)*step,behavior:'instant'})
    })
    await settle(page)
    const before=await sample(page)
    await page.screenshot({path:`${folder}/boundary-start-${width}.png`})
    await page.evaluate(()=>{
      window.__ascentFrames=[];window.__recordAscent=true;let previous=performance.now()
      const tick=time=>{
        const view=document.querySelector('.forward-viewport'),bo=document.querySelector('.bo-journey-avatar')
        window.__ascentFrames.push({dt:time-previous,progress:Number(view.dataset.progress),foot:bo.style.transform,frame:bo.dataset.frame,motion:bo.dataset.motion,facing:bo.dataset.facing})
        previous=time;if(window.__recordAscent)requestAnimationFrame(tick)
      };requestAnimationFrame(tick)
    })
    await page.mouse.move(width-18,410);await page.mouse.wheel(0,-140)
    await page.waitForFunction(start=>Number(document.querySelector('.forward-viewport').dataset.progress)>start+.04,before.progress)
    await page.screenshot({path:`${folder}/boundary-moving-${width}.png`})
    await settle(page)
    const after=await sample(page)
    await page.screenshot({path:`${folder}/boundary-end-${width}.png`})
    assert(before.progress<7&&after.progress>7,'Native wheel crosses a lesson boundary')
    const groundDifference=difference(before.ground,after.ground),skyDifference=difference(before.sky,after.sky)
    assert(groundDifference>4,'Rendered ground must visibly travel, not just Bo animation')
    assert(groundDifference>skyDifference*1.5,'Near ground optical flow dominates the distant scenery')
    await page.mouse.wheel(0,140)
    await page.waitForFunction(end=>Number(document.querySelector('.forward-viewport').dataset.progress)<end-.04,after.progress)
    await page.screenshot({path:`${folder}/reverse-moving-${width}.png`})
    await settle(page)
    const returned=await sample(page)
    await page.screenshot({path:`${folder}/reverse-end-${width}.png`})
    assert(Math.abs(returned.progress-before.progress)<.01,'Reverse wheel returns to the same world position')
    assert(difference(before.ground,returned.ground)<1,'Ground returns with Bo rather than playing a one-way background animation')
    await page.waitForTimeout(500)
    assert.equal(difference(returned.ground,(await sample(page)).ground),0,'Ground remains planted when scrolling stops')
    const frames=await page.evaluate(()=>{window.__recordAscent=false;return window.__ascentFrames})
    assert(new Set(frames.filter(f=>f.motion==='walking').map(f=>f.frame)).size>2,'Real gait poses change while travelling')
    assert(new Set(frames.map(f=>f.foot)).size>8,'Foot position follows the tread profile')
    assert(frames.some(f=>f.facing==='toward'),'Reverse travel changes Bo orientation')
    results.push({width,groundDifference,skyDifference,before:before.progress,after:after.progress,returned:returned.progress,frames,video:await page.video().path()})
    await context.close()
  }
  assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
} finally {
  await browser.close()
  await writeFile(`${folder}/motion-verification.json`,JSON.stringify({origin,results,errors,unexpected,writes},null,2))
}
console.log(`PASS: ${results.length} motion sequences; real ground flow, boundary continuity, reversal, planted idle and Bo gait. Videos are local diagnostics, not an FPS certification.`)
