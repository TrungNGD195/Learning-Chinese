// Shared scenes illustrate a word in context; captions describe what is shown.
// A word's meaning remains in its authored vocabulary record, not in the image.
export const lessonVocabularyScenes: Record<string, [number, string]> = {}
// Family vocabulary uses the human-chibi exception approved by the user.
// Atlas cells are ordered left to right, top to bottom in a 4 × 4 grid.
export const familyIllustrations: Record<string, [number, string]> = {
  爸爸: [0, 'Bố, nhân vật người chibi'],
  妈妈: [1, 'Mẹ, nhân vật người chibi'],
  父母: [2, 'Bố và mẹ, hai nhân vật người chibi'],
  家: [3, 'Gia đình chibi có bố, mẹ và hai con'],
  哥哥: [4, 'Anh trai chibi tuổi thiếu niên'],
  姐姐: [5, 'Chị gái chibi tuổi thiếu niên'],
  弟弟: [6, 'Em trai chibi nhỏ tuổi'],
  妹妹: [7, 'Em gái chibi nhỏ tuổi'],
  儿子: [8, 'Con trai chibi'],
  女儿: [9, 'Con gái chibi'],
  孩子: [10, 'Hai em bé chibi, một bé trai và một bé gái'],
  老公: [0, 'Người chồng chibi'], 丈夫: [0, 'Người chồng chibi'],
  老婆: [1, 'Người vợ chibi'], 妻子: [1, 'Người vợ chibi'],
  爷爷: [12, 'Ông nội chibi, bố của bố; đeo kính, có ria và mặc áo ghi lê xanh'],
  奶奶: [13, 'Bà nội chibi, mẹ của bố; tóc búi bạc và áo vàng'],
  外公: [14, 'Ông ngoại chibi, bố của mẹ; tóc bạc và áo màu đất nung'],
  外婆: [15, 'Bà ngoại chibi, mẹ của mẹ; tóc bạc ngắn, đeo kính và áo xanh lam'],
}
const scenes: [number, string, string[]][] = [
  [0, 'Các bạn gấu trúc chào nhau', ['大家', '你们', '我们', '同学', '们']],
  [1, 'Gấu trúc tự giới thiệu tên', ['我', '叫', '名字']],
  [2, 'Gấu trúc bày tỏ lời cảm ơn', ['谢谢', '不客气']],
  [3, 'Một bạn xin lỗi, một bạn đáp lời trấn an', ['对不起', '没关系', '没事']],
  [4, 'Thầy giáo gấu trúc đang hướng dẫn bài học', ['您', '老师', '中文', '汉语', '班', '学生']],
  [5, 'Nhân vật gấu trúc nữ', ['她', '姐姐', '妹妹', '女朋友']],
  [6, 'Nhân vật gấu trúc nam', ['他', '哥哥', '弟弟', '男', '男朋友', '喂', '再见']],
  [7, 'Hai bạn gấu trúc vui khi làm quen', ['很', '高兴', '认识', '也', '对', '好看', '真', '喜欢']],
  [8, 'Gia đình gấu trúc có bố, mẹ và hai con', ['家', '爸爸', '妈妈', '父母', '孩子', '儿子', '女儿', '和', '有', '个', '口', '多少', '几', '多', '少', '岁', '老公', '丈夫', '老婆', '妻子', '包括', '奶奶', '爷爷', '外公', '外婆']],
  [9, 'Gấu trúc bận làm việc tại bàn', ['工作', '忙', '还', '太', '下班']],
  [10, 'Lịch dùng để xem ngày tháng', ['今年', '今天', '明天', '昨天', '去年', '明年', '天', '号', '月', '星期', '星期日', '星期天', '日', '年', '周末']],
  [11, 'Gấu trúc đang nghỉ ngơi', ['休息']],
  [12, 'Gấu trúc nấu ăn trong bếp', ['会', '做', '做饭', '菜', '吃', '饭', '包子']],
  [13, 'Bữa ăn gồm mì, bánh, cơm, trứng và canh', ['面条儿', '饺子', '一些', '米饭', '馒头', '鸡蛋', '汤']],
  [14, 'Gấu trúc suy nghĩ và đặt câu hỏi', ['请问', '请', '问', '什么', '是', '的', '这', '那', '谁', '哪', '国', '吗', '想', '呢', '没有', '对象', '单身', '结婚']],
  [15, 'Chiếc máy tính xách tay', ['电脑', '新', '它']],
]
for (const [cell, caption, words] of scenes) for (const word of words) lessonVocabularyScenes[word] = [cell, caption]

export const countryIllustrations: Record<string, { label: string; colors: string[] }> = {
  中国: { label: 'Trung Quốc', colors: ['#de2910'] },
  越南: { label: 'Việt Nam', colors: ['#da251d'] },
  法国: { label: 'Pháp', colors: ['#002395', '#fff', '#ed2939'] },
  泰国: { label: 'Thái Lan', colors: ['#a51931', '#fff', '#2d2a4a', '#2d2a4a', '#fff', '#a51931'] },
}

export const foodIllustrations: Record<string, [number, string]> = {
  '面条儿': [0, 'Mì sợi'], '面条': [0, 'Mì sợi'], '饺子': [1, 'Sủi cảo có hình bán nguyệt'], '馒头': [2, 'Màn thầu không nhân'],
  '米饭': [3, 'Cơm trắng'], '鸡蛋': [4, 'Trứng gà'], '汤': [5, 'Canh'],
  '咖啡': [6, 'Cà phê'], '可乐': [7, 'Nước cola'], '啤酒': [8, 'Bia'],
  '酒': [8, 'Bia, một loại đồ uống có cồn'],
}
