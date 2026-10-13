# Step 5.2 — Raw Data Ingestion

## Goal

Implement the raw-ingestion boundary for approved V0 knowledge-source types.

The step must support:

- raw Document ingestion;
- raw Published Lesson snapshot ingestion;
- immutable raw artifacts;
- storage abstraction;
- upload validation;
- source integrity hashing;
- duplicate detection;
- ingestion metadata persistence;
- cleanup on partial failure;
- a stable raw input boundary for Step 5.3.

Do not implement parsing, cleaning, transformation, chunking, embedding, retrieval, or pipeline orchestration in this step.

---

# Scope

Support two logical raw-ingestion paths:

```text
DOCUMENT
→ original file bytes
→ Raw Document Artifact
```

and:

```text
LESSON
→ deterministic snapshot of Published Lesson state
→ Raw Lesson Snapshot
```

Both paths belong to the same ingestion module/process boundary but may use different raw representations.

---

# Existing Source Policy

Preserve Step 5.1 decisions.

KnowledgeSource types:

```text
DOCUMENT
LESSON
```

Document source categories:

```text
CURRICULUM_MATERIAL
INTERNAL_AUTHORED
```

Supported source languages:

```text
vi
zh
en
```

Supported uploaded formats:

```text
PDF
DOCX
TXT
MD
```

Do not introduce:

```text
URL ingestion
website crawling
HTML ingestion
OCR
```

in this step.

---

# Storage Abstraction

Introduce or preserve a logical storage abstraction equivalent to:

```text
FileStorage
```

V0 implementation:

```text
LocalFileStorage
```

Do not spread direct filesystem calls across routers/services.

Storage implementation details must remain behind the storage boundary so production deployment can later replace local filesystem storage with an object-storage implementation without redesigning ingestion business logic.

Do not introduce S3/MinIO solely for this step.

---

# Document Upload Path

Use V0 flow:

```text
Admin Browser
→ FastAPI
→ validate upload
→ stream raw bytes to temporary location
→ calculate SHA-256
→ finalize immutable raw artifact
→ persist Document/raw metadata
→ return success
```

The browser must not upload directly to storage via presigned URLs in V0.

Do not implement direct-to-object-storage upload flow.

---

# Admin-only Ingestion

Raw Document upload is an Admin operation.

Do not permit ordinary Learners to ingest knowledge sources.

Authentication and authorization must remain backend-authoritative.

---

# Raw Artifact Immutability

The uploaded original bytes must be preserved unchanged after successful ingestion.

Do not:

```text
rewrite PDF
normalize text into the raw file
replace the raw file with extracted text
modify original bytes during later pipeline stages
```

Later steps must create derived representations instead of mutating the raw artifact.

---

# Storage Key

Never use the user-provided filename as the storage identity/path.

Use a server-generated storage key equivalent to:

```text
documents/<document_uuid>/raw.<extension>
```

or another UUID/server-generated structure with the same properties.

Persist the original user-facing filename separately:

```text
original_filename
```

Do not trust client-provided paths.

Prevent path traversal.

---

# File Validation

Validate uploaded Document files before finalizing ingestion.

At minimum validate:

```text
non-empty file
allowed extension/type
declared MIME type
actual file signature/type when practical
maximum file size
```

Do not trust file extension alone when a stronger lightweight check is available.

V0 development default upload size:

```text
DOCUMENT_MAX_UPLOAD_MB=20
```

The limit is configuration-driven. Raising it requires representative-file profiling and PM approval because V0 processing remains synchronous.

Reject files exceeding the configured limit using a stable validation/business error.

The limit should be configurable rather than duplicated as a magic number across code.

---

# Content Hash

Calculate:

```text
SHA-256
```

for every uploaded raw Document.

Persist:

```text
content_hash
```

Use the hash for:

- integrity/debugging;
- exact duplicate detection;
- future change/reprocessing decisions.

Calculate the hash while streaming when practical rather than rereading the entire file solely for hashing.

---

# Exact Duplicate Policy

V0 policy:

```text
same raw SHA-256
→ reject duplicate Document ingestion
```

Return a stable business error equivalent to:

```text
DUPLICATE_DOCUMENT
```

Do not create a second logical Document for exact identical raw bytes in V0.

Do not attempt semantic duplicate detection in this step.

---

# Raw Document Metadata

After successful ingestion, persist enough metadata to locate and verify the raw artifact.

Required logical metadata includes:

```text
document_id
original_filename
storage_key
file_extension / file_type
mime_type
file_size_bytes
content_hash
source_category
source_origin
source_language
uploaded_by
uploaded_at
```

