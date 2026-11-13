import { sandhiGroups } from './sandhiData'
import { ongClipForDuration } from './ongDuration'

export type PronunciationCode = 'INITIALS' | 'FINALS' | 'TONES' | 'SANDHI'
export type Sound = { symbol: string; hanzi: string; pinyin: string; spoken?: string; meaning?: string; explanation?: string; note?: string; audioUnavailable?: boolean; clip?: string }

// Source: local HSK1 3.0 Hanu 24.6.26.pdf, PDF4–7,17–18,27–29.
// Ordered groups retain the server-owned21/36/5 progression contract.
type SoundGroup = { title: string; tip: string; sounds: Sound[] }

const initials: SoundGroup[] = [
  { title: 'Âm môi', tip: 'Khép hoặc đưa môi gần nhau. p bật hơi rõ hơn b.', sounds: [
    { symbol: 'b', hanzi: '八', pinyin: 'ba' }, { symbol: 'p', hanzi: '趴', pinyin: 'pa' },
    { symbol: 'm', hanzi: '妈', pinyin: 'ma' }, { symbol: 'f', hanzi: '发', pinyin: 'fa' },
  ] },
  { title: 'Đầu lưỡi', tip: 'Đặt đầu lưỡi gần lợi trên; t bật hơi rõ hơn d.', sounds: [
    { symbol: 'd', hanzi: '搭', pinyin: 'da' }, { symbol: 't', hanzi: '他', pinyin: 'ta' },
    { symbol: 'n', hanzi: '妮', pinyin: 'ni' }, { symbol: 'l', hanzi: '拉', pinyin: 'la' },
  ] },
  { title: 'Gốc lưỡi', tip: 'Phần sau của lưỡi hướng lên vòm mềm; k bật hơi rõ hơn g.', sounds: [
    { symbol: 'g', hanzi: '哥', pinyin: 'ge' }, { symbol: 'k', hanzi: '科', pinyin: 'ke' },
    { symbol: 'h', hanzi: '喝', pinyin: 'he' },
  ] },
  { title: 'Mặt lưỡi', tip: 'Giữ lưỡi phía trước và môi hơi mở. q bật hơi mạnh hơn j.', sounds: [
    { symbol: 'j', hanzi: '鸡', pinyin: 'ji' }, { symbol: 'q', hanzi: '七', pinyin: 'qi' },
    { symbol: 'x', hanzi: '西', pinyin: 'xi' },
  ] },
  { title: 'Uốn lưỡi', tip: 'Đưa đầu lưỡi hơi cong về phía vòm miệng. Chú ý phân biệt zh/ch/sh với z/c/s.', sounds: [
    { symbol: 'zh', hanzi: '渣', pinyin: 'zha' }, { symbol: 'ch', hanzi: '插', pinyin: 'cha' },
    { symbol: 'sh', hanzi: '沙', pinyin: 'sha' }, { symbol: 'r', hanzi: '扔', pinyin: 'reng' },
  ] },
  { title: 'Đầu lưỡi trước', tip: 'Đầu lưỡi ở gần mặt sau răng trên; c bật hơi rõ hơn z.', sounds: [
    { symbol: 'z', hanzi: '匝', pinyin: 'za' }, { symbol: 'c', hanzi: '擦', pinyin: 'ca' },
    { symbol: 's', hanzi: '仨', pinyin: 'sa' },
  ] },
]

