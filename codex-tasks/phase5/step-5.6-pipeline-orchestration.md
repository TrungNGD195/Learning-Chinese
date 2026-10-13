# Codex Task — Step 5.6 Pipeline Orchestration

## Task Identity

**Project:** LLM + RAG Web App học tiếng Trung cho người mới bắt đầu  
**Phase:** 5 — Data Engineering  
**Step:** 5.6 — Pipeline Orchestration  
**Owner:** Data Engineering Specialist  
**Status:** FROZEN / READY FOR CODEX AFTER PM REVIEW

Use the current accepted repository after Step 5.5. Preserve accepted Steps 5.1–5.5 and frozen decisions D-060, D-061, D-062, D-063, D-064.

Do not redesign architecture. Do not implement Step 5.7 or Phase 6. Do not add new runtime dependencies unless a real repository contradiction blocks the task.

---

# 1. Objective

Implement orchestration for the accepted V0 ingestion stages:

```text
Raw
→ Parse/Clean
→ Transform
→ Chunk
```

Stop at:

```text
KnowledgeVersion(status = PROCESSING)
+
complete persisted Chunk[]
```

Do not implement:

```text
Embedding
Vector Storage
Retrieval
KnowledgeVersion activation
```

The orchestrator owns:

```text
sequencing
prerequisite gates
source/business lifecycle gates
KnowledgeSource create/reuse
KnowledgeVersion creation
source-level concurrency protection
failure propagation
manual retry boundaries
structured stage logging
delegation to accepted stage services
```

It must not reimplement:

```text
parsing
cleaning
transformation formatting
chunk splitting
FileStorage internals
```

---

# 2. Accepted Stage Boundaries

Use exact accepted persisted references:

```text
RawArtifactRef
→ ParsedArtifactRef
→ TransformedArtifactRef
→ ChunkingService
```

Reuse existing accepted primitives equivalent to:

```text
document_raw_artifact_ref(document)
create_lesson_snapshot(...)
parse_raw_artifact(...)
transform_parsed_artifact(...)
build_chunks(...)
load_transformed_artifact(...)
```

Do not use:

```text
latest ParsingRun
latest TransformationRun
current run lookup
one giant mutable in-memory pipeline object
```

---

# 3. Orchestrator Boundary

Create equivalent:

```text
backend/app/ingestion/orchestrator.py
```

with:

```text
IngestionOrchestrator
```

Responsibilities:

```text
source-state validation
lifecycle gates
stage sequencing
stage delegation
KnowledgeSource create/reuse
KnowledgeVersion allocation
concurrency protection
failure propagation
retry coordination
structured logging
```

Must NOT contain:

```text
PDF/DOCX parser logic
cleaning implementation
canonical transformation formatting
chunk splitting strategy
embedding logic
retrieval logic
```

No:

```text
IngestionRun
PipelineRun
StageRun
```

for V0.

---

# 4. Execution Model

Remain inside the existing FastAPI modular monolith.

Synchronous orchestration is acceptable.

Do not add:

```text
Airflow
Prefect
Dagster
Celery
Kafka
Redis
queue worker
scheduler
orchestration microservice
FastAPI BackgroundTasks as critical durability
```

Use short durable DB transactions around state transitions and claims.

Do not hold DB transactions open across slow file/data processing.

---

# 5. Frozen D-060 — Exact Reviewable Document Artifact

Add:

```text
documents.review_transformation_run_id UUID NULL
```

Foreign key:

```text
→ transformation_runs.id
ON DELETE SET NULL
```

This pointer is the authoritative identity for the exact transformed artifact that Admin reviews and later approves.

Never select:

```text
latest successful TransformationRun
current TransformationRun
preferred TransformationRun
```

Freeze:

```text
Admin Preview artifact
=
Admin Approved artifact
=
Chunking input artifact
```

---

# 6. Review Pointer Lifecycle

Upload:

```text
processing_status = UPLOADED
review_status = PENDING
review_transformation_run_id = NULL
```

Process/retry claim:

```text
processing_status = PROCESSING
review_transformation_run_id = NULL
```

Parse/transform failure:

```text
processing_status = FAILED
review_transformation_run_id = NULL
```

Transform success must atomically persist in the SAME success transaction:

```text
TransformationRun = SUCCEEDED
Document.processing_status = PREVIEW_READY
Document.review_transformation_run_id = successful run.id
```

Do not commit:

```text
PREVIEW_READY
+
NULL review pointer
```

as successful state.

Pointer remains unchanged after:

```text
APPROVED
REJECTED
```

---

# 7. Transformation-Service Integration

Narrowly modify the accepted Step-5.4 transformation service so DOCUMENT success sets:

```text
review_transformation_run_id = current successful TransformationRun.id
```

in the same transaction that persists:

```text
TransformationRun = SUCCEEDED
Document.processing_status = PREVIEW_READY
```

Do not change transformation algorithms or `transformed_document/v1`.

---

# 8. Frozen D-061 + D-064 — Migration Contract

Create exactly one forward migration:

```text
0009_pipeline_orchestration_contract
```

with exact:

```text
down_revision = 0008_chunking_contract
```

Migration 0009 contains exactly:

```text
3 Step-5.6 application/domain schema deltas:

1. documents.review_transformation_run_id

2. DB uniqueness:
   one non-null KnowledgeSource.document_id
   → at most one KnowledgeSource

3. partial unique index:
   one knowledge_source_id
   → at most one KnowledgeVersion
      WHERE status = 'PROCESSING'

plus exactly:

1 migration-infrastructure compatibility delta:

4. alembic_version.version_num
   VARCHAR(32) → VARCHAR(64)
```

The Alembic width change is **not** a fourth Step-5.6 domain feature.

Preserve existing:

```text
KnowledgeSource.lesson_id uniqueness

UNIQUE(
  knowledge_source_id,
  version_number
)

one ACTIVE/source partial uniqueness
```

Do not modify migrations `0001–0008`.

Do not add unrelated schema.

---

# 8A. Frozen D-064 — Alembic Revision Storage Width

Keep exact frozen revision:

```text
0009_pipeline_orchestration_contract
```

Keep exact:

```text
down_revision = 0008_chunking_contract
```

At the **BEGINNING** of `0009_pipeline_orchestration_contract.upgrade()`, before any Step-5.6 application-schema change, widen:

```text
alembic_version.version_num
VARCHAR(32)
→ VARCHAR(64)
```

