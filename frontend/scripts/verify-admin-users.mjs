import assert from 'node:assert/strict'
import {mkdir} from 'node:fs/promises'
import {chromium} from 'playwright'

const origin=process.env.ADMIN_USERS_REVIEW_ORIGIN??'http://127.0.0.1:5174'
const output=new URL('../../.impeccable/review/admin-users/',import.meta.url)
await mkdir(output,{recursive:true})
const browser=await chromium.launch(),errors=[],unexpected=[],writes=[]
const user={id:'fixture-user',full_name:'Nguyễn Minh An',email:'minh.an@example.invalid',role:'LEARNER',is_active:true,created_at:'2026-11-14T00:00:00Z',completed_lessons:2}
try {
 for(const width of [1440,768,390]) {
  const context=await browser.newContext({viewport:{width,height:950}})
  await context.route('**/api/v1/**',async route=>{
   const req=route.request(),url=new URL(req.url()),path=url.pathname.split('/api/v1')[1]
   if(req.method()==='OPTIONS'||path==='/auth/logout')return route.fulfill({status:204})
   if(req.method()!=='GET')writes.push(path)
   if(path==='/auth/me')return route.fulfill({json:{id:'fixture-admin',full_name:'Quản trị viên',email:'admin@example.invalid',role:'ADMIN'}})
   if(path==='/admin/users')return route.fulfill({json:{items:[user],total:1,page:1,page_size:20}})
   if(path==='/admin/users/fixture-user')return route.fulfill({json:{...user,pronunciation_completed:true,graded_attempts:4,average_score:85,lesson_activity:[{lesson_id:'fixture-lesson',title:'Xin chào',lesson_number:1,hsk_level:1,started_at:'2026-11-14T00:00:00Z',theory_completed_at:'2026-11-14T00:00:00Z',completed_at:'2026-11-14T00:00:00Z'}]}})
   unexpected.push(path);return route.fulfill({status:404,json:{}})
  })
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message))
  await page.goto(origin+'/admin/users');await page.getByText(user.email,{exact:true}).waitFor();await page.evaluate(()=>document.fonts.ready)
  assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))
  await page.screenshot({path:new URL(`list-${width}.png`,output).pathname.replace(/^\/([A-Z]:)/,'$1'),fullPage:true})
  await page.getByRole('link',{name:'Xem '+user.full_name,exact:true}).click();await page.getByText('85.0%',{exact:true}).waitFor()
  assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))
  await page.screenshot({path:new URL(`detail-${width}.png`,output).pathname.replace(/^\/([A-Z]:)/,'$1'),fullPage:true})
  await context.close()
 }
 assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);assert.deepEqual(writes,[])
 console.log('PASS: list/detail at 1440, 768 and 390 px; no page errors, overflow or writes; all APIs mocked.')
}finally{await browser.close()}
