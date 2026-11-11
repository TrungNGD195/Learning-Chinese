import {fireEvent,render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router'
import {expect,it} from 'vitest'
import {CompanionGuide} from './CompanionGuide'

it('keeps the cast compact by default and opens the existing companion deep link in the profile',()=>{
 const first=render(<MemoryRouter><CompanionGuide/></MemoryRouter>)
 expect(document.querySelector('details')).not.toHaveAttribute('open')
 first.unmount()
 render(<MemoryRouter initialEntries={['/profile#companions']}><CompanionGuide/></MemoryRouter>)
 expect(document.querySelector('details')).toHaveAttribute('open')
 expect(screen.getByRole('heading',{name:'Trúc · Người giải thích'})).toBeVisible()
 fireEvent.click(screen.getByRole('button',{name:'Ăn mừng'}))
 expect(screen.getByRole('button',{name:'Ăn mừng'})).toHaveAttribute('aria-pressed','true')
})
