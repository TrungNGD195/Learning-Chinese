// Textbook HSK1: PDF 7–8, 18, 30 and 38; phrase grouping is illustrated
// conservatively. Supplementary V-一-V / A-不-A references are in the source note.
export const sandhiGroups = [
  { title: 'Thanh 3 khi nói liền', tip: 'Chú ý âm tiết đứng sau và nhịp của cụm từ; không đọc mọi thanh 3 thành một đường xuống rồi lên đầy đủ.', sounds: [
    { symbol: '3 + 3 → 2 + 3', hanzi: '你好', pinyin: 'nǐ hǎo', spoken: 'ní hǎo', meaning: 'Xin chào', explanation: 'Hai thanh 3 liền nhau trong cùng một cụm: thanh 3 đầu đọc gần thanh 2. Khi viết pinyin, vẫn giữ nǐ hǎo.' },
    { symbol: '3 → nửa thanh 3', hanzi: '老师', pinyin: 'lǎoshī', spoken: 'lǎo (hạ thấp) + shī', meaning: 'Thầy, cô giáo', explanation: 'Trước thanh 1, 2, 4 hoặc nhiều âm tiết thanh nhẹ, thanh 3 thường chỉ đọc phần hạ thấp, không nhấc lên rõ như khi đọc riêng. Không đổi thành thanh 2.', note: 'Ví dụ thêm: 很忙 hěn máng (rất bận), 想去 xiǎng qù (muốn đi). Thanh nhẹ có cách kết hợp riêng; hãy nghe cả cụm.' },
    { symbol: 'Thanh 3 theo nhịp cụm', hanzi: '我很好', pinyin: 'wǒ hěn hǎo', spoken: 'wǒ / hén hǎo', meaning: 'Tôi rất khỏe', explanation: 'Với nhịp 我 / 很好, cặp 很好 đọc gần hén hǎo; 我 thường hạ thấp. Không tự đổi mọi thanh 3 đầu chuỗi thành thanh 2.', note: 'Cách nhóm từ và nhịp nói ảnh hưởng chuỗi ba thanh 3 trở lên. Đây là một cách đọc theo nhịp minh họa, không phải công thức duy nhất.' },
  ] },
  { title: 'Biến điệu của 一', tip: 'Một mình hoặc trong số thứ tự: yī. Trước thanh 4: yí. Trước thanh 1, 2, 3: yì.', sounds: [
    { symbol: '一 + 4 → yí', hanzi: '一定', pinyin: 'yī + dìng', spoken: 'yídìng', meaning: 'Nhất định', explanation: '一 đứng trước thanh 4 thì đọc thành thanh 2. Ví dụ khác: 一次 yícì (một lần).' },
    { symbol: '一 + 1 → yì', hanzi: '一天', pinyin: 'yī + tiān', spoken: 'yìtiān', meaning: 'Một ngày', explanation: '一 đứng trước thanh 1 thì đọc thành thanh 4.' },
    { symbol: '一 + 2 → yì', hanzi: '一年', pinyin: 'yī + nián', spoken: 'yìnián', meaning: 'Một năm', explanation: '一 đứng trước thanh 2 thì đọc thành thanh 4.' },
    { symbol: '一 + 3 → yì', hanzi: '一起', pinyin: 'yī + qǐ', spoken: 'yìqǐ', meaning: 'Cùng nhau', explanation: '一 đứng trước thanh 3 thì đọc thành thanh 4. Ví dụ thêm: 一口 yì kǒu (một miếng, một ngụm).' },
    { symbol: '一 giữ thanh 1', hanzi: '第一', pinyin: 'dìyī', spoken: 'dìyī', meaning: 'Thứ nhất', explanation: '一 đứng riêng, khi đếm số hoặc trong số thứ tự thì giữ yī. Ví dụ: 一、二、三 yī, èr, sān; 第一 dìyī.' },
  ] },
  { title: 'Biến điệu của 不', tip: 'Trước thanh 4, 不 đọc thành bú; trước thanh 1, 2, 3 thường vẫn là bù.', sounds: [
    { symbol: '不 + 4 → bú', hanzi: '不是', pinyin: 'bù + shì', spoken: 'bú shì', meaning: 'Không phải', explanation: '不 đứng trước âm tiết thanh 4 thì đọc thành thanh 2. Ví dụ thêm: 不去 bú qù (không đi).' },
    { symbol: '不 giữ thanh 4', hanzi: '不好', pinyin: 'bù hǎo', spoken: 'bù hǎo', meaning: 'Không tốt', explanation: 'Trước thanh 1, 2, 3, 不 thường giữ thanh 4. Ví dụ: 不喝 bù hē (không uống), 不来 bù lái (không đến).' },
  ] },
  { title: 'Đọc nhẹ trong cụm lặp', tip: 'Trong một số cấu trúc, 一 hoặc 不 được đọc ngắn, nhẹ và không mang dấu thanh.', sounds: [
    { symbol: 'V + 一 + V', hanzi: '看一看', pinyin: 'kàn + yī + kàn', spoken: 'kàn yi kàn', meaning: 'Xem thử một chút', explanation: '一 ở giữa hai động từ giống nhau thường đọc thanh nhẹ: 看一看 kàn yi kàn. Không áp dụng máy móc quy tắc 一 trước thanh 4 ở trường hợp này.' },
    { symbol: 'A + 不 + A', hanzi: '好不好', pinyin: 'hǎo + bù + hǎo', spoken: 'hǎo bu hǎo', meaning: 'Có tốt không? / Có được không?', explanation: '不 ở giữa câu hỏi khẳng định–phủ định thường được đọc nhẹ trong lời nói tự nhiên. Ví dụ khác: 是不是 shì bu shì.' },
  ] },
]
