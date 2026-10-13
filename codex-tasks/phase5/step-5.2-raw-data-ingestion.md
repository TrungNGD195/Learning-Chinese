# Codex Task — Step 5.2 Raw Data Ingestion

## Task Identity

**Project:** LLM + RAG Web App học tiếng Trung cho người mới bắt đầu  
**Phase:** 5 — Data Engineering  
**Step:** 5.2 — Raw Data Ingestion  
**Owner:** Data Engineering Specialist  
**Task status:** FROZEN / READY FOR CODEX AFTER PM REVIEW  
**Implementation mode:** One Codex task = this Step only

Do not redesign architecture. Do not expand scope. Treat the current repository state plus the frozen decisions below as authoritative.

---

# 1. Context

Accepted state before this task:

- Phase 3: COMPLETE.
- Phase 4: COMPLETE.
- Step 5.1: PM ACCEPTED / CLOSED.
- Current Alembic head: `0004_document_source_policy`.
- Step 5.1 introduced the Document source-policy/provenance boundary.
- Ingestion is still inside the existing backend modular monolith.
- No worker/queue is introduced by default in V0.
- Step 5.2 answers:

```text
How do we safely acquire and persist the original source?
```

It does **not** answer:

```text
How do we parse / clean / transform / chunk / embed / retrieve?
```

Step 5.2 ends at:

```text
Source
→ Raw Stored
```

---

# 2. Frozen Decisions

## D-049 — Document provenance nullability / legacy compatibility

Physical PostgreSQL columns remain nullable for legacy rows:

```text
title
source_category
source_origin
source_language
usage_rights_note
```

But a **new ingestion candidate** must pass Step-5.1 source-policy validation with complete required provenance.

Mental model:

```text
legacy row may contain NULL provenance
≠
eligible for new ingestion
```

Do not backfill invented provenance.

---

## D-050 — Admin Document upload transport

The public upload endpoint is frozen as:

```http
POST /api/v1/admin/documents
Content-Type: multipart/form-data
```

Use FastAPI:

```text
UploadFile
Form
```

The multipart request carries:

```text
file
title
source_category
source_origin
source_language
usage_rights_note?   # optional
domain_allowed
```

Add exactly one new runtime dependency required for multipart parsing:

```text
python-multipart
```

Update:

```text
backend/pyproject.toml
backend/uv.lock
```

Do not replace multipart with:

```text
JSON/base64
raw-body + headers/query
direct browser-to-storage
presigned upload
S3
MinIO
```

---

## D-051 — Explicit domain eligibility attestation

The multipart request must explicitly include:

```text
domain_allowed=true
```

Rules:

```text
true
→ may continue through source-policy validation

false
→ reject ingestion

missing / invalid
→ normal request validation failure
```

`domain_allowed` is:

```text
required validation/attestation input
non-persisted
```

Do not infer `True` only because the caller is Admin.

Do not add:

```text
knowledge_domain column
domain_score
classifier_result
trust score
LLM/domain classifier
```

---

## D-005 — Ingestion execution model

Use bounded synchronous ingestion for V0.

Default:

```text
DOCUMENT_MAX_UPLOAD_MB=20
```

Do not add queue/worker infrastructure.

Do not raise the 20 MB default in this Step.

---

# 3. Current Repository State to Preserve

Repository reconciliation was already completed before this task freeze.

## Document model currently contains

```text
id
original_filename
file_type
storage_reference

processing_status
review_status

uploaded_by
approved_by
approved_at

title
source_category
source_origin
source_language
usage_rights_note

created_at
updated_at
```

Reuse:

```text
storage_reference
→ storage key/reference

file_type
→ file extension/type representation

created_at
→ uploaded-at semantics
```

Do **not** add duplicate columns named:

```text
storage_key
file_extension
uploaded_at
```

Current source-policy module exists:

```text
backend/app/ingestion/source_policy.py
```

Reuse it. Do not duplicate Step-5.1 source-policy logic.

---

## Current KnowledgeSource note

Current `KnowledgeSource` already supports:

```text
DOCUMENT
LESSON
```

Current repository has `UNIQUE(lesson_id)` but does not yet enforce `UNIQUE(document_id)`.

Do **not** fix this in Step 5.2.

The one-Document-to-one-logical-KnowledgeSource invariant must be re-evaluated before the later Step that actually creates/reuses Document KnowledgeSource records.

---

## Current ingestion package

Current logical shape before Step 5.2:

```text
backend/app/ingestion/
├── __init__.py
└── source_policy.py
```

There is no existing:

```text
FileStorage
LocalFileStorage
raw ingestion service
raw ingestion repository
raw Lesson serializer
raw artifact contract
```

---

# 4. Objective

Implement the raw-ingestion boundary for accepted V0 sources.

Required capabilities:

1. Admin-only raw Document upload.
2. Immutable original Document bytes.
3. Storage abstraction.
4. Local filesystem implementation.
5. File validation.
6. Bounded streaming.
7. SHA-256 integrity hashing.
8. Race-safe exact duplicate protection.
9. Raw metadata persistence.
10. Compensating cleanup after partial failure.
11. Deterministic raw Published-Lesson snapshot.
12. Stable `RawArtifactRef` contract for Step 5.3.

