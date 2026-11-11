import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Link, MemoryRouter } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { JourneyCloudProvider } from './JourneyCloudTransition'
import { useJourneyCloud } from './journeyCloudContext'
import { CLOUD_ENTER_MS, CLOUD_HOLD_MS, CLOUD_EXIT_MS } from './journeyCloudTiming'

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn().mockResolvedValue(undefined) }))
vi.mock('react-router', async importOriginal => ({ ...await importOriginal<typeof import('react-router')>(), useNavigate: () => navigate }))
beforeEach(() => { vi.useFakeTimers();navigate.mockReset().mockResolvedValue(undefined) })
afterEach(() => { cleanup();vi.useRealTimers() })
function Trigger({ depart, cancelled, relocate, coverDelay }: { depart?: () => void; cancelled?: () => void; relocate?: () => void; coverDelay?:number }) {
  const travel = useJourneyCloud()
  return <><button onClick={() => travel?.travel({ destination: relocate ? '/hsk/1' : '/lessons/one', depart, cancelled, relocate, returning: !!relocate,coverDelay })}>Mở cổng</button><Link to="/profile">Hồ sơ</Link><Link to="/lessons/one">Destination</Link></>
}
function setup(depart?: () => void, cancelled?: () => void, relocate?: () => void,coverDelay?:number) {
  return render(<MemoryRouter initialEntries={['/hsk/1']}><JourneyCloudProvider><Trigger depart={depart} cancelled={cancelled} relocate={relocate} coverDelay={coverDelay}/></JourneyCloudProvider></MemoryRouter>)
}
it('keeps one active trip when the learner clicks repeatedly, then releases the cloud', async () => {
  const depart = vi.fn();setup(depart)
  fireEvent.click(screen.getByText('Mở cổng'));fireEvent.click(screen.getByText('Mở cổng'))
  expect(depart).toHaveBeenCalledTimes(1)
  await act(() => vi.advanceTimersByTimeAsync(280+CLOUD_ENTER_MS))
  expect(navigate).toHaveBeenCalledTimes(1)
  expect(navigate).toHaveBeenCalledWith('/lessons/one')
  await act(() => vi.advanceTimersByTimeAsync(CLOUD_HOLD_MS-1))
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase', 'cover')
  await act(() => vi.advanceTimersByTimeAsync(1))
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase', 'reveal')
  await act(() => vi.advanceTimersByTimeAsync(CLOUD_EXIT_MS))
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase', 'idle')
})
it('cancels cleanly on Escape and accepts a new trip afterwards', async () => {
  const cancelled = vi.fn();setup(undefined, cancelled)
  fireEvent.click(screen.getByText('Mở cổng'))
  await act(() => vi.advanceTimersByTimeAsync(200))
  fireEvent.keyDown(window, { key: 'Escape' })
  await act(() => vi.advanceTimersByTimeAsync(2000))
  expect(cancelled).toHaveBeenCalledTimes(1);expect(navigate).not.toHaveBeenCalled()
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase', 'idle')
  fireEvent.click(screen.getByText('Mở cổng'))
  await act(() => vi.advanceTimersByTimeAsync(1000))
  expect(navigate).toHaveBeenCalledTimes(1)
})
it('never performs delayed navigation after the provider unmounts', async () => {
  const view = setup();fireEvent.click(screen.getByText('Mở cổng'));view.unmount()
  await act(() => vi.advanceTimersByTimeAsync(3000))
  expect(navigate).not.toHaveBeenCalled()
})
it('abandons the trip if the learner chooses another page before entering', async () => {
  const cancelled = vi.fn();setup(undefined, cancelled)
  fireEvent.click(screen.getByText('Mở cổng'));fireEvent.click(screen.getByText('Hồ sơ'))
  await act(() => vi.advanceTimersByTimeAsync(3000))
  expect(cancelled).toHaveBeenCalledTimes(1);expect(navigate).not.toHaveBeenCalled()
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase', 'idle')
})
it('always releases the veil even if a router navigation never settles', async () => {
  navigate.mockImplementationOnce(() => new Promise(() => {}));setup()
  fireEvent.click(screen.getByText('Mở cổng'))
  await act(() => vi.advanceTimersByTimeAsync(4200))
  expect(navigate).toHaveBeenCalledTimes(1)
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase', 'idle')
})
it('does not undo a committed destination when its scene keeps navigation pending',async()=>{
  const cancelled=vi.fn();navigate.mockImplementationOnce(()=>new Promise(()=>{}));setup(undefined,cancelled)
  fireEvent.click(screen.getByText('Mở cổng'))
  await act(()=>vi.advanceTimersByTimeAsync(280+CLOUD_ENTER_MS))
  fireEvent.click(screen.getByText('Destination'))
  await act(()=>vi.advanceTimersByTimeAsync(4200))
  expect(cancelled).not.toHaveBeenCalled()
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase','idle')
})
it('preserves chapter arrival while a slow router is still committing the destination',async()=>{
  const cancelled=vi.fn();navigate.mockImplementationOnce(()=>new Promise(()=>{}));setup(undefined,cancelled)
  fireEvent.click(screen.getByText('Mở cổng'))
  await act(()=>vi.advanceTimersByTimeAsync(4200))
  expect(navigate).toHaveBeenCalledTimes(1)
  expect(cancelled).not.toHaveBeenCalled()
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase','idle')
})