Preserve Step 5.1 provenance/usage fields when available:

```text
usage_rights_note
author / organization
publisher
edition / version
original reference
description
```

Reuse existing equivalent fields instead of duplicating schema.

---

# Success Semantics

An upload is successful only when:

```text
file validation succeeded
AND
raw artifact is safely finalized
AND
required metadata is persisted
```

Receiving all request bytes is not enough to report success.

Do not return successful ingestion if storage or required database persistence failed.

---

# Temporary Artifact Flow

Use a temporary artifact/location while receiving the upload.

Equivalent flow:

```text
receive stream
→ temporary raw artifact
→ validate + hash
→ finalize immutable artifact
→ short DB transaction
→ persist metadata
```

On failure before successful finalization:

```text
remove temporary artifact
```

Do not leave stale temporary files indefinitely.

---

# Transaction Boundary

Do not keep a database transaction open while performing potentially slow file streaming/storage I/O.

Preferred pattern:

```text
generate/prepare identifiers
→ stream + validate + hash raw file
→ finalize storage
→ open short DB transaction
→ persist metadata
→ commit
```

If database persistence fails after storage finalization:

```text
compensating cleanup
→ remove orphan raw artifact
```

Do not leave an unreferenced finalized artifact after a failed ingestion operation when cleanup is possible.

---

# Parsing Boundary

Do not run parsing/cleaning as part of the Step 5.2 upload request.

The Step 5.2 contract ends at:

```text
Source
→ Raw Stored
```

Step 5.3 consumes that raw artifact.

Do not couple successful raw ingestion to successful PDF/DOCX extraction.

---

# Synchronous V0

Raw upload/storage may run synchronously in the request for V0.

Do not introduce:

```text
Celery
Redis Queue
Kafka
background worker
job broker
```

for Step 5.2.

Pipeline-stage orchestration belongs to Step 5.6.

---

# Lesson Raw Ingestion

Published Lesson knowledge also requires a reproducible raw representation.

Provide an ingestion primitive equivalent to:

```text
ingestLesson(...)
```

that creates a deterministic snapshot of the Published Lesson source state.

Do not require the ingestion to be automatically triggered by the publish operation in this step.

Automatic trigger/orchestration belongs to Step 5.6.

---

# Lesson Eligibility

Only:

```text
Lesson.status = PUBLISHED
```

is eligible for raw lesson snapshot ingestion.

Do not ingest DRAFT Lesson state into the internal knowledge pipeline.

---

# Raw Lesson Snapshot

Represent the Published Lesson source state as deterministic structured data, preferably JSON.

Snapshot should contain the source-level learning content needed by downstream parsing/transformation, including equivalent fields for:

```text
lesson_id
HSK identity
lesson number
lesson title
lesson source fields
Vocabulary records
Grammar records
relevant lesson notes/content
source timestamps/version marker
```

Do not include:

```text
chunks
embeddings
retrieval scores
retrieval metadata
AI-generated summary
```

The snapshot must represent source state, not later derived knowledge artifacts.

---

# Deterministic Lesson Serialization

Serialize the same Lesson state consistently.

Avoid unstable values or arbitrary ordering that would make identical lesson state produce materially different snapshots.

Use stable ordering for repeated content such as Vocabulary and Grammar items.

The exact serialization format may follow project conventions, but JSON is recommended for V0.

---

# Raw Source Retention

V0 retention:

```text
raw source remains stored
until explicit Admin deletion
```

Do not automatically delete raw artifacts merely because a source is:

```text
REJECTED
ARCHIVED
```

Rejected/unapproved raw sources may remain for:

- review;
- debugging;
- provenance;
- future reprocessing.

Do not add a retention scheduler in this step.

---

# Raw Artifact Access

Raw artifacts must not have public storage URLs.

Only backend/internal ingestion code should have direct storage access.

If an Admin-original-download endpoint already exists or is needed for basic management, it must:

```text
authenticate Admin
authorize access
resolve storage key internally
stream the raw artifact
```

Do not expose local filesystem paths to clients.

---

# Security

Implement baseline upload security:

```text
Admin-only upload
server-generated storage key
client filename treated as metadata only
file-size validation
file-type validation
path-traversal protection
no public raw URL
```

Do not introduce antivirus/malware-scanning infrastructure solely for V0 unless an existing project requirement already requires it.

---

# Error Contract

Use the existing normalized backend error contract.

Add stable business/validation codes where needed, such as equivalents to:

```text
UNSUPPORTED_DOCUMENT_TYPE
DOCUMENT_TOO_LARGE
EMPTY_DOCUMENT
INVALID_DOCUMENT_FILE
DUPLICATE_DOCUMENT
RAW_STORAGE_FAILED
LESSON_NOT_PUBLISHED
```

