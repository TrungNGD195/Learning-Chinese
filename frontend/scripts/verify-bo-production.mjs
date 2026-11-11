import assert from 'node:assert/strict'
import { mkdir,writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const origin=process.env.BO_FRONTEND_ORIGIN||'http://127.0.0.1:5174'
const folder=resolve('../.impeccable/review/bo-production')
await mkdir(folder,{recursive:true})
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true})
const id={hsk:'00000000-0000-4000-8000-000000000001',lesson:'00000000-0000-4000-8000-000000000002',assessment:'00000000-0000-4000-8000-000000000003',attempt:'00000000-0000-4000-8000-000000000004'}
const codes=['INITIALS','FINALS','TONES'],counts=[21,36,5]
const timestamp='2026-11-03T10:00:00Z'
const results=[],errors=[],unknown=[],resources=[]
const vocabulary=[['你好','nǐ hǎo','xin chào','你好！','Hai thanh 3 liên tiếp: thanh đầu đọc gần thanh 2, nhưng giữ nguyên dấu trong pinyin.'],['八','bā','tám','八个人。','Âm b không bật hơi; đối chiếu với p.'],['女','nǚ','phụ nữ','她是女生。','Giữ hai chấm của ü sau n.'],['马','mǎ','ngựa','一匹马。','Thanh 3 khi đọc riêng hạ giọng rồi nâng lên.']].map(([hanzi,pinyin,meaning,example,note],index)=>({id:'vocab-link-'+index,order_index:index+1,note,example,item:{id:'vocab-'+index,hanzi,pinyin,vietnamese_meaning:meaning,part_of_speech:index?'danh từ':'lời chào'}}))
const unit=unlocked=>({id:'unit-1',order_index:1,unit_type:'LESSON',state:unlocked?'AVAILABLE':'LOCKED',lesson:{id:id.lesson,lesson_number:1,title:'你好 · Xin chào',status:'PUBLISHED'},assessment:null})
const lesson={id:id.lesson,hsk_level_id:id.hsk,lesson_number:1,title:'你好 · Xin chào',description:'Làm quen với lời chào và những chữ Hán đầu tiên.',vocabulary,grammar:[],assessment_ids:[id.assessment]}
const assessment={id:id.assessment,type:'LESSON_EXERCISE',title:'Luyện tập · Lời chào đầu tiên',description:'Chọn câu chào phù hợp.',pass_threshold:80,questions:[{id:'question-1',type:'multiple_choice',prompt:'Chọn lời chào: Xin chào!',order_index:1,points:1,config:{},options:[{id:'option-1',option_text:'你好！'},{id:'option-2',option_text:'谢谢！'}]}]}
function install(context,{publicPage=false,admin=false}={}){
  const state={section:0,step:0,done:false,viewed:new Set(),posts:[],authenticated:!publicPage}
  const pron=()=>({sections:codes.map((code,i)=>({id:'section-'+i,code,completed_at:state.section>i?timestamp:null,total_steps:counts[i]})),current_section:codes[state.section]??null,step_index:state.step,total_steps:counts[state.section]??0,completed_at:state.done?timestamp:null,can_finish:state.section===3&&!state.done})
  const dashboard=()=>({current_hsk:{id:id.hsk,level_number:1,title:'HSK 1'},current_unit:unit(state.done),current_lesson:state.done?{id:id.lesson,lesson_number:1,title:lesson.title,description:lesson.description}:null,progress_percentage:0,continue_learning:state.done?{type:'LESSON',lesson_id:id.lesson,assessment_id:null}:{type:'PRONUNCIATION',section_id:'section-'+Math.min(state.section,2),code:codes[state.section]??'TONES'}})
  const progress=()=>({lesson_id:id.lesson,started_at:timestamp,theory_completed_at:state.viewed.size===vocabulary.length?timestamp:null,completed_at:null,vocabulary:vocabulary.map(v=>({id:v.id,viewed:state.viewed.has(v.id)})),grammar:[]})
  context.route('**/api/v1/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname.split('/api/v1')[1],method=request.method()
    const headers={'access-control-allow-origin':origin,'access-control-allow-credentials':'true','access-control-allow-methods':'GET,POST,OPTIONS','access-control-allow-headers':'content-type'}
    const reply=(json,status=200)=>route.fulfill({status,json,headers})
    if(method==='OPTIONS')return route.fulfill({status:204,headers})
    if(method==='POST')state.posts.push(path)
    if(path==='/auth/me')return state.authenticated?reply({id:'user-1',email:'learner@example.invalid',full_name:'Nguyễn An',role:admin?'ADMIN':'LEARNER'}):reply({error:{code:'UNAUTHENTICATED',message:'Sign in required',details:null}},401)
    if(path==='/auth/refresh')return reply({error:{code:'INVALID_REFRESH_TOKEN',message:'Sign in required',details:null}},401)
    if(path==='/me/dashboard')return reply(dashboard())
    if(path==='/pronunciation/lesson')return reply(pron())
    if(path==='/pronunciation/lesson/advance'){
      const body=request.postDataJSON()
      if(body.section_code!==codes[state.section]||body.step_index!==state.step||state.step>=counts[state.section])return reply({error:{code:'PRONUNCIATION_STEP_CONFLICT',message:'Wrong step',details:null}},409)
      state.step++;return reply(pron())
    }
    if(/^\/pronunciation\/section-\d\/complete$/.test(path)){
      if(state.step!==counts[state.section]||!path.includes('section-'+state.section))return reply({error:{code:'PRONUNCIATION_INCOMPLETE',message:'Not complete',details:null}},409)
      state.section++;state.step=0;return reply({section_id:'section-'+(state.section-1),completed_at:timestamp})
    }
    if(path==='/pronunciation/lesson/complete'){
      if(state.section!==3)return reply({error:{code:'PRONUNCIATION_INCOMPLETE',message:'Not complete',details:null}},409)
      state.done=true;return reply(pron())
    }
    if(path==='/hsk-levels')return reply([{id:id.hsk,level_number:1,title:'HSK 1',description:'Những bài học đầu tiên.',state:state.done?'AVAILABLE':'LOCKED'}])
    if(path==='/hsk-levels/'+id.hsk+'/curriculum'||path==='/me/progress/hsk/'+id.hsk)return reply({hsk:{id:id.hsk,level_number:1,title:'HSK 1'},units:[unit(state.done)],progress_percentage:0})
    if(path==='/me/progress')return reply({current_hsk:state.done?1:null,progress_percentage:0})
    if(path==='/lessons/'+id.lesson)return state.done?reply(lesson):reply({error:{code:'LESSON_LOCKED',message:'Complete pronunciation first',details:null}},403)
    if(path==='/me/progress/lessons/'+id.lesson)return reply(progress())
    if(path.includes('/theory/vocabulary/')){const link=path.split('/vocabulary/')[1].split('/')[0];state.viewed.add(link);return reply({viewed_at:timestamp,theory_completed_at:state.viewed.size===vocabulary.length?timestamp:null})}
    if(path==='/assessments/'+id.assessment)return reply(assessment)
    if(path==='/assessments/'+id.assessment+'/attempts')return reply({attempt_id:id.attempt,assessment_id:id.assessment,attempt_number:1,status:'IN_PROGRESS',answers:[]})
    if(path==='/me/assessment-attempts/'+id.attempt)return reply({id:id.attempt,assessment_id:id.assessment,attempt_number:1,status:'GRADED',score:100,passed:true,submitted_at:timestamp,answers:[]})
    if(path==='/assessment-attempts/'+id.attempt+'/submit')return reply({attempt_id:id.attempt,status:'GRADED',score:100,passed:true})
    if(path==='/admin/hsk-levels')return reply([{id:id.hsk,level_number:1,title:'HSK 1'}])
    if(path==='/admin/lessons')return reply({items:[],total:0,page:1,page_size:20})
    unknown.push({path,method});return reply({error:{code:'NOT_FOUND',message:'No fixture for path',details:null}},404)
  })
  return state
}
function watch(page){page.on('pageerror',error=>errors.push(error.message));page.on('response',response=>{if(response.status()>=400&&!response.url().includes('/api/v1/'))resources.push({url:response.url(),status:response.status()})})}
async function capture(page,name,width){await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(img=>img.decode()));const sources=new Set([...document.querySelectorAll('*')].flatMap(el=>[...getComputedStyle(el).backgroundImage.matchAll(/url\("?([^"\)]+)"?\)/g)].map(match=>match[1])));await Promise.all([...sources].map(src=>{const img=new Image();img.src=src;return img.decode()}));window.scrollTo({top:0,behavior:'instant'})});await page.evaluate(()=>new Promise(requestAnimationFrame));const metrics=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight}));assert(metrics.width<=width,name+' overflow '+width);results.push({name,...metrics});await page.screenshot({path:folder+'/'+name+'-'+width+'.png',fullPage:true})}
async function visit(page,path){await page.goto(origin+path,{waitUntil:'load',timeout:60000});await page.locator('[data-layout]').waitFor()}
try{
  for(const width of [1440,768,390]){
    const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'}),state=install(context)
    const page=await context.newPage();watch(page)
    await visit(page,'/dashboard');await page.getByRole('link',{name:'Continue Learning',exact:true}).waitFor()
    assert.equal(await page.getByRole('link',{name:'Continue Learning',exact:true}).getAttribute('href'),'/pronunciation/lesson')
    await capture(page,'dashboard-locked',width)
    await visit(page,'/pronunciation');await page.getByText('Hoàn thành bài phát âm để mở khóa.',{exact:true}).waitFor()
    assert.equal(await page.getByRole('link',{name:'Mở HSK 1',exact:true}).count(),0)
    await capture(page,'journey-locked',width)
    await visit(page,'/pronunciation/lesson');await page.locator('.pronunciation-session__symbol').waitFor()
    assert.equal(await page.locator('.pronunciation-session__symbol').innerText(),'b')
    await page.getByText('Nguồn bài học và cách sử dụng',{exact:true}).click()
    assert((await page.locator('.academy-source').innerText()).includes('HSK1'))
    await capture(page,'pronunciation-initials',width)
    if(width===1440){
      for(let section=0;section<3;section++){
        for(let step=0;step<counts[section];step++){
          if(section===1&&step===0)await capture(page,'pronunciation-finals',width)
          if(section===2&&step===2)await capture(page,'pronunciation-tones',width)
          await page.getByRole('button',{name:'Tiếp theo',exact:true}).click()
          if(step<counts[section]-1)await page.waitForFunction(({code,index})=>document.querySelector('.pronunciation-session__heading>span')?.textContent?.trim()===String(index+2)+' / '+({INITIALS:21,FINALS:36,TONES:5}[code]),{code:codes[section],index:step})
          else await page.getByRole('button',{name:'Hoàn thành '+['thanh mẫu','vận mẫu','thanh điệu'][section],exact:true}).waitFor()
        }
        assert(!state.done)
        await page.getByRole('button',{name:'Hoàn thành '+['thanh mẫu','vận mẫu','thanh điệu'][section],exact:true}).click()
        if(section<2)await page.getByRole('button',{name:'Tiếp theo',exact:true}).waitFor()
      }
      await page.getByRole('button',{name:'Hoàn thành bài học',exact:true}).waitFor();assert(!state.done)
      await capture(page,'pronunciation-ready-to-finish',width)
      await page.getByRole('button',{name:'Hoàn thành bài học',exact:true}).click()
      await page.getByRole('link',{name:'Mở HSK 1',exact:true}).waitFor();assert(state.done)
      assert.equal(state.posts.filter(p=>p==='/pronunciation/lesson/advance').length,62)
    }else{
      state.section=2;state.step=2;await visit(page,'/pronunciation/lesson');await page.locator('.academy-tone-diagram').waitFor();await capture(page,'pronunciation-tones',width)
      state.section=3;state.step=0;state.done=true;await visit(page,'/pronunciation')
    }
    await capture(page,'journey-unlocked',width)
    await visit(page,'/hsk/1');await page.getByRole('link',{name:'Open Lesson',exact:true}).waitFor();await capture(page,'hsk-curriculum',width)
    await visit(page,'/lessons/'+id.lesson);await page.getByRole('heading',{name:'你好',exact:true}).waitFor();assert.equal(state.viewed.size,0)
    await page.getByRole('button',{name:'Show details',exact:true}).first().click()
    await page.waitForFunction(()=>document.querySelector('.lesson-theory-card .ui-status-badge')?.textContent==='Viewed')
    assert(state.viewed.has('vocab-link-0'))
    await capture(page,'lesson',width)
    const hanzi=await page.locator('.lesson-theory-card__hanzi').first().evaluate(el=>parseFloat(getComputedStyle(el).fontSize));assert(hanzi>=43)
    assert.equal(await page.locator('.academy-reading-settings').count(), 0)
    assert.equal(await page.locator('.bo-shell').evaluate(el=>getComputedStyle(el).getPropertyValue('--reader-font-size').trim()),'21px')
    await capture(page,'lesson-large-type',width)
    await visit(page,'/assessments/'+id.assessment);await page.getByRole('button',{name:'Start / Resume Assessment',exact:true}).waitFor();await capture(page,'assessment',width)
    await visit(page,'/assessment-attempts/'+id.attempt+'/result');await page.getByText('Passed',{exact:true}).waitFor();await capture(page,'assessment-result',width)
    await visit(page,'/companions');await page.getByRole('heading',{name:'Bo · Người dẫn đường',exact:true}).waitFor();await page.getByRole('button',{name:'Ăn mừng',exact:true}).click();await capture(page,'companions',width)
    await visit(page,'/profile');await page.getByRole('heading',{name:'Account details',exact:true}).waitFor();await capture(page,'profile',width)
    assert(!(await page.locator('body').innerText()).includes('Mây'))
    await context.close()
  }
  for(const width of [1440,390]){
    const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});install(context,{publicPage:true});const page=await context.newPage();watch(page)
    await page.goto(origin+'/login',{waitUntil:'load'});await page.getByRole('heading',{name:'Login',exact:true}).waitFor();await capture(page,'login',width);await context.close()
    const admin=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});install(admin,{admin:true});const ap=await admin.newPage();watch(ap);await visit(ap,'/admin/lessons');await ap.getByRole('heading',{name:'Lessons',exact:true}).waitFor();await capture(ap,'admin-lessons',width);await admin.close()
  }
  assert.deepEqual(errors,[]);assert.deepEqual(unknown,[]);assert.deepEqual(resources,[])
  await writeFile(folder+'/browser-verification.json',JSON.stringify({results,errors,unknown,resources,progression:'62 ordered advances; HSK1 link unavailable before final completion and available afterward',fixtureScope:'Real frontend routes with deterministic API fixtures; backend gates separately tested against dedicated PostgreSQL test database'},null,2))
  console.log(JSON.stringify({captures:results.length,errors,unknown,resources,progression:'passed',vocabularyWrites:'passed',typeSettings:'passed'}))
}finally{await browser.close()}