---

# 5. In Scope

## Document path

```text
Admin multipart request
→ require_admin
→ Step-5.1 metadata validation
→ explicit domain_allowed=true
→ extension/MIME/signature validation
→ bounded streaming
→ temporary artifact
→ incremental SHA-256 + byte count
→ finalize immutable raw artifact
→ short DB transaction
→ persist Document/raw metadata
→ commit
→ safe 201 response
```

No intentionally open DB transaction may span slow upload/file I/O.

---

## Lesson path

```text
lesson_id
→ load Lesson + HSK + ordered Vocabulary + ordered Grammar
→ require Lesson.status == PUBLISHED
→ build RawLessonSnapshot/v1
→ deterministic canonical JSON bytes
→ SHA-256
→ immutable local raw artifact
→ RawArtifactRef
```

Do not wire this to Lesson publish in Step 5.2.

---

# 6. Out of Scope / Non-Goals

Do not implement:

```text
PDF text extraction
DOCX text extraction
TXT/MD normalization
cleaning
transformation
chunking
embedding
vector storage
semantic retrieval
filtering
reranking
prompt construction
LLM generation
URL ingestion
website crawling
OCR
background worker
queue/broker
pipeline orchestration
incremental/reprocessing strategy
S3
MinIO
presigned upload
production object-storage provider
antivirus infrastructure
semantic duplicate detection
automatic retention cleanup
Document Admin frontend
Document processing/preview/review UI
automatic Lesson publish trigger
KnowledgeSource.document_id uniqueness fix
Step 5.3 behavior
```

No Step 5.3+ logic may be pulled forward.

---

# 7. Schema Reconciliation

Existing reusable raw metadata:

```text
document_id
→ Document.id

original_filename
→ Document.original_filename

storage key/reference
→ Document.storage_reference

file extension/type
→ Document.file_type

source provenance
→ title
→ source_category
→ source_origin
→ source_language
→ usage_rights_note

uploaded_by
→ Document.uploaded_by

uploaded_at semantics
→ Document.created_at
```

Genuinely missing fields:

```text
mime_type
file_size_bytes
content_hash
```

Add only these three fields.

---

# 8. Database Migration

Create exactly one forward migration:

```text
backend/migrations/versions/0005_raw_document_metadata.py
```

Required:

```text
revision identity:
0005_raw_document_metadata

down_revision:
0004_document_source_policy
```

Add nullable columns:

```text
mime_type TEXT NULL
file_size_bytes BIGINT NULL
content_hash TEXT NULL
```

Use repository conventions for SQLAlchemy/PostgreSQL types.

Legacy compatibility:

```text
existing Document rows
→ survive migration
→ new fields remain NULL
```

Do not backfill fake raw metadata.

---

## Duplicate invariant

The database is the final authority for exact duplicate protection.

Add:

```text
UNIQUE(content_hash)
```

Expected physical name:

```text
uq_documents_content_hash
```

Because `content_hash` is nullable, multiple legacy `NULL` rows remain valid while non-NULL duplicate hashes are rejected.

Do not rely solely on:

```text
SELECT by hash
→ INSERT
```

because concurrent requests can race.

A pre-check may exist only as an optimization.

---

## File-size integrity

A minimal DB CHECK equivalent to:

```text
file_size_bytes IS NULL
OR file_size_bytes > 0
```

is acceptable and recommended if it follows repository conventions.

Do not make any unrelated schema cleanup.

---

# 9. Document ORM Changes

Modify:

```text
backend/app/database/models/document.py
```

Add only:

```text
mime_type
file_size_bytes
content_hash
```

Keep Step-5.1 provenance fields unchanged.

Keep:

```text
processing_status
review_status
approval invariant
```

unchanged.

Do not change `KnowledgeSource`.

---

# 10. Configuration

Modify:

```text
backend/app/core/config.py
```

Add typed settings equivalent to:

```text
DOCUMENT_MAX_UPLOAD_MB=20
DOCUMENT_STORAGE_ROOT=<configurable path>
```

Requirements:

```text
DOCUMENT_MAX_UPLOAD_MB
→ integer
→ > 0
→ default 20

DOCUMENT_STORAGE_ROOT
→ path-like configuration
→ no machine-specific absolute default
```

Tests must use temporary storage roots.

Do not duplicate the `20 MB` magic number across implementation modules.

Convert once to bytes in the ingestion boundary.

---

# 11. Storage Abstraction

Create a minimal interface equivalent to:

```text
FileStorage
```

Recommended location:

```text
backend/app/ingestion/storage.py
```

Responsibilities:

```text
create temporary artifact
write/append bytes to temp artifact
finalize temp artifact to server-generated storage key
discard temporary artifact
delete finalized artifact
open/read finalized raw artifact
```

Do not expose local filesystem concerns to router/business code.

