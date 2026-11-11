import { useEffect, useRef, useState } from 'react'
import { sandhiGroups } from './sandhiData'

export type PronunciationCode = 'INITIALS' | 'FINALS' | 'TONES' | 'SANDHI'
export type Sound = { symbol: string; hanzi: string; pinyin: string; spoken?: string; meaning?: string; explanation?: string; note?: string }

// Source: local HSK1 3.0 Hanu 24.6.26.pdf, PDF4–7,17–18,27–29.
// Ordered groups retain the server-owned21/36/5 progression contract.
type SoundGroup = { title: string; tip: string; sounds: Sound[] }

const initials: SoundGroup[] = [
  { title: 'Âm môi', tip: 'Khép hoặc đưa môi gần nhau. p bật hơi rõ hơn b.', sounds: [
    { symbol: 'b', hanzi: '八', pinyin: 'bā' }, { symbol: 'p', hanzi: '怕', pinyin: 'pà' },
    { symbol: 'm', hanzi: '妈', pinyin: 'mā' }, { symbol: 'f', hanzi: '发', pinyin: 'fā' },
  ] },
  { title: 'Đầu lưỡi', tip: 'Đặt đầu lưỡi gần lợi trên; t bật hơi rõ hơn d.', sounds: [
    { symbol: 'd', hanzi: '大', pinyin: 'dà' }, { symbol: 't', hanzi: '他', pinyin: 'tā' },
    { symbol: 'n', hanzi: '你', pinyin: 'nǐ' }, { symbol: 'l', hanzi: '六', pinyin: 'liù' },
  ] },
  { title: 'Gốc lưỡi', tip: 'Phần sau của lưỡi hướng lên vòm mềm; k bật hơi rõ hơn g.', sounds: [
    { symbol: 'g', hanzi: '哥', pinyin: 'gē' }, { symbol: 'k', hanzi: '可', pinyin: 'kě' },
    { symbol: 'h', hanzi: '喝', pinyin: 'hē' },
  ] },
  { title: 'Mặt lưỡi', tip: 'Giữ lưỡi phía trước và môi hơi mở. q bật hơi mạnh hơn j.', sounds: [
    { symbol: 'j', hanzi: '鸡', pinyin: 'jī' }, { symbol: 'q', hanzi: '七', pinyin: 'qī' },
    { symbol: 'x', hanzi: '西', pinyin: 'xī' },
  ] },
  { title: 'Uốn lưỡi', tip: 'Đưa đầu lưỡi hơi cong về phía vòm miệng. Chú ý phân biệt zh/ch/sh với z/c/s.', sounds: [
    { symbol: 'zh', hanzi: '知', pinyin: 'zhī' }, { symbol: 'ch', hanzi: '吃', pinyin: 'chī' },
    { symbol: 'sh', hanzi: '是', pinyin: 'shì' }, { symbol: 'r', hanzi: '日', pinyin: 'rì' },
  ] },
  { title: 'Đầu lưỡi trước', tip: 'Đầu lưỡi ở gần mặt sau răng trên; c bật hơi rõ hơn z.', sounds: [
    { symbol: 'z', hanzi: '字', pinyin: 'zì' }, { symbol: 'c', hanzi: '次', pinyin: 'cì' },
    { symbol: 's', hanzi: '四', pinyin: 'sì' },
  ] },
]

