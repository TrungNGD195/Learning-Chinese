import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'
import { installJourneyFixture } from './journey-fixture.mjs'

const origin=process.env.BO_FRONTEND_ORIGIN||'http://127.0.0.1:5173'
const folder=resolve('../.impeccable/review/spatial-great-wall')
await mkdir(folder,{recursive:true})
const browser=await chromium.launch({args:process.env.SPATIAL_SOFTWARE?['--use-angle=swiftshader','--enable-unsafe-swiftshader']:['--enable-unsafe-swiftshader']})
const errors=[],unexpected=[],writes=[],captures=[],checks=[]
async function settle(page){await page.waitForTimeout(120);await page.waitForFunction(()=>!document.querySelector('.forward-viewport')?.dataset.cameraMoving,undefined,{timeout:60000});await page.waitForTimeout(240)}
async function ready(page){const level=new URL(page.url()).pathname.match(/^\/hsk\/(\d+)/)?.[1];if(level)await page.locator(`.wall-chapters a[aria-current="page"][href="/hsk/${level}"]`).waitFor();await page.locator(`.forward-viewport${level?`[data-level="${level}"]`:''}[data-ready=true]`).waitFor({timeout:60000});await page.evaluate(()=>document.fonts.ready);await settle(page);await page.waitForFunction(()=>!document.querySelector('.journey-cloud-transition')||document.querySelector('.journey-cloud-transition').dataset.phase==='idle',undefined,{timeout:15000})}
const snapshot=page=>page.locator('.forward-viewport').evaluate(view=>({progress:Number(view.dataset.progress),distance:Number(view.dataset.worldDistance),heading:Number(view.dataset.heading),eye:JSON.parse(view.dataset.worldPosition),fog:Number(view.dataset.fog),graphics:JSON.parse(view.dataset.graphics),landmarks:JSON.parse(view.dataset.landmarks),count:Number(view.dataset.pathCount)}))
async function capture(page,name,width){await settle(page);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:`${folder}/${name}-${width}.png`});captures.push({name,width,...await snapshot(page)});console.log(`Captured ${name} at ${width}px`)}
async function scrollToProgress(page,value){await page.evaluate(value=>{const track=document.querySelector('.forward-track'),view=document.querySelector('.forward-viewport'),count=Number(view.dataset.pathCount),step=(track.offsetHeight-view.clientHeight)/(count-1),start=track.getBoundingClientRect().top+scrollY-parseFloat(getComputedStyle(view).top);scrollTo({top:start+(count-1-value)*step,behavior:'instant'})},value);await page.waitForFunction(value=>Math.abs(Number(document.querySelector('.forward-viewport').dataset.progress)-value)<.006,value,{timeout:60000});await settle(page)}
async function marker(page,level){await page.getByRole('button',{name:'Xem toàn bộ lộ trình',exact:true}).click();await page.getByRole('button',{name:`Đến tháp canh HSK ${level}`,exact:true}).click();await ready(page)}
try{
 for(const width of process.env.SPATIAL_WIDTHS?.split(',').map(Number)??[1440,390]){
  const context=await browser.newContext({viewport:{width,height:920}});context.setDefaultNavigationTimeout(60000)
  await installJourneyFixture(context,{unexpected,writes});const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/THREE|Shader Error/.test(m.text()))errors.push(m.text())})
  await page.goto(origin+'/hsk/1',{waitUntil:'domcontentloaded'});await ready(page)
  await capture(page,'current',width)
  if(process.env.SPATIAL_VISUAL_ONLY){await marker(page,1);await capture(page,'milestone-hsk1',width);await context.close();continue}
  assert.equal(await page.locator('.forward-gate').count(),16)
  const before=await snapshot(page);await page.mouse.move(width-20,420);for(let i=0;i<6;i++)await page.mouse.wheel(0,-120);await settle(page)
  const after=await snapshot(page)
  assert(after.eye.y>before.eye.y,'Camera truly rises along the mountain')
  assert(Math.hypot(after.eye.x-before.eye.x,after.eye.z-before.eye.z)>1,'Camera translates through world space')
  assert(Math.abs(after.heading-before.heading)>.005,'Camera turns with the winding route')
  assert(after.fog<before.fog,'Valley haze diminishes with altitude')
  const moved=before.landmarks.flatMap(a=>{const b=after.landmarks.find(b=>b.id===a.id);return a.visible&&b?.visible?[{id:a.id,dx:b.x-a.x,dy:b.y-a.y}]:[]})
  assert(moved.some(m=>Math.abs(m.dx)>2&&Math.abs(m.dy)>1),'Fixed trees/towers change perspective in both axes, not only road motion')
  await capture(page,'climbing-turn',width)
  for(let i=0;i<6;i++)await page.mouse.wheel(0,120);await settle(page);const reversed=await snapshot(page)
  assert(Math.hypot(reversed.eye.x-before.eye.x,reversed.eye.y-before.eye.y,reversed.eye.z-before.eye.z)<.1,'Reversal restores the same real camera pose')
  checks.push({width,before,after,moved,reversed})
  const active=page.locator('.forward-gate[data-state=current] a'),destination=await active.getAttribute('href')
  await active.click();await page.waitForURL(url=>url.pathname.startsWith(destination))
  if(width!==1440)await page.waitForFunction(()=>!document.querySelector('.forward-viewport')&&document.querySelector('.journey-cloud-transition')?.dataset.phase==='idle',undefined,{timeout:60000})
  await page.goBack({waitUntil:'domcontentloaded'});await ready(page)
  assert(Math.abs((await snapshot(page)).progress-before.progress)<.006,'Opening the projected gateway and Back restore position')
  await scrollToProgress(page,7.3);await page.reload({waitUntil:'domcontentloaded'});await ready(page)
  assert(Math.abs((await snapshot(page)).progress-7.3)<.006,'Reload restores the spatial waypoint')
  for(const [name,p] of [['lower-bend',3],['upper-bend',11]]){await scrollToProgress(page,p);await capture(page,name,width)}
  await marker(page,1);await capture(page,'milestone-hsk1',width);const end1=await snapshot(page)
  await page.getByRole('link',{name:'Đi đến HSK 2',exact:true}).click();await page.waitForURL('**/hsk/2');await ready(page);await capture(page,'hsk2-shared-start',width);const start2=await snapshot(page)
  assert.equal(start2.progress,.5);assert.equal(await page.locator('.forward-gate').count(),10)
  assert.equal(start2.distance,end1.distance+7.5,'Portal arrives on the first lesson approach beyond the HSK1 tower')
  await capture(page,'hsk2-first-lesson',width)
  if(width===1440){
    await page.getByRole('link',{name:'Mở HSK 1',exact:true}).click();await page.waitForURL('**/hsk/1');await ready(page)
    await page.evaluate(()=>{const key='bo-spatial-wall-v2-hsk-2',saved=JSON.parse(sessionStorage.getItem(key));saved.progress=5.3;sessionStorage.setItem(key,JSON.stringify(saved))})
    await page.getByRole('link',{name:'Đi đến HSK 2',exact:true}).click();await page.waitForURL('**/hsk/2');await ready(page)
    assert.equal((await snapshot(page)).progress,.5,'Explicit first-lesson portal navigation overrides an older mid-chapter visual resume')
    await capture(page,'hsk2-reentry-from-marker',width)
  }
  await marker(page,2);await capture(page,'milestone-hsk2',width);const end2=await snapshot(page)
  await page.getByRole('link',{name:'Đi đến HSK 3',exact:true}).click();await page.waitForURL('**/hsk/3');await ready(page);await capture(page,'hsk3-shared-start',width);const start3=await snapshot(page)
  assert.equal(await page.locator('.forward-gate').count(),15)
  assert.equal(start3.progress,.5);assert.equal(start3.distance,end2.distance+7.5,'Portal arrives on the first HSK3 lesson approach')
  await marker(page,3);await capture(page,'milestone-hsk3',width);assert.equal(await page.locator('.painted-next-chapter').count(),0)
  await context.close()
 }
 assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
}finally{await browser.close();await writeFile(`${folder}/verification.json`,JSON.stringify({origin,captures,checks,errors,unexpected,writes},null,2))}
console.log(`PASS: ${captures.length} spatial captures; real camera translation/elevation/yaw and shared HSK milestones. No device FPS certification.`)
