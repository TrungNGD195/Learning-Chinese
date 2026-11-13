import type { PronunciationCode, Sound } from './pronunciationData'

// Editorial guidance per sound, checked against the HSK1 textbook and PolyU BEPTH.
// Reference URLs live in docs/learning-sources.md, outside the learning interface.
const initials: Record<string, string> = {
  b: 'Khép hai môi rồi mở ra nhẹ, không bật hơi mạnh.',
  p: 'Khép hai môi rồi bật ra có luồng hơi rõ.',
  m: 'Khép hai môi, để hơi thoát qua mũi rồi mở môi để chuyển sang a.',
  f: 'Chạm nhẹ răng trên vào môi dưới, cho hơi đi qua khe hẹp.',
  d: 'Chạm đầu lưỡi vào lợi sau răng trên rồi thả ra, không bật hơi mạnh.',
  t: 'Đặt đầu lưỡi ở lợi sau răng trên rồi bật hơi rõ khi thả ra.',
  n: 'Đầu lưỡi chạm lợi sau răng trên, hơi đi qua mũi.',
  l: 'Đầu lưỡi chạm lợi sau răng trên, hơi đi ra hai bên lưỡi; không đưa hơi qua mũi như n.',
  g: 'Phần sau lưỡi chạm vòm mềm rồi thả ra, không bật hơi mạnh.',
  k: 'Phần sau lưỡi chạm vòm mềm rồi thả ra kèm luồng hơi rõ.',
  h: 'Đưa phần sau lưỡi gần vòm mềm để hơi cọ qua khe, giữ luồng hơi liên tục.',
  j: 'Đầu lưỡi gần răng dưới, mặt trước lưỡi nâng lên phía vòm cứng; chặn rồi thả hơi, không bật hơi mạnh.',
  q: 'Giữ đầu lưỡi gần răng dưới, mặt trước lưỡi nâng lên phía vòm cứng rồi bật hơi rõ khi thả ra.',
  x: 'Đầu lưỡi gần răng dưới, mặt trước lưỡi nâng lên và cho hơi xát liên tục.',
  zh: 'Nâng đầu lưỡi về phía sau lợi trên, chặn rồi thả hơi, không bật hơi mạnh.',
  ch: 'Nâng đầu lưỡi về phía sau lợi trên, chặn rồi thả ra với luồng hơi rõ.',
  sh: 'Nâng đầu lưỡi về phía sau lợi trên và cho hơi xát liên tục.',
  r: 'Nâng đầu lưỡi về phía sau lợi trên, giữ luồng hơi nhẹ và có rung dây thanh; không rung đầu lưỡi.',
  z: 'Đầu lưỡi gần mặt sau răng trên, chặn rồi thả hơi, không bật hơi mạnh; không uốn lưỡi như zh.',
  c: 'Đầu lưỡi gần mặt sau răng trên, chặn rồi thả hơi xát với luồng hơi bật rõ.',
  s: 'Đầu lưỡi ở phía trước, gần mặt sau răng trên; cho hơi xát liên tục, không uốn lưỡi như sh.',
}

