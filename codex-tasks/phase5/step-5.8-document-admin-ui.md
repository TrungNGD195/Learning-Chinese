# Step 5.8 — Document Admin UI

**Status:** READY_FOR_PM_TASK_REVIEW  
**Owner:** App Engineering Specialist  
**Consulted:** Data Engineering for ingestion/read-contract consistency  
**Current Alembic head:** `0010_incremental_reprocessing_contract`

## Context

Phase 4 frontend core is accepted through Step 4.7. Phase 5 Steps 5.1–5.7 are accepted.

Step 5.8 connects the existing Admin frontend to the accepted Document ingestion/review lifecycle without making the browser an ingestion orchestrator.

PM has frozen:

- **D-068 — Step 5.8 Admin Document Read Contract**
- **D-069 — Server-Derived Document Knowledge Retry Eligibility**

The accepted Document lifecycle is:

```text
Admin upload
→ raw stored
→ Admin Process
→ Parse/Clean
→ Transform
→ PREVIEW_READY
→ Admin Preview
→ Approve or Reject
```

If approved:

```text
backend knowledge build
→ KnowledgeVersion PROCESSING + Chunk[]
→ wait for Phase 6
```

The browser must not invoke parsing, transformation, chunking, embedding, or activation as separate stage operations.

## Objective

Implement the minimum Admin Document UI and the focused backend read contract needed for server-authoritative Document management.

The completed Step must support:

- paginated Document list;
- Document detail;
- PDF/DOCX/TXT/MD upload;
- synchronous Process action and legal retry;
- separate `processing_status` and `review_status`;
- transformed-content preview;
- legal Approve / Reject;
- server-derived Knowledge Retry availability;
- safe mutation/refetch behavior;
- generated OpenAPI TypeScript contract;
- Step documentation.

## Current State

### Existing public Document routes

Preserve these accepted routes:

```http
POST /api/v1/admin/documents
POST /api/v1/admin/documents/{document_id}/process
GET  /api/v1/admin/documents/{document_id}/preview
POST /api/v1/admin/documents/{document_id}/approve
POST /api/v1/admin/documents/{document_id}/reject
POST /api/v1/admin/documents/{document_id}/knowledge/retry
```

The current backend does not yet expose list/detail reads.

### Existing frontend

The Admin shell already contains:

```text
/admin/documents
```

but it is only a structural placeholder.

Accepted frontend architecture:

```text
React + TypeScript + Vite
React Router Data Mode
TanStack Query = server state
central apiClient
generated OpenAPI types
HttpOnly cookie Auth
/auth/me = current User/session authority
```

Do not create a parallel frontend architecture.

### Current generated contract

`frontend/src/types/api.generated.ts` is stale relative to the current accepted backend and currently lacks Admin Document routes.

It must be regenerated from the final FastAPI OpenAPI after D-068/D-069 are implemented.

## In Scope

### Backend focused contract hardening

Add exactly:

```http
GET /api/v1/admin/documents
GET /api/v1/admin/documents/{document_id}
```

Add typed public Admin Document schemas and the minimum repository/service reads required by these endpoints.

Implement `knowledge_retry_available` on the detail response using the same authoritative eligibility rule used by the existing knowledge-retry action.

No migration.

### Frontend

Implement:

- Document list;
- upload form;
- Document detail route;
- processing/review state rendering;
- legal Process action;
- safe Process retry for `PENDING + FAILED`;
- transformed preview;
- Approve;
- Reject;
- Knowledge Retry when server capability is true;
- loading/error states;
- scoped TanStack Query cache management;
- central `FormData` support;
- generated OpenAPI wrappers.

## Out of Scope

Do not implement:

- Phase 6;
- embeddings;
- vector retrieval/indexing;
- reranking;
- prompting;
- LLM integration;
- OCR;
- Chunk inspection UI;
- vector inspection UI;
- knowledge activation UI;
- raw storage-path UI;
- direct browser-to-object-storage upload;
- browser calls to parse/transform/chunk/embed/activate;
- Step-5.7 maintenance/reprocessing UI;
- polling architecture;
- scheduler;
- SSE;
- WebSocket;
- background-worker UI;
- new migration;
- new ingestion lifecycle;
- broad mutation response hardening;
- unrelated Admin redesign;
- new HTTP/state/form framework.

## Functional Requirements

### FR-1 — Document list

Implement:

```http
GET /api/v1/admin/documents?page=1&page_size=20
```

Exact query contract:

```text
page: int
default = 1
minimum = 1

page_size: int
default = 20
minimum = 1
maximum = 100
```

Do not add filtering/sorting parameters in Step 5.8.

List order must be deterministic:

```text
created_at DESC
id DESC
```

Response:

```text
DocumentAdminPageResponse
├── items: DocumentAdminListItemResponse[]
├── page: int
├── page_size: int
└── total: int
```

### FR-2 — Document detail

Implement:

```http
GET /api/v1/admin/documents/{document_id}
```

Missing Document:

```text
404
error.code = NOT_FOUND
```

Response:

```text
DocumentAdminDetailResponse
```

including:

```text
knowledge_retry_available: boolean
```

### FR-3 — Public read DTOs

Use separate list-item and detail schemas to keep the collection query minimal and avoid per-row lineage checks.

