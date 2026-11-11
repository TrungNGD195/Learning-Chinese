export const previewStorageKey='bo.modern-academy-preview.v1'
export const levels=[{number:1,total:15,title:'Nền tảng giao tiếp',hanzi:'初',description:'Bắt đầu từ những cuộc trò chuyện gần gũi.'},{number:2,total:10,title:'Kết nối mỗi ngày',hanzi:'进',description:'Tự tin hơn trong những tình huống quen thuộc.'},{number:3,total:15,title:'Mở rộng thế giới',hanzi:'达',description:'Diễn đạt suy nghĩ và khám phá nhiều chủ đề hơn.'}]
export const lessonTitles=['Xin chào','Bạn tên là gì?','Bạn là ai?','Gia đình của tôi','Ngày tháng và thời gian','Hẹn gặp lại','Một ngày của bạn','Mua sắm','Bạn ở đâu?','Những điều tôi thích','Ăn uống cùng nhau','Đi đến trường','Cuộc sống thường ngày','Cùng nhau ôn tập','Nhìn lại chặng đường']
export type PreviewWord={hanzi:string;pinyin:string;meaning:string;pos:string;example:string;examplePinyin:string;translation:string;note?:string}
export const words:PreviewWord[]=[
 {hanzi:'你',pinyin:'nǐ',meaning:'bạn; người đang được nói chuyện cùng',pos:'Đại từ',example:'你好！',examplePinyin:'Nǐ hǎo!',translation:'Xin chào!',note:'你 dùng để nói trực tiếp với người nghe. Với người lớn tuổi hoặc trong tình huống trang trọng, có thể dùng 您.'},
 {hanzi:'是',pinyin:'shì',meaning:'là',pos:'Động từ',example:'我是老师。',examplePinyin:'Wǒ shì lǎoshī.',translation:'Tôi là giáo viên.',note:'Dùng 是 để giới thiệu danh tính hoặc nghề nghiệp. Khi miêu tả bằng tính từ như 好, thường không thêm 是.'},
 {hanzi:'老师',pinyin:'lǎoshī',meaning:'giáo viên; thầy, cô',pos:'Danh từ',example:'王老师，你好！',examplePinyin:'Wáng lǎoshī, nǐ hǎo!',translation:'Xin chào thầy/cô Vương!',note:'Khi gọi thầy cô theo họ, đặt họ trước 老师: 王老师.'},
 {hanzi:'朋友',pinyin:'péngyou',meaning:'bạn; bạn bè',pos:'Danh từ',example:'她是我的朋友。',examplePinyin:'Tā shì wǒ de péngyou.',translation:'Cô ấy là bạn của tôi.'},
 {hanzi:'的',pinyin:'de',meaning:'của; nối phần bổ nghĩa với danh từ',pos:'Trợ từ',example:'这是我的书。',examplePinyin:'Zhè shì wǒ de shū.',translation:'Đây là sách của tôi.',note:'Trong 我的朋友, 我的 bổ nghĩa cho 朋友. 的 đọc thanh nhẹ.'},
 {hanzi:'请问',pinyin:'qǐngwèn',meaning:'xin hỏi',pos:'Cụm từ',example:'请问，你是老师吗？',examplePinyin:'Qǐngwèn, nǐ shì lǎoshī ma?',translation:'Xin hỏi, bạn là giáo viên phải không?',note:'Dùng 请问 ở đầu câu hỏi để mở lời lịch sự.'},
]
export type PreviewQuestion={type:'choice'|'cloze'|'order';prompt:string;options:string[];answer:string;explanation:string}
export const questions:PreviewQuestion[]=[
 {type:'choice',prompt:'Từ nào có nghĩa là “giáo viên”?',options:['朋友','老师','请问','你'],answer:'老师',explanation:'老师 (lǎoshī) là giáo viên. 朋友 (péngyou) là bạn bè.'},
 {type:'choice',prompt:'Chọn câu đúng để nói “Tôi là giáo viên”.',options:['我老师是。','我是老师。','老师我。'],answer:'我是老师。',explanation:'Cấu trúc: chủ ngữ + 是 + danh từ. 我 + 是 + 老师 → Tôi là giáo viên.'},
 {type:'cloze',prompt:'她是我 ___ 朋友。',options:['是','你','的','老师'],answer:'的',explanation:'我的朋友 là “bạn của tôi”. 的 nối 我 với danh từ 朋友.'},
 {type:'order',prompt:'Sắp xếp: “Cô ấy là bạn của tôi”.',options:['朋友','她','的','是','我'],answer:'她是我的朋友',explanation:'她 + 是 + 我的朋友。Chủ ngữ là 她, phần giới thiệu là 我的朋友.'},
 {type:'choice',prompt:'Bạn dùng cụm nào để bắt đầu một câu hỏi lịch sự?',options:['朋友','老师','的','请问'],answer:'请问',explanation:'请问 (qǐngwèn) nghĩa là “xin hỏi”, dùng để mở lời trước một câu hỏi.'},
]
export type PreviewState={name:string;goal:number;reduced:boolean;seen:number[];grammarDone:boolean;readingDone:boolean;completed:boolean;reviewed:number[];weakWords:number[];attempts:{score:number;total:number}[]}
export const initialPreview:PreviewState={name:'Minh An',goal:15,reduced:false,seen:[0,1],grammarDone:false,readingDone:false,completed:false,reviewed:[],weakWords:[2,4,5],attempts:[]}
export type PreviewPatch=(patch:Partial<PreviewState>|((current:PreviewState)=>Partial<PreviewState>))=>void
export function readPreview():PreviewState{
 try{
  const data=JSON.parse(localStorage.getItem(previewStorageKey)??'null') as Partial<PreviewState>|null
  if(!data||typeof data!=='object')return {...initialPreview}
  const indices=(value:unknown,fallback:number[])=>Array.isArray(value)?[...new Set(value.filter((v):v is number=>Number.isInteger(v)&&v>=0&&v<words.length))]:fallback
  return {...initialPreview,name:typeof data.name==='string'&&data.name.trim()?data.name.slice(0,40):initialPreview.name,goal:[5,10,15].includes(data.goal??0)?data.goal!:15,reduced:data.reduced===true,seen:indices(data.seen,[0,1]),reviewed:indices(data.reviewed,[]),weakWords:indices(data.weakWords,[2,4,5]),grammarDone:data.grammarDone===true,readingDone:data.readingDone===true,completed:data.completed===true,attempts:Array.isArray(data.attempts)?data.attempts.filter(a=>Number.isFinite(a.score)&&a.score>=0&&a.score<=100&&a.total===5).slice(-20):[]}
 }catch{return {...initialPreview}}
}
export function lessonState(level:number,number:number,state:PreviewState){return level===1&&number<=2?'completed':level===1&&number===3?(state.completed?'completed':'current'):'planned'}
export const previewUrl=(params:Record<string,string|number>)=>'/academy-preview.html?'+new URLSearchParams(Object.fromEntries(Object.entries(params).map(([key,value])=>[key,String(value)]))).toString()
export const theoryComplete=(state:PreviewState)=>state.seen.length===words.length&&state.grammarDone&&state.readingDone
