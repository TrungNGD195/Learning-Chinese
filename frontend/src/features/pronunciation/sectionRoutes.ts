import type { PronunciationCode } from './pronunciationData'

export const pronunciationSections: Record<PronunciationCode, { slug: string; title: string; description: string; preview: string }> = {
  INITIALS: { slug: 'thanh-mau', title: 'Thanh mẫu', description: '21 âm đầu và cách bật hơi', preview: 'b · p · m · f' },
  FINALS: { slug: 'van-mau', title: 'Vận mẫu', description: '36 vận mẫu và cách ghép âm', preview: 'a · o · e · i · u · ü' },
  TONES: { slug: 'thanh-dieu', title: 'Thanh điệu', description: 'Bốn thanh và thanh nhẹ', preview: 'mā · má · mǎ · mà' },
  SANDHI: { slug: 'bien-dieu', title: 'Biến điệu', description: '12 ví dụ về cách đọc khi nói liền', preview: 'nǐ hǎo → ní hǎo' },
}

export function pronunciationSectionPath(code: PronunciationCode) {
  return '/pronunciation/lesson/' + pronunciationSections[code].slug
}

export function pronunciationCodeForSlug(slug: string | undefined) {
  return (Object.keys(pronunciationSections) as PronunciationCode[]).find(code => pronunciationSections[code].slug === slug)
}