using an Alembic operation equivalent to:

```python
op.alter_column(
    "alembic_version",
    "version_num",
    existing_type=sa.String(length=32),
    type_=sa.String(length=64),
    existing_nullable=False,
)
```

Only after that apply the three D-061 application-schema deltas.

The upgrade must also tolerate the intentional re-upgrade case where `alembic_version.version_num` is already `VARCHAR(64)` after a prior downgrade to 0008.

Do not use:

```text
shortened revision ID
0009a/bootstrap migration
second preparatory migration
manual/out-of-band SQL
deployment-script schema mutation
custom Alembic startup hook
```

---

# 8B. D-064 Downgrade Semantics

For:

```text
0009_pipeline_orchestration_contract
→ 0008_chunking_contract
```

revert only the Step-5.6 application-schema deltas:

```text
documents.review_transformation_run_id
Document KnowledgeSource uniqueness introduced by 0009
PROCESSING KnowledgeVersion partial uniqueness introduced by 0009
```

Do **not** narrow:

```text
alembic_version.version_num
```

back to `VARCHAR(32)`.

Expected post-downgrade state:

```text
current revision = 0008_chunking_contract
Step-5.6 application schema = reverted
alembic_version.version_num = VARCHAR(64)
```

This asymmetry is intentional and frozen.

Mental model:

```text
application migration state
≠
migration-engine storage capacity
```

`VARCHAR(64)` becomes the migration-control storage width going forward.

---

# 9. Document KnowledgeSource Identity

Freeze:

```text
1 Document
→ 1 KnowledgeSource
```

Create/reuse logic:

```text
lookup by document_id

if exists:
    validate source_type = DOCUMENT
    validate lesson_id IS NULL
    reuse

else:
    insert DOCUMENT KnowledgeSource
```

DB uniqueness must protect concurrent creation.

A concurrent loser should safely re-read/reuse the existing source according to repository transaction conventions.

Do not rely only on an application precheck.

---

# 10. Lesson KnowledgeSource Identity

Preserve existing:

```text
1 Lesson
→ 1 KnowledgeSource
```

and existing `lesson_id` DB uniqueness.

Create/reuse by `lesson_id`.

Validate:

```text
source_type = LESSON
document_id IS NULL
```

Do not create a new source per retry/build.

---

# 11. KnowledgeVersion Allocation Freeze

Every new build:

```text
→ NEW KnowledgeVersion
→ status = PROCESSING
```

Do not reuse:

```text
FAILED
SUPERSEDED
```

Do not modify existing:

```text
ACTIVE
```

Race-safe allocation:

```text
SELECT KnowledgeSource FOR UPDATE
→ verify no PROCESSING version exists
→ compute MAX(version_number) + 1 while lock held
→ INSERT new PROCESSING KnowledgeVersion
→ commit
```

Existing:

```text
UNIQUE(knowledge_source_id, version_number)
```

is the final version-number safety net.

Do not use naked `MAX()+1` without the source lock.

---

# 12. PROCESSING Concurrency Freeze

Add DB partial uniqueness equivalent to:

```text
UNIQUE(knowledge_source_id)
WHERE status = 'PROCESSING'
```

Application flow must also:

```text
lock KnowledgeSource FOR UPDATE
→ check no PROCESSING build
→ allocate version
```

If already processing:

```text
PROCESSING_ALREADY_IN_PROGRESS
```

Do not rely on stale prechecks.

---

# 13. ACTIVE Protection

Older ACTIVE version must never be mutated by a newer build.

Allowed:

```text
v1 = ACTIVE
v2 = PROCESSING
```

If v2 fails:

```text
v1 remains ACTIVE
v1 Chunks unchanged
v2 → FAILED
```

Step 5.6 never activates a version.

---

# 14. Document Upload Freeze

Existing Document upload remains Raw Stored only.

Equivalent:

```text
POST /api/v1/admin/documents
```

must still end with:

```text
processing_status = UPLOADED
review_status = PENDING
review_transformation_run_id = NULL
Raw stored
```

No automatic:

```text
parse
transform
chunk
```

Do not regress Step 5.2.

---

# 15. Document Process API Freeze

Add use-case route equivalent to:

```text
POST /api/v1/admin/documents/{document_id}/process
```

This same action handles manual retry from processing failure.

Allowed states:

```text
PENDING + UPLOADED
PENDING + FAILED
```

No separate pre-review retry route is required.

---

# 16. Document Process Concurrency Claim

Before slow processing:

```text
BEGIN
SELECT Document FOR UPDATE
```

Require one of:

```text
PENDING + UPLOADED
PENDING + FAILED
```

Then:

```text
processing_status = PROCESSING
review_transformation_run_id = NULL
COMMIT
```

Second concurrent request:

```text
sees PROCESSING
→ PROCESSING_ALREADY_IN_PROGRESS
```

Do not hold the row lock through parse/transform.

---

# 17. Document Process Flow

After claim commit:

```text
exact RawArtifactRef
→ parse_raw_artifact()
→ exact ParsedArtifactRef
→ transform_parsed_artifact()
→ exact TransformedArtifactRef
→ pinned exact successful TransformationRun
→ PREVIEW_READY
```

Do not Chunk before approval.

No latest/current run lookup.

---

# 18. Document Process Fail-Fast

Parse failure:

```text
Document → FAILED
review pointer = NULL
transform NOT RUN
chunk NOT RUN
```

Transform failure:

```text
Document → FAILED
review pointer = NULL
chunk NOT RUN
```

Committed upstream artifacts remain according to accepted stages.

Surface safe:

```text
INGESTION_PROCESSING_FAILED
```

at orchestration/business boundary.

---

# 19. Document Preview API Freeze

Add route equivalent to:

```text
GET /api/v1/admin/documents/{document_id}/preview
```

Require:

```text
processing_status = PREVIEW_READY
review_transformation_run_id != NULL
```

Load exact pinned TransformationRun.

Validate:

```text
source_type = DOCUMENT
document_id = Document.id
status = SUCCEEDED
transformed_storage_reference exists
```

Construct exact `TransformedArtifactRef`.

Then:

```text
load_transformed_artifact()
→ TransformedDocument
```

Do not preview:

```text
Raw
Chunk[]
latest transformation
```

---

# 20. Preview / Approval Exact Identity

Preview and Approval must use the same:

```text
Document.review_transformation_run_id
```

