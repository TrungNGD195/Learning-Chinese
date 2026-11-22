"""Original HSK3.0-style papers. Never copy official sample questions or recordings.

Build-time pinyin uses pypinyin; serving/grading needs only the JSON manifests.
"""
import hashlib
import json
from pathlib import Path
from pypinyin import lazy_pinyin, Style
import re

ROOT = Path(__file__).resolve().parents[1] / 'content' / 'hsk-exams'
PAPERS = {}

def paper(level, sections):
    value={'level':level,'standard':'HSK 3.0','version':'2026-11-22-v1',
        'title':f'Thi thử HSK {level} · HSK 3.0','pinyin_support':level<3,
        'source_url':f'https://www.chinesetest.cn/HSK/{level}',
        'sections':[{'id':key,'label':label,'duration_seconds':seconds,'questions':[]} for key,label,seconds in sections]}
    PAPERS[level]=value
    return value

def add(p, section, part, prompt, choices=None, answer=None, *, audio=None, reading=None,
        image=None, illustration=None, explanation='', hint=None, accepted=None, kind='choice'):
    rows=next(s['questions'] for s in p['sections'] if s['id']==section)
    q={'id':f'h{p["level"]}-{section}-{len(rows)+1:02d}','part':part,'type':kind,'prompt':prompt,
       'explanation':explanation,'reference_answer':answer,'accepted_answers':accepted or [],
       'audio_text':audio,'reading_text':reading,'image_hanzi':image,'illustration_topic':illustration,
       'phonetic_hint':hint,'options':[]}
    if choices:
        for i,c in enumerate(choices):
            q['options'].append({'id':f'o{i+1}','text':c if not isinstance(c,dict) else c.get('text',''),
                                 'image_hanzi':c.get('image') if isinstance(c,dict) else None,
                                 'illustration_topic':c.get('scene') if isinstance(c,dict) else None})
        q['correct_option_id']=f'o{(answer if isinstance(answer,int) else 0)+1}'
        q['reference_answer']=q['options'][int(q['correct_option_id'][1:])-1]['text'] or q['options'][int(q['correct_option_id'][1:])-1]['image_hanzi']
    if p['pinyin_support']:
        for field in ['prompt','reading_text']:
            q[field+'_pinyin']=' '.join(lazy_pinyin(q[field],style=Style.TONE)) if q[field] and re.search(r'[\u3400-\u9fff]',q[field]) else None
        for option in q['options']:
            option['pinyin']=' '.join(lazy_pinyin(option['text'],style=Style.TONE)) if re.search(r'[\u3400-\u9fff]',option['text']) else None
    rows.append(q)

def choices(p, section, part, rows):
    for prompt, options, explanation, *extra in rows:
        add(p,section,part,prompt,options,0,explanation=explanation,**(extra[0] if extra else {}))

def images(words):return [{'image':word} for word in words]

SCENES={'office-documents':'准备会议资料','moving-home':'搬家','high-speed-train':'乘坐高铁',
 'photography':'拍照','wedding-clothes':'选择衣服','recovery':'看病','tennis':'打网球',
 'reading-library':'借书','spring-festival':'过春节','panda-zoo':'看熊猫'}
def scenes(topics):return [{'scene':t,'text':SCENES[t]} for t in topics]

