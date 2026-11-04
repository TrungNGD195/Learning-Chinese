export type ReadingPreferences={size:number;pinyin:boolean}
const key='chinese-learning.reading.v1'
const defaults:ReadingPreferences={size:19,pinyin:true}
function project(value:unknown):ReadingPreferences{
  if(!value||typeof value!=='object')return {...defaults}
  const record=value as Record<string,unknown>
  return {size:typeof record.size==='number'&&[19,21,23].includes(record.size)?record.size:19,pinyin:typeof record.pinyin==='boolean'?record.pinyin:true}
}
export function readReadingPreferences():ReadingPreferences{
  try{return project(JSON.parse(window.localStorage.getItem(key)??'null'))}catch{return {...defaults}}
}
export function saveReadingPreferences(value:ReadingPreferences){
  try{window.localStorage.setItem(key,JSON.stringify(project(value)))}catch{/* The selected reading style still works in this tab. */}
}
