import { useEffect, useState } from 'react'
import { readReadingPreferences, saveReadingPreferences } from '../../lib/readingPreferences'
const sizes=[19,21,23]
export function ReadingSettings(){
  const [settings,setSettings]=useState(readReadingPreferences)
  useEffect(()=>{
    document.documentElement.style.setProperty('--reader-font-size',`${settings.size}px`)
    document.documentElement.dataset.showVocabularyPinyin=String(settings.pinyin)
    saveReadingPreferences(settings)
  },[settings])
  return <details className="academy-reading-settings"><summary>Aa <span>Cỡ chữ</span></summary><div><p>Chọn cỡ chữ dễ đọc với bạn</p><div role="group" aria-label="Cỡ chữ nội dung">{sizes.map((size,index)=><button type="button" key={size} aria-pressed={settings.size===size} onClick={()=>setSettings(s=>({...s,size}))}>{['Chuẩn','Lớn','Rất lớn'][index]}</button>)}</div><label><input type="checkbox" checked={settings.pinyin} onChange={e=>setSettings(s=>({...s,pinyin:e.target.checked}))}/>Hiện pinyin trong từ vựng</label></div></details>
}
