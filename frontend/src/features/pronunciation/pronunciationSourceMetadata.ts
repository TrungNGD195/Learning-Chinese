import type { PronunciationCode } from './pronunciationData'

export function pronunciationSourcePage(code:PronunciationCode,symbol=''){
  if(code==='TONES')return symbol==='Thanh nhẹ'?'PDF 18 · trang in 16':'PDF 6–7 · trang in 4–5'
  if(code==='INITIALS')return ['j','q','x'].includes(symbol)?'PDF 17 · trang in 15':['z','c','s','zh','ch','sh','r'].includes(symbol)?'PDF 27 · trang in 25':'PDF 4 · trang in 2'
  if(['a','o','e','i','u','ü','ai','ei','ao','ou','an','en','ang','eng','ong'].includes(symbol))return 'PDF 4–7 · trang in 2–5'
  if(['ia','ie','iao','iu','ian','in','iang','ing','üe','üan','ün','iong'].includes(symbol))return 'PDF 17–18 · trang in 15–16'
  return 'PDF 27–29 · trang in 25–27'
}
