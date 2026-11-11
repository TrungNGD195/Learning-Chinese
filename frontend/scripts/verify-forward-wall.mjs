import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'
import { installJourneyFixture } from './journey-fixture.mjs'

const origin=process.env.BO_FRONTEND_ORIGIN||'http://127.0.0.1:5173'
const folder=resolve('../.impeccable/review',process.env.BO_REVIEW_NAME||'third-person-great-wall')
await mkdir(folder,{recursive:true})
const browser=await chromium.launch({args:['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader']})
const captures=[],errors=[],unexpected=[],writes=[],motion=[]
async function settle(page) {
  await page.waitForTimeout(100)
  await page.waitForFunction(()=>!document.querySelector('.forward-viewport')?.dataset.cameraMoving&&(!document.querySelector('.bo-journey-avatar')||document.querySelector('.bo-journey-avatar').dataset.motion==='idle'),undefined,{timeout:30000})
  // The idle dataset flips before the 110ms sprite opacity crossfade completes.
  await page.waitForTimeout(180)
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
}
async function ready(page) {
  const level=new URL(page.url()).pathname.match(/^\/hsk\/(\d)/)?.[1]
  if(level)await page.locator(`.wall-chapters a[aria-current="page"][href="/hsk/${level}"]`).waitFor()
  await page.locator(`.forward-viewport${level?`[data-level="${level}"]`:''}[data-ready=true]`).waitFor({timeout:30000})
  await page.evaluate(()=>document.fonts.ready)
  await page.locator('.forward-mountains').evaluate(img=>img.decode())
  await page.evaluate(async()=>Promise.all([...document.querySelectorAll('img[data-bo-preload]')].map(img=>img.decode())))
  await page.waitForFunction(()=>performance.getEntriesByType('resource').some(entry=>entry.name.endsWith('/academy/great-wall/painted-v2/gate.webp')&&entry.responseEnd>0))
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
  await settle(page)
  await page.waitForFunction(()=>!document.querySelector('.journey-cloud-transition')||document.querySelector('.journey-cloud-transition').dataset.phase==='idle')
}
async function capture(page,name,width) {
  const data=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,progress:document.querySelector('.forward-viewport')?.dataset.progress,elevation:document.querySelector('.forward-viewport')?.dataset.elevation,heading:document.querySelector('.forward-viewport')?.dataset.heading,scene:document.querySelector('.forward-viewport')?.dataset.scene,visible:document.querySelectorAll('.forward-gate:not([hidden])').length}))
  assert(data.scrollWidth<=width+1,'No horizontal page overflow')
  await page.screenshot({path:`${folder}/${name}-${width}.png`,fullPage:false})
  captures.push({name,...data})
}
async function selectGate(page,index) {
  // Native scroll for the gate census: keep one graphics context alive instead
  // of compiling a new scene for every gate. Overview locate is checked below.
  await page.evaluate(index=>{
    const track=document.querySelector('.forward-track'), view=document.querySelector('.forward-viewport')
    const count=document.querySelectorAll('.forward-gate').length
    const step=(track.offsetHeight-view.clientHeight)/(count-1)
    const start=track.getBoundingClientRect().top+scrollY-parseFloat(getComputedStyle(view).top)
    scrollTo({top:start+(count-1-index)*step,behavior:'instant'})
  },index)
  await ready(page)
}
try {
 for(const width of (process.env.BO_VERIFY_EXTRAS_ONLY?[]:process.env.BO_VERIFY_WIDTHS?process.env.BO_VERIFY_WIDTHS.split(',').map(Number):process.env.BO_VISUAL_ONLY?[1440,390]:[1440,1024,390,320])) {
  const context=await browser.newContext({viewport:{width,height:920},reducedMotion:'no-preference'})
  context.setDefaultNavigationTimeout(60000)
  const state=await installJourneyFixture(context,{unexpected,writes})
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message))
  page.on('console',message=>{if(message.type()==='error'&&/THREE\.|Shader Error/.test(message.text()))errors.push(message.text())})
  await page.goto(origin+'/hsk/1',{waitUntil:'domcontentloaded'});await ready(page)
  assert.equal(await page.locator('.forward-gate').count(),16)
  await capture(page,'current',width)
  if(process.env.BO_VERIFY_STAGES_ONLY) {
    for(const [name,phase] of [['climb',.36],['bend',.70]]) {
      await selectGate(page,7+phase)
      assert.equal(await page.locator('.forward-viewport').getAttribute('data-scene'),name)
      await capture(page,name,width)
    }
    await selectGate(page,15);await capture(page,'summit',width)
    if(width===1440) for(const level of [2,3]) {
      await page.getByRole('link',{name:`Mở HSK ${level}`}).click();await page.waitForURL(`**/hsk/${level}`);await ready(page)
      await selectGate(page,level===2?9:14);await capture(page,`hsk${level}-summit`,width)
    }
    await context.close();continue
  }
  if(process.env.BO_VISUAL_ONLY) {await selectGate(page,2);await capture(page,'foothills',width);await context.close();continue}
  await page.getByRole('button',{name:'Xem toàn bộ lộ trình',exact:true}).click()
  await page.locator('.forward-overview > li').nth(0).getByRole('button',{name:/Định vị/}).click()
  await ready(page)
  for(let i=0;i<16;i++) {
    console.log(`Check gate ${i} at ${width}px`)
    await selectGate(page,i)
    const target=page.locator('.forward-gate').nth(i)
    assert(await target.isVisible(),`Gate ${i} should be visible`)
    const box=await target.boundingBox()
    assert(box.x>=0&&box.x+box.width<=width,`Gate ${i} should fit horizontally`)
    const actor=await page.locator('.bo-journey-avatar').boundingBox()
    assert(actor.x>=0&&actor.x+actor.width<=width,`Bo stays fully in frame at gate ${i}`)
    // Browser scroll coordinates round to CSS pixels. Allow at most one pixel
    // of the measured scroll step, rather than an impossible subpixel landing.
    const landingPrecision=await page.evaluate(()=>{
      const track=document.querySelector('.forward-track'),view=document.querySelector('.forward-viewport')
      return 9/((track.offsetHeight-view.clientHeight)/(document.querySelectorAll('.forward-gate').length-1))+.001
    })
    assert(Math.abs(Number(await page.locator('.forward-viewport').getAttribute('data-elevation'))-i*9)<landingPrecision,`Gate ${i} must be on its own level landing`)
    if(i===0||i===15)await capture(page,i===0?'foundation':'summit',width)
    if(i===15) {
      const continuation=page.locator('.painted-next-chapter')
      assert.equal(await continuation.getAttribute('href'),'/hsk/2','The road continues to the existing next HSK')
      if(width===1440||width===390) {
        await continuation.click();await page.waitForURL('**/hsk/2');await ready(page)
        await capture(page,'next-hsk',width)
        await page.goBack({waitUntil:'domcontentloaded'});await ready(page)
        assert(Math.abs(Number(await page.locator('.forward-viewport').getAttribute('data-progress'))-15)<.02,'Chapter return restores the final lesson')
      }
    }
  }
  if(width===1440||width===390) {
    await selectGate(page,7.36)
    assert.equal(await page.locator('.forward-viewport').getAttribute('data-scene'),'climb')
    await capture(page,'climb',width)
    const actor=await page.locator('.bo-journey-avatar').boundingBox()
    assert(actor.x>=0&&actor.x+actor.width<=width,'Bo stays fully in frame while climbing')
    await selectGate(page,7.75)
    assert.equal(await page.locator('.forward-gate').nth(7).isVisible(),false,'A gateway behind Bo and its plaque leave the camera view together')
    const climbElevation=Number(await page.locator('.forward-viewport').getAttribute('data-elevation'))
    assert(climbElevation>63&&climbElevation<72,'Bo stands on the flight between successive landings')
    await selectGate(page,7.70)
    assert.equal(await page.locator('.forward-viewport').getAttribute('data-scene'),'bend')
    await capture(page,'bend',width)
  }
  await selectGate(page,7)
  await page.evaluate(()=>{
    window.__forwardFrames=[];window.__forwardRecording=true;const start=performance.now()
    const sample=time=>{const actor=document.querySelector('.bo-journey-avatar');window.__forwardFrames.push({time:time-start,progress:Number(document.querySelector('.forward-viewport')?.dataset.progress),frame:actor?.dataset.frame,facing:actor?.dataset.facing,motion:actor?.dataset.motion});if(window.__forwardRecording&&time-start<20000)requestAnimationFrame(sample)}
    requestAnimationFrame(sample)
  })
  await page.mouse.move(width-20,400)
  // Pace inputs by observed movement rather than a 120ms wall-clock pulse that
  // can collapse both directions into one frame on software WebGL under load.
  for(const direction of [1,-1]) {
    for(let step=0;step<4;step++) {
      const before=Number(await page.locator('.forward-viewport').getAttribute('data-progress'))
      await page.mouse.wheel(0,-direction*33)
      await page.waitForFunction(({before,direction})=>(Number(document.querySelector('.forward-viewport')?.dataset.progress)-before)*direction>.025,{before,direction},{timeout:15000})
    }
    await settle(page)
  }
  await settle(page)
  await page.evaluate(()=>{window.__forwardRecording=false})
  const frames=await page.evaluate(()=>window.__forwardFrames)
  motion.push({width,frames})
  assert(new Set(frames.map(frame=>frame.progress.toFixed(4))).size>6,'Dolly movement has intermediate frames')
  assert(new Set(frames.filter(frame=>frame.motion==='walking').map(frame=>frame.frame)).size>2,'Actual Bo animation frames change during walking')
  assert(frames.some(frame=>frame.facing==='toward'),'Bo changes view when walking back')
  assert.equal(await page.locator('.bo-journey-avatar').getAttribute('data-motion'),'idle','Bo settles into a planted idle pose')
  await page.getByRole('button',{name:'Về bài đang học'}).click();await page.waitForTimeout(600);await settle(page)
  const previous=Number(await page.locator('.forward-viewport').getAttribute('data-progress'))
  assert(Math.abs(previous-7)<.02,'Locate the current learning gate')
  if(width===390) {
    await page.locator('.forward-gate[data-state=current] a').evaluate(link=>link.click());await page.waitForTimeout(160)
    await page.keyboard.press('Escape');await settle(page)
    assert(new URL(page.url()).pathname==='/hsk/1','Escape cancels the gate transition')
  }
  const cloudCover=page.waitForFunction(()=>document.querySelector('.journey-cloud-transition')?.dataset.phase==='cover',undefined,{timeout:10000})
  await page.locator('.forward-gate[data-state=current] a').evaluate(link=>link.click())
  await cloudCover
  if(width===1440||width===390)await capture(page,'cloud-transition',width)
  await page.waitForURL('**/lessons/lesson-1-7**')
  await page.waitForFunction(()=>document.querySelector('.journey-cloud-transition')?.dataset.phase==='idle')
  await page.goBack({waitUntil:'domcontentloaded'});await ready(page)
  assert(Math.abs(Number(await page.locator('.forward-viewport').getAttribute('data-progress'))-previous)<.02,'Back restores position')
  await selectGate(page,10);await page.reload({waitUntil:'domcontentloaded'});await ready(page)
  assert(Math.abs(Number(await page.locator('.forward-viewport').getAttribute('data-progress'))-10)<.02,'Reload restores position')
  const locked=page.locator('.forward-gate').nth(10).getByRole('button')
  await locked.focus();await locked.press('Enter')
  await page.getByRole('button',{name:'Đóng hướng dẫn bài học'}).click()
  await page.getByRole('button',{name:'Xem toàn bộ lộ trình'}).click()
  assert.equal(await page.locator('.forward-overview > li').count(),16)
  await capture(page,'overview',width)
  for(const level of [2,3]) {
    await page.getByRole('link',{name:`Mở HSK ${level}`}).click();await page.waitForURL(`**/hsk/${level}`);await ready(page)
    assert.equal(await page.locator('.forward-gate').count(),level===2?10:15)
    await capture(page,`hsk${level}`,width)
  }
  if(width===1440) {
    await page.getByRole('link',{name:'Mở HSK 2'}).click();await page.waitForURL('**/hsk/2');await ready(page)
    await selectGate(page,9);await capture(page,'hsk2-summit',width)
    await page.getByRole('link',{name:'Đi đến HSK 3',exact:true}).click();await page.waitForURL('**/hsk/3');await ready(page)
    await selectGate(page,14);await capture(page,'hsk3-summit',width)
    assert.equal(await page.locator('.painted-next-chapter').count(),0,'No invented chapter beyond the API curriculum')
  }
  state.partial=true;state.foundation=false;await page.reload({waitUntil:'domcontentloaded'});await ready(page)
  assert.equal(await page.locator('.forward-gate[data-state=planned]').count(),15)
  await page.emulateMedia({reducedMotion:'reduce'})
  await page.locator('.forward-overview').waitFor()
  await context.close()
 }
 if(!process.env.BO_VISUAL_ONLY&&!process.env.BO_VERIFY_STAGES_ONLY) {
  const reduced=await browser.newContext({viewport:{width:390,height:920},reducedMotion:'reduce'})
  await installJourneyFixture(reduced,{unexpected,writes});const page=await reduced.newPage();await page.goto(origin+'/hsk/1')
  await page.locator('.forward-overview').waitFor();assert.equal(await page.locator('canvas').count(),0)
  await capture(page,'reduced-motion',390);await reduced.close()
  const resized=await browser.newContext({viewport:{width:390,height:920}})
  await installJourneyFixture(resized,{unexpected,writes})
  const resizedPage=await resized.newPage();resizedPage.on('pageerror',error=>errors.push(error.message))
  await resizedPage.goto(origin+'/hsk/1');await ready(resizedPage)
  const priorProgress=Number(await resizedPage.locator('.forward-viewport').getAttribute('data-progress'))
  await resizedPage.setViewportSize({width:760,height:600});await settle(resizedPage)
  assert(Math.abs(Number(await resizedPage.locator('.forward-viewport').getAttribute('data-progress'))-priorProgress)<.02,'Resize preserves the current gate')
  const hud=await resizedPage.locator('.forward-navigation').boundingBox()
  assert(hud.y>=0&&hud.y+hud.height<=600,'Landscape navigation remains visible')
  await capture(resizedPage,'landscape',760)
  await resizedPage.setViewportSize({width:390,height:920});await settle(resizedPage)
  await resizedPage.locator('canvas').evaluate(canvas=>canvas.dispatchEvent(new Event('contextlost',{cancelable:true})))
  await resizedPage.locator('.forward-overview').waitFor()
  assert.equal(await resizedPage.locator('.forward-overview > li').count(),16)
  await capture(resizedPage,'context-lost',390);await resized.close()
  const fallback=await browser.newContext({viewport:{width:390,height:920}})
  await installJourneyFixture(fallback,{unexpected,writes})
  await fallback.addInitScript(()=>{HTMLCanvasElement.prototype.getContext=function(){return null}})
  const fallbackPage=await fallback.newPage();await fallbackPage.goto(origin+'/hsk/1');await fallbackPage.locator('.forward-overview').waitFor()
  assert.equal(await fallbackPage.locator('.forward-overview > li').count(),16)
  await capture(fallbackPage,'graphics-fallback',390);await fallback.close()
  const missingArt=await browser.newContext({viewport:{width:390,height:920}})
  await installJourneyFixture(missingArt,{unexpected,writes})
  await missingArt.route('**/academy/great-wall/painted-v2/ascent-stone-atlas.webp',route=>route.abort())
  const missingPage=await missingArt.newPage();await missingPage.goto(origin+'/hsk/1',{waitUntil:'domcontentloaded'})
  await missingPage.locator('.forward-overview').waitFor()
  assert.equal(await missingPage.locator('.forward-overview > li').count(),16)
  await capture(missingPage,'artwork-fallback',390);await missingArt.close()
 }
 assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
} finally {
 await browser.close()
 await writeFile(`${folder}/verification.json`,JSON.stringify({origin,captures,motion,errors,unexpected,writes},null,2))
}
console.log(process.env.BO_VERIFY_STAGES_ONLY?`PASS: ${captures.length} captures; exact landing, climbing and bend phases; final lesson views.`:`PASS: ${captures.length} captures; forward journey, 15/10/15 lessons, native input, restoration and fallbacks.`)
