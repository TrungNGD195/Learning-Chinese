import assert from 'node:assert/strict'
import {mkdir,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import {chromium} from 'playwright'
import {installJourneyFixture} from './journey-fixture.mjs'

const folder=resolve('../.impeccable/review/first-person-wall')
await mkdir(folder,{recursive:true})
const browser=await chromium.launch(),errors=[],unexpected=[],writes=[],checks=[]
const stepsPerGate=6
const ready=async page=>{
 await page.locator('.illustrated-climb[data-ready=true]').waitFor({timeout:90000})
 await page.evaluate(()=>document.fonts.ready)
 await page.waitForFunction(()=>document.querySelector('.journey-cloud-transition')?.dataset.phase==='idle')
}
const frame=page=>page.locator('.illustrated-climb').evaluate(el=>JSON.parse(el.dataset.motion))
const settle=(page,p)=>page.waitForFunction(expected=>{const el=document.querySelector('.illustrated-climb');return el?.dataset.moving==='false'&&Math.abs(JSON.parse(el.dataset.motion??'{}').progress-expected)<.0001},p,{timeout:180000})
async function capture(page,name){
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No horizontal page overflow')
 await page.screenshot({path:`${folder}/${name}.png`})
}
async function observe(page,baseline){
 await page.evaluate(start=>{
  window.__walkTrace=[];window.__walkImages=[]
  const surface=document.querySelector('.illustrated-climb'),marks=[.025,.075,.2,.4,.6,.8,.92,.98,1.015,1.05,1.2,1.6,1.95,2.02]
  new MutationObserver(()=>{
   const row=JSON.parse(surface.dataset.motion)
   window.__walkTrace.push({at:performance.now(),cloud:document.querySelector('.journey-cloud-transition').dataset.phase,...row})
   if(window.__walkImages.length<marks.length&&row.progress-start>=marks[window.__walkImages.length]){
    window.__walkImages.push({progress:row.progress,image:surface.querySelector('canvas').toDataURL('image/jpeg',.88)})
   }
  }).observe(surface,{attributes:true,attributeFilter:['data-motion']})
 },baseline)
}
try{
 for(const width of [1438,390,900]){
  const context=await browser.newContext({viewport:{width,height:940},recordVideo:{dir:`${folder}/video`,size:{width,height:940}}})
  const fixture=await installJourneyFixture(context,{unexpected,writes});fixture.currentLesson=3
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text())})
  const video=page.video()
  await page.goto('http://127.0.0.1:5173/hsk/1',{waitUntil:'domcontentloaded',timeout:90000});await ready(page);await settle(page,3)
  await capture(page,width===1438?'desktop':width===390?'mobile':'tablet')
  await observe(page,3)
  const initial=await frame(page)
  const count=width===1438?14:width===390?8:3
  // Queue several footfalls on the same controller. This must remain one
  // unbroken camera journey rather than reset/teleport at each integer.
  for(let sent=0;sent<count;){
   const amount=Math.min(stepsPerGate,count-sent)
   for(let i=0;i<amount;i++)await page.keyboard.press('ArrowUp')
   sent+=amount;await settle(page,3+sent/stepsPerGate)
  }
  await settle(page,3+count/stepsPerGate)
  const last=await frame(page),captured=await page.evaluate(()=>({trace:window.__walkTrace,images:window.__walkImages}))
  assert(captured.trace.length>5,'Intermediate animation frames exist')
  assert(captured.trace.every(row=>row.cloud==='idle'),'Ordinary gate crossings never use a scene curtain')
  for(let i=1;i<captured.trace.length;i++){
   const a=captured.trace[i-1],b=captured.trace[i]
   assert(b.world.distance+1e-7>=a.world.distance,'World distance never wraps at a gate')
   assert(Math.hypot(b.camera.x-a.camera.x,b.camera.y-a.camera.y,b.camera.z-a.camera.z)<2,'No camera jump or chapter-like reset during walking')
   assert.equal(b.world.roadStrips,1)
   assert.equal(b.camera.zoom,1,'Fixed field of view while climbing')
  }
  assert(last.camera.y>initial.camera.y,'The viewpoint gains altitude')
  assert(Math.abs(last.camera.x-initial.camera.x)>.1,'The viewpoint moves laterally with the curve')
  assert(Math.abs(last.camera.yaw-initial.camera.yaw)>.03,'The camera turns with the road')
  assert(new Set(captured.trace.map(row=>row.avatar.frame)).size>=5,'Bo actually advances through walking poses')
  const approaching=captured.trace.filter(row=>row.progress<3.97)
  assert(approaching.at(-1).world.mist<approaching[0].world.mist,'Distance mist clears while approaching')
  if(count>stepsPerGate){
   assert(captured.trace.some(row=>row.progress>3.995&&row.progress<4.015),'The camera physically crosses the first gate plane')
   assert(last.world.passedGates>=4,'Walking continues beyond the same gate')
  }
  const landmark=initial.landmarks.find(row=>row.id==='near-pine-3'),lastLandmark=last.landmarks.find(row=>row.id===landmark.id)
  assert.deepEqual(lastLandmark.world,landmark.world,'Scenery stays fixed in world space')
  assert(Math.abs(lastLandmark.x-landmark.x)>5,'Fixed scenery changes screen position with the camera')
  await capture(page,`after-gate-${width}`)
  const imagePaths=[]
  for(let i=0;i<captured.images.length;i++){
   const image=captured.images[i],path=`${folder}/walk-${width}-${String(i).padStart(2,'0')}.jpg`
   await writeFile(path,Buffer.from(image.image.split(',')[1],'base64'));imagePaths.push({path,progress:image.progress})
  }
  await page.waitForTimeout(250);assert.deepEqual(await frame(page),last,'No idle walking loop')
  await page.keyboard.press('ArrowDown');await settle(page,3+(count-1)/stepsPerGate)
  await page.keyboard.press('ArrowUp');await settle(page,3+count/stepsPerGate)
  await page.locator('.reference-stage').hover();await page.mouse.wheel(0,120);await page.waitForTimeout(150);assert.equal((await frame(page)).progress,3+count/stepsPerGate,'The mouse wheel no longer walks')
  await page.getByRole('button',{name:'Về bài đang học',exact:true}).click();await ready(page);await settle(page,3)
  if(width===1438){
   const destination=await page.locator('.reference-caption-hit').getAttribute('href')
   await page.locator('.reference-caption-hit').click();await page.waitForURL(`**${destination}`,{timeout:25000})
   await page.goBack();await ready(page);await settle(page,3)
   await page.getByRole('button',{name:'Thu gọn thanh bên',exact:true}).click();await capture(page,'desktop-sidebar-collapsed')
   await page.getByRole('button',{name:'Mở rộng thanh bên',exact:true}).click()
  }
  if(width===390){
   const bounds=await page.locator('.illustrated-climb').boundingBox(),hud=await page.locator('.reference-step-nav').boundingBox()
   assert(bounds.y+bounds.height<=hud.y+1,'Portrait controls never cover the feet')
   const motion=await frame(page)
   assert(motion.avatar.bounds.x>=0&&motion.avatar.bounds.x+motion.avatar.bounds.width<=bounds.width,'Bo remains inside the portrait viewport')
   await page.getByRole('button',{name:'Mở menu học viên',exact:true}).click();await capture(page,'mobile-menu')
   await page.keyboard.press('ArrowUp');assert.equal(await page.locator('.reference-stage').getAttribute('data-progress'),'3')
   await page.getByRole('button',{name:'Đóng menu',exact:true}).click()
  }
  checks.push({width,initial,last,trace:captured.trace,images:imagePaths,video:await video.path()})
  await context.close()
 }
 // Reduced movement still changes one tread and exposes all native lesson slots.
 const context=await browser.newContext({viewport:{width:390,height:940},reducedMotion:'reduce'})
 const fixture=await installJourneyFixture(context,{unexpected,writes});fixture.currentLesson=3
 const page=await context.newPage();await page.goto('http://127.0.0.1:5173/hsk/1');await ready(page);await page.keyboard.press('ArrowUp');await settle(page,3+1/stepsPerGate)
 for(const level of [1,2,3]){
  if(level!==1){await page.getByRole('link',{name:`Mở HSK ${level}`,exact:true}).click();await ready(page)}
  await page.getByRole('button',{name:'Xem toàn lộ trình',exact:true}).click()
  assert.equal(await page.locator('.reference-overview > li').count(),level===1?16:level===2?10:15)
  await page.getByRole('button',{name:'Đến mốc HSK '+level,exact:false}).click();await ready(page)
  assert.equal((await frame(page)).progress,level===1?16:level===2?10:15)
  await capture(page,`chapter-end-${level}`)
 }
 await context.close()
 const fallback=await browser.newContext({viewport:{width:390,height:940},reducedMotion:'reduce'})
 await installJourneyFixture(fallback,{unexpected,writes})
 await fallback.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(...args){if(String(args[0]).startsWith('webgl'))return null;return original.apply(this,args)}})
 const fallbackPage=await fallback.newPage();await fallbackPage.goto('http://127.0.0.1:5173/hsk/1');await fallbackPage.locator('.illustrated-climb[data-ready=fallback]').waitFor({timeout:30000})
 const destination=await fallbackPage.locator('.reference-caption-hit').getAttribute('href');await fallbackPage.locator('.reference-caption-hit').click();await fallbackPage.waitForURL(`**${destination}`)
 await fallback.close()
 assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
}finally{
 await browser.close();await writeFile(`${folder}/verification.json`,JSON.stringify({checks,errors,unexpected,writes},null,2))
}
console.log('PASS: one winding road, physical camera ascent and turning through gates, fixed scenery, distance mist, uninterrupted walking; responsive/native links/reduced motion/fallback; 15/10/15 lessons; no progress writes.')
