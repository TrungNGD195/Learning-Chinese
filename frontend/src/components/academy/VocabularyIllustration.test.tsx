import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { VocabularyIllustration } from './Companion'

it('keeps the mouth meaning of 口 distinct from its family classifier meaning', () => {
  const view = render(<VocabularyIllustration hanzi="口" partOfSpeech="danh từ" />)
  expect(screen.getByRole('img')).toHaveAccessibleName('Gấu trúc minh họa miệng')
  view.rerender(<VocabularyIllustration hanzi="口" partOfSpeech="lượng từ" />)
  expect(screen.getByRole('img')).toHaveAccessibleName('Gia đình gấu trúc có bố, mẹ và hai con')
})

it('uses different food illustrations for dumplings and unfilled steamed buns', () => {
  const view = render(<VocabularyIllustration hanzi="饺子" />)
  const first = screen.getByRole('img')
  expect(first).toHaveAccessibleName('Sủi cảo có hình bán nguyệt')
  const position = first.style.backgroundPosition
  view.rerender(<VocabularyIllustration hanzi="馒头" />)
  expect(screen.getByRole('img')).toHaveAccessibleName('Màn thầu không nhân')
  expect(screen.getByRole('img').style.backgroundPosition).not.toBe(position)
})

it('renders zero and large numerals without thousands of decorative dots', () => {
  const view = render(<VocabularyIllustration hanzi="零" />)
  expect(screen.getByLabelText('Minh họa số 0')).toHaveTextContent('0')
  view.rerender(<VocabularyIllustration hanzi="万" />)
  expect(screen.getByLabelText('Minh họa số 10000')).toHaveTextContent('10.000')
  expect(view.container.querySelectorAll('i')).toHaveLength(0)
})

it('uses distinct chibi portraits for all four grandparents', () => {
  const view = render(<VocabularyIllustration hanzi="爷爷" />)
  const positions = new Set<string>()
  for (const [word, relationship] of [['爷爷', 'bố của bố'], ['奶奶', 'mẹ của bố'], ['外公', 'bố của mẹ'], ['外婆', 'mẹ của mẹ']]) {
    view.rerender(<VocabularyIllustration hanzi={word} />)
    const picture = screen.getByRole('img')
    expect(picture).toHaveAttribute('data-illustration', 'chibi-family')
    expect(picture.getAttribute('aria-label')).toContain(relationship)
    positions.add(picture.style.backgroundPosition)
  }
  expect(positions.size).toBe(4)
})

it('shares spouse synonym portraits and preserves panda illustrations for other activities', () => {
  const view = render(<VocabularyIllustration hanzi="老公" />)
  const husband = screen.getByRole('img').style.backgroundPosition
  view.rerender(<VocabularyIllustration hanzi="丈夫" />)
  expect(screen.getByRole('img').style.backgroundPosition).toBe(husband)
  view.rerender(<VocabularyIllustration hanzi="老婆" />)
  const wife = screen.getByRole('img').style.backgroundPosition
  expect(wife).not.toBe(husband)
  view.rerender(<VocabularyIllustration hanzi="妻子" />)
  expect(screen.getByRole('img').style.backgroundPosition).toBe(wife)
  view.rerender(<VocabularyIllustration hanzi="老师" />)
  expect(screen.getByRole('img')).toHaveAttribute('data-illustration', 'panda-context')
})