EXPLANATIONS_VI={
 'h2-listening-16':'Người nam nói 身体不舒服 (không khỏe) nên muốn nghỉ thay vì đi chơi bóng.',
 'h2-listening-18':'Hai chiếc áo sơ mi 两件衬衫 là hai món quần áo, không phải ba.',
 'h2-listening-25':'Người nam đã ăn sủi cảo hôm qua và muốn đổi sang mì 面条 hôm nay.',
 'h2-reading-01':'喝茶 nghĩa là uống trà, phù hợp hình bộ ấm và chén trà.',
 'h2-reading-02':'朋友 nghĩa là bạn bè, phù hợp hình hai người bạn.',
 'h2-reading-21':'Thứ Bảy có lớp học; người nói định thăm bà vào Chủ nhật 星期日.',
 'h2-reading-22':'Ngoài màu sắc đẹp, đôi giày còn khá rẻ 比较便宜, nên cô ấy mua.',
 'h2-reading-23':'Xe đạp hỏng 自行车坏了, nên hôm nay người nói đi xe buýt 公共汽车.',
 'h2-reading-24':'Chị gái bơi giỏi 游泳游得很好 và dạy em trai; em trai chưa biết bơi.',
 'h3-listening-11':'Công ty quá xa nhà 离家太远, khiến cô ấy mất ba giờ đi đường mỗi ngày.',
 'h3-listening-12':'Họ chọn tàu cao tốc 高铁 vì vé máy bay đắt; thời gian chỉ lâu hơn một giờ.',
 'h3-listening-13':'Lịch họp đã đổi từ 9 giờ sang 9 giờ 30, thể hiện bằng 改到九点半.',
 'h3-listening-14':'Cô ấy loại váy đỏ và đen, rồi quyết định chọn váy xanh 蓝色.',
 'h3-listening-15':'Ví đã mang theo, nhưng hộ chiếu 护照 vẫn ở văn phòng.',
 'h3-listening-16':'Tiểu Lý là người mượn sách trước, sau đó đưa cho Tiểu Vương. Câu hỏi hỏi người mượn ban đầu.',
 'h3-listening-17':'上个月才开始 nghĩa là mãi tháng trước mới bắt đầu, không phải đã học nhiều năm.',
 'h3-listening-18':'累得不想动 diễn tả mệt đến mức không muốn cử động; anh ấy muốn nghỉ trước.',
 'h3-listening-19':'Máy in hỏng nên cần kiểm tra máy 检查打印机 trước khi in tài liệu.',
 'h3-listening-20':'手机没电 nghĩa là điện thoại hết pin, vì thế cô ấy không chụp ảnh được.',
 'h3-listening-21':'Họp lúc 9 giờ nhưng Tiểu Lâm đã đến lúc 8 giờ 30: anh ấy đến sớm nửa giờ.',
 'h3-listening-22':'又便宜又好吃 nêu hai ưu điểm: giá rẻ và đồ ăn ngon.',
 'h3-listening-23':'Cô ấy đã xuất viện và có thể đi dạo; sức khỏe tốt hơn trước nhiều.',
 'h3-listening-24':'Dự báo nói cuối tuần có thể mưa 可能下雨, vì vậy nên mang ô.',
 'h3-listening-25':'Cậu ấy đọc tiếng Trung và giao tiếp mỗi ngày, kiên trì một năm nên tiến bộ.',
 'h3-listening-26':'Nhà gần ga tàu điện và siêu thị, thuận tiện đi lại và mua sắm; không phải rẻ nhất.',
 'h3-listening-27':'主要吃竹子 nghĩa là chủ yếu ăn tre; đôi lúc còn ăn một ít trái cây.',
 'h3-listening-28':'Anh ấy tốt nghiệp tháng Sáu và muốn tìm việc trước, thay vì học tiếp ngay.',
 'h3-listening-29':'Dọn nhà và gói sủi cảo là những việc gia đình đang làm để chuẩn bị đón Tết.',
 'h3-listening-30':'Dù không thắng, cô ấy nhận ra vấn đề của mình và học được nhiều điều.',
 'h3-reading-01':'几点关门 hỏi giờ đóng cửa; câu trả lời phù hợp là 9 giờ tối.',
 'h3-reading-02':'Áo hơi nhỏ 有点儿小, nên lời đáp hợp lý là thử cỡ lớn hơn.',
 'h3-reading-03':'已经发了 xác nhận tài liệu đã gửi; 收到了 xác nhận người nhận đã nhận được.',
 'h3-reading-04':'忙不忙 hỏi công việc có bận không; 天天加班 cho biết ngày nào cũng tăng ca.',
 'h3-reading-05':'好些了吗 ở đây hỏi bệnh cảm đã đỡ hơn chưa; 好多了 nghĩa là đã đỡ nhiều.',
 'h3-reading-06':'还是 đặt giữa hai lựa chọn. Lời đáp chọn 高铁 và giải thích ga gần nhà.',
 'h3-reading-07':'为什么 hỏi nguyên nhân; 因为 mở đầu lời giải thích về môi trường và con người.',
 'h3-reading-08':'在哪儿拍的 hỏi nơi chụp ảnh; 在草原上 trả lời là ở thảo nguyên.',
 'h3-reading-09':'当然可以 nghĩa là tất nhiên được, phù hợp lời đồng ý giúp chuyển thùng đồ.',
 'h3-reading-10':'已经报名了 nghĩa là đã đăng ký, nên người nói sẽ tham gia cuộc thi.',
 'h3-reading-11':'了解 nghĩa là hiểu, biết rõ hoặc quen thuộc với một nơi hay tình huống.',
 'h3-reading-12':'打扫得干净 dùng 得 để nối hành động dọn dẹp với mức độ sạch sẽ đạt được.',
 'h3-reading-13':'解决问题的办法 là cách giải quyết vấn đề; 办法 đồng nghĩa với phương pháp.',
 'h3-reading-14':'Cấu trúc 把 + đồ vật + hành động mô tả cách xử lý đồ vật: cất hộ chiếu vào túi.',
 'h3-reading-15':'除了…还… bổ sung một khả năng ngoài khả năng đã nhắc: ngoài tiếng Trung còn biết tiếng Anh.',
 'h3-reading-16':'应该 diễn tả lời khuyên hoặc điều nên làm: trời gió lớn thì nên mặc áo khoác.',
 'h3-reading-17':'还是 ở đây nghĩa là vẫn: dù đã đọc ba lần, người nói vẫn thấy cuốn sách thú vị.',
 'h3-reading-18':'想…什么就…什么 thể hiện lựa chọn tự do: muốn ăn món gì thì gọi món đó.',
 'h3-reading-19':'改变计划 nghĩa là thay đổi kế hoạch; mưa lớn khiến họ phải điều chỉnh dự định.',
 'h3-reading-20':'终于 nhấn mạnh kết quả cuối cùng đạt được sau một quá trình nỗ lực.',
 'h3-reading-21':'Vé tàu cao tốc chỉ 400 tệ, bằng nửa vé máy bay; họ có nhiều thời gian nên chọn tàu.',
 'h3-reading-22':'Máy in cũ thường xuyên hỏng, khiến tài liệu không được in đúng giờ, nên cần thay máy.',
 'h3-reading-23':'虽然…但是… nêu sự tương phản: tuy mệt nhưng cảnh đẹp khiến Tiểu Lý hài lòng.',
 'h3-reading-24':'Cô ấy coi trọng cơ hội học hỏi và giao tiếp với nhiều người, không chỉ xem mức lương.',
 'h3-reading-25':'Thầy Trương khuyến khích học sinh nói ý kiến, đặt câu hỏi và cùng thảo luận.',
 'h3-reading-26':'Ông bà ở xa sẽ về đón Tết, tạo cơ hội đoàn tụ khiến các em nhỏ vui mừng.',
 'h3-reading-27':'Sách phải trả trong hai tuần; muốn mượn lâu hơn cần làm thủ tục trước.',
 'h3-reading-28':'Trước đây cô ấy ngại nói, nay chủ động hỏi đường và giới thiệu đất nước: sự tự tin tăng lên.',
 'h3-reading-29':'Anh ấy biết bạn hay quên ô nên mang thêm một chiếc để cho bạn mượn.',
 'h3-reading-30':'Đoạn văn khuyên học đều mỗi ngày và vận dụng kiến thức, thay vì chỉ học gấp trước kỳ thi.',
 'h3-writing-01':'南方 nghĩa là phía nam; chữ cần điền là 方, chỉ phương hướng.',
 'h3-writing-02':'应该 nghĩa là nên, biểu thị lời khuyên hoặc việc cần làm; chữ còn thiếu là 该.',
 'h3-writing-03':'成绩 là kết quả học tập hoặc điểm thi; chữ cần điền là 绩.',
 'h3-writing-04':'办法 là cách hoặc phương pháp giải quyết vấn đề; điền chữ 法.',
 'h3-writing-05':'打开 nghĩa là mở ra; trong 打开窗户, chữ cần điền là 打.',
}

