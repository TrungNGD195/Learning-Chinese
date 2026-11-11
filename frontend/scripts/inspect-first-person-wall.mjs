import {mkdir,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import {chromium} from 'playwright'
import {installJourneyFixture} from './journey-fixture.mjs'
const folder=resolve('../.impeccable/review/first-person-wall');await mkdir(folder,{recursive:true})
const browser=await chromium.launch(),errors=[],unexpected=[],writes=[],frames=[]
try{
 const context=await browser.newContext({viewport:{width:1438,height:940},recordVideo:{dir:`${folder}/video`,size:{width:1438,height:940}}}),fixture=await installJourneyFixture(context,{unexpected,writes});fixture.currentLesson=3
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())})
 await page.goto('http://127.0.0.1:5173/hsk/1',{waitUntil:'domcontentloaded',timeout:90000});await page.locator('.illustrated-climb[data-ready=true]').waitFor({timeout:60000})
 await page.waitForFunction(()=>document.querySelector('.illustrated-climb').dataset.moving==='false')
 const baseline=await page.locator('.illustrated-climb').evaluate(el=>JSON.parse(el.dataset.motion).progress)
 for(let step=0;step<=12;step++){
  if(step){await page.keyboard.press('ArrowUp');await page.waitForFunction(p=>{const el=document.querySelector('.illustrated-climb');return el.dataset.moving==='false'&&Math.abs(JSON.parse(el.dataset.motion).progress-p)<.0001},baseline+step/6,{timeout:25000})}
  frames.push(await page.locator('.illustrated-climb').evaluate(el=>JSON.parse(el.dataset.motion)))
  if([0,4,7,9,10,12].includes(step))await page.screenshot({path:`${folder}/initial-step-${step}.png`})
 }
 await context.close()
}finally{await browser.close();await writeFile(`${folder}/inspection.json`,JSON.stringify({frames,errors,unexpected,writes},null,2))}
console.log(JSON.stringify({errors,unexpected,writes,frames:frames.length}))
