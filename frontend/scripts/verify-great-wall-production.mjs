import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin = process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5173'
const folder = resolve('../.impeccable/review/continuous-great-wall')
await mkdir(folder, { recursive: true })
const browser = await chromium.launch()
const captures=[],errors=[],unexpected=[],writes=[],motion=[]
const total={1:15,2:10,3:15}
const time='2026-11-08T00:00:00Z'
async function install(context) {
  const state={foundation:true,partial:false}
  await context.route('**/api/v1/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname.split('/api/v1')[1]
    const reply=(json,status=200)=>route.fulfill({json,status})
    if(request.method()==='OPTIONS'||path==='/auth/logout')return route.fulfill({status:204})
    if(request.method()!=='GET')writes.push(path)
    if(path==='/auth/me')return reply({id:'fixture-student',full_name:'Nguyễn An',email:'review@example.invalid',role:'LEARNER'})
    if(path==='/hsk-levels')return reply([1,2,3].map(n=>({id:`hsk-${n}`,level_number:n,title:`HSK ${n}`,description:null,state:n===1&&!state.foundation?'LOCKED':'AVAILABLE'})))
    if(path==='/me/progress')return reply({current_hsk:1,progress_percentage:40,pronunciation_complete:state.foundation,hsk_levels:[]})
    if(path==='/pronunciation/lesson')return reply({sections:['INITIALS','FINALS','TONES','SANDHI'].map((code,i)=>({id:code,code,title:code,total_steps:[21,36,5,12][i],completed_at:state.foundation?time:null})),current_section:null,step_index:0,total_steps:0,completed_at:state.foundation?time:null,can_finish:false})
    const curriculum=path.match(/^\/hsk-levels\/hsk-(\d)\/curriculum$/)
    if(curriculum) {
      const level=Number(curriculum[1])
      const units=Array.from({length:state.partial?(level===1?1:0):total[level]},(_,i)=>({id:`unit-${level}-${i+1}`,order_index:i+1,unit_type:'LESSON',state:level===1&&!state.foundation?'LOCKED':i<6?'COMPLETED':i===6?'AVAILABLE':'LOCKED',lesson:{id:`lesson-${level}-${i+1}`,lesson_number:i+1,title:['你好 · Xin chào','Gia đình của tôi','Những người bạn','Ngày hôm nay','Cùng nhau học tập'][i%5],status:'PUBLISHED'},assessment:null}))
      return reply({hsk:{id:`hsk-${level}`,level_number:level,title:`HSK ${level}`},units:units.reverse()})
    }
    const lesson=path.match(/^\/lessons\/(lesson-(\d)-(\d+))$/)
    if(lesson)return reply({id:lesson[1],hsk_level_id:`hsk-${lesson[2]}`,lesson_number:Number(lesson[3]),title:'你好 · Xin chào',description:null,vocabulary:[],grammar:[],readings:[],assessment_ids:[]})
    const progress=path.match(/^\/me\/progress\/lessons\/(lesson-\d-\d+)$/)
    if(progress)return reply({lesson_id:progress[1],started_at:time,theory_completed_at:null,completed_at:null,vocabulary:[],grammar:[],readings:[]})
    unexpected.push(path);return reply({error:{code:'FIXTURE_ONLY',message:'Unexpected request'}},404)
  })
  return state
}
async function settled(page) {
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
  await page.waitForFunction(()=>!document.querySelector('.wall-camera-scene')?.dataset.cameraMoving)
}
async function ready(page) {
  const level=new URL(page.url()).pathname.match(/^\/hsk\/(\d)/)?.[1]
  if(level)await page.locator(`.wall-chapters a[aria-current="page"][href="/hsk/${level}"]`).waitFor()
  await page.locator('.wall-camera-scene').waitFor()
  await page.evaluate(()=>document.fonts.ready)
  await settled(page)
  await page.evaluate(async()=>{await Promise.all([...document.querySelectorAll('.wall-painted-section img')].filter(img=>img.complete||img.loading==='eager').map(img=>img.decode().catch(()=>{})))})
}
async function center(page,index) {
  const node=page.locator('.wall-lesson-stop').nth(index)
  await node.evaluate(el=>window.scrollTo({top:scrollY+el.getBoundingClientRect().top+el.getBoundingClientRect().height/2-innerHeight*.53,behavior:'instant'}))
  await settled(page)
  return node
}
async function capture(page,name,width) {
  const metrics=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,y:scrollY,camera:document.querySelector('.wall-camera-scene')?.dataset.cameraX}))
  assert(metrics.scroll<=width+1,`${name}: horizontal overflow ${metrics.scroll}/${width}`)
  await page.screenshot({path:`${folder}/${name}-${width}.png`,fullPage:false,animations:'disabled'})
  captures.push({name,...metrics})
}
async function verifyMotion(page,width) {
  // Pick an actual visible bend, away from camera travel limits at this width.
  let bendY=null
  for(let index=2;index<14;index++) {
    await center(page,index)
    const before=await page.locator('.wall-camera-scene').getAttribute('data-camera-x')
    const y=await page.evaluate(()=>scrollY)
    await page.evaluate(()=>scrollBy({top:180,behavior:'instant'}));await settled(page)
    const after=await page.locator('.wall-camera-scene').getAttribute('data-camera-x')
    if(Math.abs(Number(after)-Number(before))>20) {bendY=y;break}
  }
  assert.notEqual(bendY,null,'Find a road bend within camera travel limits')
  await page.evaluate(y=>scrollTo({top:y,behavior:'instant'}),bendY);await settled(page)
  await page.evaluate(()=>{
    window.__wallMotion=[]
    const started=performance.now()
    const record=time=>{
      const scene=document.querySelector('.wall-camera-scene')
      window.__wallMotion.push({time:time-started,y:scrollY,x:Number(scene.dataset.cameraX),moving:!!scene.dataset.cameraMoving})
      if(time-started<850)requestAnimationFrame(record)
    }
    requestAnimationFrame(record)
  })
  await page.mouse.move(width-20,400)
  const startY=await page.evaluate(()=>scrollY)
  await page.mouse.wheel(0,180)
  await page.waitForTimeout(110)
  await page.mouse.wheel(0,-90)
  await page.waitForTimeout(900)
  await settled(page)
  const result=await page.evaluate(()=>({frames:window.__wallMotion,y:scrollY,willChange:document.querySelector('.wall-camera-world').style.willChange}))
  motion.push({width,...result})
  assert(Math.abs(result.y-startY-90)<3,'Native wheel scrolling remains responsive')
  assert(result.frames.some(frame=>frame.moving),'Camera eases after wheel input')
  assert(new Set(result.frames.map(frame=>frame.x.toFixed(2))).size>5,'Wheel input produces intermediate camera frames')
  assert.equal(result.willChange,'','Camera releases its compositing hint when idle')
}
try {
 for(const width of [1440,1024,390,320]) {
  const context=await browser.newContext({viewport:{width,height:920},reducedMotion:'no-preference'})
  const state=await install(context)
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message))
  for(let attempt=0;;attempt++) {try{await page.goto(origin+'/hsk/1');break}catch(e){if(attempt>=4)throw e;await page.waitForTimeout(1000)}}
  await ready(page)
  assert.equal(await page.locator('.wall-lesson-stop[data-kind=lesson]').count(),15)
  assert.equal(await page.locator('.wall-lesson-stop[data-kind=foundation]').count(),1)
  assert.equal(await page.getByRole('button',{name:'Đoạn tiếp',exact:true}).count(),0)
  await page.getByRole('button',{name:'Về bài đang học'}).click();await settled(page)
  const active=page.locator('.wall-lesson-stop[data-state=current]')
  const activeBounds=await active.boundingBox()
  assert(activeBounds.y>70&&activeBounds.y<700)
  await capture(page,'hsk1-current',width)
  const cameraBefore=Number(await page.locator('.wall-camera-scene').getAttribute('data-camera-x'))
  await center(page,3);const cameraAfter=Number(await page.locator('.wall-camera-scene').getAttribute('data-camera-x'))
  assert(Math.abs(cameraBefore-cameraAfter)>5,'Camera should follow the turn horizontally')
  await capture(page,'foothills',width)
  await verifyMotion(page,width)
  const positions=[]
  for(let i=0;i<16;i++) {
    const node=await center(page,i)
    const box=await node.locator('.wall-seal').boundingBox()
    assert(box.x>=-1&&box.x+box.width<=width+1,`stop ${i}: clipped seal`)
    positions.push(box)
    if(i===9)await capture(page,'ridges',width)
    if(i===15)await capture(page,'summit',width)
  }
  await page.getByRole('button',{name:'Về bài đang học'}).click();await settled(page)
  const oldY=await page.evaluate(()=>scrollY)
  await active.locator('a').click();await page.waitForURL('**/lessons/lesson-1-7**')
  await page.goBack();await ready(page)
  assert(Math.abs(await page.evaluate(()=>scrollY)-oldY)<30,'Return to lesson position')
  await center(page,10);const restoreY=await page.evaluate(()=>scrollY)
  await page.reload();await ready(page)
  assert(Math.abs(await page.evaluate(()=>scrollY)-restoreY)<30,'Reload keeps map position')
  const locked = page.locator('.wall-lesson-stop[data-state=locked] button').first()
  await page.keyboard.press('Tab');await locked.focus();await settled(page)
  const lockedBounds=await locked.boundingBox()
  assert(lockedBounds.x>=0&&lockedBounds.x+lockedBounds.width<=width+1,'Keyboard focus locates a locked stop')
  await locked.press('Enter')
  await page.getByRole('button',{name:'Đóng hướng dẫn bài học'}).waitFor()
  await page.getByRole('button',{name:'Đóng hướng dẫn bài học'}).click()
  // The controls remain reachable while exploring the top of a long map.
  await page.getByRole('button',{name:'Xem danh sách',exact:true}).click()
  assert(await page.locator('.wall-camera-scene').evaluate(el=>el.classList.contains('is-list')))
  await page.getByRole('link',{name:'Mở HSK 2'}).click();await page.waitForURL('**/hsk/2');await ready(page)
  assert.equal(await page.locator('.wall-lesson-stop[data-kind=lesson]').count(),10)
  assert.equal(await page.locator('.wall-lesson-stop[data-kind=foundation]').count(),0)
  await capture(page,'hsk2-ten-lessons',width)
  await page.getByRole('link',{name:'Mở HSK 3'}).click();await page.waitForURL('**/hsk/3');await ready(page)
  assert.equal(await page.locator('.wall-lesson-stop[data-kind=lesson]').count(),15)
  await capture(page,'hsk3-fifteen-lessons',width)
  state.partial=true;state.foundation=false
  await page.reload();await ready(page)
  assert.equal(await page.locator('.wall-lesson-stop[data-state=planned]').count(),15)
  await capture(page,'hsk3-upcoming',width)
  await page.getByRole('link',{name:'Mở HSK 2'}).click();await page.waitForURL('**/hsk/2');await ready(page)
  assert.equal(await page.locator('.wall-lesson-stop[data-state=planned]').count(),10)
  await page.emulateMedia({reducedMotion:'reduce'});await settled(page)
  assert(await page.locator('.wall-camera-scene').evaluate(el=>el.classList.contains('is-list')),'Live reduced-motion preference switches to list')
  await context.close()
 }
 const reduced=await browser.newContext({viewport:{width:390,height:920},reducedMotion:'reduce'})
 await install(reduced)
 const page=await reduced.newPage();await page.goto(origin+'/hsk/1');await ready(page)
 assert(await page.locator('.wall-camera-scene').evaluate(el=>el.classList.contains('is-list')))
 await capture(page,'reduced-motion-list',390)
 await reduced.close()
 assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
} finally {
 await browser.close()
 await writeFile(`${folder}/verification.json`,JSON.stringify({captures,motion,errors,unexpected,writes,scope:'Production components, intercepted APIs; no real learning records changed.'},null,2))
}
console.log(`PASS: ${captures.length} captures; 15/10/15 lessons, camera turns, navigation and saved positions verified.`)
