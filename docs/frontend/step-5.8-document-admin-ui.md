# Step 5.8 — Document Admin UI

## Objective

Connect the Admin frontend to the accepted Document upload, processing, preview, review, and knowledge-retry lifecycle. Add paginated Admin Document reads so the backend remains the authority for persisted state and retry capability.

## Why

The previous Admin Documents route was a structural placeholder, and the backend had no Document list/detail reads. Upload responses alone cannot provide current state after later processing, review, or knowledge-build operations.

## Mental Model

```text
Admin intent
→ frontend Query/Mutation
→ central apiClient
→ backend authoritative lifecycle
→ authoritative refetch
→ render server state
```

The browser collects Admin intent and renders state. The backend performs ingestion and owns lifecycle rules.

## Core Knowledge

- The paginated list returns public Document fields only and orders by `created_at DESC, id DESC`.
- The detail response includes the server-derived `knowledge_retry_available` snapshot. It is true only when the accepted approved artifact is valid and no `PROCESSING` KnowledgeVersion exists for the Document KnowledgeSource.
- `processing_status` and `review_status` are separate state dimensions. Knowledge retry eligibility is not inferred from either field.
- D-065 re-review may leave an older approved artifact available while the new candidate is `PENDING`; a Knowledge Retry may still be available unless a KnowledgeVersion is already `PROCESSING`.
- Knowledge Retry capability can change after a GET. The mutation's source lock and uniqueness guard remain authoritative; the UI refetches after a conflict and never resends automatically.
- A `FormData` body passes through the central fetch client unchanged so the browser can set the multipart boundary. JSON bodies retain their existing serialization.
- Upload stores raw bytes and metadata only. Approval means human review was accepted; it does not mean knowledge is active for retrieval.

## Data Flow

### Read

```text
Admin Documents UI
→ TanStack Query
→ document feature API
→ central apiClient
→ FastAPI Admin read route
→ ingestion service/repository
→ PostgreSQL
→ typed DTO
→ Query cache
→ render
```

### Upload and lifecycle actions

```text
File + metadata → FormData → POST /admin/documents → raw-stored response → list invalidation
Process → POST /process → backend orchestration → detail/list/preview invalidation
Preview → GET /preview → TransformedDocument → minimal review display
Approve/Reject → backend review operation → detail/list/preview invalidation
Knowledge Retry capability → explicit POST /knowledge/retry → detail/list invalidation
```

All mutations disable TanStack automatic retry. On errors they invalidate relevant server state; no optimistic lifecycle state is assumed.

## Key Design Decisions

- Added only `GET /api/v1/admin/documents` and `GET /api/v1/admin/documents/{document_id}`. No migration or persistence model was added.
- List DTOs expose nullable legacy fields as null and omit storage paths, hashes, actor identifiers, run identifiers, and knowledge internals.
- Detail shares the same approved-artifact resolver as the existing knowledge-retry action and checks `KnowledgeVersion.status` separately from Document processing state.
- The frontend exposes Knowledge Retry only when `knowledge_retry_available` is true.
- Process is offered only for `PENDING + UPLOADED` or `PENDING + FAILED`. Approve/Reject are offered only for `PENDING + PREVIEW_READY`.
- Reject and other lifecycle mutations are followed by an authoritative refetch. The UI renders whichever review state the server returns, including an older approved artifact restored after re-review rejection.
- The preview presents ordered text blocks, section paths, and simple source locators without exposing storage or build lineage.
- The UI uses the existing Admin route guard, navigation, QueryClient retry policy, and central API client.

## Reusable Approach

Use a small feature API wrapper with generated OpenAPI request/response types, stable Query keys, scoped invalidation helpers, and mutation functions with `retry: false`. After mutation success or ambiguity, invalidate the matching collection/detail queries and render the next server response.

## Common Mistakes

- Do not derive Knowledge Retry eligibility from review state, processing state, approval time, or client-held lineage.
- Do not treat a successful upload as processed, approved, or retrieval-active.
- Do not assume Reject always results in `REJECTED`; a prior approved artifact can be restored.
- Do not set `Content-Type` for browser `FormData`; the browser must add the multipart boundary.
- Do not automatically resend an upload, process, review, or knowledge-retry mutation after an ambiguous failure.
- Do not add browser orchestration for parsing, transformation, chunking, embeddings, activation, or Step-5.7 maintenance.

