import {afterEach,beforeEach,expect,it,vi} from 'vitest'
import {cleanup,fireEvent,render,screen,within} from '@testing-library/react'
import {MemoryRouter,Route,Routes} from 'react-router'
import {ReferenceWallJourney} from './ReferenceWallJourney'
import type {JourneyStop} from './journeyData'
import type {ComponentProps,ReactNode} from 'react'

vi.mock('./IllustratedClimb',()=>({IllustratedClimb:({progress,name,gateControl,nextLevelNumber,onTowerEntered}:{progress:number;name:string;gateControl:(className:string)=>ReactNode;nextLevelNumber?:number;onTowerEntered:()=>void})=><div data-testid="continuous-climb" data-progress={progress} data-label={name}>{gateControl('test-gate')}{nextLevelNumber&&<button data-testid="tower-crossing" onClick={onTowerEntered}>Cross tower</button>}</div>}))

const stops:JourneyStop[]=Array.from({length:3},(_,i)=>({id:`lesson-${i+1}`,name:`Bài học ${i+1}: Xin chào`,shortName:`Bài ${i+1}`,kind:'lesson',state:'AVAILABLE',destination:`/lessons/${i+1}`,slot:i,lessonNumber:i+1}))
const props={stops,currentId:'lesson-3',focusId:'lesson-3',finished:false,levelNumber:1,overview:false,onOverviewChange:vi.fn()}
beforeEach(()=>{sessionStorage.clear();vi.clearAllMocks()})
afterEach(cleanup)
function setup(overrides:Partial<ComponentProps<typeof ReferenceWallJourney>>={}){return render(<MemoryRouter initialEntries={['/hsk/1']}><Routes><Route path="/hsk/1" element={<ReferenceWallJourney {...props} {...overrides}/>}/><Route path="/lessons/:id" element={<h1>Bài học đã mở</h1>}/><Route path="/hsk/2" element={<h1>HSK 2 arrival</h1>}/></Routes></MemoryRouter>)}