Approval must not reselect a transformed artifact.

Knowledge Chunking must use the exact `TransformedArtifactRef` reconstructed from this pinned run.

Tests must create multiple successful TransformationRuns and prove the pinned one wins even if another run is newer.

---

# 21. Document State Freeze

Machine state:

```text
UPLOADED
PROCESSING
PREVIEW_READY
FAILED
```

Review state:

```text
PENDING
APPROVED
REJECTED
```

Allowed Step-5.6 transitions:

```text
PENDING + UPLOADED
→ PROCESSING

PENDING + FAILED
→ PROCESSING

PROCESSING
→ PREVIEW_READY

PROCESSING
→ FAILED

PENDING + PREVIEW_READY
→ APPROVED

PENDING + PREVIEW_READY
→ REJECTED
```

Do not introduce:

```text
PREVIEW_READY → PROCESSING

APPROVED → PENDING
APPROVED → REJECTED

REJECTED → PENDING
REJECTED → APPROVED
```

Re-review/reprocessing policy is out of scope.

---

# 22. Frozen D-062 — Document Approval

Use existing approve route if present; otherwise add equivalent:

```text
POST /api/v1/admin/documents/{document_id}/approve
```

Approval transaction:

```text
BEGIN
lock Document

require:
  review_status = PENDING
  processing_status = PREVIEW_READY
  valid pinned TransformationRun

set:
  review_status = APPROVED
  approved_by
  approved_at

COMMIT
```

Only AFTER approval commit:

```text
exact pinned TransformedArtifactRef
→ create/reuse KnowledgeSource(DOCUMENT)
→ allocate NEW PROCESSING KnowledgeVersion
→ build_chunks()
```

Success:

```text
Document = APPROVED
KnowledgeVersion = PROCESSING
Chunks complete
```

No embedding.

No activation.

---

# 23. Approval Build Failure Freeze

If downstream knowledge build fails after approval:

```text
Document remains APPROVED
new KnowledgeVersion:
PROCESSING → FAILED

older ACTIVE version unchanged
```

Return safe:

```text
KNOWLEDGE_BUILD_FAILED
```

Do not rollback human approval to PENDING.

Human review decision and processing result are separate lifecycles.

---

# 24. Duplicate Approval Freeze

If:

```text
Document.review_status = APPROVED
```

and approve is called again:

```text
→ 409 DOCUMENT_ALREADY_APPROVED
```

Do not:

```text
create another version
rerun Chunking
treat approve as retry
```

---

# 25. Document Knowledge Retry Freeze

Add explicit action equivalent to:

```text
POST /api/v1/admin/documents/{document_id}/knowledge/retry
```

Require:

```text
review_status = APPROVED
valid pinned TransformationRun
no PROCESSING KnowledgeVersion exists
```

Then:

```text
reuse same KnowledgeSource
→ NEW PROCESSING KnowledgeVersion
→ build_chunks(
     exact pinned approved TransformedArtifactRef,
     new version id
   )
```

Do not rerun:

```text
parse
clean
transform
```

Do not reuse FAILED/SUPERSEDED version.

---

# 26. Document Rejection Freeze

Use/add equivalent:

```text
POST /api/v1/admin/documents/{document_id}/reject
```

Require:

```text
review_status = PENDING
processing_status = PREVIEW_READY
valid pinned review artifact
```

Commit:

```text
review_status = REJECTED
```

Then stop.

Do not create:

```text
KnowledgeSource
KnowledgeVersion
Chunk
Embedding
```

Do not delete upstream artifacts.

Pointer remains unchanged.

`REJECTED` is terminal in Step 5.6.

---

# 27. Frozen D-063 — Lesson Publish Boundary

Existing Lesson publish business transaction must commit first:

```text
Lesson
DRAFT
→ PUBLISHED
→ COMMIT
```

Only after the publish function returns from committed state may ingestion start.

Do not call ingestion inside the publish transaction.

If ingestion later fails:

```text
Lesson remains PUBLISHED
```

Do not revert to DRAFT.

---

# 28. Lesson Post-Commit Trigger Freeze

Existing route:

```text
POST /api/v1/admin/lessons/{lesson_id}/publish
```

continues to execute the accepted curriculum publish service.

After committed publish returns:

```text
IngestionOrchestrator.process_published_lesson(...)
```

No ingestion inside curriculum transaction.

Do not redesign the curriculum domain.

---

# 29. Lesson Durable Claim Freeze

At start of every Lesson ingestion attempt:

```text
BEGIN
lock Lesson
→ require PUBLISHED

create/reuse KnowledgeSource(LESSON)
→ lock KnowledgeSource

reject if PROCESSING KnowledgeVersion exists

create NEW KnowledgeVersion(PROCESSING)

COMMIT
```

Only after durable claim commit:

```text
Raw Lesson Snapshot
→ Parse
→ Transform
→ Chunk into exact claimed version
```

KnowledgeVersion represents:

```text
one knowledge-build attempt
```

This claim protects the whole long Lesson pipeline without a long transaction.

---

# 30. Lesson Successful Flow

```text
PUBLISHED Lesson
→ PROCESSING KnowledgeVersion claim
→ create_lesson_snapshot()
→ RawArtifactRef
→ parse_raw_artifact()
→ ParsedArtifactRef
→ transform_parsed_artifact()
→ TransformedArtifactRef
→ build_chunks(exact claimed version)
→ complete Chunks
→ version remains PROCESSING
```

No human review gate.

No activation.

---

# 31. Lesson Failure Freeze

Any stage failure after claim:

```text
KnowledgeVersion
PROCESSING → FAILED
```

Lesson remains:

```text
PUBLISHED
```

Older ACTIVE version remains unchanged.

Stage fail-fast:

```text
snapshot failure
→ no parse/transform/chunk

parse failure
→ no transform/chunk

transform failure
→ no chunk

chunk failure
→ version FAILED
```

Return safe:

```text
KNOWLEDGE_BUILD_FAILED
```

Do not expose stage internals.

---

# 32. Lesson Retry Freeze

Add explicit action equivalent to:

```text
POST /api/v1/admin/lessons/{lesson_id}/knowledge/retry
```

Require:

```text
Lesson = PUBLISHED
no PROCESSING KnowledgeVersion exists
```

Retry:

```text
reuse KnowledgeSource
→ NEW PROCESSING KnowledgeVersion
→ Raw Snapshot
→ Parse
→ Transform
→ Chunk
```