const finals: SoundGroup[] = [
  { title: 'Vận mẫu đơn', tip: 'Luyện từng khẩu hình. Với ü, giữ môi tròn trong khi lưỡi ở vị trí gần như khi đọc i.', sounds: [
    { symbol: 'a', hanzi: '妈', pinyin: 'mā' }, { symbol: 'o', hanzi: '波', pinyin: 'bō' },
    { symbol: 'e', hanzi: '鹅', pinyin: 'é' }, { symbol: 'i', hanzi: '衣', pinyin: 'yī' },
    { symbol: 'u', hanzi: '乌', pinyin: 'wū' }, { symbol: 'ü', hanzi: '鱼', pinyin: 'yú' },
  ] },
  { title: 'Vận mẫu ghép', tip: 'Chuyển khẩu hình liền mạch trong một âm tiết, không tách thành hai tiếng.', sounds: [
    { symbol: 'ai', hanzi: '爱', pinyin: 'ài' }, { symbol: 'ei', hanzi: '杯', pinyin: 'bēi' },
    { symbol: 'ao', hanzi: '奥', pinyin: 'ào' }, { symbol: 'ou', hanzi: '欧', pinyin: 'ōu' },
    { symbol: 'ia', hanzi: '家', pinyin: 'jiā' }, { symbol: 'ie', hanzi: '叶', pinyin: 'yè' },
    { symbol: 'iao', hanzi: '腰', pinyin: 'yāo' }, { symbol: 'iu', hanzi: '六', pinyin: 'liù' },
    { symbol: 'ua', hanzi: '瓜', pinyin: 'guā' }, { symbol: 'uo', hanzi: '我', pinyin: 'wǒ' },
    { symbol: 'uai', hanzi: '快', pinyin: 'kuài' }, { symbol: 'ui', hanzi: '水', pinyin: 'shuǐ' },
    { symbol: 'üe', hanzi: '月', pinyin: 'yuè' },
  ] },
  { title: 'Vận mẫu có âm mũi', tip: 'Phân biệt đuôi -n ở phía trước với -ng ở phía sau; nghe và luyện theo từng cặp.', sounds: [
    { symbol: 'an', hanzi: '安', pinyin: 'ān' }, { symbol: 'en', hanzi: '恩', pinyin: 'ēn' },
    { symbol: 'ang', hanzi: '昂', pinyin: 'áng' }, { symbol: 'eng', hanzi: '风', pinyin: 'fēng' },
    { symbol: 'ong', hanzi: '中', pinyin: 'zhōng' }, { symbol: 'ian', hanzi: '烟', pinyin: 'yān' },
    { symbol: 'in', hanzi: '因', pinyin: 'yīn' }, { symbol: 'iang', hanzi: '羊', pinyin: 'yáng' },
    { symbol: 'ing', hanzi: '英', pinyin: 'yīng' }, { symbol: 'iong', hanzi: '用', pinyin: 'yòng' },
    { symbol: 'uan', hanzi: '万', pinyin: 'wàn' }, { symbol: 'un', hanzi: '问', pinyin: 'wèn' },
    { symbol: 'uang', hanzi: '王', pinyin: 'wáng' }, { symbol: 'ueng', hanzi: '翁', pinyin: 'wēng' },
    { symbol: 'üan', hanzi: '元', pinyin: 'yuán' }, { symbol: 'ün', hanzi: '云', pinyin: 'yún' },
  ] },
  { title: 'Vận mẫu cuốn lưỡi', tip: 'er có thể là một âm tiết độc lập và cũng xuất hiện trong hiện tượng nhi hóa.', sounds: [
    { symbol: 'er', hanzi: '儿', pinyin: 'ér' },
  ] },
]

const tones: SoundGroup[] = [{
  title: 'Bốn thanh điệu và thanh nhẹ',
  tip: 'Thanh 1 cao và ngang; thanh 2 đi lên; thanh 3 hạ xuống rồi nhấc lên khi đọc riêng; thanh 4 đi xuống mạnh. Thanh nhẹ ngắn và không có dấu thanh.',
  sounds: [
    { symbol: 'Thanh 1 · ˉ', hanzi: '妈', pinyin: 'mā' }, { symbol: 'Thanh 2 · ˊ', hanzi: '麻', pinyin: 'má' },
    { symbol: 'Thanh 3 · ˇ', hanzi: '马', pinyin: 'mǎ' }, { symbol: 'Thanh 4 · ˋ', hanzi: '骂', pinyin: 'mà' },
    { symbol: 'Thanh nhẹ', hanzi: '妈妈', pinyin: 'māma' },
  ],
}]

