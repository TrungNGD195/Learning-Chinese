import catalogue from './data/vocabulary-art.json'

export type VocabularyArtwork = (typeof catalogue.entries)[number]
export const vocabularyArtEntries: readonly VocabularyArtwork[] = catalogue.entries
const normalize = (value: string) => value.normalize('NFC').trim().toLowerCase().replace(/\s+/g, ' ')
const key = (hanzi: string, pinyin: string, meaning: string) => [hanzi, pinyin, meaning].map(normalize).join('|')
const senses = new Map(vocabularyArtEntries.map(art => [key(art.hanzi, art.pinyin, art.meaning), art]))
const byHanzi = new Map<string, VocabularyArtwork[]>()
for (const art of vocabularyArtEntries) {
  const spelling = normalize(art.hanzi)
  byHanzi.set(spelling, [...(byHanzi.get(spelling) ?? []), art])
}

export function vocabularyArtwork(hanzi: string, pinyin?: string | null, meaning?: string | null) {
  if (pinyin && meaning) return senses.get(key(hanzi, pinyin, meaning))
  const candidates = byHanzi.get(normalize(hanzi)) ?? []
  // Never pick a different sense of a polysemous word just because its spelling matches.
  return candidates.length === 1 ? candidates[0] : undefined
}

export function vocabularyArtworkStyle(art: VocabularyArtwork) {
  return {
    backgroundImage: `url('/academy/vocabulary-art/atlas-${String(art.atlas).padStart(3, '0')}-v1.webp')`,
    backgroundSize: '400% 400%',
    backgroundPosition: `${art.cell % 4 * 100 / 3}% ${Math.floor(art.cell / 4) * 100 / 3}%`,
  }
}
