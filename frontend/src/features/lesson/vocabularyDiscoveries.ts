import data from './data/vocabulary-discoveries.json'

export type DiscoveryWord = { hanzi: string; pinyin: string; vietnamese_meaning: string }
export type DiscoverySource = { label: string; url: string; checkedOn: string }
export type VocabularyDiscovery = { id: string; title: string; teaser: string; text: string; sources: readonly DiscoverySource[] }

type Catalog = {
  sources: Record<string, DiscoverySource>
  topics: Record<string, { title: string; teaser: string; text: string; sourceIds: string[] }>
  bindings: (DiscoveryWord & { topicId: string })[]
}
const catalog: Catalog = data
const normalized = (value: string) => value.normalize('NFC').trim().replace(/\s+/gu, ' ').toLocaleLowerCase('vi')
function senseKey(word: DiscoveryWord) {
  return JSON.stringify([normalized(word.hanzi), normalized(word.pinyin).replace(/[\s·’'-]/gu, ''), normalized(word.vietnamese_meaning)])
}
// Editorial content only: no network generation, lesson DTO or progress changes.
// A different meaning/pronunciation needs its own binding, even for the same Hanzi.
const bindings = new Map(catalog.bindings.map(binding => [senseKey(binding), binding.topicId]))
export function vocabularyDiscovery(word: DiscoveryWord): VocabularyDiscovery | undefined {
  const id = bindings.get(senseKey(word))
  if (!id) return undefined
  const topic = catalog.topics[id]
  return { id, title: topic.title, teaser: topic.teaser, text: topic.text, sources: topic.sourceIds.map(sourceId => catalog.sources[sourceId]) }
}
