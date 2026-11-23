import { describe, expect, it } from 'vitest'
import catalog from './data/vocabulary-discoveries.json'
import { vocabularyDiscovery, type DiscoveryWord } from './vocabularyDiscoveries'

type CurriculumLesson = { lesson: { hsk_level: number; lesson_number: number }; vocabulary: DiscoveryWord[] }
const lessons = Object.values(import.meta.glob<CurriculumLesson>([
  '../../../../backend/content/curriculum-refresh/hsk*-lesson-*.json',
  '../../../../backend/content/hsk3/lesson-*.json',
], { eager: true, import: 'default' }))

describe('curated vocabulary discoveries', () => {
  it('covers all audited senses against the real forty-lesson curriculum', () => {
    expect(lessons).toHaveLength(40)
    expect(catalog.bindings).toHaveLength(97)
    for (const binding of catalog.bindings) {
      const lesson = lessons.find(row => row.lesson.hsk_level === binding.hskLevel && row.lesson.lesson_number === binding.lessonNumber)
      const word = lesson?.vocabulary.find(row => row.hanzi === binding.hanzi && row.pinyin === binding.pinyin && row.vietnamese_meaning === binding.vietnamese_meaning)
      expect(word, `Published sense missing: HSK ${binding.hskLevel} / ${binding.lessonNumber} / ${binding.hanzi}`).toBeDefined()
      expect(vocabularyDiscovery(word!)?.id).toBe(binding.topicId)
    }
    expect([1, 2, 3].map(hsk => lessons.filter(row => row.lesson.hsk_level === hsk).flatMap(row => row.vocabulary).filter(word => vocabularyDiscovery(word)).length)).toEqual([37, 19, 41])
  })

  it('does not attach articles to a different classifier or result-complement sense', () => {
    for (const hanzi of ['家', '块', '到']) {
      const senses = lessons.flatMap(lesson => lesson.vocabulary).filter(word => word.hanzi === hanzi)
      expect(senses.length).toBeGreaterThan(1)
      expect(senses.filter(word => vocabularyDiscovery(word))).toHaveLength(1)
    }
    const tea = catalog.bindings.find(binding => binding.hanzi === '茶')!
    expect(vocabularyDiscovery({ ...tea, pinyin: 'chà' })).toBeUndefined()
    expect(vocabularyDiscovery({ ...tea, vietnamese_meaning: 'một nghĩa mới chưa được biên tập' })).toBeUndefined()
  })

  it('keeps shared topics reachable from every related word', () => {
    const find = (hanzi: string) => vocabularyDiscovery(catalog.bindings.find(word => word.hanzi === hanzi)!)
    expect(find('您')?.id).toBe(find('你')?.id)
    expect(find('你好')?.id).toBe(find('你')?.id)
    expect(find('外婆')?.id).toBe(find('爷爷')?.id)
    expect(find('春节')?.id).not.toBe(find('春晚')?.id)
    expect(find('茶')?.id).not.toBe(find('奶茶')?.id)
    expect(find('年')?.id).toBe('leap-month')
    expect(find('月')?.id).toBe(find('年')?.id)
    expect(find('到')?.id).toBe('fu-arrives')
  })

  it('accepts harmless Unicode and pinyin spacing variations but has no generic fallback', () => {
    const word = catalog.bindings.find(binding => binding.hanzi === '您')!
    expect(vocabularyDiscovery({ ...word, hanzi: ` ${word.hanzi} `, pinyin: word.pinyin.normalize('NFD'), vietnamese_meaning: ` ${word.vietnamese_meaning.toUpperCase()} ` })?.id).toBe(word.topicId)
    const tea = catalog.bindings.find(binding => binding.hanzi === '绿茶')!
    expect(vocabularyDiscovery({ ...tea, pinyin: tea.pinyin.replace(' ', '') })?.id).toBe(tea.topicId)
    expect(vocabularyDiscovery({ hanzi: '__proto__', pinyin: '', vietnamese_meaning: '' })).toBeUndefined()
  })

  it('keeps every article brief, referenced and free of dangling or unused topic bindings', () => {
    expect(new Set(catalog.bindings.map(row => JSON.stringify([row.hanzi, row.pinyin, row.vietnamese_meaning]))).size).toBe(catalog.bindings.length)
    expect(new Set(catalog.bindings.map(row => row.topicId))).toEqual(new Set(Object.keys(catalog.topics)))
    for (const [id, topic] of Object.entries(catalog.topics)) {
      expect(topic.text.trim().split(/\s+/u).length, id).toBeGreaterThanOrEqual(30)
      expect(topic.text.trim().split(/\s+/u).length, id).toBeLessThanOrEqual(90)
      expect(topic.teaser.length, id).toBeLessThanOrEqual(65)
      expect(topic.sourceIds.length, id).toBeGreaterThan(0)
      for (const sourceId of topic.sourceIds) {
        const source = (catalog.sources as Record<string, { url: string; label: string; checkedOn: string }>)[sourceId]
        expect(source?.label, id).toBeTruthy()
        expect(new URL(source.url).protocol).toBe('https:')
        expect(source.checkedOn).toMatch(/^\d{4}-\d{2}-\d{2}$/)
      }
    }
  })
})
