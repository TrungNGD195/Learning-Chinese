import assert from 'node:assert/strict'
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const pack=JSON.parse(await readFile('../backend/content/hsk1/lesson-04-practice.json','utf8'))
const origin=process.env.BO_FRONTEND_ORIGIN || 'http://127.0.0.1:5173'
const folder=resolve('../.impeccable/review/practice-workspace')
await mkdir(folder,{recursive:true})
const qs=pack.questions.map((q,i)=>({...q,id:`question-${i+1}`,options:(q.options||[]).map((o,j)=>({...o,id:`option-${i}-${j}`}))}))
const learner=qs.map(q=>({...q,reference_answer:undefined,rubric:undefined,options:q.options.map(({id,option_text})=>({id,option_text})),config:Object.fromEntries(Object.entries(q.config).filter(([key])=>!['accepted_answers','correct_pairs','correct_order'].includes(key)))}))
const browser=await chromium.launch()
const captures=[],errors=[],unexpected=[]
try {
 for(const width of [1440,390,320]) {
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'})
  let submitted=null
  await context.route('**/api/v1/**',async route=>{
   const request=route.request(),path=new URL(request.url()).pathname.split('/api/v1')[1]
   const reply=json=>route.fulfill({json})
   if(request.method()==='OPTIONS'||path==='/auth/logout')return route.fulfill({status:204})
   if(path==='/auth/me')return reply({id:'learner',email:'review@example.invalid',role:'LEARNER',full_name:'Nguyễn An'})
   if(path==='/me/dashboard')return reply({continue_learning:null})
   if(path==='/assessments/practice'&&request.method()==='GET')return reply({id:'practice',type:'LESSON_EXERCISE',title:'Bài 4 · Luyện tập tổng hợp',description:pack.description,pass_threshold:80,questions:learner})
   if(path==='/assessments/practice/attempts')return reply({id:'fixture-attempt',assessment_id:'practice',attempt_number:1,status:'IN_PROGRESS',started_at:new Date().toISOString()})
   if(path==='/assessment-attempts/fixture-attempt/submit') { submitted=request.postDataJSON();return reply({attempt_id:'fixture-attempt',status:'GRADED',score:96.67,passed:true}) }
   if(path==='/me/assessment-attempts/fixture-attempt')return reply({id:'fixture-attempt',assessment_id:'practice',attempt_number:1,status:'GRADED',score:96.67,passed:true,submitted_at:new Date().toISOString(),answers:qs.map((q,i)=>({question_id:q.id,type:q.type,prompt:q.prompt,answer:submitted.answers.find(a=>a.question_id===q.id).answer,grading_status:'GRADED',score:i===0?0:1,is_correct:i!==0,feedback:q.rubric,rubric:q.rubric,config:q.config,reference_answer:q.type==='multiple_choice'?q.options.find(o=>o.is_correct).option_text:q.reference_answer||null,...(q.type==='multiple_choice'?{selected_option_text:q.options.find(o=>o.id===submitted.answers.find(a=>a.question_id===q.id).answer.option_id)?.option_text}:{} )}))})
   unexpected.push(path);return route.fulfill({status:404,json:{error:{code:'FIXTURE_ONLY',message:'Unexpected request'}}})
  })
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message))
  async function capture(name) {
   await page.evaluate(()=>document.fonts.ready)
   const metrics=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}))
   assert(metrics.scroll<=width+1,`${name}: overflow ${metrics.scroll}/${width}`)
   await page.screenshot({path:`${folder}/${name}-${width}.png`,fullPage:true,animations:'disabled'})
   captures.push({name,...metrics})
  }
  for(let attempt=0;;attempt++) {
   try { await page.goto(origin+'/assessments/practice');break }
   catch(error) { if(attempt>=4)throw error;await page.waitForTimeout(1000) }
  }
  await page.getByRole('button',{name:'Bắt đầu / Tiếp tục luyện tập'}).waitFor()
  await capture('start')
  await page.getByRole('button',{name:'Bắt đầu / Tiếp tục luyện tập'}).click()
  await page.locator('.practice-question-grid button').first().waitFor()
  assert.equal(await page.locator('.practice-question-grid button').count(),30)
  for(let i=0;i<qs.length;i++) {
   const q=qs[i]
   await page.getByRole('button',{name:new RegExp(`^Câu ${i+1},`)}).click()
   const section=page.locator('.assessment-question')
   if([0,4,8,12,16,22,26].includes(i))await capture(['listening','image','grammar','matching','fill','ordering','reading'][[0,4,8,12,16,22,26].indexOf(i)])
   if(q.type==='multiple_choice') {
    const option=q.options.find(o=>i===0?!o.is_correct:o.is_correct)
    await section.getByRole('radio',{name:option.option_text,exact:true}).check()
   } else if(q.type==='fill_blank') await section.getByRole('textbox').fill(q.reference_answer)
   else if(q.type==='matching') for(const pair of q.config.correct_pairs) {
    const word=q.config.left_items.find(item=>item.id===pair.left_id).text
    await section.getByRole('combobox',{name:`Ghép với ${word}`,exact:true}).selectOption(pair.right_id)
   } else {
    for(let index=0;index<q.config.correct_order.length;index++) {
     const text=q.config.items.find(item=>item.id===q.config.correct_order[index]).text
     for(let step=0;step<q.config.correct_order.length;step++) {
      const displayed=await section.locator('.reorder-list li > span').allTextContents()
      if(displayed.indexOf(text)<=index)break
      await section.getByRole('button',{name:`Đưa ${text} lên`,exact:true}).click()
     }
    }
    await section.getByRole('button',{name:'Dùng thứ tự này'}).click()
   }
  }
  await page.getByRole('button',{name:'Nộp bài',exact:true}).click()
  await page.getByRole('heading',{name:'Xem lại bài làm'}).waitFor()
  assert.equal(submitted.answers.length,30)
  assert.equal(await page.locator('.assessment-answer-card').count(),30)
  await page.getByRole('button',{name:'Chỉ xem câu cần ôn'}).click()
  assert.equal(await page.locator('.assessment-answer-card').count(),1)
  await page.getByRole('heading',{name:'Vì sao câu này chưa đúng?'}).waitFor()
  assert((await page.locator('.practice-explanation').textContent()).includes(qs[0].rubric))
  await capture('result-mistake')
  await context.close()
 }
 assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[])
} finally {
 await browser.close()
 await writeFile(`${folder}/verification.json`,JSON.stringify({captures,errors,unexpected,fixture:'All API requests intercepted; real accounts and attempts unchanged.'},null,2))
}
console.log(`PASS: ${captures.length} captures; 30 answers submitted at each width, mistake review and explanations verified.`)
