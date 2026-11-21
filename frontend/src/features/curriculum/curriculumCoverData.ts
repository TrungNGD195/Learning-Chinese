export type CoverTopic='pronunciation'|'measure-words'|'greetings'|'introductions'|'nationality'|'family'|'dates-food'|'study'|'journey'
 |'phone'|'daily-schedule'|'workplace'|'weekend'|'market'|'university'|'winter'|'cafe'|'train'|'chinese-food'
 |'beijing'|'xian'|'visiting'|'birthday'|'sports'|'watches'|'exam'|'health'|'friends'|'airport'
 |'restaurant-menu'|'moving-home'|'grassland-holiday'|'photography'|'high-speed-train'|'wedding-clothes'|'recovery'|'tennis'|'homework'|'office-documents'|'wind-and-rain'|'reading-library'|'graduation'|'panda-zoo'|'spring-festival'

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
 phone:[9,'Hai bạn gấu trúc trao đổi số điện thoại'],
 'daily-schedule':[10,'Gấu trúc xem đồng hồ để sắp xếp sinh hoạt hằng ngày'],
 workplace:[11,'Bác sĩ gấu trúc tại bệnh viện'],
 weekend:[12,'Những người bạn cùng vui chơi và ca hát cuối tuần'],
 market:[13,'Mua táo và hỏi giá ở chợ'],
 university:[14,'Sinh viên gấu trúc bên khuôn viên đại học và xe đạp'],
 winter:[15,'Gấu trúc uống trà ấm trong ngày tuyết rơi'],
 cafe:[16,'Gọi trà, bánh mì và sủi cảo ở quán ăn'],
 train:[17,'Những người bạn xem phim trên chuyến tàu'],
 'chinese-food':[18,'Gia đình gấu trúc thưởng thức các món ăn Trung Quốc'],
 beijing:[19,'Gấu trúc tham quan cung điện ở Bắc Kinh'],
 xian:[20,'Lên kế hoạch du lịch Tây An và tìm hiểu Binh Mã Dũng'],
 visiting:[21,'Gấu trúc mang quà đến thăm ông bà'],
 birthday:[22,'Mừng sinh nhật với bánh kem, quà và bút vẽ'],
 sports:[23,'Những người bạn cùng đánh cầu lông'],
 watches:[24,'So sánh hai chiếc đồng hồ ở cửa hàng'],
 exam:[25,'Gấu trúc ôn bài trong vở để chuẩn bị thi'],
 health:[26,'Bạn mang nước và thuốc đến thăm gấu trúc bị ốm'],
 friends:[27,'Những người bạn gặp nhau trước cửa nhà'],
 airport:[28,'Gấu trúc chuẩn bị hộ chiếu và hành lý ở sân bay'],
 'restaurant-menu':[29,'Gấu trúc chọn món trên thực đơn ở nhà hàng'],
 'moving-home':[30,'Hai bạn gấu trúc chuyển đồ đến căn nhà mới'],
 'grassland-holiday':[31,'Gia đình gấu trúc du lịch thảo nguyên Tân Cương'],
 photography:[32,'Gấu trúc chụp ảnh chim và cây trong công viên'],
 'high-speed-train':[33,'Gấu trúc nghe nhạc trên tàu cao tốc'],
 'wedding-clothes':[34,'Gấu trúc chọn váy và giày dự lễ cưới'],
 recovery:[35,'Bác sĩ gấu trúc trò chuyện cùng bạn đang hồi phục'],
 tennis:[36,'Những người bạn thi đấu quần vợt ở trường'],
 homework:[37,'Hai bạn gấu trúc cùng làm bài tập toán'],
 'office-documents':[38,'Nhân viên gấu trúc chuẩn bị tài liệu và máy in trước cuộc họp'],
 'wind-and-rain':[39,'Gấu trúc mang ô và áo mưa trong ngày nổi gió'],
 'reading-library':[40,'Hai bạn gấu trúc mượn sách ở thư viện'],
 graduation:[41,'Sinh viên gấu trúc trước cổng trường trong ngày tốt nghiệp'],
 'panda-zoo':[42,'Gia đình tham quan gấu trúc đang ăn tre trong vườn thú'],
 'spring-festival':[43,'Gia đình gấu trúc làm sủi cảo và đón Tết dưới đèn lồng đỏ'],
}

