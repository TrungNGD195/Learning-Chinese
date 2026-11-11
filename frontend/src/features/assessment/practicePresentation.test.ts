import { expect, it } from 'vitest'
import { questionForAttempt } from './practicePresentation'
import type { AssessmentQuestion } from './QuestionRenderer'

it('shuffles choices stably per attempt without changing IDs or the stored question', () => {
  const question: AssessmentQuestion = { id:'q', type:'multiple_choice', prompt:'Test', order_index:1, points:1, config:{}, options:['a','b','c','d'].map(id => ({id,option_text:id})) }
  const original=JSON.stringify(question)
  const orders=new Set<string>()
  for(let attempt=0;attempt<20;attempt++) {
    const result=questionForAttempt(question,String(attempt))
    expect(result).toEqual(questionForAttempt(question,String(attempt)))
    if(result.type !== 'multiple_choice') throw new Error('Wrong type')
    expect(result.options.map(option=>option.id).sort()).toEqual(['a','b','c','d'])
    orders.add(result.options.map(option=>option.id).join(''))
  }
  expect(orders.size).toBeGreaterThan(4)
  expect(JSON.stringify(question)).toBe(original)
})
