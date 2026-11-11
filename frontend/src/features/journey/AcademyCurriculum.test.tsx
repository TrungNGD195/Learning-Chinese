import {fireEvent,render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {GreatWallJourneyPage} from './GreatWallJourneyPage'
import {getCurriculum,getHskLevels} from '../curriculum/api'
import {getPronunciationLesson} from '../pronunciation/api'
import {getDashboard} from '../dashboard/api'
import {getProgressOverview} from '../progress/api'
import type {JourneyUnit} from './journeyData'

vi.mock('../dashboard/api',()=>({getDashboard:vi.fn()}))
vi.mock('../curriculum/api',()=>({getCurriculum:vi.fn(),getHskLevels:vi.fn()}))
vi.mock('../pronunciation/api',()=>({getPronunciationLesson:vi.fn()}))
vi.mock('../progress/api',()=>({getProgressOverview:vi.fn()}))

const units:JourneyUnit[]=[
 {id:'published',order_index:1,unit_type:'LESSON',state:'AVAILABLE',lesson:{id:'real-lesson',lesson_number:1,title:'Xin chào',status:'PUBLISHED'},assessment:null},
 {id:'draft',order_index:2,unit_type:'LESSON',state:'AVAILABLE',lesson:{id:'draft-lesson',lesson_number:2,title:'Đang biên soạn',status:'DRAFT'},assessment:null},
 {id:'locked',order_index:3,unit_type:'LESSON',state:'LOCKED',lesson:{id:'locked-lesson',lesson_number:3,title:'Bài tiếp theo',status:'PUBLISHED'},assessment:null},
]
function mount(level=1,view='list'){
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
 return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[`/hsk/${level}?view=${view}`]}><GreatWallJourneyPage requestedLevel={String(level)}/></MemoryRouter></QueryClientProvider>)
}
beforeEach(()=>{
 vi.resetAllMocks()
 vi.mocked(getDashboard).mockResolvedValue({current_hsk:null,current_unit:null,current_lesson:null,progress_percentage:0,continue_learning:null})
 vi.stubGlobal('ResizeObserver',class{observe(){}disconnect(){}})
 Object.defineProperty(HTMLElement.prototype,'scrollTo',{configurable:true,value:vi.fn()})
 vi.mocked(getHskLevels).mockResolvedValue([1,2,3].map(n=>({id:`hsk-${n}`,level_number:n,title:`HSK ${n}`,description:null,state:'AVAILABLE'})))
 vi.mocked(getCurriculum).mockImplementation(async id=>({hsk:{id,level_number:Number(id.slice(-1)),title:'HSK'},units}))
 vi.mocked(getPronunciationLesson).mockResolvedValue({sections:[],current_section:null,step_index:0,total_steps:0,completed_at:'2026-11-10T00:00:00Z',can_finish:false})
 vi.mocked(getProgressOverview).mockResolvedValue({current_hsk:1,progress_percentage:0,pronunciation_complete:true,hsk_levels:[]})
})
afterEach(()=>{vi.unstubAllGlobals();Reflect.deleteProperty(HTMLElement.prototype,'scrollTo')})
describe('approved academy curriculum with real learning access',()=>{
 it('links the published lesson but never drafts, locked lessons or planned slots, in either view',async()=>{
  const {container}=mount()
  expect(await screen.findByRole('link',{name:'Học Bài học 1: Xin chào'})).toHaveAttribute('href','/lessons/real-lesson')
  expect(container.querySelectorAll('.lc-lesson-grid > li')).toHaveLength(15)
  expect(container.querySelectorAll('.lc-lesson-cover .lc-painted-cover')).toHaveLength(15)
  expect(container.querySelector('a[href="/lessons/draft-lesson"]')).toBeNull()
  expect(container.querySelector('a[href="/lessons/locked-lesson"]')).toBeNull()
  expect(screen.queryByRole('button',{name:'Bản đồ 2D'})).toBeNull()
  expect(container.querySelector('.lc-map-node')).toBeNull()
  fireEvent.click(screen.getByRole('button',{name:'Bài 2: Sắp có nội dung'}))
  expect(screen.getByRole('status')).toHaveTextContent('Bài 2 đang được chuẩn bị')
 })
 it('requires pronunciation for HSK1 but allows HSK2 independently',async()=>{
  vi.mocked(getPronunciationLesson).mockResolvedValue({sections:[],current_section:null,step_index:0,total_steps:0,completed_at:null,can_finish:false})
  const first=mount()
  await screen.findByRole('link',{name:/phát âm nền tảng/i})
  expect(first.container.querySelector('a[href="/lessons/real-lesson"]')).toBeNull()
  first.unmount()
  mount(2)
  expect(await screen.findByRole('link',{name:'Học Bài học 1: Xin chào'})).toHaveAttribute('href','/lessons/real-lesson')
 })
 it('provides a recoverable error instead of fabricated progress when curriculum fails',async()=>{
  vi.mocked(getCurriculum).mockRejectedValue(new Error('Offline'))
  const {container}=mount()
  expect(await screen.findByRole('alert')).toHaveTextContent('Không thể tải giáo trình')
  expect(screen.getByRole('button',{name:'Thử lại'})).toBeVisible()
  expect(container.querySelector('.lc-lesson-grid')).toBeNull()
 })
})