#### DocumentAdminListItemResponse

```text
id: UUID

original_filename: str
file_type: str
mime_type: str | null
file_size_bytes: int | null

title: str | null
source_category:
  "CURRICULUM_MATERIAL"
  | "INTERNAL_AUTHORED"
  | null
source_origin: str | null
source_language:
  "vi"
  | "zh"
  | "en"
  | null
usage_rights_note: str | null

processing_status:
  "UPLOADED"
  | "PROCESSING"
  | "PREVIEW_READY"
  | "FAILED"

review_status:
  "PENDING"
  | "APPROVED"
  | "REJECTED"

created_at: datetime
updated_at: datetime
approved_at: datetime | null
```

#### DocumentAdminDetailResponse

Contain all fields from `DocumentAdminListItemResponse` plus:

```text
knowledge_retry_available: bool
```

#### Legacy-safe nullability

The current persisted model requires legacy-safe nullable API fields for:

```text
mime_type
file_size_bytes
title
source_category
source_origin
source_language
usage_rights_note
approved_at
```

Do not synthesize non-null values for old rows.

Do not expose:

```text
storage_reference
content_hash
uploaded_by
approved_by
review_transformation_run_id
approved_transformation_run_id
ParsingRun IDs
TransformationRun IDs
Chunk IDs
Embedding/vector identifiers
internal artifact storage references
```

### FR-4 — Knowledge Retry capability

The frontend must not derive retry eligibility from Document statuses.

The detail response must expose:

```text
knowledge_retry_available: boolean
```

This field represents a server-derived snapshot of whether Admin may legally request a Document knowledge retry **now**.

Freeze the implementation source as follows.

#### Approved artifact condition

Keep the accepted D-069 artifact resolution exactly.

Refactor/reuse the current approved-artifact eligibility logic used by
`IngestionOrchestrator.retry_document_knowledge(...)` through one reusable
internal helper equivalent to:

```python
resolve_document_knowledge_retry_artifact(
    session: AsyncSession,
    document: Document,
) -> TransformedArtifactRef | None
```

The helper must use the accepted rule already embodied by the current retry action:

```text
document.approved_transformation_run_id exists
AND
referenced TransformationRun exists
AND
run.status = SUCCEEDED
AND
run.source_type = DOCUMENT
AND
run.document_id = document.id
AND
run.transformed_storage_reference exists
```

Do **not** add `review_status == APPROVED` as an artifact requirement.

`retry_document_knowledge(...)` must continue to reuse this artifact resolution.

#### PROCESSING KnowledgeVersion condition

Capability evaluation must also reuse the accepted KnowledgeSource / KnowledgeVersion
concurrency/read convention.

Resolve the exact Document `KnowledgeSource` if one exists, then determine whether
that source currently has a `KnowledgeVersion` with:

```text
status = PROCESSING
```

Do not create a new state table.

Do not infer this condition from:

```text
Document.processing_status
```

`Document.processing_status` is ingestion processing state and is a different state
machine from `KnowledgeVersion.status`.

If no `KnowledgeSource` exists, there cannot be a PROCESSING KnowledgeVersion for
that source; continue according to the approved-artifact rule and the accepted
retry contract.

#### Exact capability rule

Document detail must compute:

```text
valid approved transformed artifact exists
AND
no PROCESSING KnowledgeVersion currently exists for the Document KnowledgeSource
→ knowledge_retry_available = true

otherwise
→ knowledge_retry_available = false
```

Use existing repository/service primitives. If repository style supports a small
shared internal predicate/helper, use an equivalent of:

```python
is_document_knowledge_retry_available(...)
```

or another repository-consistent name.

Do not redesign orchestration solely to share a helper.

The actual `POST /knowledge/retry` mutation remains authoritative and must preserve
its existing concurrency-safe locked claim / uniqueness protections.

`knowledge_retry_available` is a snapshot capability, **not** a concurrency guarantee.

Valid race:

```text
GET detail
→ knowledge_retry_available = true

another request claims a PROCESSING KnowledgeVersion

Admin clicks Knowledge Retry

POST /knowledge/retry
→ PROCESSING_ALREADY_IN_PROGRESS

frontend
→ no automatic resend
→ authoritative detail refetch
→ knowledge_retry_available = false
```

Do not weaken mutation concurrency checks merely because the earlier GET returned
`true`.

Do not expose the TransformationRun ID, KnowledgeSource ID, or KnowledgeVersion
internals.

This must correctly support D-065:

```text
review_status = PENDING
+
older approved artifact still valid
+
no PROCESSING KnowledgeVersion
→ knowledge_retry_available = true
```

### FR-5 — Upload

Preserve:

```http
POST /api/v1/admin/documents
Content-Type: multipart/form-data
HTTP 201
```

Exact multipart fields:

Required:

```text
file
title
source_category
source_origin
source_language
domain_allowed
```

Optional:

```text
usage_rights_note
```

Supported V0 formats:

```text
PDF
DOCX
TXT
MD
```

Upload success means:

```text
raw bytes safely stored
+
raw metadata persisted
```

It does not mean processed, approved, or retrieval-active.

Backend remains authoritative for type/size/content validation.

Do not hard-code a frontend upload-size limit if no server-configured value is exposed.

### FR-6 — Process

Legal process state:

