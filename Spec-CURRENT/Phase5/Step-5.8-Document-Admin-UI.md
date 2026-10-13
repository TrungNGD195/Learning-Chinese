# Step 5.8 — Document Admin UI

## Context
Steps 5.2–5.7 provide the Admin-controlled document ingestion lifecycle. Product requires Upload → Process/Extract → Preview → Review → Approve/Reject before content can enter the internal knowledge build.

## Objective
Connect the existing Admin frontend to the document ingestion/review APIs without making the browser an ingestion orchestrator.

## Current State
Backend ingestion endpoints/state machines from 5.2–5.7 are complete; App foundation/Admin layout exists.

## In Scope
- document list/detail.
- upload supported PDF/DOCX/TXT/MD with configured size boundary.
- process action.
- display `processing_status` and `review_status` separately.
- transformed-content preview.
- approve/reject actions when legal.
- clear failure/retry UX for synchronous processing.

## Out of Scope
OCR, chunk/vector inspection, raw storage path exposure, background job UI, direct browser-to-object-storage upload, knowledge activation controls.

## Functional Requirements
Upload success means raw storage/metadata persisted only; do not show it as approved/active. Process action may visibly block/load because V0 is synchronous. Approve is enabled only for `PREVIEW_READY` documents. Approval means human review accepted; it does not imply vector-active knowledge. Reject remains review state and preserves retained raw/derived artifacts per backend policy.

## Technical Requirements
Use existing Admin API layer and generated types. File upload must use the central client-compatible multipart path and must not read secrets/storage credentials. The UI must read configured/server validation errors instead of hard-coding 100 MB.

## Inputs / Outputs
Inputs: Admin file, metadata, process/review actions. Outputs: state transitions and transformed preview.

## Data Flow
```text
Admin upload → Backend raw ingestion → UPLOADED/PENDING
Admin process → parse/clean/transform → PREVIEW_READY
Admin review  → APPROVED or REJECTED
APPROVED      → backend knowledge-build path (not browser-orchestrated)
```

## Interfaces / API
Reuse exact Phase-5 Admin document routes and states. If route naming differs from examples, generated OpenAPI is authoritative.

## Files / Components
`features/admin/documents` (or existing equivalent), `/admin/documents`, focused upload/process/preview/review components and tests.

## Config / Env
No new frontend secret/config. Display limits from server copy/error where practical; backend setting remains authoritative.

## Error Handling
Distinguish validation (type/size/duplicate), processing failure, illegal review transition, auth failure and network/5xx. Failed processing must offer safe manual retry when backend permits.

## Testing
Cover valid/invalid upload, configured size error, duplicate error, process success/failure, preview, approve/reject gates, and the invariant that approved != retrieval-active.

## Acceptance Criteria
- [ ] Admin can complete Upload → Process → Preview → Approve/Reject.
- [ ] Processing and review states are rendered separately.
- [ ] Only PREVIEW_READY can be approved.
- [ ] No chunk/vector/storage internals are exposed as required UI workflow.
- [ ] Synchronous long-running action has visible loading/error state.
- [ ] Browser does not orchestrate downstream chunk/embed/activation stages.

## Constraints / Non-goals
Do not introduce polling/worker architecture merely for this V0 synchronous flow.

## Open Questions
None that block this Step; D-005 remains an evidence gate after representative profiling.