The interface should be sufficient for Step 5.3 to read immutable stored bytes later.

---

# 12. LocalFileStorage

Implement:

```text
LocalFileStorage
```

behind `FileStorage`.

Root:

```text
Settings.DOCUMENT_STORAGE_ROOT
```

Logical layout equivalent to:

```text
<storage_root>/
├── tmp/
│   └── <generated-id>.part
│
├── documents/
│   └── <document_uuid>/
│       └── raw.<extension>
│
└── lessons/
    └── <lesson_uuid>/
        └── raw/
            └── <source_hash>.json
```

Exact path helper names are implementation details.

Properties that must hold:

```text
client filename
→ metadata only

storage key
→ server generated

raw artifact
→ immutable after successful finalization

storage root
→ configurable

raw files
→ not publicly mounted
```

---

# 13. Path Safety

User-controlled values must not determine final filesystem path.

Reject or defensively prevent keys/paths involving:

```text
absolute paths
..
Windows drive-prefixed paths
backslash traversal
resolved paths outside configured storage root
```

Use resolved path containment checks.

Client filename may be persisted only as:

```text
original_filename
```

Do not expose absolute filesystem paths to API clients.

---

# 14. Temporary Artifact and Atomic Finalization

Use a temp artifact under the configured storage root.

Preferred model:

```text
receive stream
→ write temp file
→ validate/hash/count
→ finalize
```

Finalization should use a cross-platform standard-library atomic replacement/rename primitive equivalent to:

```text
os.replace(...)
```

Keep temp and final artifacts on the same configured filesystem/root so rename semantics remain safe.

Do not introduce an object-storage transaction model.

---

# 15. Admin Upload API

Modify existing Admin routing structure.

Endpoint:

```http
POST /api/v1/admin/documents
```

Auth:

```text
reuse require_admin
```

Do not create a new authorization mechanism.

Request:

```text
multipart/form-data
```

Fields:

```text
file                required
title               required
source_category     required
source_origin       required
source_language     required
usage_rights_note   optional
domain_allowed      required
```

Use `UploadFile` + `Form`.

`domain_allowed` is not persisted.

---

# 16. Request Validation

Reuse Step-5.1 typed metadata validation.

Do not duplicate source-policy rules in the router.

Required metadata contract:

```text
title
→ non-blank

source_category
→ CURRICULUM_MATERIAL | INTERNAL_AUTHORED

source_origin
→ non-blank

source_language
→ vi | zh | en

usage_rights_note
→ optional
```

Then invoke the accepted Step-5.1 ingestion eligibility boundary using:

```text
metadata
+
input format
+
domain_allowed
```

Rules:

```text
domain_allowed=false
→ reject ingestion

missing/invalid form field
→ existing request-validation behavior
```

Do not persist incomplete Documents merely because physical DB columns are nullable.

---

# 17. Supported Document Formats

Support exactly:

```text
PDF
DOCX
TXT
MD
```

Do not add other formats.

---

# 18. MIME and Signature Validation

Use stdlib where sufficient. Do not add a third-party file-type library.

## PDF

Require a consistent combination equivalent to:

```text
.pdf extension
+
allowed declared MIME
+
%PDF signature
```

Do not parse PDF content.

---

## DOCX

Require equivalent:

```text
.docx extension
+
allowed DOCX/ZIP MIME
+
ZIP signature
+
lightweight zipfile structural validation where practical
```

Do not extract document text.

---

## TXT / MD

Require equivalent:

```text
.txt or .md extension
+
allowed text MIME family
+
UTF-8 / text-like validation
```

Do not normalize content.

Raw bytes stored after successful validation must remain exactly the uploaded bytes.

---

# 19. Empty File Validation

Reject zero-byte upload.

Canonical error:

```text
EMPTY_DOCUMENT
HTTP 422
```

Temporary artifact must be removed.

---

# 20. Size Limit

Default:

```text
DOCUMENT_MAX_UPLOAD_MB=20
```

During streaming:

```text
total_bytes += len(chunk)
```

Once configured maximum is exceeded:

```text
stop processing
→ cleanup temp artifact
→ DOCUMENT_TOO_LARGE
→ HTTP 413
```

Do not wait until the entire oversized upload has been materialized before rejecting it where streaming allows earlier detection.

---

# 21. Streaming and SHA-256

Use bounded chunks.

Do not load the whole file into application memory.

During each chunk:

```text
hash.update(chunk)
file_size_bytes += len(chunk)
write chunk to temp
```

After EOF:

```text
content_hash = sha256.hexdigest()
```

Do not reread the full file solely to calculate SHA-256.

---

# 22. Raw Byte Immutability

Successful raw Document bytes must equal uploaded source bytes exactly.

Do not:

```text
rewrite PDF
rewrite DOCX
normalize TXT/MD
change line endings
strip BOM
change encoding
replace source with extracted text
```

Any transformed representation belongs to later Steps.

---

# 23. Success Semantics

A Document upload succeeds only when all are true:

```text
source-policy validation passed
file validation passed
raw artifact finalized safely
required Document metadata persisted
DB commit succeeded
```