def build_hsk1():
    p=paper(1,[('listening','Nghe hiểu',12*60+3*60),('reading','Đọc hiểu',20*60)])
    # Part 1: listen and judge a picture, 5 items.
    for audio,image,correct,why in [
        ('这是水。','水',True,'Bản nghe nói 这是水: đây là nước, khớp hình.'),
        ('她是我的朋友。','朋友',True,'朋友 nghĩa là bạn; hình minh họa những người bạn.'),
        ('这是一本书。','茶',False,'Bản nghe nói 书 (sách), nhưng hình là trà.'),
        ('这是一匹马。','马',True,'马 là ngựa, khớp với hình.'),
        ('他在喝茶。','书',False,'喝茶 là uống trà; hình minh họa sách, không khớp.')]:
        add(p,'listening',1,'Nghe và chọn hình có đúng với nội dung không。',['Đúng','Sai'],0 if correct else 1,audio=audio,image=image,explanation=why)
    # Part 2/3 use picture choices; each item is independently answerable.
    for part,rows in [(2,[
        ('我想喝水。',['水','茶','书'],'Người nói muốn uống 水 (nước).'),
        ('请给我一本书。',['书','水','马'],'一本书 là một quyển sách.'),
        ('我喜欢喝茶。',['茶','水','书'],'喝茶 nghĩa là uống trà.'),
        ('这座山很高。',['山','书','马'],'山 là núi; câu nói ngọn núi rất cao.'),
        ('我们是好朋友。',['朋友','山','茶'],'好朋友 nghĩa là những người bạn tốt.')]),(3,[
        ('女：你喝什么？男：我喝茶。',['茶','水','书'],'Người nam trả lời 我喝茶: tôi uống trà.'),
        ('男：你买什么？女：我买书。',['书','茶','马'],'Người nữ mua sách: 买书.'),
        ('女：你想喝茶吗？男：不，我喝水。',['水','茶','书'],'Người nam từ chối trà và chọn nước.'),
        ('男：你们去哪里？女：我们去看山。',['山','马','茶'],'去看山 nghĩa là đi ngắm núi.'),
        ('女：她是谁？男：她是我的朋友。',['朋友','书','水'],'Người nam giới thiệu 她是我的朋友.')])]:
        for audio,opts,why in rows:add(p,'listening',part,'Nghe và chọn hình phù hợp。',images(opts),0,audio=audio,explanation=why)
    choices(p,'listening',4,[
        ('他几岁？',['八岁','十八岁','三岁'],'八岁 nghĩa là tám tuổi.',{'audio':'女：你弟弟几岁？男：他八岁。'}),
        ('他们什么时候见？',['星期六','星期一','星期三'],'Hai người hẹn 星期六, thứ Bảy.',{'audio':'男：我们星期六见，好吗？女：好，星期六见。'}),
        ('妈妈在哪儿？',['家里','学校','医院'],'妈妈在家: mẹ đang ở nhà.',{'audio':'女：你妈妈在学校吗？男：不，她在家。'}),
        ('他想吃什么？',['米饭','面条','苹果'],'Người nam chọn 米饭, cơm.',{'audio':'女：你想吃面条吗？男：我想吃米饭。'}),
        ('这本书多少钱？',['十五块','五块','五十块'],'十五块 là mười lăm đồng.',{'audio':'男：这本书多少钱？女：十五块。'})])
    for image,statement,correct,why in [
        ('书','这是一本书。',True,'书 là sách; 一本 dùng để đếm sách.'),
        ('茶','这是水。',False,'Hình là trà 茶, không phải nước 水.'),
        ('马','这是一匹马。',True,'马 là ngựa; 匹 là lượng từ của ngựa.'),
        ('朋友','他们是朋友。',True,'他们是朋友: họ là bạn bè.'),
        ('山','这是学校。',False,'Hình là núi 山; 学校 nghĩa là trường học.')]:
        add(p,'reading',1,statement,['Đúng','Sai'],0 if correct else 1,image=image,explanation=why)
    choices(p,'reading',2,[
        ('你叫什么名字？',['我叫安。','我很好。','我十岁。'],'Hỏi tên bằng 叫什么名字, trả lời 我叫…'),
        ('谢谢你！',['不客气！','对不起。','再见。'],'Đáp lại lời cảm ơn bằng 不客气.'),
        ('你是哪国人？',['我是越南人。','我是老师。','我在学校。'],'哪国人 hỏi quốc tịch; 越南人 là người Việt Nam.'),
        ('现在几点？',['九点。','九岁。','九块。'],'几点 hỏi giờ; 九点 là chín giờ.'),
        ('你家有几口人？',['四口人。','四本书。','四点。'],'几口人 hỏi số thành viên gia đình.')])
    choices(p,'reading',3,[
        ('我（　）越南人。',['是','在','有'],'是 nối chủ ngữ với danh từ chỉ quốc tịch.'),
        ('桌子上（　）一本书。',['有','是','叫'],'有 diễn tả sự tồn tại: trên bàn có một quyển sách.'),
        ('我每天（　）七点起床。',['早上','昨天','明年'],'每天早上七点: mỗi sáng lúc bảy giờ.'),
        ('她是我（　）老师。',['的','吗','呢'],'的 nối 我 với 老师 để chỉ quan hệ: giáo viên của tôi.'),
        ('你喜欢喝茶（　）？',['吗','的','是'],'吗 đặt cuối câu để hỏi có/không.')])
    choices(p,'reading',4,[
        ('她做什么工作？',['老师','学生','医生'],'老师 là giáo viên; đây là nghề của chị.',{'reading':'我姐姐是老师。她在学校工作。'}),
        ('他想买什么？',['苹果','书','茶'],'Câu cuối nói 想买三个苹果: muốn mua ba quả táo.',{'reading':'他去商店，想买三个苹果。'}),
        ('他们几点吃饭？',['十二点','十点','两点'],'十二点吃午饭: ăn trưa lúc mười hai giờ.',{'reading':'我们上午学习，十二点吃午饭。'}),
        ('他今天去哪儿？',['医院','学校','商店'],'他去医院看妈妈: anh ấy đến bệnh viện thăm mẹ.',{'reading':'妈妈生病了，他今天去医院看妈妈。'}),
        ('明天天气怎么样？',['下雨','很热','下雪'],'明天会下雨: ngày mai sẽ mưa.',{'reading':'今天不下雨，明天会下雨。'})])

