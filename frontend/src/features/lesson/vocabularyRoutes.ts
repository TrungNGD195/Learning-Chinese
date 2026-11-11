export function vocabularyPath(lessonId: string, linkId: string) {
  return `/lessons/${encodeURIComponent(lessonId)}/vocabulary/${encodeURIComponent(linkId)}`
}