Receiving the entire request body is not success.

Do not return success when storage finalization or DB persistence failed.

---

# 24. Transaction Boundary

No intentionally open DB transaction may span slow upload/file I/O.

Required model:

```text
generate Document UUID
→ stream / validate / hash / write temp
→ finalize raw artifact
→ begin short DB work
→ insert Document
→ commit
```

Follow existing application transaction conventions.

Do not invent a long-lived unit-of-work abstraction.

---

# 25. Compensating Cleanup

## Failure before finalization

```text
discard temp artifact
```

## Failure after finalization but before successful DB commit

```text
rollback DB
+
delete this request's finalized artifact
```

## Duplicate race

```text
finalize raw artifact
→ INSERT Document
→ database unique violation on content_hash
→ rollback
→ delete this request's finalized artifact
→ DUPLICATE_DOCUMENT
```

If cleanup itself fails:

```text
log safely
do not convert failed ingestion into success
```

Do not expose filesystem exception text to the client.

---

# 26. Duplicate Handling

Canonical error:

```text
DUPLICATE_DOCUMENT
HTTP 409
```

The DB uniqueness constraint on `content_hash` is the final race-safe authority.

If an optional pre-check is used:

```text
hash exists
→ may reject early
```

but the unique constraint must still be retained and IntegrityError must be translated to the same canonical error.

---

# 27. Document Persistence

Persist:

```text
id
original_filename
file_type
storage_reference

mime_type
file_size_bytes
content_hash

title
source_category
source_origin
source_language
usage_rights_note

processing_status = UPLOADED
review_status = PENDING

uploaded_by = current Admin id
created_at / updated_at
```

Do not mark the Document:

```text
PREVIEW_READY
APPROVED
ACTIVE
```

in Step 5.2.

Raw ingestion success is not human approval and not active knowledge.

---

# 28. Upload Response Contract

Create an explicit response schema equivalent to:

```text
DocumentRawIngestionResponse
```

Successful response:

```text
HTTP 201 Created
```

Expose:

```text
id
original_filename
file_type
mime_type
file_size_bytes
content_hash
title
source_category
source_origin
source_language
usage_rights_note
processing_status
review_status
created_at
```

Must NOT expose:

```text
storage_reference
absolute filesystem path
temporary path
storage root
storage credentials
```

Keep response safe for future Step 5.8 frontend consumption.

---

# 29. Raw Artifact Access

Do not add a public download endpoint in this Step.

Raw artifacts remain backend/internal.

No:

```text
StaticFiles raw mount
public URL
direct filesystem path response
```

Step 5.3 reads raw artifacts through the internal storage boundary.

---

# 30. Repository Boundary

Create a focused persistence boundary equivalent to:

```text
RawIngestionRepository
```

Recommended location:

```text
backend/app/ingestion/repository.py
```

Responsibilities may include:

```text
insert Document metadata
query duplicate hash as optional optimization
load Lesson source graph
```

Repositories must use the provided `AsyncSession`.

Do not put filesystem operations in the repository.

---

# 31. Service Boundary

Create a service equivalent to:

```text
RawIngestionService
```

Recommended:

```text
backend/app/ingestion/service.py
```

Responsibilities:

### Document ingestion

```text
validate source policy
stream upload
validate raw file
calculate size/hash
finalize storage
persist Document
translate duplicate race
cleanup on partial failure
return safe result
```

### Lesson ingestion

```text
validate Lesson eligibility
load canonical source data
build deterministic snapshot
serialize canonical JSON
hash snapshot bytes
store immutable snapshot
return RawArtifactRef
```

Router must not own these orchestration rules.

---

# 32. Error Contract

Reuse existing `ApplicationError` infrastructure.

Canonical Step-5.2 errors:

```text
UNSUPPORTED_DOCUMENT_TYPE → HTTP 422
EMPTY_DOCUMENT            → HTTP 422
INVALID_DOCUMENT_FILE     → HTTP 422
DOCUMENT_TOO_LARGE        → HTTP 413
DUPLICATE_DOCUMENT        → HTTP 409
RAW_STORAGE_FAILED        → HTTP 500
LESSON_NOT_PUBLISHED      → HTTP 409
```

Step-5.1 source/form metadata validation:

```text
INVALID_REQUEST → HTTP 422
```

Missing Lesson:

```text
NOT_FOUND → HTTP 404
```

Do not create another error hierarchy.

Do not expose raw SQL/filesystem/driver exceptions.

---

# 33. Published Lesson Eligibility

Only:

```text
Lesson.status == PUBLISHED
```

may produce a Step-5.2 raw Lesson snapshot.

Reject/ineligible:

```text
DRAFT
ARCHIVED
```

Canonical non-published error:

```text
LESSON_NOT_PUBLISHED
HTTP 409
```

Do not mutate Lesson lifecycle.

---

# 34. Current Lesson Source Model

Use actual repository source fields.

## Lesson

```text
id
hsk_level_id
lesson_number
title
description
status
created_at
updated_at
published_at
```

