import type { Sound } from './pronunciationData'

// Legal tone-1 syllables. Do not reuse lexical tone-2/3/4 examples such as
// bu (不), kuai (快), lüe (略), or lü (吕) with their accents merely hidden.
export const finalCombinations: Record<string, Sound> = Object.fromEntries([
  ['a', '妈', 'ma'], ['o', '波', 'bo'], ['e', '哥', 'ge'],
  ['i', '咪', 'mi'], ['u', '姑', 'gu'], ['ü', '居', 'ju'],
  ['ai', '掰', 'bai'], ['ei', '杯', 'bei'], ['ao', '猫', 'mao'], ['ou', '抠', 'kou'],
  ['ia', '家', 'jia'], ['ie', '些', 'xie'], ['iao', '喵', 'miao'], ['iu', '丢', 'diu'],
  ['ua', '瓜', 'gua'], ['uo', '锅', 'guo'], ['uai', '摔', 'shuai'], ['ui', '灰', 'hui'],
  ['üe', '缺', 'que'], ['an', '班', 'ban'], ['en', '奔', 'ben'], ['ang', '帮', 'bang'],
  ['eng', '风', 'feng'], ['ong', '中', 'zhong'], ['ian', '天', 'tian'], ['in', '宾', 'bin'],
  ['iang', '香', 'xiang'], ['ing', '冰', 'bing'], ['iong', '兄', 'xiong'],
  ['uan', '关', 'guan'], ['un', '蹲', 'dun'], ['uang', '光', 'guang'],
  ['üan', '捐', 'juan'], ['ün', '军', 'jun'],
].map(([symbol, hanzi, pinyin]) => [symbol, { symbol, hanzi, pinyin }]))

export const finalReadingNotes: Record<string, string> = {
  e: 'e riêng trong mẫu nghe có lưỡi lùi về sau. Trong ie và üe, phần e được đọc mở hơn, lưỡi ở phía trước; không giữ nguyên khẩu hình của e đơn.',
  i: 'i trong mi giữ lưỡi phía trước, gần như i nghe riêng. Sau z, c, s và zh, ch, sh, r, chữ i có cách đọc khác theo vị trí lưỡi của nhóm đó; không đọc thành i thông thường, và cũng không phải vận mẫu ü.',
  ü: 'j + ü viết thành ju: bỏ hai chấm nhưng vẫn đọc ü. Quy tắc tương tự áp dụng sau q, x và y; không đổi thành u.',
  iu: 'Khi đọc riêng, nghe dạng đầy đủ iou; sau thanh mẫu, viết gọn thành iu như d + iou → diu.',
  ui: 'Khi đọc riêng, nghe dạng đầy đủ uei; sau thanh mẫu, viết gọn thành ui như h + uei → hui.',
  un: 'Khi đọc riêng, nghe dạng đầy đủ uen; sau thanh mẫu, viết gọn thành un như d + uen → dun. Phân biệt với ün trong jun.',
  üe: 'q + üe viết thành que, bỏ hai chấm nhưng vẫn giữ âm ü. Phần e ở đây khác khẩu hình e đơn.',
  üan: 'j + üan viết thành juan, bỏ hai chấm nhưng vẫn giữ âm ü ở đầu vần.',
  ün: 'j + ün viết thành jun, bỏ hai chấm nhưng vẫn đọc ün, khác un trong dun.',
  ueng: 'Vần ueng ở âm tiết không có thanh mẫu được viết weng. Không dùng feng thay cho ueng hoặc ghép thêm một thanh mẫu không hợp lệ.',
  er: 'er không ghép thêm thanh mẫu. Nghe liền một âm tiết, không đọc tách thành e rồi r.',
}

export const specialIExamples: Sound[] = [
  { symbol: 'z', hanzi: '资', pinyin: 'zi' },
  { symbol: 'c', hanzi: '疵', pinyin: 'ci' },
  { symbol: 's', hanzi: '丝', pinyin: 'si' },
  { symbol: 'zh', hanzi: '知', pinyin: 'zhi' },
  { symbol: 'ch', hanzi: '吃', pinyin: 'chi' },
  { symbol: 'sh', hanzi: '诗', pinyin: 'shi' },
  { symbol: 'r', hanzi: '日', pinyin: 'ri' },
].map(example => ({ ...example, clip: `/academy/audio/special-i-native-v7/cmn-${example.pinyin}1.wav` }))

export const specialIGroups = [
  { title: 'i sau z, c, s', sounds: specialIExamples.slice(0, 3) },
  { title: 'i sau zh, ch, sh, r', sounds: specialIExamples.slice(3) },
]
