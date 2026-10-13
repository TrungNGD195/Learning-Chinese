import { useState } from 'react'
import type { FormEvent } from 'react'
import type { DocumentUploadInput } from '../api'

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
    <form className="learning-card" onSubmit={submit} aria-labelledby="document-upload-heading">
      <h2 id="document-upload-heading">Upload a source document</h2>
      <label>File (PDF, DOCX, TXT, or MD)
        <input
          type="file"
          accept=".pdf,.docx,.txt,.md"
          required
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>
      <label>Title<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label>Source category
        <select value={sourceCategory} onChange={(event) => setSourceCategory(event.target.value as DocumentUploadInput['source_category'])}>
          <option value="CURRICULUM_MATERIAL">Curriculum material</option>
          <option value="INTERNAL_AUTHORED">Internally authored</option>
        </select>
      </label>
      <label>Source origin<input required value={sourceOrigin} onChange={(event) => setSourceOrigin(event.target.value)} /></label>
      <label>Source language
        <select value={sourceLanguage} onChange={(event) => setSourceLanguage(event.target.value as DocumentUploadInput['source_language'])}>
          <option value="vi">Vietnamese</option><option value="zh">Chinese</option><option value="en">English</option>
        </select>
      </label>
      <label>Usage rights note (optional)
        <textarea value={usageRightsNote} onChange={(event) => setUsageRightsNote(event.target.value)} />
      </label>
      <label>
        <input type="checkbox" required checked={domainAllowed} onChange={(event) => setDomainAllowed(event.target.checked)} />
        I confirm this source is eligible for use in the Chinese learning domain.
      </label>
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={pending || !file || !title.trim() || !sourceOrigin.trim() || !domainAllowed}>
        {pending ? 'Uploading…' : 'Upload document'}
      </button>
    </form>
  )
}
