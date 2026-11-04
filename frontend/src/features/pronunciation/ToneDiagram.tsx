const descriptions=['Thanh 1: cao và ngang, 5–5','Thanh 2: đi lên, 3–5','Thanh 3 khi đọc riêng: hạ xuống rồi lên, 2–1–4','Thanh 4: đi xuống, 5–1']
const paths=['M35 20H165','M35 65 165 20','M35 85 85 107 165 43','M35 20 165 107']
export function ToneDiagram({tone}:{tone:number}){
  if(tone>3)return <p className="academy-neutral-tone">Thanh nhẹ: đọc ngắn, nhẹ và không đánh dấu thanh; độ cao phụ thuộc âm tiết trước.</p>
  return <figure className="academy-tone-diagram"><svg viewBox="0 0 190 130" role="img" aria-label={descriptions[tone]}>{[20,42,64,86,108].map((y,index)=><g key={y}><path d={'M30 '+y+'H170'} stroke="#ceddc2" strokeWidth="1" strokeDasharray="3 4"/><text x="10" y={y+4} fill="#59714d" fontSize="10">{5-index}</text></g>)}<path d={paths[tone]} stroke="#296747" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" fill="none"/><circle cx="165" cy={[20,20,43,107][tone]} r="4" fill="#a74730"/></svg><figcaption>{descriptions[tone]}</figcaption></figure>
}