const lessonTopics:Record<number,readonly CoverTopic[]>={
 1:['greetings','introductions','nationality','family','dates-food','phone','daily-schedule','workplace','weekend','market','university','winter','cafe','train','chinese-food'],
 2:['beijing','xian','visiting','birthday','sports','watches','exam','health','friends','airport'],
 3:['restaurant-menu','moving-home','grassland-holiday','photography','high-speed-train','wedding-clothes','recovery','tennis','homework','office-documents','wind-and-rain','reading-library','graduation','panda-zoo','spring-festival'],
}

export function curriculumCoverTopic(title:string,unavailable=false,lesson?:{hskLevel:number;lessonNumber:number}):CoverTopic{
 if(unavailable)return 'study'
 if(lesson){const topic=lessonTopics[lesson.hskLevel]?.[lesson.lessonNumber-1];if(topic)return topic}
 const text=title.toLowerCase()
 if(/sân bay|hộ chiếu|chuyến bay|机场|护照/.test(text))return 'airport'
 if(/sinh nhật|生日/.test(text))return 'birthday'
 if(/cầu lông|thể thao|羽毛球|运动/.test(text))return 'sports'
 if(/đồng hồ|手表/.test(text))return 'watches'
 if(/sức khỏe|bị ốm|uống thuốc|讨厌吃药|看病/.test(text))return 'health'
 if(/thời tiết|tuyết|下雪|天气/.test(text))return 'winter'
 if(/điện thoại|手机号|手机/.test(text))return 'phone'
 if(/mua sắm|giá cả|便宜/.test(text))return 'market'
 if(/tây an|兵马俑/.test(text))return 'xian'
 if(/bắc kinh|北京旅游/.test(text))return 'beijing'
 if(/ôn thi|kỳ thi|考试|词难|题难/.test(text))return 'exam'
 if(/gọi món|一杯茶/.test(text))return 'cafe'
 if(/火车|chuyến tàu|hoạt động đã hoàn thành/.test(text))return 'train'
 if(/sở thích|中国菜/.test(text))return 'chinese-food'
 if(/大学|đại học/.test(text))return 'university'
 if(/quốc tịch|việt nam|người trung quốc|越南|中国人|哪国人|nationalit/.test(text))return 'nationality'
 if(/gia đình|hai đứa con|con cái|bố mẹ|家|孩子|父母/.test(text))return 'family'
 if(/ngày|tháng|thời gian|星期|今天|明天|时间|几月|几号/.test(text))return 'dates-food'
 if(/tên|名字|姓名|叫|giới thiệu|làm quen/.test(text))return 'introductions'
 if(/chào|tạm biệt|你好|再见/.test(text))return 'greetings'
 if(/quốc gia|nghề nghiệp|giáo viên|老师|工作/.test(text))return 'nationality'
 if(/hành trình|trường thành|长城/.test(text))return 'journey'
 return 'study'
}

export function curriculumCoverAtlas(topic:CoverTopic){
 const [index,label]=topics[topic]
 if(index<9)return {src:'/academy/curriculum-v2/covers.png',cell:index,label,size:'300% 300%',position:`${index%3*50}% ${Math.floor(index/3)*50}%`}
 if(index>=29){
  const cell=index-29,column=cell%3,row=Math.floor(cell/3)
  const xs=[0,309,625,971],ys=[0,324,648,972,1295,1619]
  const x=xs[column]+2,width=xs[column+1]-x-2,height=width/1.5
  const y=ys[row]+(cell===5?2:(ys[row+1]-ys[row]-height)/2)
  return {src:'/academy/curriculum-v4/hsk3-covers.webp',cell,label,size:`${971/width*100}% ${1619/height*100}%`,position:`${x/(971-width)*100}% ${y/(1619-height)*100}%`}
 }
 const cell=index-9,column=cell%4,row=Math.floor(cell/4)
 // The generated atlas has slightly different row heights. Use its measured
 // seams with a 1px inset so neighboring scenes never bleed into a cover.
 const xs=[0,350,701,1052,1402],ys=[0,232,463,680,901,1122]
 const x=xs[column]+1,y=ys[row]+1,width=xs[column+1]-x-1,height=ys[row+1]-y-1
 return {src:'/academy/curriculum-v3/lesson-covers.webp',cell,label,size:`${1402/width*100}% ${1122/height*100}%`,position:`${x/(1402-width)*100}% ${y/(1122-height)*100}%`}
}