Do not reuse FAILED/SUPERSEDED version.

Do not republish.

No automatic retry.

---

# 33. Repeated Lesson Publish Freeze

Preserve existing curriculum invalid-transition behavior for an already-PUBLISHED Lesson.

Repeated publish:

```text
must not create another knowledge build
```

If knowledge build needs retry:

```text
use /knowledge/retry
```

---

# 34. KnowledgeVersion Failure Propagation

Step 5.5 intentionally does not mark failed versions.

Step 5.6 owns:

```text
try:
    build_chunks(...)
except:
    short transaction
    → lock newly-created version
    → if status == PROCESSING:
         status = FAILED
    → commit
    → surface KNOWLEDGE_BUILD_FAILED
```

The same failure propagation applies to Lesson failures after durable claim, including snapshot/parse/transform before Chunking.

If failure-state persistence itself fails:

```text
safe structured log
```

Do not expose raw DB exception.

Do not modify an older ACTIVE version.

---

# 35. Exact Artifact Ref Freeze

Use exact refs end-to-end.

Document process:

```text
RawArtifactRef
→ exact ParsedArtifactRef
→ exact TransformedArtifactRef
```

Document later preview/approval:

```text
pinned TransformationRun
→ exact TransformedArtifactRef
```

Lesson:

```text
Raw Snapshot ref
→ Parsed ref
→ Transformed ref
→ exact claimed KnowledgeVersion for Chunking
```

No latest/current semantics.

---

# 36. Transaction Boundary Freeze

No giant pipeline transaction.

Use:

```text
claim
→ short COMMIT

stage work
→ stage-owned short commits

source/version allocation
→ short COMMIT

Chunking
→ Step-5.5 atomic transaction

failure propagation
→ short COMMIT
```

Never keep transaction open through:

```text
file I/O
PDF/DOCX parse
transformation
Chunk planning
```

Specific required ordering:

```text
Document process claim commits before parse

Document approval commits before knowledge build

Lesson publish commits before ingestion

Lesson PROCESSING version claim commits before Raw Snapshot
```

---

# 37. Admin API Freeze

Use use-case-oriented routes only.

Required equivalents:

```text
POST /api/v1/admin/documents/{id}/process
GET  /api/v1/admin/documents/{id}/preview
POST /api/v1/admin/documents/{id}/approve
POST /api/v1/admin/documents/{id}/reject
POST /api/v1/admin/documents/{id}/knowledge/retry

existing:
POST /api/v1/admin/lessons/{id}/publish

new:
POST /api/v1/admin/lessons/{id}/knowledge/retry
```

Follow actual accepted route conventions.

Do not expose:

```text
POST /parse
POST /transform
POST /chunk
```

Preserve Admin authorization dependencies.

---

# 38. Route / Service Boundary

Router:

```text
auth
request/path validation
call application use case
return safe response
```

Application/admin/curriculum service:

```text
business-state transaction where appropriate
```

IngestionOrchestrator:

```text
pipeline sequencing
claims
source/version allocation
stage delegation
failure propagation
```

Stage services:

```text
actual parse/transform/chunk work
```

Do not put pipeline algorithms in HTTP routes.

---

# 39. Error Contract Freeze

Freeze orchestration/business codes:

```text
DOCUMENT_NOT_PREVIEW_READY
DOCUMENT_ALREADY_APPROVED
PROCESSING_ALREADY_IN_PROGRESS
INVALID_SOURCE_STATE
KNOWLEDGE_BUILD_FAILED
INGESTION_PROCESSING_FAILED
```

HTTP/application semantics:

```text
DOCUMENT_NOT_PREVIEW_READY
→ 409

DOCUMENT_ALREADY_APPROVED
→ 409

PROCESSING_ALREADY_IN_PROGRESS
→ 409

INVALID_SOURCE_STATE
→ 409

KNOWLEDGE_BUILD_FAILED
→ 500

INGESTION_PROCESSING_FAILED
→ 500
```

Reuse stage error codes internally where appropriate.

Do not expose:

```text
raw DB errors
filesystem paths
tracebacks
unsafe nested exception text
```

---

# 40. Structured Logging Freeze

Use existing Python logging only.

No new observability dependency.

Structured equivalents:

```text
source_id
source_type
stage
status
knowledge_version_id optional
error_code optional
duration_ms
```

Stages:

```text
raw
parse
transform
chunk
review
```

Do not log raw content, secrets, credentials, or internal absolute paths.

---

# 41. Repository Boundary

Add only persistence/locking methods needed for orchestration.

Likely equivalents:

```text
get_document_for_update
get_transformation_run
get_pinned_review_run

get_or_create_knowledge_source
get_knowledge_source_for_update

find_processing_version
allocate_processing_version
get_knowledge_version_for_update
mark_knowledge_version_failed
```

Repository must not own pipeline sequencing.

---

# 42. KnowledgeSource Concurrent Create Behavior

For initial source creation race:

```text
attempt create
→ expected unique conflict
→ rollback/savepoint according to repository convention
→ reread existing logical source
→ validate source identity
→ reuse
```

Do not swallow unrelated integrity errors.

Do not create duplicate rows.

---

# 43. Version Allocation Behavior

Inside one short transaction:

```text
lock KnowledgeSource

if PROCESSING exists:
    PROCESSING_ALREADY_IN_PROGRESS

next_version =
    MAX(version_number) + 1

insert PROCESSING version
flush
commit
```

The `MAX()` is safe only because the source row is locked and DB uniqueness remains.

No unbounded retry loop.

---

# 44. Manual Retry Freeze

Supported manual retry boundaries:

```text
Document FAILED pre-review
→ POST /documents/{id}/process

Document APPROVED failed knowledge build
→ POST /documents/{id}/knowledge/retry

Lesson PUBLISHED failed knowledge build
→ POST /lessons/{id}/knowledge/retry
```

Do not implement:

```text
automatic retry
exponential backoff
scheduled retry
daemon
incremental dependency-aware retry
```

---

# 45. Step-5.7 Boundary

Do not decide:

```text
source changed?
parser version changed?
transformation version changed?
chunking version changed?
which old stage can be reused?
```

Step 5.6 explicit retries use the frozen flows.

Incremental invalidation/reprocessing belongs Step 5.7.

---

# 46. Dependencies

Expected:

```text
NO new runtime dependency
```

Reuse:

```text
FastAPI
Pydantic
SQLAlchemy
PostgreSQL
Alembic
FileStorage / LocalFileStorage
Python logging
pytest
uv
```

---

# 47. Likely Files — Modify

Likely modify:

```text
backend/app/database/models/document.py
backend/app/database/models/knowledge.py

backend/app/ingestion/repository.py
backend/app/ingestion/transformation/service.py
backend/app/ingestion/schemas.py

backend/app/admin/router.py
backend/app/admin/service.py

backend/tests/test_database.py
backend/tests/test_migration_preservation.py
```

Potential narrow Lesson publish integration:

```text
backend/app/curriculum/service.py
```

only if needed to keep the existing committed publish boundary clean.

Do not perform unrelated refactors.

---

# 48. Likely Files — Create

Likely create:

```text
backend/app/ingestion/orchestrator.py

backend/migrations/versions/
    0009_pipeline_orchestration_contract.py

backend/tests/
    test_step56_document_pipeline.py
    test_step56_lesson_pipeline.py
    test_step56_orchestration_concurrency.py

docs/data/
    step-5.6-pipeline-orchestration.md
```

Do not create:

```text
Embedding service
Vector service
queue/worker
generic pipeline-run model
frontend files
```

---

# 49. Test Freeze — Document Upload

Verify upload still:

```text
ends Raw Stored
processing_status = UPLOADED
review_status = PENDING
review pointer = NULL
```

Verify it does not call:

```text
parse
transform
chunk
```

---

# 50. Test Freeze — Document Process Success

Verify:

```text
PENDING + UPLOADED
→ PROCESSING claim
→ claim COMMIT
→ exact Raw ref
→ parse
→ exact Parsed ref
→ transform
→ exact Transformed ref
→ PREVIEW_READY
→ exact review run pinned
```

No Chunk before approval.

---

# 51. Test Freeze — Document Retry from FAILED

Given:

```text
PENDING + FAILED
```

process again:

```text
→ PROCESSING
→ clear pointer
→ parse
→ transform
→ PREVIEW_READY
→ new exact pinned successful run
```

Do not process:

```text
APPROVED
REJECTED
PREVIEW_READY
```

through this action.

---

# 52. Test Freeze — Parse Failure

Inject parse failure.

Verify:

```text
Document = FAILED
review pointer = NULL
transform not called
chunk not called
Raw survives
```

Surface:

```text
INGESTION_PROCESSING_FAILED
```

without unsafe nested details.

---

# 53. Test Freeze — Transform Failure

Inject transform failure.

Verify:

```text
Document = FAILED
review pointer = NULL
chunk not called
Raw/Parsed artifacts survive
```

No PREVIEW_READY.

---

# 54. Test Freeze — Concurrent Document Process

Two process triggers.

Prove row-lock claim behavior:

```text
first claims PROCESSING
second sees committed PROCESSING
→ PROCESSING_ALREADY_IN_PROGRESS
```

Do not accept a stale-precheck-only test.

---

# 55. Test Freeze — Review Pointer Atomicity

Prove successful transformation transaction commits together:

```text
TransformationRun = SUCCEEDED
Document = PREVIEW_READY
review_transformation_run_id = exact run.id
```

Inject final DB success persistence failure.

Verify no successful committed state:

```text
PREVIEW_READY + NULL pointer
```

Existing transformed-artifact orphan cleanup semantics must remain intact.

---

# 56. Test Freeze — Preview

Non-ready:

```text
→ DOCUMENT_NOT_PREVIEW_READY
```

Ready:

```text
pinned run
→ exact TransformedArtifactRef
→ exact TransformedDocument
```

Fixture with:

```text
successful run A = pinned
successful run B = newer
```

Preview must use A.

No Chunk/Raw preview.

---

# 57. Test Freeze — Approval Uses Previewed Artifact

Using same A/B fixture:

```text
Preview → A
Approve build → A
```

B must not be selected by recency.

This test is mandatory D-060 evidence.

---

# 58. Test Freeze — Approval Success

Given:

```text
PENDING + PREVIEW_READY
valid pinned run
```

Approve:

```text
approval commits
→ one/reused Document KnowledgeSource
→ NEW PROCESSING version
→ exact Step-5.5 build_chunks()
```

Success:

```text
Document = APPROVED
KnowledgeVersion = PROCESSING
Chunks complete
```

No embedding/activation.

---

# 59. Test Freeze — Approval Build Failure

Inject chunk/build failure after approval commit.

Verify:

```text
Document remains APPROVED
approved_by/approved_at remain
new version → FAILED
old ACTIVE untouched
```

Return:

```text
KNOWLEDGE_BUILD_FAILED
```

---

# 60. Test Freeze — Duplicate Approval

Given APPROVED:

```text
approve again
→ DOCUMENT_ALREADY_APPROVED
```

Verify:

```text
no new KnowledgeVersion
no Chunk build
no pointer change
```

---

# 61. Test Freeze — Document Knowledge Retry

Given:

```text
Document APPROVED
pinned approved artifact
prior FAILED build
no PROCESSING version
```

Retry:

```text
reuse KnowledgeSource
→ NEW PROCESSING version
→ chunk exact pinned artifact
```

Verify:

```text
no parse
no transform
```

---

# 62. Test Freeze — Rejection

Given:

```text
PENDING + PREVIEW_READY
```

reject:

```text
→ REJECTED
```

Verify:

```text
pointer retained
no new KnowledgeSource/version/chunks
artifacts retained
```

Reverse/repeat transition rejected.

---

# 63. Test Freeze — Document KnowledgeSource DB Identity

Runtime PostgreSQL:

```text
same non-null document_id
→ second KnowledgeSource rejected
```

Different documents allowed.

Lesson NULL document_id rows unaffected.

Existing Lesson uniqueness remains valid.

---

# 64. Test Freeze — Concurrent Source Creation

Race/repository test:

```text
same logical Document or Lesson
→ exactly one KnowledgeSource persists
```

Second path safely reuses the existing row or receives expected handled concurrency result.

Do not prove only via serial precheck.

---

# 65. Test Freeze — KnowledgeVersion Allocation

Fixture:

```text
v1 ACTIVE
v2 FAILED
v3 SUPERSEDED
```

new build:

```text
lock source
→ next = 4
→ v4 PROCESSING
```

Do not reuse historical version numbers.