## HSK

```text
id
level_number
title
```

## Vocabulary source

```text
Vocabulary:
- id
- hanzi
- pinyin
- vietnamese_meaning
- part_of_speech

LessonVocabulary:
- lesson_id
- vocabulary_id
- order_index
- note
- example
```

## Grammar source

```text
Grammar:
- id
- name
- structure
- explanation
- usage

LessonGrammar:
- lesson_id
- grammar_id
- order_index
- note
- example
```

Do not invent extra source fields.

---

# 35. Raw Lesson Snapshot Schema

Freeze schema identity:

```text
raw_lesson_snapshot/v1
```

Logical shape:

```text
RawLessonSnapshot
├── schema_version = "raw_lesson_snapshot/v1"
│
├── lesson
│   ├── id
│   ├── hsk
│   │   ├── id
│   │   ├── level_number
│   │   └── title
│   ├── lesson_number
│   ├── title
│   ├── description
│   └── status = PUBLISHED
│
├── vocabulary[]
│   ├── order_index
│   ├── lesson_vocabulary_id
│   ├── vocabulary_id
│   ├── hanzi
│   ├── pinyin
│   ├── vietnamese_meaning
│   ├── part_of_speech
│   ├── note
│   └── example
│
└── grammar[]
    ├── order_index
    ├── lesson_grammar_id
    ├── grammar_id
    ├── name
    ├── structure
    ├── explanation
    ├── usage
    ├── note
    └── example
```

Do not include:

```text
Chunk
Embedding
retrieval score
retrieval metadata
AI-generated summary
processing timestamp noise
```

This snapshot is source state, not RAG-derived state.

---

# 36. Lesson Deterministic Ordering

Vocabulary ordering:

```text
LessonVocabulary.order_index ASC
```

Grammar ordering:

```text
LessonGrammar.order_index ASC
```

Use existing repository/database ordering semantics.

Do not sort by random UUID.

Do not invent another `position` field.

---

# 37. Lesson Canonical Serialization

Serialize the snapshot deterministically.

Required properties:

```text
UTF-8
sorted object keys
compact deterministic separators
stable vocabulary array order
stable grammar array order
no processing-time timestamps
```

Equivalent Python behavior may use:

```text
json.dumps(
  data,
  ensure_ascii=False,
  sort_keys=True,
  separators=(",", ":")
).encode("utf-8")
```

Exact helper name is implementation detail.

Do not add a separate Lesson versioning subsystem.

---

# 38. Lesson Source Hash

Calculate:

```text
source_hash
=
SHA-256(canonical snapshot bytes)
```

Same source state must produce the same canonical bytes and same hash.

Meaningful source-state change must change canonical bytes/hash.

Do not include ingestion-time noise in the fingerprint.

---

# 39. Lesson Raw Storage

Server-generated layout equivalent to:

```text
lessons/<lesson_id>/raw/<source_hash>.json
```

The snapshot artifact is immutable.

Do not overwrite another different snapshot.

If the exact same source state is ingested again, the implementation may safely reuse/recognize the same hash-keyed artifact behavior without inventing a new version table.

Do not wire publish-trigger orchestration.

---

# 40. RawArtifactRef Contract

Create an internal schema/value object equivalent to:

```text
RawArtifactRef
```

Fields:

```text
source_type: DOCUMENT | LESSON
source_id: UUID
storage_key: str
file_format: str
mime_type: str
file_size_bytes: int
content_hash: str
```

This is an internal handoff boundary, not a public API response.

For Document:

```text
source_id = Document.id
```

For Lesson:

```text
source_id = Lesson.id
file_format = JSON
mime_type = application/json
```

---

# 41. Step 5.3 Handoff Contract

Step 5.3 must later receive:

```text
RawArtifactRef
+
FileStorage
```

and read immutable stored bytes.

Important:

```text
Lesson Step 5.3 processing
→ must read the stored raw Lesson snapshot

NOT
→ re-read live Lesson/Vocabulary/Grammar state
```

This preserves reproducibility.

Do not implement Step 5.3 parsing now.

---

# 42. Dependency Change

Add exactly one runtime dependency required for multipart:

```text
python-multipart
```

Update:

```text
backend/pyproject.toml
backend/uv.lock
```

Do not add:

```text
python-magic
filetype
Pillow
S3 SDK
MinIO SDK
queue packages
workflow orchestrators
```

unless this task becomes impossible without them. If a new dependency appears necessary, stop and report rather than silently adding it.

---

# 43. Expected Files

## Modify

```text
backend/pyproject.toml
backend/uv.lock

backend/app/core/config.py
backend/app/database/models/document.py
backend/app/admin/router.py

backend/tests/test_config.py
backend/tests/test_database.py
backend/tests/test_migration_preservation.py
```

If application route registration conventions require one narrow additional existing file modification, preserve current repository structure and report it in the handoff.

Do not expand architecture.

---

## Create

