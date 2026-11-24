/// <reference types="node" />
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { VocabularyIllustration } from './Companion'
import { vocabularyArtEntries, vocabularyArtwork, vocabularyArtworkStyle } from './vocabularyArt'

const root = resolve(process.cwd(), '..')

it('covers every current curriculum word with a unique real image cell', () => {
  const folders = ['curriculum-refresh', 'hsk3'].map(folder => resolve(root, 'backend/content', folder))
  let words = 0
  const slots = new Set<string>()
  const assets = new Set<string>()
  for (const folder of folders) for (const file of readdirSync(folder).filter(name => /^(hsk\d-)?lesson-\d+\.json$/.test(name))) {
    const lesson = JSON.parse(readFileSync(resolve(folder, file), 'utf8')) as { vocabulary: { hanzi: string; pinyin: string; vietnamese_meaning: string }[] }
    for (const word of lesson.vocabulary) {
      const art = vocabularyArtwork(word.hanzi, word.pinyin, word.vietnamese_meaning)
      expect(art, `${file}: ${word.hanzi} (${word.vietnamese_meaning})`).toBeDefined()
      if (!art) continue
      const slot = `${art.atlas}:${art.cell}`
      expect(slots.has(slot), `Shared illustration: ${word.hanzi}`).toBe(false)
      slots.add(slot)
      expect(art.cell).toBeGreaterThanOrEqual(0)
      expect(art.cell).toBeLessThan(16)
      assets.add(resolve(root, 'frontend/public/academy/vocabulary-art', `atlas-${String(art.atlas).padStart(3, '0')}-v1.webp`))
      words++
    }
  }
  expect(words).toBe(1097)
  expect(vocabularyArtEntries).toHaveLength(words)
  for (const asset of assets) {
    expect(statSync(asset).size).toBeGreaterThan(50_000)
    const bytes = readFileSync(asset)
    expect(bytes.subarray(0, 4).toString()).toBe('RIFF')
    expect(bytes.subarray(8, 12).toString()).toBe('WEBP')
  }
})

it('distinguishes clock and ordering-food senses of 点 instead of guessing by spelling', () => {
  const clock = vocabularyArtEntries.find(art => art.hanzi === '点' && art.meaning.includes('giờ'))!
  const food = vocabularyArtEntries.find(art => art.hanzi === '点' && art.meaning.includes('gọi'))!
  expect(clock).toBeDefined(); expect(food).toBeDefined()
  expect(vocabularyArtwork('点')).toBeUndefined()
  expect(vocabularyArtwork('点', clock.pinyin, clock.meaning)?.id).not.toBe(food.id)
  expect(vocabularyArtworkStyle(clock)).not.toEqual(vocabularyArtworkStyle(food))
  expect(vocabularyArtwork('点', clock.pinyin, 'A different, unauthored meaning')).toBeUndefined()
})

it('uses the same sense-specific illustration in lesson and inline flashcard contexts', () => {
  const word = vocabularyArtEntries[0]
  const view = render(<VocabularyIllustration hanzi={word.hanzi} pinyin={word.pinyin} meaning={word.meaning}/>)
  const style = screen.getByRole('img').getAttribute('style')
  expect(screen.getByRole('img')).toHaveAttribute('data-artwork-id', word.id)
  view.rerender(<button><VocabularyIllustration hanzi={word.hanzi} pinyin={word.pinyin} meaning={word.meaning} inline/></button>)
  expect(screen.getByRole('img')).toHaveAttribute('data-artwork-id', word.id)
  expect(screen.getByRole('img').getAttribute('style')).toBe(style)
  expect(view.container.querySelector('button figure')).toBeNull()
})
