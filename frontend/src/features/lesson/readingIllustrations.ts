// Editorial illustrations matched to reviewed reading content. Punctuation/spacing
// changes preserve the scene; new or materially edited readings get no guessed image.
export const readingScenes = [
  {
    "title": "Chào hỏi · 你好",
    "content": "A：你好！\nB：你好！",
    "cell": 0,
    "alt": "Bút và một người bạn vẫy tay chào nhau ở sân trường."
  },
  {
    "title": "Chào lớp và giới thiệu tên",
    "content": "老师：大家好！\n同学们：您好！\n小丽：你们好！我叫小丽。\n同学们：你好，小丽！",
    "cell": 1,
    "alt": "Bút tự giới thiệu trước lớp, thầy cô và các bạn cùng lắng nghe."
  },
  {
    "title": "Cảm ơn và đáp lời",
    "content": "老师：同学们，谢谢！\n同学们：不客气！",
    "cell": 2,
    "alt": "Bút trao tập sách cho thầy cô, cùng mỉm cười cảm ơn và đáp lời."
  },
  {
    "title": "Xin lỗi và đáp lời",
    "content": "李文：对不起！\n白家月：没关系！",
    "cell": 3,
    "alt": "Bút xin lỗi vì làm rơi hộp bút, người bạn dịu dàng đáp lại."
  },
  {
    "title": "Làm quen",
    "content": "李文：你好！我叫李文。\n白家月：你好！我叫白家月。\n李文：很高兴认识你。\n白家月：认识你我也很高兴。",
    "cell": 4,
    "alt": "Bút bắt tay và làm quen với một người bạn mới."
  },
  {
    "title": "Hỏi tên và quốc tịch",
    "content": "李文：请问，你叫什么名字？\n陈天中：我叫陈天中，我是中国人。\n李文：我是越南人，我的中文老师也是中国人。",
    "cell": 5,
    "alt": "Bút trò chuyện với bạn học bên quả địa cầu về tên và quê hương."
  },
  {
    "title": "Giới thiệu một người",
    "content": "安妮：这是谁？\n陈天中：这是我女朋友。\n安妮：你女朋友是哪国人？\n陈天中：我是泰国人，她是法国人。",
    "cell": 6,
    "alt": "Bút giới thiệu một người bạn với bạn học khác."
  },
  {
    "title": "Hỏi thăm qua điện thoại",
    "content": "王一雪：喂，一飞！\n王一飞：姐姐！\n王一雪：你工作还忙吗？\n王一飞：对，还很忙。你也很忙吗？\n王一雪：我不太忙。我们很想你。\n王一飞：我也想你们。\n王一雪：再见！\n王一飞：再见！",
    "cell": 7,
    "alt": "Bút gọi điện hỏi thăm người thân từ bàn làm việc."
  },
  {
    "title": "Hỏi số lượng học sinh",
    "content": "刘明：一飞忙吗？\n王一雪：她很忙。\n刘明：她有多少个学生？\n王一雪：她有二十个学生。",
    "cell": 8,
    "alt": "Bút quan sát và đếm học sinh trong lớp học."
  },
  {
    "title": "Gia đình có mấy người?",
    "content": "王一雪：我有两个哥哥，你呢？\n杨同乐：我没有哥哥。\n王一雪：你家有几口人？\n杨同乐：我家有四口人，爸爸、妈妈、妹妹和我。",
    "cell": 9,
    "alt": "Bút giới thiệu bức ảnh gia đình có bốn thành viên."
  },
  {
    "title": "Giới thiệu con và hỏi tuổi",
    "content": "杨同乐：这是您儿子吗？\n王一雪：是的，我有两个孩子，一个儿子，一个女儿。\n杨同乐：您儿子几岁？\n王一雪：他今年五岁。\n杨同乐：您女儿多大？\n王一雪：她今年十二。",
    "cell": 10,
    "alt": "Bút gặp một phụ huynh cùng con trai nhỏ và con gái lớn hơn."
  },
  {
    "title": "Hỏi ngày tháng và thứ",
    "content": "小丽：请问，今天几月几号？\n小刚：今天十一月二十一号。\n小丽：明天星期几？\n小刚：星期日。明天我休息。",
    "cell": 11,
    "alt": "Bút và bạn cùng xem lịch để hỏi về ngày tháng và ngày nghỉ."
  },
  {
    "title": "Bạn biết nấu món gì?",
    "content": "小丽：你会做饭吗？\n小刚：我会做。\n小丽：你会做什么？\n小刚：我会做面条儿、饺子，也会做一些菜，星期天我也做饭。",
    "cell": 12,
    "alt": "Bút mặc tạp dề làm mì và sủi cảo trong bếp."
  },
  {
    "title": "Chiếc máy tính mới",
    "content": "小丽：小刚，下班吗？\n小刚：下班。\n小丽：这是你的新电脑吗？\n小刚：是的，是我的新电脑。\n小丽：真好看！\n小刚：我也很喜欢它。",
    "cell": 13,
    "alt": "Bút giới thiệu chiếc máy tính mới với bạn."
  }
] as const

const normalize = (content: string) => content.normalize('NFC').replace(/[\s\p{P}]/gu, '')
const scenesByContent = new Map<string, typeof readingScenes[number]>(readingScenes.map(scene => [normalize(scene.content), scene]))

export function readingIllustration(content: string) {
  return scenesByContent.get(normalize(content))
}