```text
review_status = PENDING
AND
processing_status ∈ {UPLOADED, FAILED}
```

Therefore:

```text
PENDING + UPLOADED
→ Process

PENDING + FAILED
→ Retry Processing using the same POST /process
```

Do not expose Process in other states.

Current backend errors include:

```text
PROCESSING_ALREADY_IN_PROGRESS
INVALID_SOURCE_STATE
INGESTION_PROCESSING_FAILED
NOT_FOUND
```

Processing remains synchronous:

```text
click Process
→ mutation pending UI
→ backend request remains foreground
→ success/error
→ authoritative refetch
```

No polling.

### FR-7 — Preview

Use:

```http
GET /api/v1/admin/documents/{document_id}/preview
```

Current typed response:

```text
TransformedDocument
```

Fetch preview only for a reviewable current candidate. Backend remains authoritative if the pinned review candidate is invalid.

Minimal preview rendering:

```text
title
source metadata
ordered blocks
section hierarchy/path
block text
human-readable source locator when useful
```

Do not render storage internals, chunks, vectors, or build a rich CMS.

### FR-8 — Approve / Reject

UI action gate:

```text
review_status = PENDING
AND
processing_status = PREVIEW_READY
```

Backend additionally validates the pinned review candidate.

No optimistic lifecycle success.

Required flow:

```text
mutation
→ server success acknowledgement
→ invalidate/refetch authoritative list/detail
→ render actual state
```

Reject must never assume:

```text
reject → REJECTED
```

D-065 may produce:

```text
candidate rejected
→ previous approved artifact restored
→ review_status = APPROVED
```

Approval means human review accepted. It does not mean knowledge is ACTIVE or retrieval-serving.

### FR-9 — Knowledge Retry UI

Render/enable Knowledge Retry only when:

```text
document.knowledge_retry_available === true
```

Use:

```http
POST /api/v1/admin/documents/{document_id}/knowledge/retry
```

Do not derive eligibility from `review_status`, `processing_status`, `approved_at`, or hidden lineage.

Do not expose Step-5.7 maintenance/reprocessing controls.

### FR-10 — Ambiguous mutation failure

TanStack mutations must use the existing:

```text
retry = false
```

For ambiguous network/5xx outcomes of:

```text
upload
process
approve
reject
knowledge retry
```

do not automatically resend the mutation.

Instead:

```text
error
→ refetch authoritative list/detail where an identity is known
→ render current server state
→ user explicitly decides whether another mutation is needed
```

Existing single-flight Auth refresh plus its accepted one request replay remains unchanged and is not considered mutation auto-retry.

## Technical Requirements

### Backend read implementation

Add to `app.ingestion.repository`:

```python
async def list_documents(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Document], int]
```

Behavior:

```text
total = COUNT(documents)
items =
  SELECT Document
  ORDER BY created_at DESC, id DESC
  OFFSET (page - 1) * page_size
  LIMIT page_size
```

Reuse existing:

```python
get_document(session, document_id)
```

for detail.

Add the smallest read application/service mapping under the existing ingestion boundary, equivalent to:

```python
list_admin_documents(session, page, page_size)
get_admin_document_detail(session, document_id)
```

Responsibilities:

- call repository;
- map ORM objects to public schemas;
- raise existing `NOT_FOUND`/404 convention for missing detail;
- compute `knowledge_retry_available` only for detail from the shared approved-artifact rule **plus** the existing KnowledgeSource/KnowledgeVersion PROCESSING-state check;
- reuse existing repository/service primitives for KnowledgeSource and active PROCESSING KnowledgeVersion lookup;
- keep capability evaluation read-only;
- do not infer KnowledgeVersion build state from `Document.processing_status`;
- preserve the mutation's existing concurrency-safe locked claim / uniqueness protections;
- no writes or ingestion execution.

Routers remain transport adapters.

The detail capability GET is a snapshot. A later `POST /knowledge/retry` may still
return `PROCESSING_ALREADY_IN_PROGRESS` if another request claims the build after
the GET. That race is valid and must not be removed.

### Admin authorization

Both GET routes inherit the existing `/admin` router dependency:

```text
Depends(require_admin)
```

Do not add new auth/token behavior.

### Central apiClient FormData support

Current `apiClient` JSON behavior must remain unchanged.

Modify request body handling exactly as:

```text
body === undefined
→ no Content-Type
→ no request body

body instanceof FormData
→ pass FormData object directly to fetch
→ DO NOT JSON.stringify
→ DO NOT set Content-Type
→ browser generates multipart boundary

all other defined body values
→ Content-Type: application/json
→ JSON.stringify(body)
```

Preserve:

```text
Accept: application/json
credentials: include
ApiError normalization
NETWORK_ERROR behavior
401 refresh single-flight
accepted one replay after successful refresh
ACCOUNT_DISABLED/session invalidation semantics
ordinary ADMIN_REQUIRED 403 does not log out
```

No Axios.

### Multipart generated body helper

Extend `frontend/src/lib/api/types.ts` with a multipart request extraction helper equivalent to:

```ts
type MultipartRequestBody<Operation> =
  Operation extends {
    requestBody: { content: { 'multipart/form-data': infer Body } }
  }
    ? Body
    : never

export type MultipartRequestBodyOf<
  Path extends keyof paths,
  Method extends HttpMethod,
> = MultipartRequestBody<OperationAt<Path, Method>>
```

