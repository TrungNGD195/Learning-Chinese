import openapiTS from 'openapi-typescript'
import ts from 'typescript'

export const openApiUrl = 'http://localhost:8000/openapi.json'

export async function generateContract() {
  let response
  try {
    response = await fetch(openApiUrl, { headers: { Accept: 'application/json' } })
  } catch {
    throw new Error(`Could not reach the accepted FastAPI OpenAPI endpoint: ${openApiUrl}`)
  }

  if (!response.ok) {
    throw new Error(`OpenAPI request failed with HTTP ${response.status}`)
  }

  let schema
  try {
    schema = await response.json()
  } catch {
    throw new Error('FastAPI returned an invalid OpenAPI JSON document')
  }

  const statements = await openapiTS(schema)
  const printer = ts.createPrinter({ newLine: ts.NewLineKind.LineFeed })
  const sourceFile = ts.createSourceFile(
    'api.generated.ts',
    '',
    ts.ScriptTarget.Latest,
    false,
    ts.ScriptKind.TS,
  )
  return `${statements
    .map((statement) => printer.printNode(ts.EmitHint.Unspecified, statement, sourceFile))
    .join('\n')}\n`
}