## Definition of Done

- [x] Admin Document list and detail reads use the backend contract.
- [x] Upload sends the required multipart fields through the central API client.
- [x] Processing and review states are rendered separately with the frozen action gates.
- [x] Preview uses the typed backend `TransformedDocument` response.
- [x] Knowledge Retry follows the backend capability flag and refetches after mutations/errors.
- [x] No migration, new runtime dependency, or future-phase UI is introduced.
- [x] Backend/frontend focused tests and required regression commands are recorded in the handoff.

## Verification

- `uv sync`: passed; 42 packages checked, no dependency changes.
- `uv run python -c "from app.main import app; assert app is not None"`: passed with process-local test settings.
- `uv run pytest -q tests/test_admin_document_read_contracts.py`: 5 passed.
- `uv run pytest`: 368 passed.
- `uv run alembic current`: `0010_incremental_reprocessing_contract (head)`.
- `uv run alembic check`: passed; no new upgrade operations detected. SQLAlchemy reports the existing cyclic-FK sorting warning for `documents`, `parsing_runs`, and `transformation_runs`.
- `npm ci`: passed; 219 packages installed, 0 vulnerabilities.
- `npm run api:generate` / `npm run api:check`: passed against live FastAPI OpenAPI.
- Focused frontend tests: 80 passed; full `npm test -- --run`: 288 passed.
- `npm run build`: passed; Vite reports the existing >500 kB bundle warning.
- `npm run lint`: passed with six warnings: the existing `AdminPages.tsx` Fast Refresh warning and five `set-state-in-effect` warnings in existing lesson/curriculum/assessment pages.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Server-authoritative UI state | SYSTEM | 5.8 | The browser renders backend lifecycle state instead of becoming its source of truth. |
| Multipart/form-data | SYSTEM | 5.8 | Carries file bytes and upload metadata through the central HTTP boundary. |
| Generated API contract | SYSTEM | 5.8 | Keeps frontend wrappers aligned with FastAPI OpenAPI. |
| Server state / cache invalidation | SYSTEM | 5.8 | TanStack Query refetches authoritative Document state after mutations. |
| Mutation ambiguity | SYSTEM | 5.8 | Prevents unsafe automatic resends when a mutation may have committed. |
| Lifecycle-driven UI | SYSTEM | 5.8 | Action availability follows legal backend states. |
| Backend-derived capability flag | SYSTEM | 5.8 | `knowledge_retry_available` avoids duplicating retry rules in the UI. |
| Pagination | SYSTEM | 5.8 | Bounds collection reads and defines the Admin list contract. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| React | SYSTEM | 5.8 | Admin Document screens and forms. |
| TypeScript | SYSTEM | 5.8 | Typed API wrappers and frontend state. |
| React Router | SYSTEM | 5.8 | Admin Documents list/detail routes. |
| TanStack Query | SYSTEM | 5.8 | Server-state reads, mutations, and invalidation. |
| native fetch / FormData | SYSTEM | 5.8 | JSON and multipart transport through the central client. |
| openapi-typescript | SYSTEM | 5.8 | Generate frontend API types from the running FastAPI OpenAPI schema. |
| Vitest | SYSTEM | 5.8 | Frontend unit/integration tests. |
| React Testing Library | SYSTEM | 5.8 | Admin Document behavior tests. |
| npm | SYSTEM | 5.8 | Install frontend dependencies and run API contract generation, tests, build, and lint scripts. |
| FastAPI | SYSTEM | 5.8 | Admin Document read routes. |
| Pydantic | SYSTEM | 5.8 | Typed public read DTOs. |
| SQLAlchemy | DE | 5.8 | Bounded Document reads and KnowledgeVersion capability lookup. |
| PostgreSQL | DE | 5.8 | Persisted Document and KnowledgeVersion authority. |
| pytest | SYSTEM | 5.8 | Backend read-contract tests. |
| uv | SYSTEM | 5.8 | Backend synchronization and verification. |