```text
backend/app/ingestion/schemas.py
backend/app/ingestion/storage.py
backend/app/ingestion/repository.py
backend/app/ingestion/service.py
backend/app/ingestion/router.py

backend/migrations/versions/
0005_raw_document_metadata.py

backend/tests/test_step52_storage.py
backend/tests/test_step52_document_ingestion.py
backend/tests/test_step52_lesson_ingestion.py

docs/data/
step-5.2-raw-data-ingestion.md
```

Reuse:

```text
backend/app/ingestion/source_policy.py
```

Do not create duplicate source-policy modules.

---

# 44. Router Integration

Follow existing Admin conventions.

Preferred architecture:

```text
Admin router
→ include ingestion/document upload router
→ require_admin
→ RawIngestionService
```

Do not put file streaming/business rules directly in `admin/router.py`.

If the repository's current router registration style makes `app/ingestion/router.py` the appropriate route owner, keep business logic there and mount it under the existing Admin prefix.

Public path must still resolve exactly to:

```text
POST /api/v1/admin/documents
```

Do not invent a second public path.

---

# 45. OpenAPI Contract

The backend FastAPI schema is the API contract authority.

The new endpoint must produce correct multipart OpenAPI.

Do not manually edit:

```text
frontend/src/types/api.generated.ts
```

in this Step unless the accepted repository workflow explicitly requires contract regeneration as part of backend API changes.

If OpenAPI regeneration/check is run, generated code must come from the running backend schema under the existing workflow.

Do not implement the Step-5.8 frontend API wrapper/UI.

---

# 46. Tests — Document Upload

Add focused tests proving at least:

1. Admin valid PDF upload succeeds.
2. Admin valid DOCX upload succeeds.
3. Admin valid TXT upload succeeds.
4. Admin valid MD upload succeeds.
5. Learner cannot upload knowledge Documents.
6. Missing auth is rejected by existing auth rules.
7. Empty upload returns `EMPTY_DOCUMENT`.
8. Unsupported extension/type returns `UNSUPPORTED_DOCUMENT_TYPE`.
9. Invalid signature/content returns `INVALID_DOCUMENT_FILE`.
10. Configured max upload limit is enforced.
11. `DOCUMENT_TOO_LARGE` uses HTTP 413.
12. Original filename is persisted only as metadata.
13. Original filename cannot control storage path.
14. Storage key is generated server-side.
15. `../` traversal filename cannot escape storage root.
16. Windows-style traversal filename cannot escape storage root.
17. Raw stored bytes equal uploaded bytes exactly.
18. SHA-256 is correct and persisted.
19. `file_size_bytes` is correct and persisted.
20. MIME type is persisted.
21. Exact duplicate hash is rejected.
22. Duplicate race / IntegrityError is translated to `DUPLICATE_DOCUMENT`.
23. Required Step-5.1 provenance is persisted.
24. `domain_allowed=false` is rejected.
25. Missing/invalid `domain_allowed` is rejected.
26. No incomplete Document is persisted when Step-5.1 validation fails.
27. Temp artifact is removed after validation failure.
28. Finalized artifact is removed when DB persistence fails.
29. No successful persisted Document remains after partial failure.
30. `storage_reference` is absent from public response.
31. Absolute/local filesystem path is absent from response.
32. Raw storage is not publicly addressable.
33. Upload success returns HTTP 201.
34. Success leaves:
    - `processing_status=UPLOADED`
    - `review_status=PENDING`
35. Slow file I/O path does not require an intentionally open DB transaction.

---

# 47. Tests — Storage

Cover:

```text
temp creation
temp write
temp discard
finalization
read/open
delete finalized artifact
server-generated keys
root containment
absolute path rejection
.. traversal rejection
backslash traversal rejection
Windows drive-path rejection
cross-platform key handling
```

Tests must use temporary directories.

Do not write tests against developer-specific directories.

---

# 48. Tests — Duplicate / Race Safety

Verify:

```text
content_hash unique constraint exists
```

and:

```text
same non-NULL content_hash
→ database rejects second row
```

Service-level translation:

```text
IntegrityError caused by content_hash uniqueness
→ rollback
→ cleanup finalized artifact
→ HTTP 409 DUPLICATE_DOCUMENT
```

Do not translate unrelated IntegrityError cases into `DUPLICATE_DOCUMENT`.

---

# 49. Tests — Lesson Snapshot

Cover:

1. `PUBLISHED` Lesson snapshot succeeds.
2. `DRAFT` Lesson returns/reports `LESSON_NOT_PUBLISHED`.
3. `ARCHIVED` Lesson is not treated as active candidate.
4. Snapshot includes actual Lesson fields.
5. Snapshot includes HSK identity.
6. Snapshot includes Vocabulary source data.
7. Snapshot includes Grammar source data.
8. Vocabulary is ordered by `LessonVocabulary.order_index ASC`.
9. Grammar is ordered by `LessonGrammar.order_index ASC`.
10. Same source state produces byte-for-byte identical snapshot.
11. Same source state produces same SHA-256.
12. Meaningful source change changes canonical bytes/hash.
13. No processing timestamp noise is included.
14. No Chunk data exists.
15. No Embedding data exists.
16. No retrieval data exists.
17. No AI-generated summary exists.
18. Snapshot stored at server-generated Lesson raw path.
19. No automatic publish-trigger orchestration was added.
20. `RawArtifactRef` points to immutable stored snapshot.

