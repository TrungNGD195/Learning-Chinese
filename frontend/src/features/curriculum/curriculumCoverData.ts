export type CoverTopic='pronunciation'|'measure-words'|'greetings'|'introductions'|'nationality'|'family'|'dates-food'|'study'|'journey'

export const topics:Record<CoverTopic,[number,string]>={
 pronunciation:[0,'Gấu trúc luyện nói và nghe cùng giáo viên'],
 'measure-words':[1,'Gấu trúc phân nhóm táo, sách và chén trà để học cách đếm'],
 greetings:[2,'Hai bạn gấu trúc chào nhau trong sân vườn'],
 introductions:[3,'Hai bạn gấu trúc giới thiệu bản thân và làm quen'],
 nationality:[4,'Thầy cô và các bạn gấu trúc tìm hiểu quốc tịch, nghề nghiệp'],
 family:[5,'Gia đình gấu trúc với bố mẹ, hai con và ông bà'],
 'dates-food':[6,'Gấu trúc lên kế hoạch ngày nghỉ và bữa ăn'],
 study:[7,'Sách, bút và trà trong góc học tập'],
 journey:[8,'Trường Thành uốn quanh những dãy núi'],
}

export function curriculumCoverTopic(title:string,unavailable=false):CoverTopic{
 if(unavailable)return 'study'
 const text=title.toLowerCase()
 if(/quốc tịch|việt nam|người trung quốc|越南|中国人|哪国人|nationalit/.test(text))return 'nationality'
 if(/gia đình|hai đứa con|con cái|bố mẹ|家|孩子|父母/.test(text))return 'family'
 if(/ngày|tháng|thời gian|星期|今天|明天|时间|几月|几号/.test(text))return 'dates-food'
 if(/tên|名字|姓名|叫|giới thiệu|làm quen/.test(text))return 'introductions'
 if(/chào|tạm biệt|你好|再见/.test(text))return 'greetings'
 if(/quốc gia|nghề nghiệp|giáo viên|老师|工作/.test(text))return 'nationality'
 if(/hành trình|trường thành|长城/.test(text))return 'journey'
 return 'study'
}
