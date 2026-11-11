import type { PronunciationCode, Sound } from './pronunciationData'

// Editorial guidance per sound, checked against the HSK1 textbook and PolyU BEPTH.
// Reference URLs live in docs/learning-sources.md, outside the learning interface.
const initials: Record<string, string> = {
  b: 'Khép hai môi rồi mở ra, không bật hơi mạnh. b trong bā khác p ở lượng hơi, không phải b hữu thanh của tiếng Việt.',
  p: 'Khép hai môi rồi bật ra có luồng hơi rõ. Thử giữ mẩu giấy trước miệng khi đọc pà và so với bā.',
  m: 'Khép hai môi, để hơi thoát qua mũi rồi mở sang a trong mā.',
  f: 'Chạm nhẹ răng trên vào môi dưới, cho hơi đi qua khe hẹp; không khép cả hai môi như m.',
  d: 'Chạm đầu lưỡi vào lợi sau răng trên rồi thả ra, không bật hơi mạnh. So sánh với t trong tā.',
  t: 'Đặt đầu lưỡi ở lợi sau răng trên rồi bật hơi rõ khi thả ra. t có nhiều hơi hơn d.',
  n: 'Đầu lưỡi chạm lợi sau răng trên, hơi đi qua mũi. Phân biệt n trong nǐ với l trong liù.',
  l: 'Đầu lưỡi chạm lợi sau răng trên, hơi đi ra hai bên lưỡi; không đưa hơi qua mũi như n.',
  g: 'Phần sau lưỡi chạm vòm mềm rồi thả ra, không bật hơi mạnh. g trong gē không phải âm g xát của tiếng Việt.',
  k: 'Phần sau lưỡi chạm vòm mềm rồi thả ra kèm luồng hơi rõ; k bật hơi hơn g.',
  h: 'Đưa phần sau lưỡi gần vòm mềm để hơi cọ qua khe; giữ luồng hơi liên tục, không chặn rồi bật như k.',
  j: 'Đầu lưỡi gần răng dưới, mặt trước lưỡi nâng lên phía vòm cứng; chặn rồi thả hơi, không bật hơi mạnh.',
  q: 'Giữ đầu lưỡi gần răng dưới như j, nhưng bật hơi rõ khi thả ra. Không uốn đầu lưỡi như ch.',
  x: 'Đầu lưỡi gần răng dưới, mặt trước lưỡi nâng lên; cho hơi xát liên tục, không chặn rồi bật như q.',
  zh: 'Nâng đầu lưỡi về phía sau lợi trên, chặn rồi thả hơi; không bật hơi mạnh. Không đặt lưỡi sát răng như z.',
  ch: 'Giữ vị trí lưỡi như zh nhưng bật hơi rõ. Phân biệt ch uốn lưỡi với c đặt lưỡi phía trước.',
  sh: 'Nâng đầu lưỡi về phía sau lợi trên và cho hơi xát liên tục; không chặn rồi bật như ch.',
  r: 'Nâng đầu lưỡi về phía sau lợi trên, giữ luồng hơi nhẹ và có rung dây thanh; không rung đầu lưỡi.',
  z: 'Đầu lưỡi gần mặt sau răng trên, chặn rồi thả hơi, không bật hơi mạnh; không uốn lưỡi như zh.',
  c: 'Giữ vị trí lưỡi như z nhưng bật hơi rõ. Phân biệt c với ch bằng vị trí đầu lưỡi.',
  s: 'Đầu lưỡi ở phía trước, gần mặt sau răng trên; cho hơi xát liên tục, không uốn lưỡi như sh.',
}