it('relocates within the journey only after full cloud cover, without router navigation', async () => {
  const relocate = vi.fn();setup(undefined, undefined, relocate)
  fireEvent.click(screen.getByText('Mở cổng'));fireEvent.click(screen.getByText('Mở cổng'))
  await act(() => vi.advanceTimersByTimeAsync(CLOUD_ENTER_MS-1))
  expect(relocate).not.toHaveBeenCalled()
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase', 'cover')
  await act(() => vi.advanceTimersByTimeAsync(1))
  expect(relocate).toHaveBeenCalledTimes(1)
  expect(navigate).not.toHaveBeenCalled()
  await act(() => vi.advanceTimersByTimeAsync(CLOUD_HOLD_MS+CLOUD_EXIT_MS))
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase', 'idle')
})

it('cancels a local relocation on Escape before swapping the scene', async () => {
  const relocate = vi.fn();setup(undefined, undefined, relocate)
  fireEvent.click(screen.getByText('Mở cổng'))
  await act(() => vi.advanceTimersByTimeAsync(200))
  fireEvent.keyDown(window, { key: 'Escape' })
  await act(() => vi.advanceTimersByTimeAsync(1500))
  expect(relocate).not.toHaveBeenCalled()
  expect(navigate).not.toHaveBeenCalled()
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase', 'idle')
})

it('renders no transition text during cloud entry, covered navigation, hold or exit', async () => {
  setup();fireEvent.click(screen.getByText('Mở cổng'))
  const cloud=document.querySelector('.journey-cloud-transition')!
  for(const elapsed of [280,CLOUD_ENTER_MS,CLOUD_HOLD_MS,CLOUD_EXIT_MS]) {
    await act(()=>vi.advanceTimersByTimeAsync(elapsed))
    expect(cloud.textContent).toBe('')
    expect(cloud.querySelector('p,[role="status"]')).toBeNull()
    expect(cloud).toHaveAttribute('aria-hidden','true')
  }
})

it('leaves the scene visible while Bo enters the tower, then covers before navigation',async()=>{
  const depart=vi.fn();setup(depart,undefined,undefined,1470)
  fireEvent.click(screen.getByText('Mở cổng'))
  expect(depart).toHaveBeenCalledTimes(1)
  await act(()=>vi.advanceTimersByTimeAsync(1469))
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase','idle')
  expect(navigate).not.toHaveBeenCalled()
  await act(()=>vi.advanceTimersByTimeAsync(1))
  expect(document.querySelector('.journey-cloud-transition')).toHaveAttribute('data-phase','cover')
  await act(()=>vi.advanceTimersByTimeAsync(CLOUD_ENTER_MS))
  expect(navigate).toHaveBeenCalledTimes(1)
})
