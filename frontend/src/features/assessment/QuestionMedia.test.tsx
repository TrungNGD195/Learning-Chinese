import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { QuestionMedia } from './QuestionMedia'

it('keeps the listening transcript hidden until explicitly requested and supports a text fallback', () => {
  render(<QuestionMedia question={{id:'q',type:'multiple_choice',prompt:'Nghe',order_index:1,points:1,options:[],config:{presentation:{skill:'listening',focus:'vocabulary',difficulty:'easy',review:false,audio_text:'你好'}}}}/>)
  expect(screen.queryByText('你好')).not.toBeInTheDocument()
  const toggle=screen.getByRole('button',{name:'Xem bản chữ nếu không nghe được'})
  expect(toggle).toHaveAttribute('aria-expanded','false')
  fireEvent.click(toggle)
  expect(screen.getByText('你好')).toBeInTheDocument()
  expect(screen.getByRole('button',{name:'Ẩn bản chữ'})).toHaveAttribute('aria-expanded','true')
})