const finals: Record<string, string> = {
  a: 'Mở miệng rộng, lưỡi hạ thấp, môi không tròn. Giữ nguyên khẩu hình khi đọc a trong mā.',
  o: 'Tròn môi khi đọc o trong bō. Có thể nghe một chuyển tiếp u rất ngắn; không tách thành hai tiếng.',
  e: 'Môi không tròn, lưỡi lùi về sau. e trong é không đọc như chữ e của tiếng Việt.',
  i: 'Trong yī, lưỡi nâng cao về phía trước, môi không tròn. i sau z/c/s và zh/ch/sh/r có cách đọc khác.',
  u: 'Tròn môi, lưỡi nâng cao về phía sau. Khi đứng riêng, u được viết là wu như trong wū.',
  ü: 'Đặt lưỡi gần vị trí đọc i rồi tròn môi, không lùi lưỡi về sau như u. Trong yú, ü viết thành u sau y.',
  ai: 'Bắt đầu với a mở rộng rồi lướt về i trong cùng một âm tiết; không đọc thành a và i tách rời.',
  ei: 'Lướt từ e về i trong một âm tiết, như ēi trong bēi. Phân biệt với ai có điểm đầu mở rộng hơn.',
  ao: 'Bắt đầu bằng a rồi thu môi và lướt về cuối vần ao; giữ thành một âm tiết, không tách a–o.',
  ou: 'Bắt đầu với môi tròn ở o rồi thu hẹp về u. Không đổi ou thành ao.',
  ia: 'Lướt nhanh từ i sang a, như trong jiā; phần a mở rõ, cả vần nằm trong một âm tiết.',
  ie: 'Lướt từ i sang âm e mở ở phía trước, không dùng e lùi sau như trong é. Đứng riêng viết ye, như yè.',
  iao: 'Lướt từ i qua a rồi thu về cuối vần ao; không chia yāo thành nhiều tiếng.',
  iu: 'iu là cách viết gọn của iou sau thanh mẫu, như liù. Có chuyển tiếp qua o; dấu thanh đặt trên u.',
  ua: 'Từ u tròn môi, mở sang a trong cùng một âm tiết, như guā.',
  uo: 'Từ u, mở môi vừa phải sang o nhưng vẫn giữ môi tròn, như trong wǒ.',
  uai: 'Lướt từ u qua a rồi về i, như kuài; phần a mở rõ, không tách thành ba tiếng.',
  ui: 'ui là cách viết gọn của uei sau thanh mẫu. Trong shuǐ, lướt qua e rồi về i; dấu thanh đặt trên i.',
  üe: 'Bắt đầu với ü tròn môi rồi mở sang âm e phía trước. Trong yuè, bỏ hai chấm khi viết sau y.',
  an: 'Bắt đầu với a, kết thúc bằng đầu lưỡi chạm lợi sau răng trên để tạo -n; không đổi thành -ng.',
  en: 'Kết thúc bằng -n ở đầu lưỡi, như ēn; phân biệt với eng có âm mũi ở phần sau lưỡi.',
  ang: 'Từ a, nâng phần sau lưỡi để kết thúc bằng -ng; đầu lưỡi không chạm lợi như khi đọc an.',
  eng: 'Kết thúc bằng -ng ở phần sau lưỡi, như trong fēng; không dùng đầu lưỡi chặn thành -n.',
  ong: 'Giữ môi tròn, kết thúc bằng -ng ở phần sau lưỡi, như zhōng; không thêm tiếng g ở cuối.',
  ian: 'Lướt từ i sang phần nguyên âm mở phía trước rồi khép bằng -n. a trong ian không mở rộng như a đứng riêng.',
  in: 'Giữ i ở phía trước rồi chạm đầu lưỡi vào lợi trên để kết thúc -n; không thêm âm g như ing.',
  iang: 'Lướt từ i qua a và kết thúc bằng -ng. Đứng riêng viết yang, như yáng.',
  ing: 'Từ i, nâng phần sau lưỡi để kết thúc bằng -ng; phân biệt với in dùng đầu lưỡi.',
  iong: 'Tròn môi khi đọc vần iong và kết thúc bằng -ng. Khi không có thanh mẫu, viết yong như trong yòng.',
  uan: 'Lướt từ u sang a rồi kết thúc bằng -n. Trong wàn, đầu u được viết thành w.',
  un: 'Vần uen được viết wen khi đứng riêng, như wèn; sau thanh mẫu thường viết gọn thành un, như lùn. Đừng nhầm với ün trong jūn.',
  uang: 'Lướt từ u qua a rồi kết thúc -ng. Đứng riêng viết wang, như wáng; phân biệt với wan kết thúc -n.',
  ueng: 'Từ u, lướt qua e và kết thúc -ng. Khi đứng riêng viết weng, như wēng; không đọc thành wen.',
  üan: 'Bắt đầu với ü tròn môi, mở sang nguyên âm phía trước rồi kết thúc -n. Trong yuán, ü viết thành u sau y.',
  ün: 'Giữ lưỡi ở vị trí ü, môi tròn rồi kết thúc -n. Trong yún, ü viết thành u; cách đọc khác un trong lùn.',
  er: 'Nâng đầu lưỡi hơi hướng về sau khi đọc ér; không thêm một tiếng r riêng. Vần er có thể đứng thành một âm tiết.',
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
