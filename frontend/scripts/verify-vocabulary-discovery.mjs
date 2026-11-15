import assert from 'node:assert/strict'
import {mkdir} from 'node:fs/promises'
import {fileURLToPath} from 'node:url'
import {chromium} from 'playwright'

const origin=process.argv[2]??'http://localhost:5173'
const folder=new URL('../../.impeccable/review/vocabulary-discovery/',import.meta.url)
await mkdir(folder,{recursive:true})
const words=[{id:'ni',order_index:1,item:{id:'catalog-ni',hanzi:'你',pinyin:'nǐ',vietnamese_meaning:'bạn, cậu; anh, chị (người đang được nói chuyện cùng)',part_of_speech:'đại từ'},example:'你是学生。\nNǐ shì xuésheng.\nBạn là học sinh.',note:'Dùng 你 để nói trực tiếp với người đang trò chuyện cùng bạn.'},{id:'jiaozi',order_index:2,item:{id:'catalog-jiaozi',hanzi:'饺子',pinyin:'jiǎozi',vietnamese_meaning:'sủi cảo',part_of_speech:'danh từ'},example:'我喜欢吃饺子。\nWǒ xǐhuan chī jiǎozi.\nTôi thích ăn sủi cảo.',note:'子 trong 饺子 đọc thanh nhẹ.'},{id:'one',order_index:3,item:{id:'catalog-one',hanzi:'一',pinyin:'yī',vietnamese_meaning:'một',part_of_speech:'số từ'},example:'一个人',note:null}]
words.push(...[
 {hanzi:'中国',pinyin:'Zhōngguó',meaning:'Trung Quốc'},
 {hanzi:'爸爸',pinyin:'bàba',meaning:'bố, ba, cha'},
 {hanzi:'老公/丈夫',pinyin:'lǎogōng / zhàngfu',meaning:'chồng; cách gọi người bạn đời nam trong những hoàn cảnh giao tiếp khác nhau; nội dung dài dùng để kiểm tra xuống dòng'},
 {hanzi:'八',pinyin:'bā',meaning:'tám'},
].map((word,index)=>({id:`layout-${index}`,order_index:index+4,item:{id:`catalog-layout-${index}`,hanzi:word.hanzi,pinyin:word.pinyin,vietnamese_meaning:word.meaning,part_of_speech:index===2?null:'danh từ'},example:null,note:null})))
const browser=await chromium.launch()
try{
 for(const width of [1600,1024,390,320]){
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'})
  const calls=[],errors=[],writes=[]
  await context.route('**/api/v1/**',route=>{
   const request=route.request(),path=new URL(request.url()).pathname.split('/api/v1')[1]
   if(path==='/auth/logout')return route.fulfill({status:204})
   if(request.method()!=='GET')writes.push(path)
   const reply=json=>route.fulfill({json})
   if(path==='/auth/me')return reply({id:'fixture-student',full_name:'Nguyễn An',email:'review@example.invalid',role:'LEARNER'})
   if(path==='/hsk-levels')return reply([{id:'hsk-1',level_number:1,title:'HSK 1',state:'AVAILABLE'}])
   if(path==='/lessons/discovery-fixture')return reply({id:'discovery-fixture',hsk_level_id:'hsk-1',lesson_number:1,title:'你好 · Xin chào',description:null,vocabulary:words,grammar:[],readings:[],assessment_ids:[]})
   if(path==='/me/progress/lessons/discovery-fixture')return reply({lesson_id:'discovery-fixture',started_at:'2026-11-15T00:00:00Z',theory_completed_at:null,completed_at:null,vocabulary:words.map(word=>({id:word.id,viewed:true})),grammar:[],readings:[]})
   calls.push(path);return route.fulfill({status:404,json:{}})
  })
  const page=await context.newPage()
  page.on('pageerror',error=>errors.push(error.message))
  await page.goto(origin+'/lessons/discovery-fixture/vocabulary/ni')
  const trigger=page.getByRole('button',{name:'Khám phá thêm về 你',exact:true})
  await trigger.waitFor()
  await page.evaluate(()=>document.fonts.ready)
  await page.locator('.vocabulary-study-card__media .academy-word-illustration').evaluate(async e=>{const image=new Image();image.src=getComputedStyle(e).backgroundImage.slice(5,-2);await image.decode()})
  assert.equal(await trigger.locator('button,a').count(),0)
  const art=await page.locator('.vocabulary-study-card__media .academy-word-illustration').boundingBox()
  const discoveryBounds=await trigger.boundingBox()
  assert(art.height>discoveryBounds.height,'Illustration must be larger than discovery')
  const exampleBounds=await page.locator('.vocabulary-study-card__example').boundingBox()
  assert(discoveryBounds.y>=art.y+art.height,'Discovery must be below illustration')
  if(width===1600) assert(discoveryBounds.y>exampleBounds.y,'Discovery must start below example divider')
  assert(await page.locator('.vocabulary-study-card__identity').evaluate(e=>e.querySelector('.vocabulary-study-card__pos').compareDocumentPosition(e.querySelector('.vocabulary-study-card__meaning'))&Node.DOCUMENT_POSITION_FOLLOWING))
  assert.equal(await page.locator('.vocabulary-study-card__note .academy-companion').count(),0)
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await page.evaluate(()=>window.scrollTo(0,0))
  await page.screenshot({path:fileURLToPath(new URL(`word-${width}.png`,folder)),fullPage:true})
  await trigger.click()
  const popup=page.getByRole('dialog',{name:'Một lời chào, hai cách xưng hô',exact:true})
  await popup.waitFor()
  const bounds=await popup.boundingBox()
  assert(bounds.width<width-20&&bounds.height<950)
  await page.screenshot({path:fileURLToPath(new URL(`popup-${width}.png`,folder))})
  await page.keyboard.press('Escape')
  assert.equal(await page.getByRole('dialog').count(),0)
  assert(await trigger.evaluate(e=>e===document.activeElement))
  await page.locator('.lesson-word-index a').nth(1).click()
  await page.getByRole('button',{name:'Khám phá thêm về 饺子',exact:true}).waitFor()
  await page.locator('.lesson-word-index a').nth(2).click()
  await page.getByRole('heading',{name:'一',exact:true}).waitFor()
  assert.equal(await page.locator('.vocabulary-discovery-entry').count(),0)
  let expectedSize=null
  for(let index=0;index<words.length;index++){
   await page.locator('.lesson-word-index a').nth(index).click()
   await page.getByRole('heading',{name:words[index].item.hanzi,exact:true}).waitFor()
   const frame=page.locator('.vocabulary-study-card__artwork')
   const size=await frame.boundingBox()
   expectedSize??=size.width
   assert(Math.abs(size.width-size.height)<1,'Artwork must remain square')
   assert(Math.abs(size.width-expectedSize)<1,'All words must use identical image dimensions')
   const identity=page.locator('.vocabulary-study-card__identity')
   assert(await identity.evaluate(e=>e.scrollWidth<=e.clientWidth+1),'Long word/meaning must wrap')
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
   assert.equal(await page.locator('.vocabulary-study-card').count(),1)
   assert.equal(await page.locator('.vocabulary-study-card__writing').count(),1)
   if(index===5){assert(await page.locator('.vocabulary-study-card__artwork-placeholder').isVisible())}
  }
  assert.deepEqual({calls,errors,writes},{calls:[],errors:[],writes:[]})
  await context.close()
 }
 console.log('Vocabulary layout/discovery verified at 1600, 1024, 390 and 320px; identical square frames across words, countries, numbers, family and missing artwork; optional content, whole-block click, part-of-speech order, popup/focus and no API mutations.')
}finally{await browser.close()}