const finals: SoundGroup[] = [
  { title: 'Vận mẫu đơn', tip: 'Luyện từng khẩu hình. Với ü, giữ môi tròn trong khi lưỡi ở vị trí gần như khi đọc i.', sounds: [
    { symbol: 'a', hanzi: '阿', pinyin: 'a' }, { symbol: 'o', hanzi: '噢', pinyin: 'o' },
    { symbol: 'e', hanzi: '婀', pinyin: 'e' }, { symbol: 'i', hanzi: '衣', pinyin: 'i', note: 'Mẫu này là i thông thường. Sau z, c, s và zh, ch, sh, r, chữ i được đọc với vị trí lưỡi khác; không phải âm i trong yi và không phải vận mẫu ü. Các âm ghép đặc biệt này được học tại phần ghi nhớ vận mẫu.' },
    { symbol: 'u', hanzi: '乌', pinyin: 'u' }, { symbol: 'ü', hanzi: '迂', pinyin: 'ü' },
  ] },
  { title: 'Vận mẫu ghép', tip: 'Chuyển khẩu hình liền mạch trong một âm tiết, không tách thành hai tiếng.', sounds: [
    { symbol: 'ai', hanzi: '', pinyin: 'ai', clip: '/academy/audio/isolated-finals-v1/ai.wav' }, { symbol: 'ei', hanzi: '诶', pinyin: 'ei' },
    { symbol: 'ao', hanzi: '凹', pinyin: 'ao' }, { symbol: 'ou', hanzi: '欧', pinyin: 'ou' },
    { symbol: 'ia', hanzi: '鸭', pinyin: 'ia' }, { symbol: 'ie', hanzi: '椰', pinyin: 'ie' },
    { symbol: 'iao', hanzi: '腰', pinyin: 'iao' }, { symbol: 'iu', hanzi: '优', pinyin: 'iu' },
    { symbol: 'ua', hanzi: '蛙', pinyin: 'ua' }, { symbol: 'uo', hanzi: '窝', pinyin: 'uo' },
    { symbol: 'uai', hanzi: '歪', pinyin: 'uai' }, { symbol: 'ui', hanzi: '威', pinyin: 'ui' },
    { symbol: 'üe', hanzi: '约', pinyin: 'üe' },
  ] },
  { title: 'Vận mẫu có âm mũi', tip: 'Phân biệt đuôi -n ở phía trước với -ng ở phía sau; nghe và luyện theo từng cặp.', sounds: [
    { symbol: 'an', hanzi: '安', pinyin: 'an' }, { symbol: 'en', hanzi: '恩', pinyin: 'en' },
    { symbol: 'ang', hanzi: '肮', pinyin: 'ang' }, { symbol: 'eng', hanzi: '', pinyin: 'eng', clip: '/academy/audio/isolated-finals-v1/eng.wav' },
    { symbol: 'ong', hanzi: '', pinyin: 'ong', clip: ongClipForDuration() }, { symbol: 'ian', hanzi: '烟', pinyin: 'ian' },
    { symbol: 'in', hanzi: '因', pinyin: 'in' }, { symbol: 'iang', hanzi: '央', pinyin: 'iang' },
    { symbol: 'ing', hanzi: '英', pinyin: 'ing' }, { symbol: 'iong', hanzi: '拥', pinyin: 'iong' },
    { symbol: 'uan', hanzi: '弯', pinyin: 'uan' }, { symbol: 'un', hanzi: '温', pinyin: 'un' },
    { symbol: 'uang', hanzi: '汪', pinyin: 'uang' }, { symbol: 'ueng', hanzi: '翁', pinyin: 'ueng' },
    { symbol: 'üan', hanzi: '冤', pinyin: 'üan' }, { symbol: 'ün', hanzi: '晕', pinyin: 'ün' },
  ] },
  { title: 'Vận mẫu cuốn lưỡi', tip: 'er có thể là một âm tiết độc lập và cũng xuất hiện trong hiện tượng nhi hóa.', sounds: [
    { symbol: 'er', hanzi: '', pinyin: 'er', clip: '/academy/audio/isolated-finals-v1/er.wav', note: 'Âm mẫu đọc riêng vận mẫu er, không ghép thanh mẫu.' },
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
    intro: 'Nghe thanh mẫu trong một âm tiết ghép đơn giản, quan sát khẩu hình và đọc lại. Âm mẫu đọc cao, ngang; pinyin ở đây không ghi dấu thanh.',
    groups: initials,
    notes: ['Bộ 21 thanh mẫu thường được học theo các nhóm ở trên. y và w chủ yếu là quy ước viết âm tiết không có thanh mẫu, không được tính vào 21 âm này.', 'Mẹo phân biệt b/p, d/t và g/k: đặt một mẩu giấy trước miệng; âm bật hơi làm giấy chuyển động rõ hơn.'],
  },
  FINALS: {
    intro: 'Nghe vần riêng ở ô bên trái, rồi so sánh với vần ghép thanh mẫu ở ô bên phải. Âm ghép đọc cao, ngang; pinyin không ghi dấu thanh.',
    groups: finals,
    notes: ['Khi i, u, ü đứng đầu âm tiết, cách viết thường dùng y hoặc w: yi, wu, yu. Đây là cách viết Pinyin, không phải thêm phụ âm mới.', 'Sau j, q, x và y, hai chấm của ü thường được lược trong chữ viết: ju, qu, xu, yu. Khi nghe riêng, iu, ui, un được đọc theo dạng đầy đủ iou, uei, uen.', 'Chữ i trong zi, ci, si, zhi, chi, shi, ri không phát âm giống i trong yi. Đây là cách đọc đặc biệt của i sau các nhóm thanh mẫu này; không đọc như chữ i của tiếng Việt và cũng không thay bằng vận mẫu ü.'],
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
