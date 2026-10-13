import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { generateContract } from './openapi-contract.mjs'

const outputPath = resolve(dirname(fileURLToPath(import.meta.url)), '../src/types/api.generated.ts')
const content = await generateContract()
await mkdir(dirname(outputPath), { recursive: true })
await writeFile(outputPath, content, 'utf8')
console.log(`Generated ${outputPath}`)
