import assert from 'node:assert/strict'
import {mkdir,writeFile} from 'node:fs/promises'
import {resolve} from 'node:path'
import {chromium} from 'playwright'
import {installJourneyFixture} from './journey-fixture.mjs'
const folder=resolve('../.impeccable/review/spatial-great-wall'),origin='http://127.0.0.1:5173'
await mkdir(folder,{recursive:true})
const browser=await chromium.launch({args:['--enable-unsafe-swiftshader']}),unexpected=[],writes=[],results=[]
try{
 const context=await browser.newContext({viewport:{width:320,height:920}});await installJourneyFixture(context,{unexpected,writes})
 const page=await context.newPage();await page.goto(origin+'/hsk/1',{waitUntil:'domcontentloaded'});await page.locator('.forward-viewport[data-ready=true]').waitFor({timeout:60000});await page.waitForTimeout(500)
 await page.screenshot({path:`${folder}/narrow-320.png`});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
 const distance=await page.locator('.forward-viewport').getAttribute('data-world-distance')
 await page.setViewportSize({width:760,height:600});await page.waitForTimeout(500)
 assert(Math.abs(Number(await page.locator('.forward-viewport').getAttribute('data-world-distance'))-Number(distance))<.1)
 const hud=await page.locator('.forward-navigation').boundingBox();assert(hud.y>=0&&hud.y+hud.height<=600)
 await page.screenshot({path:`${folder}/landscape-760.png`});results.push('320px overflow and landscape resize preserve position/HUD')
 const loss=await page.locator('canvas').evaluate(canvas=>{const gl=canvas.getContext('webgl2'),extension=gl.getExtension('WEBGL_lose_context');if(extension){extension.loseContext();return'extension'}canvas.dispatchEvent(new Event('webglcontextlost',{cancelable:true}));return'synthetic'})
 await page.locator('.forward-overview').waitFor();assert.equal(await page.locator('.forward-overview > li').count(),16)
 await page.screenshot({path:`${folder}/context-loss-760.png`});results.push({contextLoss:loss});await context.close()
 for(const mode of ['reduced','no-webgl','missing-art']){
  const ctx=await browser.newContext({viewport:{width:390,height:920},reducedMotion:mode==='reduced'?'reduce':'no-preference'});await installJourneyFixture(ctx,{unexpected,writes})
  if(mode==='no-webgl')await ctx.addInitScript(()=>{Object.defineProperty(window,'WebGL2RenderingContext',{value:undefined,configurable:true})})
  if(mode==='missing-art')await ctx.route('**/academy/great-wall/spatial-v1/pines.webp',route=>route.abort())
  const p=await ctx.newPage();await p.goto(origin+'/hsk/1',{waitUntil:'domcontentloaded'});await p.locator('.forward-overview').waitFor({timeout:30000});assert.equal(await p.locator('.forward-overview > li').count(),16)
  await p.screenshot({path:`${folder}/${mode}-390.png`});results.push(mode);await ctx.close()
 }
 assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
}finally{await browser.close();await writeFile(`${folder}/fallback-verification.json`,JSON.stringify({results,unexpected,writes},null,2))}
console.log('PASS: narrow/landscape, context loss, reduced motion, unavailable WebGL and missing artwork recover to usable navigation.')