Concurrency test must prove no duplicate next version.

---

# 66. Test Freeze — PROCESSING Unique Index

Runtime PostgreSQL:

```text
same source
+ PROCESSING
+ second PROCESSING
→ rejected
```

Allowed:

```text
ACTIVE + PROCESSING
```

for same source.

Historical FAILED/SUPERSEDED rows remain allowed.

---

# 67. Test Freeze — Application Processing Check

Repository/service allocation must:

```text
lock source
→ detect existing PROCESSING
→ PROCESSING_ALREADY_IN_PROGRESS
```

Do not rely only on catching the partial-index violation after insert.

---

# 68. Test Freeze — ACTIVE Protection

Fixture:

```text
v1 ACTIVE with chunks
v2 PROCESSING
```

Force v2 failure.

Verify:

```text
v1 ACTIVE unchanged
v1 Chunks unchanged
v2 FAILED
```

---

# 69. Test Freeze — Lesson DRAFT

Direct orchestration attempt for DRAFT:

```text
→ INVALID_SOURCE_STATE
```

No ingestion/build state created by invalid trigger.

---

# 70. Test Freeze — Lesson Publish Commit Boundary

Instrument publish/orchestration.

Prove ingestion runs only after committed:

```text
Lesson = PUBLISHED
```

Inject post-commit build failure.

Verify DB still shows:

```text
PUBLISHED
```

---

# 71. Test Freeze — Lesson Durable Claim

Before snapshot:

```text
PROCESSING KnowledgeVersion already committed
```

Test order with mock/spies and DB state.

If snapshot fails:

```text
claimed version exists
→ FAILED
```

---

# 72. Test Freeze — Lesson Successful Flow

Verify exact order:

```text
claim
→ snapshot
→ parse
→ transform
→ chunk exact claimed version
```

Success:

```text
Lesson = PUBLISHED
KnowledgeVersion = PROCESSING
Chunks complete
```

No activation.

---

# 73. Test Freeze — Lesson Stage Failures

Cover:

```text
snapshot failure
parse failure
transform failure
chunk failure
```

Each must produce:

```text
Lesson remains PUBLISHED
claimed version → FAILED
old ACTIVE untouched
no downstream stage after failure
```

---

# 74. Test Freeze — Concurrent Lesson Trigger

Two knowledge-build triggers:

```text
one PROCESSING claim succeeds
second → PROCESSING_ALREADY_IN_PROGRESS
```

Evidence must exercise row lock and/or DB partial index.

No duplicate KnowledgeSource.

---

# 75. Test Freeze — Lesson Retry

Given:

```text
Lesson PUBLISHED
prior build FAILED
no PROCESSING build
```

Retry:

```text
reuse source
→ NEW PROCESSING version
→ Snapshot → Parse → Transform → Chunk
```

Do not reuse FAILED/SUPERSEDED.

Do not republish.

---

# 76. Test Freeze — Repeated Lesson Publish

Preserve existing curriculum invalid-transition semantics.

Repeated publish must not create another knowledge build.

Knowledge retry must use dedicated retry action.

---

# 77. Test Freeze — Fail-Fast

Document:

```text
parse fail
→ no transform/chunk

transform fail
→ no chunk
```

Lesson:

```text
snapshot fail
→ no parse/transform/chunk

parse fail
→ no transform/chunk

transform fail
→ no chunk
```

Chunk failure:

```text
version FAILED
→ no embedding/activation
```

---

# 78. Test Freeze — Transaction Boundaries

Prove:

```text
Document claim committed before parse

Document approval committed before knowledge build

Lesson publish committed before ingestion

Lesson PROCESSING version claim committed before snapshot

Step-5.5 Chunking retains its own atomic transaction
```

Committed upstream state/artifacts survive downstream failure.

---

# 79. Test Freeze — Error Contract

Verify exact codes/statuses:

```text
DOCUMENT_NOT_PREVIEW_READY → 409
DOCUMENT_ALREADY_APPROVED → 409
PROCESSING_ALREADY_IN_PROGRESS → 409
INVALID_SOURCE_STATE → 409
KNOWLEDGE_BUILD_FAILED → 500
INGESTION_PROCESSING_FAILED → 500
```

No raw DB/filesystem/traceback text in client-safe errors.

---

# 80. Test Freeze — Structured Logging

Capture logs and verify equivalents:

```text
source_id
source_type
stage
status
duration_ms
```

and where applicable:

```text
knowledge_version_id
error_code
```

Cover success + failure.

No external observability dependency.

---

# 81. Test Freeze — Admin API

Verify:

```text
Admin authorization preserved
use-case routes only
```

No public endpoints:

```text
/parse
/transform
/chunk
```

---

# 82. Test Freeze — Migration 0009 + D-064

Migration verification must explicitly cover all four D-064 cases.

## Case 1 — Existing 0008 database

Given:

```text
current = 0008_chunking_contract
alembic_version.version_num = VARCHAR(32)
```

Run:

```text
upgrade head
```

Verify:

```text
current = 0009_pipeline_orchestration_contract
alembic_version.version_num = VARCHAR(64)
```

Verify all three D-061 Step-5.6 application-schema changes exist and legacy data survives.

This must work with no manual/preparatory SQL.

## Case 2 — Downgrade

From 0009 run:

```text
downgrade 0008_chunking_contract
```

Verify:

```text
current = 0008_chunking_contract
```

Verify Step-5.6 application schema is removed.

Verify intentionally:

```text
alembic_version.version_num = VARCHAR(64)
```

Legacy data must survive.

## Case 3 — Re-upgrade

From downgraded 0008 state with:

```text
alembic_version.version_num = VARCHAR(64)
```

run:

```text
upgrade head
```

Must PASS and return to:

```text
0009_pipeline_orchestration_contract
```

The migration must tolerate the control column already being wide enough.

## Case 4 — Fresh database

From:

```text
base
```

run:

```text
upgrade head
```

Must PASS without:

```text
manual SQL
preparation script
custom deployment step
custom Alembic startup hook
```

Verify final:

```text
current = 0009_pipeline_orchestration_contract
alembic_version.version_num = VARCHAR(64)
```

## Final Alembic verification

Run:

```text
alembic current
```

Expected:

```text
0009_pipeline_orchestration_contract
```

Run:

```text
alembic check
```

Expected:

```text
PASS
no pending upgrade operations
```

Do not rewrite old migrations.