Keep existing JSON `RequestBodyOf` behavior unchanged.

### Upload wrapper construction

In `features/admin/api.ts`, after regenerated types:

```ts
const documentsPath = '/api/v1/admin/documents'
const documentPath = '/api/v1/admin/documents/{document_id}'
const documentProcessPath = '/api/v1/admin/documents/{document_id}/process'
const documentPreviewPath = '/api/v1/admin/documents/{document_id}/preview'
const documentApprovePath = '/api/v1/admin/documents/{document_id}/approve'
const documentRejectPath = '/api/v1/admin/documents/{document_id}/reject'
const documentKnowledgeRetryPath =
  '/api/v1/admin/documents/{document_id}/knowledge/retry'
```

Generated aliases:

```ts
export type AdminDocumentFilters =
  QueryParametersOf<typeof documentsPath, 'get'>

export type AdminDocumentPage =
  ResponseBodyOf<typeof documentsPath, 'get'>

export type AdminDocumentDetail =
  ResponseBodyOf<typeof documentPath, 'get'>

export type AdminDocumentPreview =
  ResponseBodyOf<typeof documentPreviewPath, 'get'>

type GeneratedDocumentUpload =
  MultipartRequestBodyOf<typeof documentsPath, 'post'>

export type DocumentUploadInput =
  Omit<GeneratedDocumentUpload, 'file'> & { file: File }
```

`openapi-typescript` represents FastAPI's binary form field as a string-like generated field, so the UI-facing input overrides only `file` with browser `File`; other multipart fields remain tied to generated schema.

`uploadDocument(input)` must:

1. create `new FormData()`;
2. append `file`;
3. append each required scalar field using exact backend names;
4. append `usage_rights_note` only when supplied/non-empty according to form semantics;
5. encode `domain_allowed` as the normal `FormData` string representation accepted by FastAPI;
6. call:

```ts
apiClient<ResponseBodyOf<typeof documentsPath, 'post'>, FormData>({
  method: 'POST',
  path: '/admin/documents',
  body: formData,
})
```

Do not manually set `Content-Type`.

For process/approve/reject/knowledge-retry wrappers, do not depend on their current `{}` success response shape. Treat success as acknowledgement and rely on invalidation/refetch.

## Inputs / Outputs

### Inputs

- Admin-selected supported file;
- title;
- source category;
- source origin;
- source language;
- domain eligibility attestation;
- optional rights note;
- Process / Approve / Reject / Knowledge Retry actions;
- page selection.

### Outputs

- server-persisted raw Document;
- current Document list/detail state;
- transformed preview;
- server-authoritative review/processing state;
- knowledge-retry capability;
- normalized errors.

## Data Flow

### Read

```text
Admin Documents UI
→ TanStack Query
→ document feature API
→ central apiClient
→ FastAPI Admin GET
→ ingestion read service/repository
→ PostgreSQL
→ typed DTO
→ Query cache
→ render
```

### Upload

```text
File + metadata
→ FormData
→ central apiClient
→ POST /admin/documents
→ backend validates/stores raw source
→ 201 raw-ingestion response
→ invalidate Document list
→ render UPLOADED + PENDING
```

### Process

```text
Admin Process
→ POST /documents/{id}/process
→ backend Parse/Clean/Transform orchestration
→ PREVIEW_READY or FAILED
→ refetch list/detail
```

### Preview

```text
Document detail
→ GET /documents/{id}/preview
→ TransformedDocument
→ minimal review rendering
```

### Review

```text
Approve / Reject
→ backend authoritative lifecycle
→ success acknowledgement
→ refetch list/detail
→ render actual server state
```

### Knowledge Retry

```text
detail.knowledge_retry_available
→ true
→ Admin explicit retry
→ POST /knowledge/retry
→ backend authoritative build logic
→ refetch detail/list
```

## Interfaces / API

### New D-068 routes

```http
GET /api/v1/admin/documents?page={page}&page_size={page_size}
GET /api/v1/admin/documents/{document_id}
```

### Existing mutation/preview routes

```http
POST /api/v1/admin/documents
POST /api/v1/admin/documents/{document_id}/process
GET  /api/v1/admin/documents/{document_id}/preview
POST /api/v1/admin/documents/{document_id}/approve
POST /api/v1/admin/documents/{document_id}/reject
POST /api/v1/admin/documents/{document_id}/knowledge/retry
```

Do not add other public Document routes.

## Generated OpenAPI Requirements

After backend D-068/D-069 implementation, regenerate through the accepted live FastAPI workflow.

Exact frontend scripts:

```bash
npm run api:generate
npm run api:check
```

The scripts consume:

```text
http://localhost:8000/openapi.json
```

Do not manually edit:

```text
frontend/src/types/api.generated.ts
```

The final generated contract must contain all of:

```text
GET  /admin/documents
GET  /admin/documents/{document_id}
POST /admin/documents
POST /admin/documents/{document_id}/process
GET  /admin/documents/{document_id}/preview
POST /admin/documents/{document_id}/approve
POST /admin/documents/{document_id}/reject
POST /admin/documents/{document_id}/knowledge/retry
```

and typed schemas:

```text
DocumentAdminListItemResponse
DocumentAdminDetailResponse
DocumentAdminPageResponse
```

with Literal/unions for processing/review statuses.

## TanStack Query

Add exact keys following the existing convention:

```ts
adminDocumentsRoot: ['admin', 'documents'] as const,

adminDocuments: (filters: Record<string, string | number>) =>
  ['admin', 'documents', filters] as const,

adminDocument: (documentId: string) =>
  ['admin', 'document', documentId] as const,

adminDocumentPreview: (documentId: string) =>
  ['admin', 'document', documentId, 'preview'] as const,
```

Use filters:

```text
{ page, page_size }
```

### Invalidation

Add focused helpers:

```text
invalidateDocumentList
→ adminDocumentsRoot

invalidateDocumentProcess(id)
→ adminDocumentsRoot
→ adminDocument(id)
→ adminDocumentPreview(id)

invalidateDocumentReview(id)
→ adminDocumentsRoot
→ adminDocument(id)
→ adminDocumentPreview(id)

invalidateDocumentKnowledgeRetry(id)
→ adminDocumentsRoot
→ adminDocument(id)
```

Upload:

```text
→ adminDocumentsRoot
```

Do not clear the global QueryClient.

### Query behavior

Reads use existing bounded Query retry policy.

Mutations use existing `retry = false`.

## Frontend Routing

Replace structural placeholder:

```text
/admin/documents
```

with:

```text
/admin/documents
→ AdminDocumentsPage
```

Add:

```text
/admin/documents/:documentId
→ AdminDocumentDetailPage
```

Reuse `AdminLayout`, `AdminRoute`, and current navigation.

## Frontend Component Split

Use the following minimal structure:

```text
frontend/src/features/admin/documents/
├── AdminDocumentsPage.tsx
├── AdminDocumentDetailPage.tsx
├── DocumentUploadForm.tsx
├── DocumentPreview.tsx
└── step58-documents.test.tsx
```

Responsibilities:

### AdminDocumentsPage

- paginated list;
- upload entry/form placement;
- processing/review status display;
- navigation to detail;
- loading/error/empty states.

### DocumentUploadForm

- File input;
- title;
- source category;
- source origin;
- source language;
- domain eligibility confirmation;
- optional usage-rights note;
- build upload input only;
- no backend validation duplication beyond basic required form UX.

### AdminDocumentDetailPage

- fetch canonical Document detail;
- show metadata and two statuses separately;
- gate Process/Retry Processing;
- fetch/show preview when legal/useful;
- gate Approve/Reject;
- show Knowledge Retry only from `knowledge_retry_available`;
- mutation loading/error;
- authoritative refetch after mutation.

### DocumentPreview

- receive typed `TransformedDocument`;
- render source metadata and ordered content blocks;
- no storage/chunk/vector internals.

Do not add a local/global Document lifecycle store.

## Error Handling

Continue using `ApiError` and `adminErrorText`.

Add mappings for actual backend Document codes:

```text
INVALID_REQUEST
→ Check the document metadata and eligibility fields.

UNSUPPORTED_DOCUMENT_TYPE
→ Upload a PDF, DOCX, TXT, or MD file.

DOCUMENT_TOO_LARGE
→ The document exceeds the server's configured upload limit.

EMPTY_DOCUMENT
→ The selected document is empty.

INVALID_DOCUMENT_FILE
→ The selected file is invalid or does not match its declared format.

DUPLICATE_DOCUMENT
→ An identical document has already been uploaded.

RAW_STORAGE_FAILED
→ The document could not be stored. Retry when safe.

PROCESSING_ALREADY_IN_PROGRESS
→ This document is already being processed.

INVALID_SOURCE_STATE
→ The document state changed. Reloaded server state must be used.

INGESTION_PROCESSING_FAILED
→ Processing failed. If authoritative detail returns PENDING + FAILED,
  expose explicit Process retry.

DOCUMENT_NOT_PREVIEW_READY
→ A reviewable preview is not currently available.

DOCUMENT_ALREADY_APPROVED
→ The document was already approved; refetch authoritative state.

KNOWLEDGE_BUILD_FAILED
→ The knowledge build could not be started/completed; refetch state.
```

Keep existing:

```text
ADMIN_REQUIRED
NOT_FOUND
NETWORK_ERROR
5xx fallback
ACCOUNT_DISABLED/session behavior
```

Do not display raw backend exception details, storage paths, or stack traces.

## Auth Behavior

Preserve accepted Auth architecture:

```text
AdminRoute = frontend UX gate
backend require_admin = security authority
/auth/me = session/User authority
HttpOnly cookie Auth
```

Do not:

- parse JWT;
- store tokens;
- create localStorage/sessionStorage auth state;
- log out on ordinary `ADMIN_REQUIRED` 403.

## Files / Components Expected to Change

### Backend

Expected:

```text
backend/app/admin/router.py
backend/app/ingestion/repository.py
backend/app/ingestion/schemas.py
backend/app/ingestion/orchestrator.py
backend/app/ingestion/service.py
backend/tests/test_admin_document_read_contracts.py
```

If the current repository already has a more appropriate focused Admin read-service file, reuse it instead of adding parallel structure. Do not move unrelated ingestion logic.

No migration file.

### Frontend

Expected:

```text
frontend/src/lib/api/client.ts
frontend/src/lib/api/client.test.ts
frontend/src/lib/api/types.ts

frontend/src/types/api.generated.ts
# generator output only

frontend/src/app/query/keys.ts
frontend/src/app/router/routes.tsx

frontend/src/features/admin/api.ts
frontend/src/features/admin/invalidation.ts
frontend/src/features/admin/AdminPrimitives.tsx

frontend/src/features/admin/documents/AdminDocumentsPage.tsx
frontend/src/features/admin/documents/AdminDocumentDetailPage.tsx
frontend/src/features/admin/documents/DocumentUploadForm.tsx
frontend/src/features/admin/documents/DocumentPreview.tsx
frontend/src/features/admin/documents/step58-documents.test.tsx

docs/frontend/step-5.8-document-admin-ui.md
```

Remove/stop using the structural `AdminPages.Documents` placeholder once the real route is wired. Do not refactor unrelated Admin pages.

## Config / Environment

No new application configuration.

Do not expose backend filesystem/storage settings to the browser.

Do not add a frontend upload-size environment variable.

Existing backend upload limit remains server-authoritative.

## Dependencies

Expected:

```text
NO new runtime dependency
```

Do not add:

- Axios;
- form framework;
- Redux;
- Zustand;
- polling library;
- SSE/WebSocket dependency;
- upload-progress library.

Reuse:

- React;
- TypeScript;
- React Router;
- TanStack Query;
- native fetch/FormData;
- FastAPI;
- Pydantic;
- SQLAlchemy;
- PostgreSQL;
- openapi-typescript;
- existing test/build tooling.

## Backend Testing

Create:

```text
backend/tests/test_admin_document_read_contracts.py
```

Focused tests must cover at least:

1. Admin list success.
2. Default pagination `page=1`, `page_size=20`.
3. Explicit pagination.
4. `page_size > 100` rejected by FastAPI validation.
5. Response contains `items/page/page_size/total`.
6. Deterministic list order.
7. Detail success.
8. Missing detail → current `NOT_FOUND` 404 contract.
9. Processing status typed to the four frozen values.
10. Review status typed to the three frozen values.
11. Legacy nullable fields serialize as `null` rather than fake values.
12. Valid approved artifact + no PROCESSING KnowledgeVersion
    → `knowledge_retry_available=true`.
13. Valid approved artifact + PROCESSING KnowledgeVersion exists
    → `knowledge_retry_available=false`.
14. D-065 re-review:
    `review_status=PENDING` + valid older approved artifact + no PROCESSING KnowledgeVersion
    → `knowledge_retry_available=true`.
15. D-065 re-review:
    `review_status=PENDING` + valid older approved artifact + PROCESSING KnowledgeVersion exists
    → `knowledge_retry_available=false`.
16. Missing/invalid approved artifact + no PROCESSING KnowledgeVersion
    → `knowledge_retry_available=false`.
17. Capability evaluation does not use `Document.processing_status` as a substitute for KnowledgeVersion build state.
18. Capability GET performs no writes and does not claim/create a KnowledgeVersion.
19. Public response contains no `storage_reference`.
20. Public response contains no review/approved TransformationRun IDs.
21. Public response contains no KnowledgeSource/KnowledgeVersion/Chunk/vector/internal artifact IDs.
22. OpenAPI exposes both new GET paths.
23. OpenAPI schemas use typed processing/review enums.
24. Existing write/preview routes remain present and unchanged in path/method.
25. GET routes have no write/ingestion side effects.
26. Admin authorization remains required.

Where practical, test repository/service behavior without file-storage/network dependence.

## Central apiClient Tests

Extend:

```text
frontend/src/lib/api/client.test.ts
```

Require:

1. Existing JSON object body still sets `application/json`.
2. Existing JSON object body still uses `JSON.stringify`.
3. `FormData` is passed to `fetch` by identity.
4. `FormData` is not JSON-stringified.
5. `Content-Type` is not set for `FormData`.
6. `Accept: application/json` remains.
7. `credentials: include` remains.
8. Backend `ApiError` normalization remains.
9. network error normalization remains.
10. ordinary `ADMIN_REQUIRED` does not invalidate session.
11. 401 single-flight refresh behavior remains.
12. accepted one replay behavior remains.

## Frontend Step-5.8 Tests

Create:

```text
frontend/src/features/admin/documents/step58-documents.test.tsx
```

Cover at least:

1. `/admin/documents` uses real Documents UI, not placeholder.
2. Document list loading/success/empty/error.
3. List renders title/source/statuses.
4. Processing and review status appear separately.
5. Pagination requests correct `page/page_size`.
6. Detail route `/admin/documents/:documentId`.
7. Detail loading/success/error/not-found.
8. Upload valid PDF request.
9. Upload valid DOCX request.
10. Upload valid TXT request.
11. Upload valid MD request.
12. Exact FormData field names.
13. Required `domain_allowed`.
14. Optional `usage_rights_note`.
15. Upload goes through central client.
16. Upload success renders/refetches raw-only state.
17. Upload does not imply approved.
18. Upload does not imply active knowledge.
19. `UNSUPPORTED_DOCUMENT_TYPE`.
20. `DOCUMENT_TOO_LARGE`.
21. `EMPTY_DOCUMENT`.
22. `INVALID_DOCUMENT_FILE`.
23. `DUPLICATE_DOCUMENT`.
24. Legal Process only for `PENDING + UPLOADED`.
25. Legal Process retry for `PENDING + FAILED`.
26. No Process for illegal states.
27. Process pending/loading UI.
28. Process success invalidates/refetches.
29. Process failure renders error and authoritative state.
30. Preview fetch for reviewable detail.
31. Preview renders `TransformedDocument`.
32. Preview does not render storage/Chunk/vector internals.
33. Approve gate.
34. Approve success refetches.
35. Approve error refetch/error behavior.
36. Reject gate.
37. Reject success refetches.
38. Reject does not assume `REJECTED`.
39. Restored server `APPROVED` after reject is rendered.
40. `APPROVED` is not labeled retrieval-active.
41. Knowledge Retry visible/enabled only when
    `knowledge_retry_available=true`.
42. Knowledge Retry absent/disabled when false.
43. Server returns `knowledge_retry_available=false` because a knowledge build is already in progress while Document review/processing statuses might otherwise look retryable
    → frontend still does not offer an enabled retry action and does not infer a different answer from those statuses.
44. Knowledge Retry success invalidates list/detail.
45. Knowledge Retry `PROCESSING_ALREADY_IN_PROGRESS` race/error does not auto-resend and refetches authoritative detail.
46. No Step-5.7 maintenance/reprocessing UI.
47. ambiguous Process/Approve/Reject/Retry failure does not automatically resend.
48. ambiguous failure triggers authoritative refetch where identity is known.
49. ADMIN_REQUIRED behavior does not log out authenticated User.
50. No raw storage path displayed.
51. No TransformationRun IDs displayed.
52. No KnowledgeSource/KnowledgeVersion internals displayed.
53. No Chunk/vector controls.
54. No browser parse/transform/chunk/embed/activation calls.
55. Step-4.7 Admin navigation/regression remains intact.

## Full Verification

### Backend

From `backend/`:

```bash
uv sync
uv run pytest -q tests/test_admin_document_read_contracts.py
uv run pytest -q
```

Verify Alembic head remains:

```text
0010_incremental_reprocessing_contract
```

No migration should be generated.

### OpenAPI / Frontend

Run the accepted FastAPI application at the existing local OpenAPI endpoint:

```text
http://localhost:8000/openapi.json
```

Then from `frontend/`:

```bash
npm ci
npm run api:generate
npm run api:check
npm test -- --run src/lib/api/client.test.ts src/features/admin/documents/step58-documents.test.tsx
npm test -- --run
npm run build
npm run lint
```

Do not hand-edit generated API output to make `api:check` pass.

## Acceptance Criteria

- [ ] D-068 list endpoint exists.
- [ ] D-068 detail endpoint exists.
- [ ] List uses `page/page_size` with defaults 1/20 and max 100.
- [ ] List response is typed and bounded.
- [ ] Detail response is typed.
- [ ] Legacy nullable fields remain nullable.
- [ ] Processing and review statuses are separate typed enums.
- [ ] No internal storage/lineage/vector fields leak through public DTOs.
- [ ] D-069 `knowledge_retry_available` exists on detail.
- [ ] D-069 preserves the exact approved-artifact rule.
- [ ] `knowledge_retry_available=true` only when a valid approved artifact exists **and** no PROCESSING KnowledgeVersion currently exists for that Document KnowledgeSource.
- [ ] A current PROCESSING KnowledgeVersion forces `knowledge_retry_available=false`.
- [ ] Capability evaluation does not confuse `Document.processing_status` with `KnowledgeVersion.status`.
- [ ] D-065 PENDING re-review can expose retry capability when an older approved artifact exists and no PROCESSING KnowledgeVersion exists.
- [ ] D-065 PENDING re-review returns retry capability false when a PROCESSING KnowledgeVersion already exists.
- [ ] Capability GET remains read-only and does not weaken the mutation's concurrency-safe claim/uniqueness guard.
- [ ] A post-GET race may still produce `PROCESSING_ALREADY_IN_PROGRESS`; frontend refetches authority and does not auto-resend.
- [ ] No DB migration is added.
- [ ] Existing Document mutation/preview routes remain intact.
- [ ] Mutation response `{}` schemas are not broadened merely for Step 5.8.
- [ ] Central apiClient supports FormData without regressing JSON/Auth/error behavior.
- [ ] Generated OpenAPI TypeScript is regenerated, not manually edited.
- [ ] `/admin/documents` is a real management screen.
- [ ] `/admin/documents/:documentId` is implemented.
- [ ] Admin can upload PDF/DOCX/TXT/MD.
- [ ] Upload success means raw-stored only.
- [ ] Backend remains upload validation authority.
- [ ] `processing_status` and `review_status` render separately.
- [ ] Process action follows exact legal state.
- [ ] FAILED initial processing can be retried manually.
- [ ] Preview uses backend `TransformedDocument`.
- [ ] Approve/Reject follow server lifecycle.
- [ ] Reject result is server-authoritative.
- [ ] Approved is not represented as retrieval-active.
- [ ] Knowledge Retry appears only from server capability flag.
- [ ] Step-5.7 maintenance retry is not exposed.
- [ ] Mutations are not auto-retried blindly.
- [ ] Ambiguous mutation failure refetches authority rather than automatically resending.
- [ ] No browser ingestion-stage orchestration exists.
- [ ] No new runtime dependency is introduced.
- [ ] Backend focused tests pass.
- [ ] Backend full tests pass.
- [ ] `api:generate` succeeds.
- [ ] `api:check` succeeds.
- [ ] Focused frontend tests pass.
- [ ] Full frontend tests pass.
- [ ] Build passes.
- [ ] Lint passes according to existing project warning policy.
- [ ] Step Note is complete.