const finals: Record<string, string> = {
  a: 'Mở miệng rộng, lưỡi hạ thấp, môi không tròn. Giữ nguyên khẩu hình khi đọc a riêng.',
  o: 'Tròn môi, mở miệng vừa phải khi đọc o riêng; giữ âm liền mạch, không thêm phụ âm phía trước.',
  e: 'Môi không tròn, lưỡi lùi về sau. Vần e không đọc như chữ e của tiếng Việt.',
  i: 'Trong yi, lưỡi nâng cao về phía trước, môi không tròn. i sau z/c/s và zh/ch/sh/r có cách đọc khác.',
  u: 'Tròn môi, lưỡi nâng cao về phía sau. Khi đứng riêng, u được viết là wu.',
  ü: 'Đặt lưỡi gần vị trí đọc i rồi tròn môi, không lùi lưỡi về sau như u. Trong yu, ü viết thành u sau y.',
  ai: 'Bắt đầu với a mở rộng rồi lướt về i trong cùng một âm tiết; không đọc thành a và i tách rời.',
  ei: 'Lướt từ e về i trong một âm tiết. Phân biệt với ai có điểm đầu mở rộng hơn.',
  ao: 'Bắt đầu bằng a rồi thu môi và lướt về cuối vần ao; giữ thành một âm tiết, không tách a–o.',
  ou: 'Bắt đầu với môi tròn ở o rồi thu hẹp về u. Không đổi ou thành ao.',
  ia: 'Lướt nhanh từ i sang a; phần a mở rõ, cả vần nằm trong một âm tiết. Không thêm j phía trước.',
  ie: 'Lướt từ i sang âm e mở ở phía trước, không dùng khẩu hình lùi sau của vần e đơn. Đứng riêng viết ye.',
  iao: 'Lướt từ i qua a rồi thu về cuối vần ao; không chia yao thành nhiều tiếng.',
  iu: 'iu là cách viết gọn của iou sau thanh mẫu. Khi nghe riêng, đọc cả vần iou, có chuyển tiếp qua o.',
  ua: 'Từ u tròn môi, mở sang a trong cùng một âm tiết; không thêm g phía trước.',
  uo: 'Từ u, mở môi vừa phải sang o nhưng vẫn giữ môi tròn, như trong wo.',
  uai: 'Lướt từ u qua a rồi về i; phần a mở rõ, không tách thành ba tiếng.',
  ui: 'ui là cách viết gọn của uei sau thanh mẫu. Khi nghe riêng, đọc uei, lướt qua e rồi về i.',
  üe: 'Bắt đầu với ü tròn môi rồi mở sang âm e phía trước. Trong yue, bỏ hai chấm khi viết sau y.',
  an: 'Bắt đầu với a, kết thúc bằng đầu lưỡi chạm lợi sau răng trên để tạo -n; không đổi thành -ng.',
  en: 'Kết thúc bằng -n ở đầu lưỡi, như en; phân biệt với eng có âm mũi ở phần sau lưỡi.',
  ang: 'Từ a, nâng phần sau lưỡi để kết thúc bằng -ng; đầu lưỡi không chạm lợi như khi đọc an.',
  eng: 'Bắt đầu với nguyên âm giữa, môi không tròn rồi kết thúc bằng -ng ở phần sau lưỡi; không chặn thành -n ở đầu lưỡi.',
  ong: 'Giữ môi tròn, lưỡi ở phía sau rồi kết thúc bằng -ng; không thêm tiếng g ở cuối hoặc phụ âm ở đầu.',
  ian: 'Lướt từ i sang phần nguyên âm mở phía trước rồi khép bằng -n. a trong ian không mở rộng như a đứng riêng.',
  in: 'Giữ i ở phía trước rồi chạm đầu lưỡi vào lợi trên để kết thúc -n; không thêm âm g như ing.',
  iang: 'Lướt từ i qua a và kết thúc bằng -ng. Đứng riêng viết yang.',
  ing: 'Từ i, nâng phần sau lưỡi để kết thúc bằng -ng; phân biệt với in dùng đầu lưỡi.',
  iong: 'Tròn môi khi đọc vần iong và kết thúc bằng -ng. Khi không có thanh mẫu, viết yong.',
  uan: 'Lướt từ u sang a rồi kết thúc bằng -n. Trong wan, đầu u được viết thành w.',
  un: 'Vần uen được viết wen khi đứng riêng, như wen; sau thanh mẫu thường viết gọn thành un, như lun. Đừng nhầm với ün trong jun.',
  uang: 'Lướt từ u qua a rồi kết thúc -ng. Đứng riêng viết wang; phân biệt với wan kết thúc -n.',
  ueng: 'Từ u, lướt qua e và kết thúc -ng. Khi đứng riêng viết weng; không đọc thành wen.',
  üan: 'Bắt đầu với ü tròn môi, mở sang nguyên âm phía trước rồi kết thúc -n. Trong yuan, ü viết thành u sau y.',
  ün: 'Giữ lưỡi ở vị trí ü, môi tròn rồi kết thúc -n. Trong yun, ü viết thành u; cách đọc khác un trong lun.',
  er: 'Nâng đầu lưỡi hơi hướng về sau khi đọc er; không thêm một tiếng r riêng. Vần er có thể đứng thành một âm tiết.',
}