---

# 83. Full Backend Regression

Run:

```text
uv run pytest
```

All required tests must pass.

Do not claim completion when required verification is blocked or fails.

Report unrelated warnings separately.

---

# 84. Step Note

Create:

```text
docs/data/step-5.6-pipeline-orchestration.md
```

Required sections:

```text
Objective
Why
Mental Model
Core Knowledge
Data Flow
Key Design Decisions
Reusable Approach
Common Mistakes
Definition of Done
Concepts Discovered
Tools Used
```

Mental model:

```text
business/source claim
→ commit
→ exact persisted stage ref
→ next accepted service
→ short durable transition
→ next stage
```

Document flow:

```text
Raw
→ Parse
→ Transform
→ pinned review artifact
→ human review
→ PROCESSING KnowledgeVersion
→ Chunk
```

Lesson flow:

```text
Publish COMMIT
→ PROCESSING KnowledgeVersion claim
→ Raw Snapshot
→ Parse
→ Transform
→ Chunk
```

---

# 85. Concepts Discovered Format

Use:

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|

Likely concepts if actually used:

```text
Pipeline Orchestration — DE
Stage Boundary — DE
Artifact Reference Chaining — DE
Business vs Processing State — DE
Durable Processing Claim — DE
KnowledgeSource Identity — DE
KnowledgeVersion Allocation — DE
Source-Level Concurrency — DE
Failure Propagation — DE
Fail-Fast Pipeline — DE
Manual Retry Boundary — DE
ACTIVE-Version Protection — DE
Short Transaction Boundary — BOTH
Partial Unique Index — DE
Row Locking — SYSTEM
Use-Case API — SYSTEM
Structured Logging — SYSTEM
```

Only record concepts actually used.

---

# 86. Tools Used Format

Use:

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|

Likely tools if actually used:

```text
FastAPI — SYSTEM
PostgreSQL — DE
SQLAlchemy — DE
Alembic — DE
Pydantic — SYSTEM
FileStorage / LocalFileStorage — DE
Python logging — SYSTEM
pytest — SYSTEM
uv — SYSTEM
```

No new runtime dependency expected.

---

# 87. Scope Guardrails

Do not implement:

```text
Embedding
EmbeddingProfile execution
Vector Storage
Vector Indexing
Retrieval
Filtering
Reranking
Prompt Construction
LLM Generation

KnowledgeVersion activation

Step 5.7 incremental/reprocessing logic
source-change detection
parser-version invalidation
transform-version invalidation
chunk-version invalidation

automatic retries
scheduler
worker
queue

Airflow
Prefect
Dagster
Celery
Kafka
Redis

generic IngestionRun
PipelineRun
StageRun

frontend redesign
observability platform
```

Step 5.6 ends at:

```text
KnowledgeVersion(PROCESSING)
+
complete persisted Chunk[]
```

---

# 88. Acceptance Criteria

Step 5.6 is acceptable only when all are true:

- [ ] Accepted Step 5.1–5.5 services are reused.
- [ ] No stage algorithm is duplicated in orchestration.
- [ ] `IngestionOrchestrator` exists.
- [ ] Exactly one migration `0009_pipeline_orchestration_contract` follows 0008.
- [ ] Revision ID remains exactly `0009_pipeline_orchestration_contract`.
- [ ] `down_revision` remains exactly `0008_chunking_contract`.
- [ ] Migration 0009 widens `alembic_version.version_num` from VARCHAR(32) to VARCHAR(64) at the beginning of `upgrade()` when needed.
- [ ] Alembic width compatibility is handled before D-061 application-schema changes.
- [ ] No 0009a/bootstrap/preparatory migration exists.
- [ ] No manual/out-of-band SQL or deployment hook handles revision width.
- [ ] Downgrade removes only Step-5.6 application-schema deltas.
- [ ] Downgrade intentionally leaves `alembic_version.version_num` as VARCHAR(64).
- [ ] Existing 0008/VARCHAR(32) → head passes.
- [ ] 0009 → 0008 downgrade passes with width remaining 64.
- [ ] Re-upgrade from 0008/VARCHAR(64) passes.
- [ ] Fresh base → head passes without preparation.
- [ ] Migrations 0001–0008 are unchanged.
- [ ] `Document.review_transformation_run_id` exists.
- [ ] Pointer FK uses `ON DELETE SET NULL`.
- [ ] Transform success atomically persists SUCCEEDED + PREVIEW_READY + review pointer.
- [ ] Process/retry claim clears pointer.
- [ ] Failed process leaves pointer NULL.
- [ ] Preview uses exact pinned run.
- [ ] Approval chunks exact pinned run.
- [ ] No latest/current TransformationRun lookup exists.
- [ ] One Document maps to one KnowledgeSource at DB boundary.
- [ ] Existing Lesson source uniqueness is preserved.
- [ ] One PROCESSING KnowledgeVersion/source is DB-enforced.
- [ ] Existing ACTIVE uniqueness is preserved.
- [ ] Existing source/version uniqueness is preserved.
- [ ] Version allocation locks KnowledgeSource.
- [ ] `MAX(version)+1` occurs only under source lock.
- [ ] FAILED/SUPERSEDED versions are not reused.
- [ ] ACTIVE version is not modified.
- [ ] Upload remains Raw Stored only.
- [ ] Document process supports UPLOADED and FAILED retry.
- [ ] Concurrent process is rejected.
- [ ] No Chunk before Document approval.
- [ ] Preview returns exact TransformedDocument.
- [ ] Approval accepts only PENDING + PREVIEW_READY.
- [ ] Approval commits before build.
- [ ] Build failure does not roll back APPROVED.
- [ ] Duplicate approval returns `DOCUMENT_ALREADY_APPROVED`.
- [ ] Document knowledge retry uses exact pinned approved artifact.
- [ ] Document knowledge retry does not parse/transform.
- [ ] Rejection creates no knowledge build.
- [ ] REJECTED is terminal.
- [ ] Lesson publish commits before ingestion.
- [ ] DRAFT Lesson cannot ingest.
- [ ] Lesson durable PROCESSING claim commits before snapshot.
- [ ] Lesson flows Snapshot → Parse → Transform → Chunk.
- [ ] Lesson failure leaves PUBLISHED.
- [ ] Lesson failure marks claimed version FAILED.
- [ ] Lesson retry creates a NEW version.
- [ ] Repeated publish does not create another build.
- [ ] One active Lesson build/source is enforced.
- [ ] Chunking failure marks new version FAILED.
- [ ] Successful Chunking leaves version PROCESSING.
- [ ] Old ACTIVE remains untouched.
- [ ] Fail-fast behavior is tested.
- [ ] No giant pipeline transaction exists.
- [ ] Exact persisted artifact refs are passed stage-to-stage.
- [ ] No generic orchestration-run table exists.
- [ ] Admin routes remain use-case oriented and authorized.
- [ ] Exact orchestration error contract is implemented.
- [ ] Structured stage logging exists.
- [ ] No new runtime dependency was added.
- [ ] No Embedding/Vector/Retrieval behavior was added.
- [ ] No KnowledgeVersion activation was added.
- [ ] No Step-5.7 invalidation logic was added.
- [ ] Document pipeline tests pass.
- [ ] Lesson pipeline tests pass.
- [ ] Concurrency tests pass.
- [ ] PostgreSQL runtime invariant tests pass.
- [ ] Migration upgrade/downgrade tests pass.
- [ ] Full backend regression passes.
- [ ] Alembic current/check pass.
- [ ] Step Note is complete.
- [ ] Concepts/Tools tables use project format.
- [ ] No scope creep.

