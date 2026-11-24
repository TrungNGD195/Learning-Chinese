import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { VocabularyIllustration } from './Companion'
import { vocabularyArtEntries } from './vocabularyArt'

function word(hanzi: string) {
  const art = vocabularyArtEntries.find(art => art.hanzi === hanzi)
  if (!art) throw new Error(`Missing current vocabulary illustration: ${hanzi}`)
  return { hanzi: art.hanzi, pinyin: art.pinyin, meaning: art.meaning }
}

it('uses the authored mouth sense and preserves an explicitly requested classifier context', () => {
  const noun = word('口')
  const view = render(<VocabularyIllustration {...noun} partOfSpeech="danh từ"/>)
  expect(screen.getByRole('img').getAttribute('aria-label')).toContain(noun.meaning)
  expect(screen.getByRole('img')).toHaveAttribute('data-illustration', 'vocabulary-sense')
  view.rerender(<VocabularyIllustration hanzi="口" partOfSpeech="lượng từ"/>)
  expect(screen.getByRole('img')).toHaveAccessibleName('Gia đình gấu trúc có bố, mẹ và hai con')
})

it('uses distinct images for dumplings and unfilled steamed buns', () => {
  const view = render(<VocabularyIllustration {...word('饺子')}/>)
  const first = screen.getByRole('img').getAttribute('data-artwork-id')
  const style = screen.getByRole('img').getAttribute('style')
  view.rerender(<VocabularyIllustration {...word('馒头')}/>)
  expect(screen.getByRole('img').getAttribute('data-artwork-id')).not.toBe(first)
  expect(screen.getByRole('img').getAttribute('style')).not.toBe(style)
})

it('keeps zero and large numeral pictures compact without thousands of decorative dots', () => {
  const view = render(<VocabularyIllustration hanzi="零"/>)
  expect(view.container.querySelector('.academy-word-illustration,.academy-numeral-illustration')).not.toBeNull()
  view.rerender(<VocabularyIllustration hanzi="万"/>)
  expect(view.container.querySelector('.academy-word-illustration,.academy-numeral-illustration')).not.toBeNull()
  expect(view.container.querySelectorAll('i')).toHaveLength(0)
})

it('gives all four grandparent terms a different illustration', () => {
  const view = render(<VocabularyIllustration {...word('爷爷')}/>)
  const ids = new Set<string | null>()
  for (const hanzi of ['爷爷', '奶奶', '外公', '外婆']) {
    const current = word(hanzi)
    view.rerender(<VocabularyIllustration {...current}/>)
    expect(screen.getByRole('img').getAttribute('aria-label')).toContain(current.meaning)
    ids.add(screen.getByRole('img').getAttribute('data-artwork-id'))
  }
  expect(ids.size).toBe(4)
  expect(ids.has(null)).toBe(false)
})

it('does not reuse parent pictures for spouse terms or teacher activities', () => {
  const view = render(<VocabularyIllustration {...word('爸爸')}/>)
  const ids = new Set<string | null>()
  for (const hanzi of ['爸爸', '老公', '妈妈', '老婆', '班主任']) {
    view.rerender(<VocabularyIllustration {...word(hanzi)}/>)
    ids.add(screen.getByRole('img').getAttribute('data-artwork-id'))
  }
  expect(ids.size).toBe(5)
  expect(ids.has(null)).toBe(false)
})
