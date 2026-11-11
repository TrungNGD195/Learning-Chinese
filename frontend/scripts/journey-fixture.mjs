export async function installJourneyFixture(context,{writes=[],unexpected=[],lessonTitles=[]}={}) {
  const total={1:15,2:10,3:15},time='2026-11-08T00:00:00Z'
  const state={foundation:true,partial:false,currentLesson:7}
  await context.route('**/api/v1/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname.split('/api/v1')[1]
    const reply=(json,status=200)=>route.fulfill({json,status})
    if(request.method()==='OPTIONS'||path==='/auth/logout')return route.fulfill({status:204})
    if(request.method()!=='GET')writes.push(path)
    if(path==='/auth/me')return reply({id:'fixture-student',full_name:'Nguyễn An',email:'review@example.invalid',role:'LEARNER'})
    if(path==='/hsk-levels')return reply([1,2,3].map(n=>({id:`hsk-${n}`,level_number:n,title:`HSK ${n}`,description:null,state:n===1&&!state.foundation?'LOCKED':'AVAILABLE'})))
    if(path==='/me/dashboard')return reply({current_hsk:{id:'hsk-1',level_number:1,title:'HSK 1'},current_lesson:null,current_unit:null,progress_percentage:40,continue_learning:{type:'LESSON',lesson_id:`lesson-1-${state.currentLesson}`}})
    if(path==='/me/progress')return reply({current_hsk:1,progress_percentage:40,pronunciation_complete:state.foundation,hsk_levels:[]})
    if(path==='/pronunciation/lesson')return reply({sections:['INITIALS','FINALS','TONES','SANDHI'].map((code,i)=>({id:code,code,title:code,total_steps:[21,36,5,12][i],completed_at:state.foundation?time:null})),current_section:null,step_index:0,total_steps:0,completed_at:state.foundation?time:null,can_finish:false})
    const curriculum=path.match(/^\/hsk-levels\/hsk-(\d)\/curriculum$/)
    if(curriculum) {
      const level=Number(curriculum[1])
      const units=Array.from({length:state.partial?(level===1?1:0):total[level]},(_,i)=>({id:`unit-${level}-${i+1}`,order_index:i+1,unit_type:'LESSON',state:level===1&&!state.foundation?'LOCKED':i<state.currentLesson-1?'COMPLETED':i===state.currentLesson-1?'AVAILABLE':'LOCKED',lesson:{id:`lesson-${level}-${i+1}`,lesson_number:i+1,title:lessonTitles[i]??['你好 · Xin chào','Gia đình của tôi','Những người bạn','Ngày hôm nay','Cùng nhau học tập'][i%5],status:'PUBLISHED'},assessment:null}))
      return reply({hsk:{id:`hsk-${level}`,level_number:level,title:`HSK ${level}`},units:units.reverse()})
    }
    const lesson=path.match(/^\/lessons\/(lesson-(\d)-(\d+))$/)
    if(lesson)return reply({id:lesson[1],hsk_level_id:`hsk-${lesson[2]}`,lesson_number:Number(lesson[3]),title:'你好 · Xin chào',description:null,vocabulary:[],grammar:[],readings:[],assessment_ids:[]})
    const progress=path.match(/^\/me\/progress\/lessons\/(lesson-\d-\d+)$/)
    if(progress)return reply({lesson_id:progress[1],started_at:time,theory_completed_at:null,completed_at:null,vocabulary:[],grammar:[],readings:[]})
    unexpected.push(path);return reply({error:{code:'FIXTURE_ONLY',message:'Unexpected request'}},404)
  })
  return state
}
