import {mkdir,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import {chromium} from 'playwright'
import {installJourneyFixture} from './journey-fixture.mjs'
const folder=resolve('../.impeccable/review/illustrated-climb');await mkdir(folder,{recursive:true})
const browser=await chromium.launch(),errors=[],unexpected=[],writes=[],frames=[]
try{
 const context=await browser.newContext({viewport:{width:1438,height:940},recordVideo:{dir:`${folder}/video`,size:{width:1438,height:940}}})
 const fixture=await installJourneyFixture(context,{unexpected,writes});fixture.currentLesson=3
 const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text())})
 await page.goto('http://127.0.0.1:5173/hsk/1',{waitUntil:'domcontentloaded',timeout:90000})
 const view=page.locator('.illustrated-climb');await view.locator('canvas').waitFor();await page.locator('.illustrated-climb[data-ready=true]').waitFor({timeout:60000})
 await page.waitForFunction(()=>document.querySelector('.illustrated-climb').dataset.moving==='false')
 for(let step=0;step<=9;step++){
  if(step){await page.getByRole('button',{name:'Lên một bậc',exact:true}).click();await page.waitForFunction(expected=>{const el=document.querySelector('.illustrated-climb');return el.dataset.moving==='false'&&Math.abs(JSON.parse(el.dataset.motion).progress-expected)<.0001},step/10,{timeout:20000})}
  const frame=await view.getAttribute('data-motion');frames.push({step,frame:JSON.parse(frame)})
  if([0,3,6,9].includes(step))await page.screenshot({path:`${folder}/desktop-step-${step}.png`})
 }
 await context.close()
}finally{await browser.close();await writeFile(`${folder}/inspection.json`,JSON.stringify({frames,errors,unexpected,writes},null,2))}
console.log(JSON.stringify({errors,unexpected,writes,frames:frames.length}))