---

# 89. Suggested Verification Commands

Focused Step-5.6:

```text
uv run pytest \
  tests/test_step56_document_pipeline.py \
  tests/test_step56_lesson_pipeline.py \
  tests/test_step56_orchestration_concurrency.py \
  -vv
```

Database/migration:

```text
uv run pytest \
  tests/test_database.py \
  tests/test_migration_preservation.py \
  -vv
```

Full backend:

```text
uv run pytest
```

Alembic:

```text
uv run alembic current
uv run alembic check
```

Use dedicated test PostgreSQL configuration.

---

# 90. Codex Constraints

Codex must:

```text
inspect current accepted Step-5.5 implementation before editing
reuse accepted stage services
preserve D-060 / D-061 / D-062 / D-063 / D-064
follow current router/service/repository/session/error/logging conventions
use short transactions
use row locks for claims/allocation
preserve exact artifact references
preserve Step-5.5 atomic Chunking
preserve old ACTIVE versions
```

Codex must NOT:

```text
change D-060 / D-061 / D-062 / D-063 / D-064
shorten 0009_pipeline_orchestration_contract
change down_revision away from 0008_chunking_contract
modify migrations 0001–0008
create 0009a/bootstrap migration
create a second preparatory migration
use manual/out-of-band SQL for revision width
mutate alembic_version from deployment scripts
add custom Alembic startup hooks for this issue
select latest TransformationRun
add generic pipeline-run state
activate KnowledgeVersion
add embeddings
add vectors
add retrieval
add Step-5.7 invalidation
add automatic retry
add worker/queue/workflow framework
add runtime dependency without reporting blocker
perform unrelated refactors
```

If actual accepted repository materially contradicts this task:

```text
STOP
→ report exact contradiction
```

Do not silently choose new architecture.

---

# 91. Required Codex Completion Handoff

Return:

```text
Step:
Status:

What was done:
- ...

D-060 preserved:
- ...

D-061 preserved:
- ...

D-062 preserved:
- ...

D-063 preserved:
- ...

D-064 incorporated:
- exact 0009 revision preserved
- exact down_revision preserved
- upgrade width behavior
- downgrade width behavior
- existing-0008 migration test
- downgrade migration test
- re-upgrade migration test
- fresh base→head test
- Alembic current/check

Files/components changed:
- ...

Orchestrator boundary:
- ...

Stage-service reuse:
- ...

Migration 0009:
- exact revision / down_revision
- D-061 application-schema delta
- D-064 Alembic control-column widening
- intentional downgrade width asymmetry

Review-artifact pointer:
- ...

Document-source uniqueness:
- ...

PROCESSING-version uniqueness:
- ...

Version allocation:
- ...

Document upload:
- ...

Document process:
- ...

Document preview:
- ...

Document approval:
- ...

Document rejection:
- ...

Document processing retry:
- ...

Document knowledge retry:
- ...

Duplicate approval:
- ...

Lesson publish:
- ...

Lesson post-commit trigger:
- ...

Lesson durable claim:
- ...

Lesson failure:
- ...

Lesson retry:
- ...

KnowledgeSource identity:
- ...

KnowledgeVersion lifecycle:
- ...

ACTIVE protection:
- ...

Artifact-reference flow:
- ...

Fail-fast behavior:
- ...

Transaction boundaries:
- ...

Failure propagation:
- ...

Admin API:
- ...

Error contract:
- ...

Structured logging:
- ...

Dependencies:
- ...

Concepts added:
- ...

Tools added:
- ...

Tests / verification:
- document pipeline
- lesson pipeline
- concurrency
- DB/schema
- migration
- full backend
- Alembic current/check

Problems / risks:
- ...

Decisions needed:
- ...

Recommended next action:
- ...
```

Do not claim COMPLETE if required tests were blocked or failed.

---

# 92. Definition of Done

Ready for Data Engineering specialist review only when:

```text
requirements satisfied
D-060 preserved
D-061 preserved
D-062 preserved
D-063 preserved
D-064 incorporated

migration 0009 verified
exact 0009 revision preserved
exact down_revision preserved
existing 0008 VARCHAR(32) → head PASS
alembic_version widened to VARCHAR(64)
0009 → 0008 downgrade PASS
downgrade leaves VARCHAR(64)
re-upgrade from 0008/VARCHAR(64) PASS
fresh base → head PASS

exact review artifact pinning verified
Preview/Approval same-artifact identity verified

Document source uniqueness verified
PROCESSING-version uniqueness verified
race-safe version allocation verified

Document lifecycle flows verified
Lesson lifecycle flows verified

KnowledgeVersion failure propagation verified
ACTIVE protection verified

exact artifact refs verified
fail-fast verified
short transaction boundaries verified

error contract verified
structured logging verified

no new dependency
no Embedding
no activation
no Step 5.7
no generic orchestration-run table

focused tests pass
DB/migration tests pass
full backend regression passes
Alembic current/check pass

Step Note complete
Concepts/Tools correct
no scope creep
```

After Codex completes:

```text
Data Engineering Specialist
→ independent actual-code review
→ PM acceptance
```

Do not begin Step 5.7 automatically.
