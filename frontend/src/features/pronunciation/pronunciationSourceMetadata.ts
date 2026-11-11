import type { PronunciationCode } from './pronunciationData'

export const sandhiSources = {
  eduhk: 'https://corpus.eduhk.hk/mandarin_pronunciation/?page_id=33',
  polyu: 'https://www.polyu.edu.hk/bepth/introduction-to-phonetics/tones/tone-sandhi/?sc_lang=en',
}

export function pronunciationSourcePage(code:PronunciationCode,symbol=''){
  if(code==='SANDHI')return 'PDF 7–8, 18, 30, 38 · trang in 5–6, 16, 28, 36'
  if(code==='TONES')return symbol==='Thanh nhẹ'?'PDF 18 · trang in 16':'PDF 6–7 · trang in 4–5'
  if(code==='INITIALS')return ['j','q','x'].includes(symbol)?'PDF 17 · trang in 15':['z','c','s','zh','ch','sh','r'].includes(symbol)?'PDF 27 · trang in 25':'PDF 4 · trang in 2'
  if(['a','o','e','i','u','ü','ai','ei','ao','ou','an','en','ang','eng','ong'].includes(symbol))return 'PDF 4–7 · trang in 2–5'
  if(['ia','ie','iao','iu','ian','in','iang','ing','üe','üan','ün','iong'].includes(symbol))return 'PDF 17–18 · trang in 15–16'
  return 'PDF 27–29 · trang in 25–27'
}