export const pronunciationContent: Record<PronunciationCode, { intro: string; groups: SoundGroup[]; notes: string[] }> = {
  INITIALS: {
    intro: 'Thanh mẫu là phụ âm đứng đầu âm tiết. Hãy nghe âm tiết mẫu, quan sát khẩu hình và thử đọc lại.',
    groups: initials,
    notes: ['Bộ 21 thanh mẫu thường được học theo các nhóm ở trên. y và w chủ yếu là quy ước viết âm tiết không có thanh mẫu, không được tính vào 21 âm này.', 'Mẹo phân biệt b/p, d/t và g/k: đặt một mẩu giấy trước miệng; âm bật hơi làm giấy chuyển động rõ hơn.'],
  },
  FINALS: {
    intro: 'Vận mẫu là phần vần của âm tiết. Các ví dụ cho thấy cách viết vận mẫu khi đứng một mình hoặc kết hợp với thanh mẫu.',
    groups: finals,
    notes: ['Khi i, u, ü đứng đầu âm tiết, cách viết thường dùng y hoặc w: yi, wu, yu. Đây là cách viết Pinyin, không phải thêm phụ âm mới.', 'Sau j, q, x và y, hai chấm của ü thường được lược trong chữ viết: ju, qu, xu, yu. Các dạng iu, ui, un là cách viết rút gọn trong một số âm tiết.', 'Chữ i trong zi, ci, si, zhi, chi, shi, ri không phát âm giống i trong yi; hãy nghe mẫu thay vì áp dụng một khẩu hình cho mọi trường hợp.'],
  },
  TONES: {
    intro: 'Thanh điệu thay đổi độ cao của giọng và có thể làm đổi nghĩa. Hãy nghe và đọc rõ từng âm mẫu.',
    groups: tones,
    notes: ['Dấu thanh đặt trên nguyên âm chính: ưu tiên a, rồi o/e; với iu và ui, dấu đặt trên nguyên âm cuối. Khi i mang dấu, bỏ chấm trên i.', 'Hai thanh 3 đứng cạnh nhau: âm đầu thường được đọc gần thanh 2, nhưng cách viết vẫn giữ nguyên dấu thanh 3, ví dụ nǐ hǎo.', 'Trước thanh 1, 2, 4 hoặc thanh nhẹ, thanh 3 thường chỉ đọc phần hạ giọng (nửa thanh 3), không nâng lên đầy đủ như khi đọc riêng.', 'Âm 不 thường đọc bú trước thanh 4, ví dụ bú shì; hãy luyện biến điệu trong ngữ cảnh.', 'Thanh nhẹ không có dấu thanh và có độ cao phụ thuộc thanh điệu của âm tiết đứng trước; luyện với māma, nǐmen và bàba.'],
  },
  SANDHI: {
    intro: 'Khi nói liền, một số thanh thay đổi theo ngữ cảnh. So sánh thanh gốc với cách đọc, nghe cả cụm và tự đọc lại.',
    groups: sandhiGroups,
    notes: ['Biến điệu thay đổi cách phát âm; không đổi chữ Hán.', 'Thanh 3 vẫn giữ dấu gốc trong pinyin. Với 一 và 不, giáo trình có thể ghi dấu theo cách đọc để hỗ trợ học. Dòng “Thanh gốc” phân tích từng âm, không phải luôn là cách viết pinyin của cả từ.', 'Nửa thanh 3 là phần giọng hạ thấp, khác với thanh 2 đi lên.', 'Thanh nhẹ không mang dấu thanh. Nhịp nói và cách nhóm từ ảnh hưởng biến điệu; không biến mọi thanh 3 trong chuỗi thành thanh 2.'],
  },
}

function isMandarinVoice(voice: SpeechSynthesisVoice) {
  return /^(cmn|zh-(cn|sg|tw|hans))(?:-|$)/i.test(voice.lang)
}

export function useMandarinSpeech() {
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [speechError, setSpeechError] = useState<string | null>(null)
  const active = useRef<SpeechSynthesisUtterance | null>(null)
  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
    const synth = window.speechSynthesis
    const updateVoice = () => {
      const voices = synth.getVoices().filter(isMandarinVoice)
      setVoice(voices.find((candidate) => candidate.localService) ?? voices[0] ?? null)
    }
    updateVoice()
    synth.addEventListener('voiceschanged', updateVoice)
    return () => {
      synth.removeEventListener('voiceschanged', updateVoice)
      if (active.current) {
        active.current = null
        synth.cancel()
      }
    }
  }, [])

  const speak = (sound: Pick<Sound, 'hanzi'>) => {
    if (!voice || typeof SpeechSynthesisUtterance === 'undefined') return
    const utterance = new SpeechSynthesisUtterance(sound.hanzi)
    utterance.voice = voice
    utterance.lang = voice.lang
    utterance.rate = 0.8
    active.current = utterance
    setSpeechError(null)
    setIsSpeaking(true)
    utterance.onend = () => {
      if (active.current !== utterance) return
      active.current = null
      setIsSpeaking(false)
    }
    utterance.onerror = event => {
      if (active.current !== utterance) return
      active.current = null
      setIsSpeaking(false)
      if (!['canceled', 'interrupted'].includes(event.error)) setSpeechError('Chưa thể phát âm thanh. Bạn hãy bấm nghe lại.')
    }
    try {
      window.speechSynthesis.cancel()
      window.speechSynthesis.speak(utterance)
    } catch {
      active.current = null
      setIsSpeaking(false)
      setSpeechError('Chưa thể phát âm thanh. Bạn hãy bấm nghe lại.')
    }
  }

  return { voiceAvailable: voice !== null && typeof SpeechSynthesisUtterance !== 'undefined', speak, isSpeaking, speechError }
}
