import { adminLabel } from '../labels'
import type { AdminDocumentPreview } from '../api'
import { Surface } from '../../../components/ui'

function sourceLocatorLabel(locator: AdminDocumentPreview['blocks'][number]['source_locator']) {
  if (locator.kind === 'PDF_PAGE') return `Trang ${locator.page_number}`
  if (locator.kind === 'DOCX_TABLE') return `Bảng ${locator.table_index + 1}`
  if (locator.kind === 'DOCX_PARAGRAPH') return `Khối nội dung ${locator.block_index + 1}`
  if ('block_index' in locator && typeof locator.block_index === 'number') return `Khối nội dung ${locator.block_index + 1}`
  return 'Vị trí trong tài liệu nguồn'
}

export function DocumentPreview({ preview }: { preview: AdminDocumentPreview }) {
  return (
    <Surface as="section" className="admin-document-preview" aria-labelledby="document-preview-heading">
      <h2 id="document-preview-heading">Nội dung sau xử lý</h2>
      <h3 className="admin-document-preview-title">{preview.title}</h3>
      <div className="admin-document-preview-provenance">
        <p>Nguồn: {adminLabel(preview.source_category)} · {adminLabel(preview.source_language)}</p>
        <p>Xuất xứ: {'source_origin' in preview.provenance ? preview.provenance.source_origin : "Bài học"}</p>
      </div>
      {preview.blocks.length === 0 ? <p>Chưa có nội dung xem trước.</p> : (
        <ol className="admin-document-preview-blocks admin-document-preview-list">
          {[...preview.blocks].sort((left, right) => left.order - right.order).map((block) => (
            <li className="admin-document-preview-item" key={block.order}>
              {block.section_path.length > 0 && <p className="admin-document-preview-section-path">{block.section_path.join(' / ')}</p>}
              {block.block_kind === 'HEADING' ? <h4 className="admin-document-preview-block-heading">{block.text}</h4> : <pre className="admin-document-preview-text">{block.text}</pre>}
              <small className="admin-document-preview-locator">{sourceLocatorLabel(block.source_locator)}</small>
            </li>
          ))}
        </ol>
      )}
    </Surface>
  )
}