## Constraints / Non-goals

- Preserve modular-monolith architecture.
- Backend remains business/lifecycle/security authority.
- Frontend is an intent + server-state rendering layer.
- Keep the solution small and traceable for a beginner.
- Do not add technology for future phases.
- Do not expose persistence/ingestion internals merely to simplify UI logic.
- Do not implement Phase 6 opportunistically.

## Step Note

Create:

```text
docs/frontend/step-5.8-document-admin-ui.md
```

Include:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- Reusable Approach
- Common Mistakes
- Definition of Done
- Concepts Discovered
- Tools Used

Mental model:

```text
Admin intent
→ frontend Query/Mutation
→ central apiClient
→ backend authoritative lifecycle
→ authoritative refetch
→ render server state
```

Browser orchestrates user intent.

Backend orchestrates ingestion.

## Concepts Discovered

Only record concepts actually used.

Expected classification:

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Server-authoritative UI state | SYSTEM | 5.8 | Browser renders backend lifecycle instead of becoming source of truth |
| Multipart/form-data | SYSTEM | 5.8 | Carries file bytes plus upload metadata through the central HTTP boundary |
| Generated API contract | SYSTEM | 5.8 | Keeps frontend wrappers aligned with FastAPI OpenAPI |
| Server state / cache invalidation | SYSTEM | 5.8 | TanStack Query refetches authoritative Document state after mutations |
| Mutation ambiguity | SYSTEM | 5.8 | Prevents unsafe automatic resend when a mutation may already have committed |
| Lifecycle-driven UI | SYSTEM | 5.8 | Action availability follows legal backend states |
| Backend-derived capability flag | SYSTEM | 5.8 | `knowledge_retry_available` avoids duplicating retry business rules in UI |
| Pagination | SYSTEM | 5.8 | Bounds collection reads and defines the Admin list access contract |

Do not add AI concepts.

Do not classify a concept as DE merely because PostgreSQL is involved.

## Tools Used

Only record tools actually used in the final implementation.

Expected likely tools:

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| React | SYSTEM | 5.8 | Admin Document UI |
| TypeScript | SYSTEM | 5.8 | Typed frontend contracts |
| React Router | SYSTEM | 5.8 | Documents list/detail routes |
| TanStack Query | SYSTEM | 5.8 | Server-state queries/mutations/invalidation |
| native fetch / FormData | SYSTEM | 5.8 | JSON + multipart transport through central client |
| openapi-typescript | SYSTEM | 5.8 | Generate frontend API types from FastAPI OpenAPI |
| Vitest | SYSTEM | 5.8 | Frontend unit/integration tests |
| React Testing Library | SYSTEM | 5.8 | UI behavior tests |
| npm | SYSTEM | 5.8 | Frontend dependency/scripts workflow |
| FastAPI | SYSTEM | 5.8 | Admin HTTP read endpoints |
| Pydantic | SYSTEM | 5.8 | Typed public read DTOs |
| SQLAlchemy | DE | 5.8 | Bounded Document reads from PostgreSQL |
| PostgreSQL | DE | 5.8 | Persisted Document source of truth |
| pytest | SYSTEM | 5.8 | Backend contract tests |
| uv | SYSTEM | 5.8 | Backend environment/test workflow |

If a listed tool is not actually exercised/changed/used during implementation, omit it from the final Step Note.

## Open Questions

None that block implementation.

If actual repository state at Codex execution materially contradicts this frozen task in a way that changes:

- public API;
- persistence/schema;
- lifecycle/business rule;
- knowledge retry semantics;
- auth/security;
- dependency requirements;
- major UX flow;

Codex must stop and report:

```text
BLOCKED — Decision Needed
```

Do not silently resolve the contradiction.

## Required Completion Report

Codex must return:

```text
Step
Status
What was implemented

D-068 implementation
D-069 implementation

Backend read contract
Knowledge retry eligibility:
- approved artifact condition
- PROCESSING KnowledgeVersion condition
- D-065 PENDING re-review behavior
- snapshot/race semantics
Existing mutation concurrency guard preservation
OpenAPI/generated contract

Central apiClient FormData change
Document feature API
Routes
Query keys/invalidation
Document UI
Lifecycle/action gates
Mutation ambiguity behavior
Auth/security behavior

Files changed
Dependencies changed
Migrations changed
Tests added

Focused backend test results
Backend full test results
api:generate result
api:check result
Focused frontend test results
Frontend full test results
Build result
Lint result

Step Note
Concepts added
Tools added

Problems/risks
Deviations
Decisions needed
Recommended next action
```

Codex must also provide a focused Step-5.8 ZIP for independent App Engineering Specialist actual-code review.

Codex must not claim PM acceptance.
