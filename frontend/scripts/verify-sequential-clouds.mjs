import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'
import { installJourneyFixture } from './journey-fixture.mjs'

const folder=resolve('../.impeccable/review/spatial-great-wall/sequential-clouds')
await mkdir(folder,{recursive:true})
const browser=await chromium.launch({args:['--enable-unsafe-swiftshader']})
const errors=[],unexpected=[],writes=[],checks=[]
async function settle(page){await page.waitForTimeout(140);await page.waitForFunction(()=>!document.querySelector('.forward-viewport')?.dataset.cameraMoving,undefined,{timeout:60000});await page.waitForTimeout(360)}
async function ready(page,level){await page.locator(`.forward-viewport[data-level="${level}"][data-ready=true]`).waitFor({timeout:60000});await page.evaluate(()=>document.fonts.ready);await settle(page);await page.waitForFunction(()=>document.querySelector('.journey-cloud-transition').dataset.phase==='idle')}
const snapshot=page=>page.locator('.forward-viewport').evaluate(view=>({progress:Number(view.dataset.progress),distance:Number(view.dataset.worldDistance),eye:JSON.parse(view.dataset.worldPosition),gates:JSON.parse(view.dataset.gateStages),landmarks:JSON.parse(view.dataset.landmarks)}))
async function move(page,p){await page.evaluate(p=>{const track=document.querySelector('.forward-track'),view=document.querySelector('.forward-viewport'),count=Number(view.dataset.pathCount),step=(track.offsetHeight-view.clientHeight)/(count-1),start=track.getBoundingClientRect().top+scrollY-parseFloat(getComputedStyle(view).top);scrollTo({top:start+(count-1-p)*step,behavior:'instant'})},p);await page.waitForFunction(p=>Math.abs(Number(document.querySelector('.forward-viewport').dataset.progress)-p)<.0001,p,{timeout:60000});await settle(page)}
async function capture(page,name,width){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:`${folder}/${name}-${width}.png`})}
async function milestone(page,level){await page.getByRole('button',{name:'Xem toàn bộ lộ trình',exact:true}).click();await page.getByRole('button',{name:new RegExp(`Đến (?:cột mốc|tháp canh) HSK ${level}`)}).click();await ready(page,level)}
try{
  for(const width of [1440,390]){
    const context=await browser.newContext({viewport:{width,height:920}});await installJourneyFixture(context,{unexpected,writes})
    const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error'&&/THREE|Shader Error/.test(message.text()))errors.push(message.text())})
    await page.goto('http://127.0.0.1:5173/hsk/1',{waitUntil:'domcontentloaded'});await ready(page,1)
    const sequence=[]
    for(const p of [7,7.4,7.5,7.7,7.9,8]){
      await move(page,p);const state=await snapshot(page);sequence.push(state)
      if(p<=7.4){assert.equal(state.gates[7].opacity,1);assert(state.gates.slice(8).every(gate=>gate.opacity===0));assert.equal(state.gates[8].mist,1)}
      if(p===7.5){assert.equal(state.gates[7].opacity,0);assert.equal(state.gates[8].opacity,0)}
      if(p>7.5&&p<8){assert(state.gates[8].opacity>0&&state.gates[8].opacity<1);assert(state.gates[8].mist>0&&state.gates[8].mist<1)}
      if(p===8){assert.equal(state.gates[8].opacity,1);assert.equal(state.gates[8].mist,0);assert(state.gates.slice(9).every(gate=>gate.opacity===0))}
      await capture(page,`reveal-${p}`,width)
    }
    const rising=sequence.slice(2).map(state=>state.gates[8])
    for(let i=1;i<rising.length;i++){assert(rising[i].opacity>rising[i-1].opacity);assert(rising[i].mist<rising[i-1].mist)}
    await move(page,7.4);const reversed=await snapshot(page);assert.equal(reversed.gates[7].opacity,1);assert.equal(reversed.gates[8].opacity,0)
    await milestone(page,1);const end1=await snapshot(page);await capture(page,'watchtower-hsk1',width)
    const landmark=end1.landmarks.find(item=>item.id==='milestone-hsk-1');assert(landmark.visible&&landmark.x>0&&landmark.x<width)
    await page.evaluate(()=>{
      window.cloudTrace=[]
      window.cloudObserver=new MutationObserver(()=>{const cloud=document.querySelector('.journey-cloud-transition');window.cloudTrace.push({at:performance.now(),phase:cloud.dataset.phase,opacity:Number(getComputedStyle(cloud,'::before').opacity),duration:getComputedStyle(cloud.querySelector('.journey-cloud-curtain')).transitionDuration})})
      window.cloudObserver.observe(document.querySelector('.journey-cloud-transition'),{attributes:true,attributeFilter:['data-phase']})
    })
    await page.getByRole('button',{name:'Về bài đang học',exact:true}).click()
    await page.waitForFunction(()=>Number(document.querySelector('.forward-viewport').dataset.progress)===7)
    await page.waitForFunction(()=>document.querySelector('.journey-cloud-transition').dataset.phase==='idle')
    const timing=await page.evaluate(()=>{window.cloudObserver.disconnect();return window.cloudTrace})
    const cover=timing.find(frame=>frame.phase==='cover'),reveal=timing.find(frame=>frame.phase==='reveal'),idle=timing.find(frame=>frame.phase==='idle')
    assert(reveal.at-cover.at>=850,'Clouds take at least 620ms to gather and hold at least 260ms')
    assert(idle.at-reveal.at>=540,'Cloud exit lasts around 560ms')
    assert(cover.duration.includes('0.62s')&&reveal.duration.includes('0.56s'),'CSS and controller use the same longer durations')
    await milestone(page,1)
    await page.getByRole('link',{name:'Đi đến HSK 2',exact:true}).click();await page.waitForURL('**/hsk/2');await ready(page,2)
    const start2=await snapshot(page);assert.equal(start2.progress,.5);assert.equal(start2.distance,end1.distance+7.5)
    await capture(page,'first-lesson-hsk2',width)
    await move(page,1);await capture(page,'beyond-watchtower-hsk2',width)
    if(width===1440){
      await milestone(page,2);await capture(page,'watchtower-hsk2',width)
      await page.getByRole('link',{name:'Đi đến HSK 3',exact:true}).click();await page.waitForURL('**/hsk/3');await ready(page,3)
      await milestone(page,3);await capture(page,'watchtower-hsk3',width)
      assert.equal(await page.locator('.painted-next-chapter').count(),0)
    }
    checks.push({width,sequence,reversed,end1,start2,timing});await context.close()
  }
  assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
}finally{await browser.close();await writeFile(`${folder}/verification.json`,JSON.stringify({checks,errors,unexpected,writes},null,2))}
console.log('PASS: sequential gate reveal with receding mist, reversal, longer cloud enter/hold/exit, stone watchtowers and shared HSK milestones on desktop/mobile.')
