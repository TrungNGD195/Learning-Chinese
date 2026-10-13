import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { generateContract } from './openapi-contract.mjs'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const committedPath = resolve(projectRoot, 'src/types/api.generated.ts')
const tempDirectory = await mkdtemp(resolve(tmpdir(), 'step-4-2-openapi-'))
const generatedPath = resolve(tempDirectory, 'api.generated.ts')

try {
  const generated = await generateContract()
  await writeFile(generatedPath, generated, 'utf8')
  const [expected, actual] = await Promise.all([
    readFile(committedPath, 'utf8'),
    readFile(generatedPath, 'utf8'),
  ])

  if (expected !== actual) {
    console.error('Generated API contract is out of date. Run npm run api:generate.')
    process.exitCode = 1
  } else {
    console.log('Generated API contract matches the live FastAPI OpenAPI schema.')
  }
} finally {
  await rm(tempDirectory, { recursive: true, force: true })
}