---

# 50. Tests — Configuration

Verify:

```text
DOCUMENT_MAX_UPLOAD_MB default = 20
override is honored
invalid/non-positive value rejected
no duplicated hard-coded 20 MB limit in runtime behavior
DOCUMENT_STORAGE_ROOT override is honored
tests can isolate storage with tmp_path
```

---

# 51. Tests — Migration

Verify:

```text
0004 → 0005 upgrade
legacy Document rows survive
mime_type NULL for legacy rows
file_size_bytes NULL for legacy rows
content_hash NULL for legacy rows
UNIQUE(content_hash) exists
expected unique name = uq_documents_content_hash
file-size CHECK exists if implemented
downgrade removes only Step-5.2 additions
current head = 0005_raw_document_metadata
```

Do not rewrite `0004`.

Run:

```text
alembic current
alembic check
```

against the dedicated test database/runtime where the project already expects this verification.

---

# 52. Full Regression

Run the entire backend test suite.

Required:

```text
full backend pytest
→ PASS
```

Any existing unrelated warning should be reported separately from Step-5.2 failures.

Do not declare the Step complete if required tests are blocked.

---

# 53. Step Note

Create:

```text
docs/data/step-5.2-raw-data-ingestion.md
```

Must contain:

## Objective

Implement the safe immutable raw-ingestion boundary for Document and Published Lesson sources.

## Why

Preserve reproducible original source data before parsing/transformation.

## Mental Model

```text
Source
→ validate/acquire
→ immutable Raw Artifact
→ Step 5.3 derives parsed/cleaned representations
```

## Core Knowledge

Only concepts actually used.

## Data Flow

Both Document and Lesson flows.

## Key Design Decisions

Include at least:

```text
multipart Admin upload
explicit domain attestation
20 MB bounded synchronous V0
FileStorage / LocalFileStorage
immutable raw source
server-generated storage keys
incremental SHA-256
database unique duplicate invariant
short DB transaction
compensating cleanup
deterministic Lesson snapshot
RawArtifactRef handoff
```

## Reusable Approach

Explain how to separate raw acquisition from downstream transformation in another project.

## Common Mistakes

Include:

```text
using client filename as path
holding DB transaction during file streaming
mutating raw data
hashing only after rereading full file
duplicate SELECT without DB uniqueness
leaking storage path
mixing upload and parsing
nondeterministic Lesson snapshot
```

## Definition of Done

Reflect actual implementation/tests.

---

# 54. Concepts to Record If Actually Used

Likely concepts:

| Concept | Category | Role |
|---|---|---|
| Raw Data Ingestion | DE | Safely acquire original source |
| Raw Artifact | DE | Immutable source representation |
| Data Immutability | DE | Preserve original bytes/state |
| Data Provenance | DE | Trace raw source origin |
| Content Hash / SHA-256 | DE | Integrity and exact identity |
| Exact Duplicate Detection | DE | Reject same raw bytes |
| Storage Abstraction | DE | Separate storage implementation from ingestion logic |
| Deterministic Snapshot | DE | Stable Lesson source representation |
| Schema Evolution | DE | Add raw metadata through forward migration |
| Raw-to-Processed Contract | BOTH | Boundary consumed by Step 5.3 |
| Streaming I/O | SYSTEM | Bound memory during upload |
| Filesystem Safety | SYSTEM | Path containment/traversal prevention |
| Authorization | SYSTEM | Admin-only upload |
| Transaction Boundary | SYSTEM | Keep slow I/O outside DB transaction |
| Compensating Cleanup | SYSTEM | Repair cross-storage/DB partial failure |
| Validation Boundary | SYSTEM | Separate metadata/file/content checks |

Do not record concepts only mentioned but not actually used.

---

# 55. Tools to Record If Actually Used

Likely:

| Tool | Category | Role |
|---|---|---|
| FastAPI | SYSTEM | Multipart Admin endpoint |
| python-multipart | SYSTEM | Multipart parsing |
| PostgreSQL | DE | Raw metadata and duplicate invariant |
| SQLAlchemy | DE | ORM/repository persistence |
| Alembic | DE | `0005` forward migration |
| Pydantic | SYSTEM | Typed contracts/validation |
| pathlib/os | SYSTEM | Safe local filesystem operations |
| hashlib | SYSTEM | SHA-256 |
| zipfile | SYSTEM | Lightweight DOCX validation |
| pytest | SYSTEM | Verification |
| uv | SYSTEM | Dependency/runtime workflow |

Do not add a tool to project records unless implementation really uses it.

---

# 56. Acceptance Criteria

Step 5.2 is acceptable only when all are true:

