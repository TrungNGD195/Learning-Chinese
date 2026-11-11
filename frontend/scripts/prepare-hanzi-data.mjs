// Serve licensed stroke data locally, one character per request. Keep these
// generated assets out of Git and out of the initial JavaScript bundle.
import { copyFile, mkdir, readFile, readdir, writeFile, access } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'

const root = fileURLToPath(new URL('../', import.meta.url))
const source = resolve(root, 'node_modules/hanzi-writer-data')
const target = resolve(root, 'public/hanzi-data')
const { version } = JSON.parse(await readFile(resolve(source, 'package.json'), 'utf8'))
const files = (await readdir(source)).filter(name => /^\p{Script=Han}\.json$/u.test(name))
const stamp = JSON.stringify({ version, characters: files.length, format: 1 })
try {
  if (await readFile(resolve(target, 'ready.json'), 'utf8') === stamp) {
    await access(resolve(target, '5b57.json')); await access(resolve(target, 'ARPHICPL.TXT'))
    process.exit(0)
  }
} catch { /* First preparation or an incomplete output. */ }
await mkdir(target, { recursive: true })
for (let index = 0; index < files.length; index += 48) {
  await Promise.all(files.slice(index, index + 48).map(name => copyFile(resolve(source, name), resolve(target, name.codePointAt(0).toString(16) + '.json'))))
}
await copyFile(resolve(source, 'ARPHICPL.TXT'), resolve(target, 'ARPHICPL.TXT'))
await writeFile(resolve(target, 'NOTICE.txt'), 'Make Me a Hanzi / hanzi-writer-data ' + version + '\nCopyright 1999 Arphic Technology Co., Ltd.; copyright 2016 Shaunak Kishore.\nUnmodified character data, distributed under the Arphic Public License.\nSource: https://github.com/chanind/hanzi-writer-data\nLicense: ARPHICPL.TXT\n')
await writeFile(resolve(target, 'ready.json'), stamp)
console.log(`Prepared ${files.length} locally served Hanzi stroke files (${version}).`)