def build_hsk2():
    p=paper(2,[('listening','Nghe hiểu',17*60+3*60),('reading','Đọc hiểu',25*60),('writing','Viết',10*60)])
    for part,rows in [(1,[
        ('请把这本书放在桌子上。',['书','茶','水'],'Bản nghe nhắc đến quyển sách 这本书.'),
        ('运动以后，我想喝一杯水。',['水','茶','书'],'Sau khi vận động, người nói muốn uống nước.'),
        ('周末我常常跟朋友见面。',['朋友','山','马'],'跟朋友见面 nghĩa là gặp bạn bè.'),
        ('我们明天去爬山吧。',['山','马','书'],'爬山 là leo núi.'),
        ('爸爸每天早上喝茶。',['茶','水','书'],'Người bố uống trà 每天早上.')]),(2,[
        ('女：你要喝水吗？男：不用了，我有茶。',['茶','水','马'],'Người nam đã có trà: 我有茶.'),
        ('男：你在找什么？女：我在找昨天买的书。',['书','茶','山'],'Người nữ đang tìm quyển sách mua hôm qua.'),
        ('女：你们是什么关系？男：我们是朋友。',['朋友','书','水'],'Hai người có quan hệ bạn bè.'),
        ('男：周末去哪儿？女：去爬那座山。',['山','茶','书'],'那座山 chỉ ngọn núi mà họ sẽ leo.'),
        ('女：这是你的水吗？男：是的，谢谢。',['水','茶','书'],'Người nam xác nhận đó là nước của mình.'),
        ('男：这里的茶怎么样？女：非常好喝。',['茶','山','水'],'Cuộc hội thoại đánh giá trà rất ngon.'),
        ('女：你喜欢看书吗？男：喜欢，我每天都看。',['书','马','茶'],'每天都看书: đọc sách mỗi ngày.'),
        ('男：这是你家的马吗？女：不是，是爷爷的。',['马','山','书'],'Câu trả lời nói con ngựa thuộc về ông.'),
        ('女：谁来你家？男：我的两个朋友。',['朋友','水','茶'],'Hai người bạn sẽ đến nhà.'),
        ('男：这座山高不高？女：很高，也很漂亮。',['山','书','水'],'Hai người đang nói về ngọn núi vừa cao vừa đẹp.')])]:
        for audio,opts,why in rows:add(p,'listening',part,'Nghe và chọn hình phù hợp。',images(opts),0,audio=audio,explanation=why)
    choices(p,'listening',3,[
        ('他为什么不去打球？',['身体不舒服','没有球','要去上课'],'他不舒服，所以不去打球.',{'audio':'女：下午一起打球吧。男：我今天身体不舒服，想休息。'}),
        ('他们在哪儿见面？',['电影院门口','学校里面','饭店门口'],'电影院门口 là trước cửa rạp phim.',{'audio':'男：我们在哪儿见？女：电影院门口，别迟到。'}),
        ('女的买了几件衣服？',['两件','三件','一件'],'两件衬衫，共两件衣服.',{'audio':'男：你买衣服了吗？女：买了两件衬衫，没买裤子。'}),
        ('男的几点出门？',['七点半','八点半','七点'],'七点半 đi ra khỏi nhà.',{'audio':'女：你每天几点出门？男：七点半，八点到公司。'}),
        ('这杯咖啡怎么样？',['太甜了','不热','很便宜'],'太甜了 nghĩa là quá ngọt.',{'audio':'男：咖啡好喝吗？女：糖太多了，太甜了。'}),
        ('她什么时候回来？',['下星期','明天','下个月'],'她下星期回来: cô ấy về vào tuần sau.',{'audio':'男：小王回来了吗？女：没有，她下星期回来。'}),
        ('他要去哪里？',['北京','上海','西安'],'Mua vé đi 北京, Bắc Kinh.',{'audio':'女：您要买去哪里的票？男：一张明天去北京的票。'}),
        ('谁比较高？',['哥哥','弟弟','一样高'],'哥哥比弟弟高: anh trai cao hơn em trai.',{'audio':'女：你哥哥和弟弟谁高？男：哥哥比弟弟高一点。'}),
        ('她为什么迟到？',['起床晚了','车坏了','下雨了'],'起床晚了 là dậy muộn.',{'audio':'男：你怎么迟到了？女：对不起，我今天起床晚了。'}),
        ('男的想吃什么？',['面条','米饭','饺子'],'他选择面条，不是饺子.',{'audio':'女：今天吃饺子，行吗？男：昨天吃过了，今天吃面条吧。'})])
    choices(p,'reading',1,[
        ('选择合适的图片：我喜欢喝茶。',images(['茶','水','书']),'喝茶指喝茶水。'),
        ('选择合适的图片：他们是好朋友。',images(['朋友','山','马']),'朋友表示友好的关系。'),
        ('选择合适的图片：这是我刚买的书。',images(['书','水','茶']),'刚买的书 là sách vừa mua.'),
        ('选择合适的图片：周末我们去爬山。',images(['山','马','朋友']),'爬山 là leo núi.'),
        ('选择合适的图片：请给我一杯水。',images(['水','茶','书']),'一杯水 nghĩa là một cốc nước.')])
    choices(p,'reading',2,[
        ('你为什么学汉语？',['因为我想去中国。','我学了两年。','我在家学习。'],'为什么 hỏi nguyên nhân; 因为 mở đầu nguyên nhân.'),
        ('这件衣服有大一点儿的吗？',['有，请试试这件。','在桌子上。','是昨天。'],'Người mua hỏi cỡ lớn hơn, người bán mời thử áo khác.'),
        ('请问，去机场怎么走？',['先坐地铁，再坐公共汽车。','九点到了。','我去过。'],'怎么走 hỏi đường đi, trả lời bằng phương tiện và thứ tự.'),
        ('你的生日是什么时候？',['十月二日。','下午三点。','我二十岁。'],'生日 hỏi ngày sinh; 十月二日 là ngày 2 tháng 10.'),
        ('你觉得这个电影怎么样？',['我觉得很有意思。','我在电影院。','我想去。'],'怎么样 hỏi đánh giá; 很有意思 nghĩa là thú vị.')])
    choices(p,'reading',3,[
        ('今天（　）昨天冷。',['比','给','从'],'比 dùng để so sánh hai đối tượng.'),
        ('他（　）吃完饭，就去上班。',['一','很','最'],'一…就… diễn tả vừa làm xong việc này liền làm việc khác.'),
        ('这件事我已经（　）了。',['知道','高兴','漂亮'],'已经知道了: đã biết rồi.'),
        ('请你（　）我一下。',['等','热','远'],'等我一下 nghĩa là đợi tôi một chút.'),
        ('他跑得（　）快。',['很','个','本'],'Sau 得 dùng bổ ngữ mức độ, 很快 là rất nhanh.'),
        ('我想买两（　）电影票。',['张','本','口'],'张 là lượng từ của vé.'),
        ('我们（　）坐地铁去吧。',['一起','已经','正在'],'一起 nghĩa là cùng nhau.'),
        ('外面下雨了，别忘了（　）伞。',['带','喝','问'],'带伞 nghĩa là mang ô.'),
        ('我在中国住（　）两年。',['过','得','着'],'过 biểu thị trải nghiệm đã từng sống ở Trung Quốc.'),
        ('他不但会说汉语，（　）会写汉字。',['而且','所以','但是'],'不但…而且… nghĩa là không những…mà còn….')])
    choices(p,'reading',4,[
        ('他打算什么时候去看奶奶？',['星期日','星期六','星期一'],'星期六有课，星期日才去看奶奶.',{'reading':'星期六我有课，星期日我打算去看奶奶。'}),
        ('她为什么买这双鞋？',['比较便宜','颜色不好看','太小'],'她买的原因是价格比较便宜.',{'reading':'这双鞋颜色很好看，也比较便宜，我买了一双。'}),
        ('他今天怎么上班？',['坐公共汽车','骑自行车','坐地铁'],'自行车坏了，所以改坐公共汽车.',{'reading':'我的自行车坏了，今天坐公共汽车上班。'}),
        ('哪句话是对的？',['姐姐会游泳','姐姐不会游泳','弟弟每天游泳'],'姐姐会游泳，弟弟不会.',{'reading':'姐姐游泳游得很好，弟弟还不会，姐姐每个周末教他。'}),
        ('他的手机在哪里？',['家里','公司','出租车上'],'忘在家里了 nghĩa là đã để quên ở nhà.',{'reading':'我到公司以后才发现，手机忘在家里了。'})])
    for word,component,others,why in [('河','氵',['亻','口'],'河 mang bộ 氵, thường liên quan đến nước.'),('妈','女',['木','日'],'妈 có bộ 女, bên phải là 马.'),('你','亻',['扌','心'],'你 có bộ 亻 ở bên trái.'),('喝','口',['月','土'],'喝 có bộ 口, liên quan đến hoạt động của miệng.'),('休','木',['火','水'],'休 gồm 亻 và 木; ở đây chọn thành phần 木.')]:
        add(p,'writing',1,f'选择“{word}”里的部件。',[component,*others],0,explanation=why)
    for sentence,answer,hint,why in [('这本书是我（　）。','的','de','的 dùng để chỉ sở hữu: quyển sách này là của tôi.'),('我（　）以坐这里吗？','可','kě','可以 biểu thị sự cho phép.'),('今天的天气很（　）。','好','hǎo','天气很好: thời tiết rất tốt.'),('我们每天（　）习汉语。','学','xué','学习 là học tập; chữ còn thiếu là 学.'),('吃饭以前要（　）手。','洗','xǐ','洗手 là rửa tay.')]:
        add(p,'writing',2,sentence,answer=answer,hint=hint,explanation=why,kind='fill')