Exact code names may follow existing naming conventions.

Do not expose filesystem/internal exception text directly to clients.

---

# Suggested Backend Boundaries

Equivalent structure:

```text
ingestion/
├── service
├── storage
│   ├── interface
│   └── local implementation
├── raw_document
└── raw_lesson
```

Exact filenames/modules may differ.

Preserve existing modular-monolith boundaries.

Do not create a separate microservice for ingestion.

---

# Schema / Migration

Inspect current `Document` and related ingestion/storage models before adding fields.

If missing, persist equivalent fields for:

```text
original_filename
storage_key
mime_type
file_size_bytes
content_hash
```

Reuse Step 5.1 fields:

```text
source_category
source_origin
source_language
usage_rights_note
```

If schema changes are required:

- create a new Alembic migration;
- do not rewrite already-applied migrations;
- manually review generated migration;
- preserve existing production-shaped migration discipline.

Do not add Chunk or Embedding schema changes in this step.

---

# Tests

Add focused tests covering at least:

## Document ingestion

- Admin can ingest a valid PDF.
- Admin can ingest valid DOCX/TXT/MD inputs.
- Learner cannot ingest knowledge documents.
- Empty upload is rejected.
- Unsupported type is rejected.
- File above the configured `DOCUMENT_MAX_UPLOAD_MB` limit is rejected.
- Original filename is stored as metadata, not used as trusted path.
- Storage key is server-generated.
- Raw stored bytes match uploaded bytes.
- SHA-256 is persisted correctly.
- Exact duplicate hash is rejected.
- Successful ingestion persists required metadata.
- Temporary artifact is removed on validation failure.
- Finalized artifact is cleaned up when DB persistence fails.
- No successful Document state remains after partial ingestion failure.
- Raw file is not publicly addressable.

## Lesson ingestion

- Published Lesson can create a raw snapshot.
- Draft Lesson cannot create an eligible raw knowledge snapshot.
- Snapshot contains Lesson/Vocabulary/Grammar source content.
- Snapshot excludes chunks/embeddings/retrieval data.
- Same Lesson source state serializes deterministically.
- Lesson ingestion primitive does not require automatic publish-trigger orchestration.

Mock storage where useful.

Use temporary filesystem locations for LocalFileStorage tests.

---

# Out of Scope

Do not implement in Step 5.2:

```text
PDF text extraction
DOCX text extraction
TXT/MD normalization
text cleaning
document transformation
chunking
embedding
vector storage
semantic retrieval
retrieval filtering
reranking
prompt construction
LLM generation
URL ingestion
web crawling
OCR
background pipeline workers
pipeline orchestration
incremental reprocessing policy
production object-storage provider
presigned upload
semantic duplicate detection
automatic raw retention cleanup
```

These belong to later steps/phases.

---

# Acceptance Criteria

- [ ] Both DOCUMENT and Published LESSON have defined raw-ingestion paths.
- [ ] Document uploads pass through FastAPI.
- [ ] File storage is behind a storage abstraction.
- [ ] V0 uses LocalFileStorage.
- [ ] Raw Document bytes are preserved unchanged.
- [ ] Storage keys are server-generated.
- [ ] Original filename is metadata only.
- [ ] PDF/DOCX/TXT/MD are validated as supported types.
- [ ] V0 development default is `DOCUMENT_MAX_UPLOAD_MB=20`; code reads the configured value rather than hard-coding 100 MB.
- [ ] SHA-256 is persisted for raw Documents.
- [ ] Exact duplicate raw files are rejected.
- [ ] Required raw/provenance metadata is persisted.
- [ ] Successful ingestion requires both finalized storage and persisted metadata.
- [ ] Temporary/orphan artifacts are cleaned up after failure.
- [ ] Long file I/O does not hold a DB transaction open.
- [ ] Parsing does not run inside the raw-ingestion request.
- [ ] No queue/worker is introduced in Step 5.2.
- [ ] Published Lessons can produce deterministic raw snapshots.
- [ ] Draft Lessons cannot become raw internal knowledge.
- [ ] Lesson ingestion is not automatically wired to publish orchestration yet.
- [ ] Raw artifacts are retained until explicit Admin deletion.
- [ ] Raw artifacts are not publicly exposed.
- [ ] Step 5.3 can obtain a stable raw artifact as its parsing input.

# Expected Deliverable

Raw-ingestion foundation plus documentation:

```text
docs/data/
└── step-5.2-raw-data-ingestion.md
```

Next Step:

**Step 5.3 — Parsing & Cleaning**