- [ ] `POST /api/v1/admin/documents` exists.
- [ ] Endpoint uses multipart/form-data.
- [ ] Endpoint is Admin-only through existing authorization.
- [ ] Exactly one multipart runtime dependency (`python-multipart`) was added.
- [ ] Step-5.1 provenance validation remains mandatory.
- [ ] `domain_allowed=true` is explicitly required and non-persisted.
- [ ] `domain_allowed=false` rejects ingestion.
- [ ] New Document fields are only `mime_type`, `file_size_bytes`, `content_hash`.
- [ ] One forward migration `0005_raw_document_metadata` follows `0004`.
- [ ] Legacy Document rows survive with new fields NULL.
- [ ] `UNIQUE(content_hash)` is enforced by PostgreSQL.
- [ ] Exact duplicate race is translated to `DUPLICATE_DOCUMENT`.
- [ ] Default upload limit is 20 MB and configuration-driven.
- [ ] Supported formats remain PDF/DOCX/TXT/MD only.
- [ ] Empty/invalid/oversized raw files are rejected explicitly.
- [ ] SHA-256 and byte count are calculated during streaming.
- [ ] Raw bytes are preserved unchanged.
- [ ] Client filename never determines storage path.
- [ ] Storage keys are server generated.
- [ ] LocalFileStorage prevents path traversal/root escape.
- [ ] File I/O does not intentionally hold an open DB transaction.
- [ ] Partial failures clean temp/final artifacts as specified.
- [ ] Public response excludes `storage_reference`/filesystem paths.
- [ ] No public raw file access was added.
- [ ] PUBLISHED Lesson can create deterministic `raw_lesson_snapshot/v1`.
- [ ] DRAFT/ARCHIVED Lessons cannot create active-candidate raw snapshots.
- [ ] Vocabulary/Grammar use canonical `order_index`.
- [ ] Same Lesson source state serializes identically.
- [ ] Lesson source hash is SHA-256 of canonical snapshot bytes.
- [ ] RawArtifactRef exists and is usable by Step 5.3.
- [ ] Step 5.3 would read stored Lesson snapshot instead of live Lesson state.
- [ ] No parser/cleaning/chunking/embedding/retrieval was added.
- [ ] No worker/queue/object storage was added.
- [ ] No Document frontend was added.
- [ ] No Lesson publish trigger was added.
- [ ] No `KnowledgeSource.document_id` uniqueness fix was added.
- [ ] Focused Step-5.2 tests pass.
- [ ] Migration/schema tests pass.
- [ ] Full backend test suite passes.
- [ ] Alembic head/check verification passes.
- [ ] Step Note is complete.
- [ ] Concepts/Tools reflect actual implementation only.

---

# 57. Verification Commands

Use repository-standard commands.

At minimum execute equivalent verification for:

```text
uv sync
```

Focused Step-5.2 tests:

```text
uv run pytest \
  tests/test_step52_storage.py \
  tests/test_step52_document_ingestion.py \
  tests/test_step52_lesson_ingestion.py \
  -vv
```

Migration/schema/config focused tests as applicable:

```text
uv run pytest \
  tests/test_config.py \
  tests/test_database.py \
  tests/test_migration_preservation.py \
  -vv
```

Full backend regression:

```text
uv run pytest
```

Alembic:

```text
uv run alembic current
uv run alembic check
```

Use the repository's dedicated test PostgreSQL configuration.

Do not point destructive tests at a production database.

---

# 58. Codex Constraints

Codex must:

```text
inspect current files before modifying
preserve existing repository conventions
keep one Step scope
use current service/repository/error/auth patterns
review generated migration manually
avoid speculative abstractions
avoid future-phase technologies
```

Codex must NOT:

```text
change frozen decisions
invent another upload API
change upload size default
change Step-5.1 source taxonomy
invent authority/trust scoring
add optional source categories
add parser behavior
add queues/workers
add object-storage providers
add frontend Document UI
modify unrelated migrations
perform broad refactors
```

If current repository state contradicts this task materially, stop and report the contradiction instead of choosing a new architecture.

---

# 59. Required Codex Completion Handoff

Return:

```text
Step:
Status:

What was done:
- ...

Key decisions preserved:
- D-049
- D-050
- D-051
- D-005

Files/components changed:
- ...

Migration:
- ...

API contract:
- ...

Storage implementation:
- ...

Lesson snapshot implementation:
- ...

RawArtifactRef / Step-5.3 handoff:
- ...

Concepts added:
- ...

Tools added:
- ...

Tests / verification:
- focused tests
- migration/schema
- full backend
- Alembic current/check

Problems / risks:
- ...

Decisions needed:
- ...

Recommended next action:
- ...
```

Do not claim COMPLETE if required tests did not run/pass.

---

# 60. Definition of Done

This Codex task is complete only when:

```text
requirements satisfied
implementation works
required tests pass
migration verified
full backend regression passes
data flow is traceable
Step Note exists
Concepts/Tools are updated based on actual use
no scope creep occurred
Data Engineering Specialist can review the final implementation
```

After Codex finishes, the Data Engineering Specialist must review the actual implementation before PM acceptance.

Do not begin Step 5.3 automatically.
