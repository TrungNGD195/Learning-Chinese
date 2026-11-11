import assert from 'node:assert/strict'
import {mkdir,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import {chromium} from 'playwright'
import {installJourneyFixture} from './journey-fixture.mjs'

const reducedOnly=process.argv.includes('--reduced-only')
const folder=resolve(reducedOnly?'../tmp/journey-tower-primary':'../tmp/journey-tower'),base=process.env.JOURNEY_TEST_URL??'http://127.0.0.1:5173'
await mkdir(folder,{recursive:true})
const browser=await chromium.launch(),errors=[],unexpected=[],writes=[],checks=[]
const ready=async page=>{
 const level=new URL(page.url()).pathname.split('/').at(-1)
 await page.locator(`.reference-journey[data-level="${level}"] .illustrated-climb[data-ready=true]`).waitFor({timeout:90000})
 await page.waitForFunction(number=>{
  const root=document.querySelector(`.reference-journey[data-level="${number}"] .illustrated-climb`)
  return root?.dataset.ready==='true'&&root.dataset.moving==='false'&&document.querySelector('.journey-cloud-transition')?.dataset.phase==='idle'
 },level)
}
const frame=page=>page.locator('.illustrated-climb').evaluate(el=>JSON.parse(el.dataset.motion))
const settle=(page,p)=>page.waitForFunction(expected=>{const el=document.querySelector('.illustrated-climb');return el?.dataset.moving==='false'&&Math.abs(JSON.parse(el.dataset.motion??'{}').progress-expected)<.0001},p,{timeout:60000})
const shot=async(page,name)=>{
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
 await page.screenshot({path:`${folder}/${name}.png`})
}
async function trace(page){
 await page.evaluate(()=>{
  window.__towerTrace=[]
  const root=document.querySelector('.illustrated-climb')
  new MutationObserver(()=>window.__towerTrace.push({at:performance.now(),cloud:document.querySelector('.journey-cloud-transition').dataset.phase,...JSON.parse(root.dataset.motion)})).observe(root,{attributes:true,attributeFilter:['data-motion']})
 })
}
async function marker(page,level){
 await page.locator('.wall-overview-toggle').click()
 await page.locator('.reference-marker-button').click();await ready(page)
 await settle(page,level===1?16:level===2?10:15)
}
try{
 for(const width of [1438,390]){
  const context=await browser.newContext({viewport:{width,height:940},reducedMotion:reducedOnly||width===390?'reduce':'no-preference',recordVideo:{dir:`${folder}/video`,size:{width,height:940}}})
  const fixture=await installJourneyFixture(context,{unexpected,writes});fixture.currentLesson=15
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text())})
  await page.goto(`${base}/hsk/1`);await ready(page)
  assert.equal(await page.locator('.reference-step-nav > button').count(),0,'Movement has no mouse buttons')
  const original=await frame(page)
  await page.locator('.illustrated-climb').hover();await page.mouse.wheel(0,-900);await page.waitForTimeout(180)
  assert.equal((await frame(page)).progress,original.progress,'Wheel does not move Bo')
  await page.keyboard.press('ArrowLeft');await page.keyboard.press('ArrowRight');assert.equal((await frame(page)).progress,original.progress)
  await shot(page,`last-gate-${width}`)
  await marker(page,1);await shot(page,`tower-hsk1-${width}`)
  assert((await frame(page)).world.towerDistance>0)
  await trace(page)
  for(let step=1;step<=2;step++){
   await page.keyboard.press('ArrowUp');await settle(page,16+step/6)
   assert.equal((await frame(page)).world.towerEntered,false)
   await shot(page,`entrance-${step}-${width}`)
  }
  await page.keyboard.press('ArrowUp');await page.waitForURL('**/hsk/2',{timeout:60000});await ready(page)
  await settle(page,0)
  const entry=await page.evaluate(()=>window.__towerTrace),arrival=await frame(page)
  assert(entry.some(row=>row.world.towerEntered&&row.avatar.bounds.opacity===0),'Bo disappears inside the tower before changing HSK')
  assert.equal(arrival.progress,0,'The next chapter starts on its first approach')
  assert.equal(arrival.avatar.bounds.opacity,1,'Bo returns in the next chapter')
  assert(arrival.world.distance>entry.at(-1).world.distance,'Arrival continues beyond the tower')
  assert.equal((await page.locator('.journey-cloud-transition').textContent()).trim(),'','Cloud transition has no text')
  await shot(page,`arrival-hsk2-${width}`)
  await page.goBack();await ready(page);await page.waitForTimeout(400)
  assert(new URL(page.url()).pathname==='/hsk/1','Back does not immediately re-enter the tower')
  assert.equal((await frame(page)).world.towerEntered,false)
  await page.goto(`${base}/hsk/2`);await ready(page);await marker(page,2);await shot(page,`tower-hsk2-${width}`)
  await trace(page)
  for(let step=1;step<=2;step++){await page.keyboard.press('ArrowUp');await settle(page,10+step/6)}
  await page.keyboard.press('ArrowUp');await page.waitForURL('**/hsk/3',{timeout:60000});await ready(page)
  await settle(page,0)
  assert((await page.evaluate(()=>window.__towerTrace)).some(row=>row.world.towerEntered))
  assert.equal((await frame(page)).progress,0)
  assert.equal((await frame(page)).world.towerDistance,null,'The final configured chapter has no invented HSK 4 exit')
  await shot(page,`arrival-hsk3-${width}`)
  checks.push({width,entry,arrival,video:await page.video().path()});await context.close()
 }
 assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
}finally{await browser.close();await writeFile(`${folder}/verification.json`,JSON.stringify({base,reducedOnly,checks,errors,unexpected,writes},null,2))}
console.log('PASS: keyboard-only walking; HSK1/2 towers, black-door disappearance, automatic HSK2/3 arrival, Back/reduced motion; no learning writes.')
