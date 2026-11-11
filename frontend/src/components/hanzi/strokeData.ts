import { loadHanziStrokeAsset } from '../../lib/api/client'

export type StrokeData = { strokes: string[]; medians: [number, number][][] }
const cache = new Map<string, Promise<StrokeData>>()

export function hanziCharacters(text: string) {
  return Array.from(text).filter(character => /^\p{Script=Han}$/u.test(character))
}

export async function loadStrokeData(character: string): Promise<StrokeData> {
  if (!/^\p{Script=Han}$/u.test(character)) throw new Error('UNSUPPORTED_CHARACTER')
  const existing = cache.get(character)
  if (existing) return existing
  const request = (async () => {
    const data = await loadHanziStrokeAsset(character.codePointAt(0)!.toString(16))
    if (!data || typeof data !== 'object' || !('strokes' in data) || !('medians' in data)) throw new Error('INVALID_STROKE_DATA')
    const { strokes, medians } = data
    if (!Array.isArray(strokes) || !strokes.length || strokes.length > 100 || !strokes.every(stroke => typeof stroke === 'string') || !Array.isArray(medians) || medians.length !== strokes.length || !medians.every(points => Array.isArray(points) && points.length > 1 && points.every(point => Array.isArray(point) && point.length === 2 && point.every(Number.isFinite)))) throw new Error('INVALID_STROKE_DATA')
    return { strokes, medians } as StrokeData
  })()
  cache.set(character, request)
  try { return await request } catch (error) { cache.delete(character); throw error }
}
