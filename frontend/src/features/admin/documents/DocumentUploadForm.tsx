import { useState } from 'react'
import type { FormEvent } from 'react'
import type { DocumentUploadInput } from '../api'
import { Alert, Button } from '../../../components/ui'

export function DocumentUploadForm({
  onSubmit,
  pending,
  error,
}: {
  onSubmit: (input: DocumentUploadInput) => void
  pending: boolean
  error: string | null
}) {
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [sourceCategory, setSourceCategory] = useState<DocumentUploadInput['source_category']>('CURRICULUM_MATERIAL')
  const [sourceOrigin, setSourceOrigin] = useState('')
  const [sourceLanguage, setSourceLanguage] = useState<DocumentUploadInput['source_language']>('zh')
  const [usageRightsNote, setUsageRightsNote] = useState('')
  const [domainAllowed, setDomainAllowed] = useState(false)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file) return
    onSubmit({
      file,
      title: title.trim(),
      source_category: sourceCategory,
      source_origin: sourceOrigin.trim(),
      source_language: sourceLanguage,
      usage_rights_note: usageRightsNote.trim() || null,
      domain_allowed: domainAllowed,
    })
  }

  return (
    <form className="admin-documents-upload-form" onSubmit={submit} aria-labelledby="document-upload-heading">
      <h2 id="document-upload-heading" className="admin-documents-upload-title">Tải tài liệu nguồn lên</h2>
      <div className="admin-documents-upload-fields">
        <label className="admin-documents-file-field">Tệp (PDF, DOCX, TXT hoặc MD)
          <span className="admin-file-control"><span>Chọn tệp</span><span>{file?.name ?? 'Chưa chọn tệp'}</span><input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            required
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          /></span>
        </label>
        <label className="admin-documents-title-field">Tiêu đề<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
        <div className="admin-documents-source-fields">
          <label>Loại nguồn
            <select value={sourceCategory} onChange={(event) => setSourceCategory(event.target.value as DocumentUploadInput['source_category'])}>
              <option value="CURRICULUM_MATERIAL">Giáo trình</option>
              <option value="INTERNAL_AUTHORED">Tài liệu nội bộ</option>
            </select>
          </label>
          <label>Xuất xứ<input required value={sourceOrigin} onChange={(event) => setSourceOrigin(event.target.value)} /></label>
          <label>Ngôn ngữ nguồn
            <select value={sourceLanguage} onChange={(event) => setSourceLanguage(event.target.value as DocumentUploadInput['source_language'])}>
              <option value="vi">Tiếng Việt</option><option value="zh">Tiếng Trung</option><option value="en">Tiếng Anh</option>
            </select>
          </label>
        </div>
        <label className="admin-documents-rights-field">Ghi chú quyền sử dụng (không bắt buộc)
          <textarea value={usageRightsNote} onChange={(event) => setUsageRightsNote(event.target.value)} />
        </label>
      </div>
      <div className="admin-documents-upload-footer">
        <label className="admin-documents-attestation">
          <input type="checkbox" required checked={domainAllowed} onChange={(event) => setDomainAllowed(event.target.checked)} />
          Tôi xác nhận tài liệu đủ điều kiện sử dụng cho việc học tiếng Trung.
        </label>
        {error && <Alert role="alert" tone="error">{error}</Alert>}
        <Button variant="primary" type="submit" disabled={pending || !file || !title.trim() || !sourceOrigin.trim() || !domainAllowed}>
          {pending ? "Đang tải lên…" : "Tải tài liệu lên"}
        </Button>
      </div>
    </form>
  )
}
