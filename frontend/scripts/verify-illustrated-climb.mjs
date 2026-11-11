import assert from 'node:assert/strict'
import {mkdir,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import {chromium} from 'playwright'
import {installJourneyFixture} from './journey-fixture.mjs'
const folder=resolve('../.impeccable/review/illustrated-climb');await mkdir(folder,{recursive:true})
const browser=await chromium.launch(),errors=[],unexpected=[],writes=[],checks=[]
async function ready(page){await page.locator('.illustrated-climb[data-ready=true]').waitFor({timeout:60000});await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>document.querySelector('.journey-cloud-transition').dataset.phase==='idle')}
async function settle(page,p){await page.waitForFunction(expected=>{const el=document.querySelector('.illustrated-climb');return el?.dataset.moving==='false'&&Math.abs(JSON.parse(el.dataset.motion??'{}').progress-expected)<.0001},p,{timeout:15000})}
async function frame(page){return page.locator('.illustrated-climb').evaluate(el=>JSON.parse(el.dataset.motion))}
async function shot(page,name){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:`${folder}/${name}.png`})}
try{
 for(const width of [1438,390]){
  const context=await browser.newContext({viewport:{width,height:940},recordVideo:{dir:`${folder}/video`,size:{width,height:940}}})
  const fixture=await installJourneyFixture(context,{unexpected,writes});fixture.currentLesson=3
  const page=await context.newPage(),assets=new Set();page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});page.on('request',request=>{if(request.url().includes('/academy/great-wall/'))assets.add(new URL(request.url()).pathname)})
  const video=page.video();await page.goto('http://127.0.0.1:5173/hsk/1',{waitUntil:'domcontentloaded',timeout:90000});await ready(page);await settle(page,0)
  await page.evaluate(()=>{window.__climbShots=[];window.__climbTrace=[];const marks=[.02,.045,.07,.42,.44,.46,.48,.5,.72,.74,.76,.78,.8,.88];new MutationObserver(()=>{const el=document.querySelector('.illustrated-climb'),data=JSON.parse(el.dataset.motion);window.__climbTrace.push({at:performance.now(),...data});const next=marks[window.__climbShots.length];if(next!==undefined&&data.progress>=next){window.__climbShots.push({progress:data.progress,image:el.querySelector('canvas').toDataURL('image/jpeg',.9)})}}).observe(document.querySelector('.illustrated-climb'),{attributes:true,attributeFilter:['data-motion']})})
  assert.equal(await page.locator('.reference-scenes').count(),0,'The reference images are animation keys, not a gallery')
  const frames=[await frame(page)];await shot(page,`final-start-${width}`)
  const samples=await page.evaluate(async()=>new Promise(resolve=>{const rows=[],started=performance.now();function sample(){const el=document.querySelector('.illustrated-climb'),data=JSON.parse(el.dataset.motion);rows.push({at:performance.now()-started,...data});if(performance.now()-started>150&&el.dataset.moving==='false'&&data.progress>.099)resolve(rows);else if(performance.now()-started>10000)resolve(rows);else requestAnimationFrame(sample)}requestAnimationFrame(sample);document.querySelector('button[aria-label="Lên một bậc"]').click()}))
  await settle(page,.1);assert(new Set(samples.filter(s=>s.progress>0&&s.progress<.099).map(s=>s.progress)).size>=3,`One footfall has intermediate motion frames: ${samples.map(s=>s.progress).join(',')}`);assert(new Set(samples.map(s=>s.avatar.frame)).size>=3,'Actual walking poses advance')
  const first=await frame(page);await page.waitForTimeout(250);assert.deepEqual(await frame(page),first,'Idle Bo does not walk in place')
  for(let step=2;step<=9;step++){await page.getByRole('button',{name:'Lên một bậc',exact:true}).click();await settle(page,step/10);frames.push(await frame(page));if([3,5,6,7,9].includes(step))await shot(page,`final-step-${step}-${width}`)}
  const captured=await page.evaluate(()=>({images:window.__climbShots,trace:window.__climbTrace})),motionPictures=[]
  for(let i=0;i<captured.images.length;i++){const capture=captured.images[i],path=`${folder}/motion-${width}-${String(i).padStart(2,'0')}.jpg`;await writeFile(path,Buffer.from(capture.image.split(',')[1],'base64'));motionPictures.push({path,progress:capture.progress})}
  assert(captured.trace.some(row=>row.avatar.pose==='turn'),'A separate turning pose is used between walking directions')
  if(width===390)for(const row of captured.trace){assert(row.avatar.bounds.x>=-1&&row.avatar.bounds.x+row.avatar.bounds.width<=width+1,`Complete portrait character during phase ${row.progress}`);if(row.gate.opacity>.2)assert(row.gate.x>=-1&&row.gate.x+row.gate.width<=width+1,`Revealed portrait gate during phase ${row.progress}`)}
  assert(frames.some(f=>f.action==='bend'));assert(frames.some(f=>f.action==='gate'))
  const a=frames[0],b=frames.at(-1);assert(Math.abs(a.avatar.x-b.avatar.x)>10);assert(Math.abs(a.avatar.y-b.avatar.y)>40);assert(b.camera.zoom>a.camera.zoom);assert(frames.some(f=>Math.abs(f.camera.yaw)>.01))
  if(width===390){assert(b.gate.x>=0&&b.gate.x+b.gate.width<=width,'Mobile gateway fits the frame');const scene=await page.locator('.illustrated-climb').boundingBox(),hud=await page.locator('.reference-step-nav').boundingBox();assert(scene.y+scene.height<=hud.y+1,'Mobile controls do not cover the feet')}
  const near=b.landmarks[0].x-a.landmarks[0].x,far=b.landmarks[1].x-a.landmarks[1].x;assert(Math.abs(near-far)>1,'Near wall and distant scenery have different tracking displacement')
  await page.getByRole('button',{name:'Về bài đang học',exact:true}).click();await ready(page);await settle(page,0)
  await page.getByRole('button',{name:'Lên một bậc',exact:true}).click();await page.getByRole('button',{name:'Lên một bậc',exact:true}).click();await page.getByRole('button',{name:'Lên một bậc',exact:true}).click();await settle(page,.3)
  await page.keyboard.press('ArrowDown');await settle(page,.2)
  await page.getByRole('button',{name:'Về bài đang học',exact:true}).click();await ready(page);await settle(page,0)
  const destination=await page.locator('.reference-caption-hit').getAttribute('href');await page.locator('.reference-caption-hit').click();await page.waitForURL(`**${destination}`,{timeout:20000});await page.goBack();await ready(page);await settle(page,0);assert(await page.getByRole('button',{name:'Lên một bậc',exact:true}).isEnabled())
  if(width===1438){await page.getByRole('button',{name:'Thu gọn thanh bên',exact:true}).click();await shot(page,'final-collapsed-1438');await page.getByRole('button',{name:'Mở rộng thanh bên',exact:true}).click()}
  else{await page.getByRole('button',{name:'Mở menu học viên',exact:true}).click();await shot(page,'final-menu-390');await page.keyboard.press('ArrowUp');assert.equal(await page.locator('.reference-stage').getAttribute('data-progress'),'3');await page.getByRole('button',{name:'Đóng menu',exact:true}).click()}
  for(const level of [1,2,3]){if(level!==1){await page.getByRole('link',{name:`Mở HSK ${level}`,exact:true}).click();await ready(page)}await page.getByRole('button',{name:'Xem toàn lộ trình',exact:true}).click();assert.equal(await page.locator('.reference-overview > li').count(),level===1?16:level===2?10:15);await page.getByRole('button',{name:'Trở lại hành trình',exact:true}).click();await ready(page)}
  for(const name of ['master.webp','bo-turn.webp'])assert([...assets].some(path=>path.includes(`/climb-motion-v2/${name}`)))
  await context.close();checks.push({width,frames,samples,trace:captured.trace,motionPictures,assets:[...assets],video:await video.path()})
 }
 const reducedContext=await browser.newContext({viewport:{width:390,height:940},reducedMotion:'reduce'});const fixture=await installJourneyFixture(reducedContext,{unexpected,writes});fixture.currentLesson=3
 const reducedPage=await reducedContext.newPage();await reducedPage.goto('http://127.0.0.1:5173/hsk/1');await ready(reducedPage);await reducedPage.keyboard.press('ArrowUp');await settle(reducedPage,.1);assert.equal(await reducedPage.locator('.illustrated-climb').getAttribute('data-moving'),'false');await reducedContext.close()
 const fallbackContext=await browser.newContext({viewport:{width:390,height:940}});await installJourneyFixture(fallbackContext,{unexpected,writes});await fallbackContext.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(...args){if(String(args[0]).startsWith('webgl'))return null;return original.apply(this,args)}})
 const fallbackPage=await fallbackContext.newPage();await fallbackPage.goto('http://127.0.0.1:5173/hsk/1');await fallbackPage.locator('.illustrated-climb[data-ready=fallback]').waitFor();assert(await fallbackPage.getByText('Chế độ minh họa tĩnh.',{exact:false}).isVisible());const fallbackDestination=await fallbackPage.locator('.reference-caption-hit').getAttribute('href');await fallbackPage.locator('.reference-caption-hit').click();await fallbackPage.waitForURL(`**${fallbackDestination}`,{timeout:20000});await fallbackContext.close()
 assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
}finally{await browser.close();await writeFile(`${folder}/verification.json`,JSON.stringify({checks,errors,unexpected,writes},null,2))}
console.log('PASS: continuous gait/intermediate frames, coherent painted world, rear turn poses, camera tracking, idle/reduced motion/WebGL fallback, navigation, responsive sidebar and 15/10/15 lesson slots; no learning writes.')