def build_hsk3():
    p=paper(3,[('listening','Nghe hiểu',23*60+5*60),('reading','Đọc hiểu',30*60),('writing','Viết',20*60)])
    for audio,opts,why in [
        ('男：会议马上开始了，资料打印好了吗？女：刚打好，我现在拿过去。',['office-documents','reading-library','moving-home'],'会议、资料、打印 cho biết hai người đang chuẩn bị tài liệu họp.'),
        ('女：箱子太重了，你帮我搬进新家吧。男：没问题，我来帮你。',['moving-home','panda-zoo','tennis'],'箱子 và 搬进新家 miêu tả hoạt động chuyển nhà.'),
        ('男：车站到了，准备上车吧。女：好的，坐高铁两个小时就能到了。',['high-speed-train','wedding-clothes','office-documents'],'坐高铁 nghĩa là đi tàu cao tốc.'),
        ('女：那边的鸟真漂亮，你快拍下来。男：好，我把相机拿出来。',['photography','recovery','spring-festival'],'拍下来 và 相机 cho biết họ đang chụp ảnh.'),
        ('男：你准备穿哪件衣服去参加婚礼？女：我想试试这条裙子。',['wedding-clothes','moving-home','panda-zoo'],'参加婚礼、裙子 cho biết người nữ đang chọn trang phục dự cưới.'),
        ('女：医生，我的身体比昨天好多了。男：再休息几天，按时吃药。',['recovery','photography','tennis'],'医生、吃药 cho thấy bối cảnh khám và điều trị bệnh.'),
        ('男：比赛几点开始？女：九点，我们先去网球场练习一下吧。',['tennis','spring-festival','reading-library'],'网球场 là sân quần vợt, phù hợp cảnh thi đấu.'),
        ('女：这本书可以借多久？男：两个星期，请按时还到图书馆。',['reading-library','high-speed-train','recovery'],'借、还、图书馆 nói về mượn và trả sách ở thư viện.'),
        ('男：春节快到了，大家都回来了吗？女：回来了，正在一起包饺子。',['spring-festival','office-documents','photography'],'春节 và 一起包饺子 gợi cảnh gia đình đón Tết.'),
        ('女：熊猫在吃什么？男：竹子，它们一天要吃很多。',['panda-zoo','tennis','moving-home'],'熊猫、竹子 nói về quan sát gấu trúc ăn tre.')]:
        add(p,'listening',1,'听对话，选择合适的图片。',scenes(opts),0,audio=audio,explanation=why)
    choices(p,'listening',2,[
        ('她为什么换工作？',['离家太远','工资太高','同事太多'],'她换工作的原因是公司离家太远.',{'audio':'男：你为什么要换工作？女：现在的公司离家太远，每天在路上要花三个小时。'}),
        ('他们准备怎么去？',['坐高铁','坐飞机','开车'],'高铁虽然时间长一点，但比较便宜.',{'audio':'女：飞机票有点儿贵。男：那我们坐高铁吧，只多花一个小时。女：好。'}),
        ('会议几点开始？',['九点半','九点','十点'],'会议推迟到九点半.',{'audio':'男：会议还是九点开始吗？女：改到九点半了，经理刚通知我。'}),
        ('她想买什么颜色的裙子？',['蓝色','红色','黑色'],'她选择蓝色裙子去参加婚礼.',{'audio':'女：红色的太贵，黑色的又不适合婚礼，我还是买这条蓝色的吧。男：蓝色也很好看。'}),
        ('男的把什么忘在办公室了？',['护照','手机','钱包'],'护照落在办公室，并非钱包.',{'audio':'女：你的钱包带了吗？男：带了，可是护照还在办公室，我得回去拿。'}),
        ('这本书是谁借的？',['小李','小王','老师'],'小李借给小王，持有者不是最初借书的人.',{'audio':'女：这是小王从图书馆借的书吗？男：不是，是小李借的，后来给了小王。'}),
        ('她什么时候开始学游泳？',['上个月','去年','昨天'],'上个月才开始学习游泳.',{'audio':'男：你游得真好，学了几年了？女：没有那么久，我上个月才开始学。'}),
        ('男的现在最想做什么？',['休息一下','继续跑步','去吃饭'],'他累得不想动，想先休息.',{'audio':'女：我们跑了这么久，一起去吃饭吧。男：我累得不想动了，先让我休息一会儿。'}),
        ('他们要先做什么？',['检查打印机','打印资料','离开公司'],'先修好打印机，再打印资料.',{'audio':'男：资料还没打印好？女：打印机坏了，得先检查一下。男：我来看看。'}),
        ('她为什么没拍照？',['手机没电了','不喜欢风景','忘带相机'],'手机没电导致无法拍照.',{'audio':'男：风景这么美，你怎么不拍照？女：我想拍，可是手机没电了。'})])
    choices(p,'listening',3,[
        ('关于小林，可以知道什么？',['他提前到了','他迟到了','他忘记了会议'],'提前半小时到达，说明他提前到了.',{'audio':'小林担心堵车，所以今天很早就出门了。会议九点开始，他八点半已经到了。'}),
        ('这家饭馆为什么受欢迎？',['又便宜又好吃','只卖外国菜','离学校很远'],'饭馆受欢迎的两个原因是价格低、味道好.',{'audio':'学校门口的这家饭馆不大，但是菜又便宜又好吃，学生们常常到这里吃饭。'}),
        ('她现在的身体怎么样？',['比以前好多了','越来越差','还不能走路'],'已经能散步，身体比以前好.',{'audio':'上个月她生病住院了。现在她已经出院，每天还能去公园散步，身体比以前好多了。'}),
        ('周末的天气会怎样？',['可能下雨','一直晴天','非常热'],'周末可能下雨，要带伞.',{'audio':'今天阳光很好，但是天气预报说周末可能下雨。打算出门的人最好带上雨伞。'}),
        ('小张怎么提高汉语水平？',['坚持每天练习','只在考试前复习','不和别人交流'],'坚持每日阅读和交流让他进步.',{'audio':'小张每天都读一段中文，也常常用汉语和朋友聊天。坚持了一年，他的汉语水平提高了很多。'}),
        ('他为什么选择这套房子？',['附近很方便','房租最低','房间最多'],'附近交通购物方便，是选房原因.',{'audio':'这套房子的房租不是最便宜的，房间也不大。不过，楼下就是地铁站，旁边还有超市，所以他决定租下来。'}),
        ('关于熊猫，可以知道什么？',['主要吃竹子','只吃水果','每年换颜色'],'熊猫主要吃竹子，竹子提供其日常食物.',{'audio':'熊猫很可爱，很多人喜欢看它们吃东西。它们主要吃竹子，有时也会吃一点儿水果。'}),
        ('他今年有什么计划？',['毕业后找工作','去医院上班','买一辆汽车'],'他今年毕业，并准备先找工作.',{'audio':'今年六月我就要毕业了。我不打算马上继续读书，想先找一份工作，多了解社会。'}),
        ('春节前他们在做什么？',['准备过年','搬到国外','准备考试'],'包饺子、打扫房间都是过年前的准备.',{'audio':'春节快到了。爸爸在打扫房间，妈妈和奶奶一起包饺子，孩子们正在帮忙。大家都很高兴。'}),
        ('她觉得这次比赛怎么样？',['学到了很多','完全没有意思','太容易了'],'虽然没赢，但她认为学到了很多.',{'audio':'这次比赛我们没有赢。但是我认识了很多打得很好的同学，也发现了自己的问题。我觉得学到了很多。'})])
    choices(p,'reading',1,[
        ('你知道图书馆几点关门吗？',['晚上九点，周末也一样。','在三楼左边。','我昨天去了。'],'问题问关门时间，回答晚上九点.'),
        ('这件衬衫有点儿小。',['那试试大一号的吧。','我坐地铁来。','今天星期六。'],'衣服太小，可以换大一号试穿.'),
        ('你把文件发给经理了吗？',['已经发了，他说收到了。','我觉得很好吃。','我们住在楼上。'],'已经发了回应文件是否发送.'),
        ('最近工作忙不忙？',['比较忙，天天加班。','八点到九点。','这是他的书。'],'忙不忙问工作状态.'),
        ('你的感冒好些了吗？',['好多了，谢谢关心。','天气非常好。','没关系，下次再来。'],'好些了吗在此询问病情是否改善.'),
        ('我们坐飞机还是坐高铁？',['坐高铁吧，车站离家近。','他已经到了。','这本书是我的。'],'还是引出选择，两种交通工具中选高铁.'),
        ('你为什么喜欢这座城市？',['因为这里环境好，人也热情。','我明天去。','这里有两个人。'],'为什么问原因，使用因为回答.'),
        ('这张照片是在哪儿拍的？',['去年在草原上拍的。','我觉得很漂亮。','照片有三张。'],'在哪儿拍的询问拍摄地点.'),
        ('你能帮我搬一下箱子吗？',['当然可以，我来帮你。','他住得很远。','我已经吃饱了。'],'当然可以表达同意提供帮助.'),
        ('明天的比赛你参加吗？',['参加，我已经报名了。','这双鞋很好看。','早上天气晴朗。'],'已经报名说明会参加比赛.')])
    choices(p,'reading',2,[
        ('我刚到北京，对这里还不太（　）。',['了解','结婚','打印'],'了解指理解、熟悉这里的情况.'),
        ('他把房间打扫得很（　）。',['干净','突然','按时'],'打扫得干净描述清洁后的结果.'),
        ('这道题太难，我还没找到解决的（　）。',['办法','照片','季节'],'解决问题的办法就是方法.'),
        ('请（　）护照放在包里。',['把','被','比'],'把+宾语+动词短语，说明如何处理护照.'),
        ('除了汉语，他（　）会说英语。',['还','才','别'],'除了…还…表示追加一种能力.'),
        ('外面风很大，你（　）穿件外套。',['应该','突然','终于'],'应该表达建议和必要性.'),
        ('这本书我看了三遍，（　）觉得很有意思。',['还是','或者','于是'],'还是在这里表示仍然.'),
        ('你想吃（　）就点什么。',['什么','多少','哪儿'],'什么…就…什么表示选择自由一致.'),
        ('雨越下越大，我们只好（　）计划。',['改变','毕业','结婚'],'改变计划指调整原本安排.'),
        ('他努力学习，（　）通过了考试。',['终于','已经','正在'],'终于强调经过努力后实现结果.')])
    choices(p,'reading',3,[
        ('为什么他们没有坐飞机？',['高铁更便宜','机场关门了','飞机飞得太慢'],'文中明确比较价格并选择高铁.',{'reading':'去上海坐飞机要八百元，坐高铁只要四百元。我们时间比较多，所以买了高铁票。'}),
        ('小王为什么买新的打印机？',['旧的经常出问题','旧的颜色不好','新的不用电'],'旧打印机经常出问题，影响打印.',{'reading':'办公室的打印机最近经常出问题，资料总是不能按时打印。小王决定换一台新的。'}),
        ('小李对这次旅行感觉怎样？',['虽然累但很满意','完全不满意','后悔参加'],'虽然…但是…表达转折，最终评价满意.',{'reading':'这次草原旅行每天都要走很远的路，大家都很累。但是景色比我们想象的还美，小李说下次还想来。'}),
        ('她找工作的主要要求是什么？',['能学到东西','工资一定最高','不用和别人交流'],'她最看重学习机会，并不只看工资.',{'reading':'找工作时，她不只看工资，更想找一份能学到东西、能和不同的人交流的工作。'}),
        ('关于张老师，可以知道什么？',['他重视学生提问','他不许学生说话','他只讲课本'],'张老师鼓励提问并讨论，所以重视学生思考.',{'reading':'张老师常常请学生说说自己的想法。遇到不明白的地方，他鼓励大家提问，然后一起讨论。'}),
        ('春节前，孩子们为什么高兴？',['可以和家人团聚','不用吃饭','都要搬家'],'春节带来团聚的机会.',{'reading':'爷爷奶奶住得远，平时很少见面。春节他们要来一起过年，孩子们一听就高兴得跳了起来。'}),
        ('借书的人需要做什么？',['按时还书','每天买一本书','只能借一天'],'两周以内还书即按时归还.',{'reading':'图书馆的书每次可以借两本，两个星期以内要还。如果需要多借几天，请提前办理手续。'}),
        ('哪句话符合短文？',['她比以前自信','她不再学汉语','她从来不练习'],'过去害怕，现在能主动交流，说明自信增加.',{'reading':'以前她不敢开口说汉语。练习了半年后，现在她能主动向别人问路，也愿意介绍自己的国家。'}),
        ('他为什么带两把伞？',['一把借给朋友','因为伞坏了','因为今天很热'],'他知道朋友没带伞，因此多带一把.',{'reading':'天气预报说下午下雨。他知道朋友常常忘记带伞，就在包里放了两把，准备借一把给朋友。'}),
        ('这段话主要想告诉我们什么？',['坚持比着急更重要','学习不需要计划','一天必须学很多'],'分散、持续练习的效果比临时突击更稳定.',{'reading':'学语言不能只在考试前着急。每天学一点儿，再把学过的内容用起来，时间长了就会发现自己的进步。'})])
    for sentence,answer,hint,why in [('地图上可以找到南（　）。','方','fāng','南方指方位南部；方是方向的方。'),('你应（　）早点儿休息。','该','gāi','应该表示建议或必要。'),('这次考试的成（　）提高了。','绩','jì','成绩表示考试结果。'),('这个办（　）很有用。','法','fǎ','办法表示解决问题的方法。'),('请把窗户（　）开。','打','dǎ','打开表示使关闭的东西开启。')]:
        add(p,'writing',1,sentence,answer=answer,hint=hint,explanation=why,kind='fill')
    for word,reference,topic,why in [('搬','他们一起把箱子搬进新家。','moving-home','Câu cần dùng 搬 để tả hành động chuyển đồ, có chủ ngữ và ngữ cảnh rõ.'),('比赛','他们正在参加网球比赛。','tennis','比赛 là cuộc thi hoặc thi đấu; nêu đúng hoạt động trong tranh.'),('借','她从图书馆借了一本书。','reading-library','借 chỉ mượn; có thể dùng 从…借… để diễn tả mượn sách ở thư viện.'),('饺子','一家人正在一起包饺子。','spring-festival','饺子 là sủi cảo; 包饺子 là gói sủi cảo.'),('点菜','他们正在饭馆看菜单、点菜。','restaurant-menu','点菜 là gọi món; chú ý câu phải có hành động và bối cảnh phù hợp.')]:
        add(p,'writing',2,f'看图，用“{word}”写一个句子。',answer=reference,illustration=topic,explanation=why,kind='sentence')

def main():
    build_hsk1();build_hsk2();build_hsk3();ROOT.mkdir(parents=True,exist_ok=True)
    counts={1:[20,20],2:[25,25,10],3:[30,30,10]}
    for level,p in PAPERS.items():
        assert [len(s['questions']) for s in p['sections']]==counts[level]
        p['total_questions']=sum(counts[level]);p['max_score']=100*len(p['sections']);p['pass_score']=p['max_score']*.6
        assert len({q['id'] for s in p['sections'] for q in s['questions']})==p['total_questions']
        for s in p['sections']:
            for q in s['questions']:
                if q['id'] in EXPLANATIONS_VI:q['explanation']=EXPLANATIONS_VI[q['id']]
                assert q['explanation'] and q['reference_answer']
                if level==3:assert not any('pinyin' in key for key in q)
        path=ROOT/f'hsk-{level}.json';path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'HSK{level}: {p["total_questions"]} original items; sha256={hashlib.sha256(path.read_bytes()).hexdigest()}')

if __name__=='__main__':main()