const tones: Record<string, string> = {
  'Thanh 1 · ˉ': 'Đọc mā với giọng cao và ngang trong khoảng giọng thoải mái của bạn; giữ độ cao đều, không nhấc lên ở cuối.',
  'Thanh 2 · ˊ': 'Đọc má với giọng đi từ mức vừa lên cao; nâng giọng liền mạch, không hạ xuống trước như thanh 3 đọc riêng.',
  'Thanh 3 · ˇ': 'Khi đọc riêng mǎ, hạ giọng thấp rồi nâng lên. Khi nói liền, thanh 3 thường không nâng đầy đủ; học cách kết hợp ở phần biến điệu.',
  'Thanh 4 · ˋ': 'Đọc mà với giọng đi từ cao xuống thấp, gọn và dứt khoát; không kéo đuôi ngang hoặc nâng lại ở cuối.',
  'Thanh nhẹ': 'Trong māma, âm ma thứ hai ngắn và nhẹ hơn âm đầu, không mang dấu thanh; độ cao phụ thuộc âm tiết trước.',
}

export function pronunciationTip(code: PronunciationCode, sound: Sound): string | undefined {
  if (code === 'SANDHI') return sandhi[sound.hanzi]
  return (code === 'INITIALS' ? initials : code === 'FINALS' ? finals : tones)[sound.symbol]
}

const sandhi: Record<string, string> = {
  '你好': 'Ở đây chỉ đổi cách đọc của 你 thành gần ní; 好 vẫn là thanh 3. Pinyin của lời chào vẫn viết nǐ hǎo.',
  '老师': 'Trong lǎoshī, lǎo hạ xuống thấp rồi nối sang shī; không nâng lǎo thành láo.',
  '我很好': 'Với nhịp 我 / 很好 đang minh họa, 我 đọc thấp, 很 đọc gần hén. Nhịp nói khác có thể làm cả chuỗi biến đổi khác.',
  '一定': '定 là thanh 4, vì vậy 一 đọc yí trong yídìng; đừng giữ yī khi đọc liền cụm này.',
  '一天': '天 là thanh 1, vì vậy 一 đọc yì. Giữ tiān cao và ngang sau yì.',
  '一年': '年 là thanh 2, vì vậy 一 đọc yì. Nối yì đi xuống với nián đi lên.',
  '一起': '起 là thanh 3, vì vậy 一 đọc yì. Không áp dụng quy tắc hai thanh 3 cho cụm này.',
  '第一': '第一 là số thứ tự nên 一 giữ yī; không đổi thành yì chỉ vì đứng sau dì.',
  '不是': '是 mang thanh 4 nên 不 đổi cách đọc thành bú. Ở đây nguyên nhân là thanh phía sau, không phải nghĩa phủ định.',
  '不好': '好 mang thanh 3 nên 不 vẫn đọc bù. Chỉ đổi 不 thành bú khi âm tiết phía sau mang thanh 4.',
  '看一看': 'Trong cấu trúc động từ + 一 + động từ này, đọc yi ngắn và nhẹ; không đọc thành yí dù 看 mang thanh 4.',
  '好不好': 'Trong câu hỏi 好不好, bu thường đọc nhẹ và ngắn. Đừng đọc cả cụm như ba từ tách rời.',
}
