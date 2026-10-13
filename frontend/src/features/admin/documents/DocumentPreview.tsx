import type { AdminDocumentPreview } from '../api'

function sourceLocatorLabel(locator: AdminDocumentPreview['blocks'][number]['source_locator']) {
  if (locator.kind === 'PDF_PAGE') return `Page ${locator.page_number}`
  if (locator.kind === 'DOCX_TABLE') return `Table ${locator.table_index + 1}`
  if (locator.kind === 'DOCX_PARAGRAPH') return `Source block ${locator.block_index + 1}`
  if ('block_index' in locator && typeof locator.block_index === 'number') return `Source block ${locator.block_index + 1}`
  return locator.kind.replaceAll('_', ' ').toLowerCase()
}

export function DocumentPreview({ preview }: { preview: AdminDocumentPreview }) {
  return (
    <section className="learning-card" aria-labelledby="document-preview-heading">
      <h2 id="document-preview-heading">Transformed preview</h2>
      <h3>{preview.title}</h3>
      <p>Source: {preview.source_category ?? '—'} · {preview.source_language ?? '—'}</p>
      <p>Origin: {'source_origin' in preview.provenance ? preview.provenance.source_origin : 'Lesson'}</p>
      {preview.blocks.length === 0 ? <p>No preview blocks are available.</p> : (
        <ol className="document-preview-blocks">
          {[...preview.blocks].sort((left, right) => left.order - right.order).map((block) => (
            <li key={block.order}>
              {block.section_path.length > 0 && <p>{block.section_path.join(' / ')}</p>}
              {block.block_kind === 'HEADING' ? <h4>{block.text}</h4> : <pre>{block.text}</pre>}
              <small>{sourceLocatorLabel(block.source_locator)}</small>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