it('uses one continuous climbing stage rather than independent scene buttons',()=>{
  const {container}=setup()
  expect(screen.getByTestId('continuous-climb')).toHaveAttribute('data-progress','2')
  expect(screen.getByTestId('continuous-climb')).toHaveAttribute('data-label','Bài 3')
  expect(container.querySelector('.reference-scenes')).toBeNull()
})
it('advances one target footfall only per up or down key',()=>{
  const {container}=setup()
  const stage=container.querySelector('.reference-stage')!
  expect(stage).toHaveAttribute('data-progress','2')
  fireEvent.keyDown(window,{key:'ArrowUp'})
  expect(stage).toHaveAttribute('data-progress',String(2+1/6))
  expect(stage).toHaveAttribute('data-scene','climb')
  fireEvent.keyDown(window,{key:'ArrowUp',repeat:true})
  expect(stage).toHaveAttribute('data-progress',String(2+1/6))
  fireEvent.keyDown(window,{key:'ArrowDown'})
  expect(stage).toHaveAttribute('data-progress','2')
  for(let i=0;i<3;i++)fireEvent.keyDown(window,{key:'ArrowUp'})
  expect(stage).toHaveAttribute('data-progress','2.5')
  expect(stage).toHaveAttribute('data-scene','bend')
  for(let i=0;i<2;i++)fireEvent.keyDown(window,{key:'ArrowUp'})
  expect(stage).toHaveAttribute('data-scene','gate')
})
it('does not move on mouse wheels, trackpad inertia, or left and right arrows',()=>{
  const {container}=setup(),stage=container.querySelector('.reference-stage')!
  fireEvent.wheel(stage,{deltaY:-46});fireEvent.wheel(stage,{deltaY:-20});fireEvent.wheel(stage,{deltaY:-3})
  expect(stage).toHaveAttribute('data-progress','2')
  fireEvent.wheel(stage,{deltaY:-120});fireEvent.wheel(stage,{deltaY:-120})
  fireEvent.keyDown(window,{key:'ArrowLeft'});fireEvent.keyDown(window,{key:'ArrowRight'})
  expect(stage).toHaveAttribute('data-progress','2')
  expect(screen.queryByRole('button',{name:'Lên một bậc'})).not.toBeInTheDocument()
})
it('keeps a published gate as a native lesson link',async()=>{
  setup();fireEvent.click(screen.getAllByRole('link',{name:'Học Bài học 3: Xin chào'})[0])
  expect(await screen.findByRole('heading',{name:'Bài học đã mở'})).toBeInTheDocument()
})
it('explains unavailable lessons without navigating or changing learning data',()=>{
  setup({stops:stops.map(item=>({...item,state:'LOCKED',destination:null}))})
  fireEvent.click(screen.getAllByRole('button',{name:'Bài 3'})[0])
  expect(screen.getByRole('status')).toHaveTextContent('Bài 3 chưa mở')
})
it('shows every supplied lesson in the overview',()=>{
  setup({overview:true})
  const list=screen.getByRole('list',{name:'Các bài trong cấp độ HSK'})
  expect(within(list).getAllByRole('link')).toHaveLength(3)
  expect(screen.getByRole('button',{name:'Định vị Bài 3'})).toBeEnabled()
})
it('retains the same lesson position when resuming an older ten-step journey',()=>{
  sessionStorage.setItem('bo-reference-journey-v1-hsk-1',JSON.stringify({step:25,ids:stops.map(s=>s.id).join('|')}))
  setup()
  expect(screen.getByTestId('continuous-climb')).toHaveAttribute('data-progress','2.5')
})
it('automatically changes chapter when the renderer reports crossing the tower',async()=>{
  setup({nextLevel:{number:2,destination:'/hsk/2'}})
  expect(screen.queryByRole('heading',{name:'HSK 2 arrival'})).not.toBeInTheDocument()
  fireEvent.click(screen.getByTestId('tower-crossing'))
  expect(await screen.findByRole('heading',{name:'HSK 2 arrival'})).toBeInTheDocument()
  expect(sessionStorage.getItem('bo-reference-arrival-2')).toBe('first')
})
it('resumes outside the tower so browser Back cannot create an automatic navigation loop',()=>{
  sessionStorage.setItem('bo-reference-journey-v1-hsk-1',JSON.stringify({step:21,stepsPerGate:6,ids:stops.map(s=>s.id).join('|')}))
  setup({nextLevel:{number:2,destination:'/hsk/2'}})
  expect(screen.getByTestId('continuous-climb')).toHaveAttribute('data-progress','3')
  expect(screen.queryByRole('heading',{name:'HSK 2 arrival'})).not.toBeInTheDocument()
})
it('keeps a tower arrival at the first approach across remounts until the learner moves',()=>{
  sessionStorage.setItem('bo-reference-arrival-2','first')
  setup({levelNumber:2})
  expect(screen.getByTestId('continuous-climb')).toHaveAttribute('data-progress','0')
  cleanup();setup({levelNumber:2})
  expect(screen.getByTestId('continuous-climb')).toHaveAttribute('data-progress','0')
  fireEvent.keyDown(window,{key:'ArrowUp'})
  expect(sessionStorage.getItem('bo-reference-arrival-2')).toBeNull()
  cleanup();setup({levelNumber:2})
  expect(screen.getByTestId('continuous-climb')).toHaveAttribute('data-progress',String(1/6))
})
it('lets an explicit current-lesson location replace the tower arrival position',()=>{
  sessionStorage.setItem('bo-reference-arrival-2','first')
  const view=render(<MemoryRouter><ReferenceWallJourney {...props} levelNumber={2} locateSignal={0}/></MemoryRouter>)
  view.rerender(<MemoryRouter><ReferenceWallJourney {...props} levelNumber={2} locateSignal={1}/></MemoryRouter>)
  expect(screen.getByTestId('continuous-climb')).toHaveAttribute('data-progress','2')
  expect(sessionStorage.getItem('bo-reference-arrival-2')).toBeNull()
  cleanup();setup({levelNumber:2})
  expect(screen.getByTestId('continuous-climb')).toHaveAttribute('data-progress','2')
})
