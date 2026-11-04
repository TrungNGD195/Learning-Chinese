import { mkdir, writeFile } from 'node:fs/promises'

const destination='public/academy/fonts'
await mkdir(destination,{recursive:true})
const userAgent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
const sources=[]
let stylesheet=''
for(const [family,slug] of [['Noto Sans','noto-sans'],['Noto Sans SC','noto-sans-sc']]){
  const source=`https://fonts.googleapis.com/css2?family=${family.replaceAll(' ','+')}:wght@400..700&display=swap`
  const response=await fetch(source,{headers:{'User-Agent':userAgent}})
  if(!response.ok)throw new Error(`${family}: ${response.status}`)
  let css=await response.text()
  const urls=[...new Set([...css.matchAll(/url\((https:[^)]+)\)/g)].map(m=>m[1]))]
  const files=new Map(urls.map((url,index)=>[url,`${slug}-${index}.${url.includes('.woff2')?'woff2':'ttf'}`]))
  let next=0
  await Promise.all(Array.from({length:6},async()=>{
    while(next<urls.length){const url=urls[next++];const asset=await fetch(url);if(!asset.ok)throw new Error(`${family} asset ${asset.status}`);await writeFile(`${destination}/${files.get(url)}`,Buffer.from(await asset.arrayBuffer()))}
  }))
  for(const [url,file] of files)css=css.replaceAll(url,`/academy/fonts/${file}`)
  stylesheet+=css+'\n'
  sources.push({family,cssSource:source,files:[...files].map(([source,file])=>({source,file}))})
  const license=await fetch(`https://raw.githubusercontent.com/google/fonts/main/ofl/${slug.replaceAll('-','')}/OFL.txt`)
  if(!license.ok)throw new Error(`${family} license ${license.status}`)
  await writeFile(`${destination}/OFL-${slug}.txt`,await license.text())
  console.log(`${family}: ${files.size} local font files`)
}
await writeFile(`${destination}/fonts.css`,stylesheet)
await writeFile(`${destination}/sources.json`,JSON.stringify({created:'2026-11-03',sources},null,2))
