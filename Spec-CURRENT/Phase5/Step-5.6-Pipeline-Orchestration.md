# Step 5.6 — Pipeline Orchestration

## Goal

Implement the V0 ingestion orchestration layer that connects the already-defined ingestion stages into safe end-to-end workflows for both uploaded Documents and Published Lessons.

Step 5.6 must orchestrate:

```text
Raw
→ Parse/Clean
→ Transform
→ Chunk
```

and stop before:

```text
Embedding
Vector Storage
Retrieval
```

The orchestrator must manage sequencing, gates, failure propagation, retry boundaries, and KnowledgeVersion state without duplicating stage-specific implementation.

Do not introduce production workflow infrastructure such as Airflow, Prefect, Dagster, Celery, Kafka, or Redis queues in V0.

---

# Architectural Boundary

Create or preserve an application-service boundary equivalent to:

```text
IngestionOrchestrator
```

The orchestrator decides:

- which stage runs next;
- whether prerequisites are satisfied;
- whether processing should stop;
- when KnowledgeSource/KnowledgeVersion objects are created;
- how failures update processing state;
- whether retries are allowed;
- when downstream stages must not run.

The orchestrator must not implement:

```text
PDF parsing
DOCX parsing
text cleaning
document transformation algorithms
chunk splitting algorithms
file storage internals
embedding
retrieval
```

Delegate actual work to stage services.

Equivalent dependency shape:

```text
IngestionOrchestrator
├── RawIngestionService
├── ParsingService
├── TransformationService
└── ChunkingService
```

Exact names may follow the codebase.

---

# V0 Execution Model

Keep orchestration inside the existing FastAPI modular monolith.

Do not add:

```text
Airflow
Prefect
Dagster
Celery
Kafka
Redis Queue
dedicated orchestration microservice
```

for this step.

V0 processing may remain synchronous because current source volume is small.

Do not use FastAPI `BackgroundTasks` as a substitute for a durable job system for critical knowledge processing.

If production workload later requires durable asynchronous processing, that is a later architecture decision.

---

# Pipeline Scope

Step 5.6 ends after a valid Chunk set has been persisted for a `PROCESSING` KnowledgeVersion.

Result:

```text
KnowledgeVersion
status = PROCESSING

Chunk[]
= complete
```

Do not:

```text
generate embeddings
activate KnowledgeVersion
index vectors
```

in Step 5.6.

Step 6.1 continues from persisted Chunk records.

---

# Two Source Workflows

Support two source paths:

```text
DOCUMENT
LESSON
```

They share stage services and the same KnowledgeSource/KnowledgeVersion/Chunk model but differ in lifecycle gates.

Do not create separate incompatible pipelines.

---

# Document Workflow — Overview

Document processing is intentionally split around Admin Review.

Required V0 flow:

```text
Upload
↓
Raw Stored
↓
Admin Process
↓
Parse/Clean
↓
Transform
↓
PREVIEW_READY
↓
Admin Preview
↓
Approve / Reject
```

If approved:

```text
Approve
↓
create/reuse KnowledgeSource(DOCUMENT)
↓
create KnowledgeVersion(PROCESSING)
↓
Chunk
↓
wait for Step 6.1
```

If rejected:

```text
Reject
↓
no knowledge build
```

Admin must review the transformed document, not Chunk output.

---

# Document Upload Boundary

Preserve Step 5.2 behavior.

Document upload request ends at:

```text
Source
→ Raw Stored
```

Do not automatically parse/transform inside the upload endpoint.

The upload endpoint should return after the raw artifact and required raw metadata are safely persisted.

---

# Document Process Action

Provide an admin action equivalent to:

```http
POST /api/v1/admin/documents/{document_id}/process
```

Exact route may follow existing Admin API naming conventions.

This action orchestrates:

```text
Raw Document
→ Parse/Clean
→ Transform
→ PREVIEW_READY
```

It does not create Chunks before approval.

---

# Synchronous Document Processing

V0 may execute document processing synchronously:

```text
POST /process
→ parse
→ clean
→ transform
→ persist transformed artifact
→ return status/result
```

Do not add background queues solely for this step.

The operation must remain safe to retry manually after failure.

---

# Processing State vs Review State

Keep machine-processing state separate from human-review state.

Recommended logical processing status:

```text
UPLOADED
PROCESSING
PREVIEW_READY
FAILED
```

Recommended review status:

```text
PENDING
APPROVED
REJECTED
```

Do not combine machine state and human-review state into one confusing enum.

If the current model already provides equivalent fields/statuses, reuse them.

---

# Processing Status Semantics

```text
UPLOADED
→ raw artifact exists

PROCESSING
→ parse/clean/transform currently running

PREVIEW_READY
→ valid TransformedDocument exists and is reviewable

FAILED
→ machine processing failed
```

Do not mark `PREVIEW_READY` until transformed artifact schema validation has succeeded.

---

# Review Status Semantics

```text
PENDING
→ no final Admin decision

APPROVED
→ Admin accepted transformed content for internal knowledge

REJECTED
→ Admin rejected it
```

A raw uploaded file is not implicitly approved.

A machine-successful parse is not implicitly approved.

---

# Approval Gate

Admin approval is allowed only when:

```text
processing_status = PREVIEW_READY
AND
valid TransformedDocument exists
```

Reject attempts to approve:

```text
UPLOADED
PROCESSING
FAILED
```

documents.

Use a stable business error.

---

# Document Approval Workflow

Approval must orchestrate:

```text
validate PREVIEW_READY
↓
set review_status = APPROVED
↓
create/reuse KnowledgeSource(DOCUMENT)
↓
create new KnowledgeVersion(PROCESSING)
↓
run Chunking
↓
persist complete Chunk set
↓
leave KnowledgeVersion PROCESSING
```

Do not embed.

Do not activate.

A fully chunked version is still incomplete until Phase 6 embedding succeeds.

---

# Document Rejection Workflow

Reject:

```text
review_status = REJECTED
```

Then stop.

Do not create:

```text
KnowledgeVersion
Chunk
Embedding
ACTIVE retrieval knowledge
```

for the rejected document.

Preserve existing raw/parsed/transformed artifacts according to the current retention policy.

---

# Admin Preview

Admin Preview should read from:

```text
TransformedDocument
```

not from:

```text
raw file only
Chunk[]
```

The preview representation must be cleaned, normalized, source-traceable, and pre-chunking.

The full frontend Preview UI may remain minimal if not already implemented, but backend orchestration must expose/reuse enough data for review.

---

# Lesson Workflow — Overview

A Published Lesson is already approved product content.

When Lesson publishing succeeds:

```text
Lesson PUBLISHED
↓
processPublishedLesson(...)
↓
Raw Lesson Snapshot
↓
Parse/Clean
↓
Transform
↓
create/reuse KnowledgeSource(LESSON)
↓
create KnowledgeVersion(PROCESSING)
↓
Chunk
↓
wait for Step 6.1
```

No separate human document-review gate is required for a Published Lesson.

---

# Lesson Publish Trigger

Wire successful Lesson publish to the ingestion orchestrator after the publish transaction commits.

Equivalent:

```text
commit Lesson PUBLISHED
↓
processPublishedLesson(...)
```

Do not build knowledge from DRAFT Lesson content.

Do not start ingestion before the publish operation has committed.

---

# Lesson Publish Failure Isolation

Knowledge ingestion failure must not roll back the business publishing decision.

Required behavior:

```text
Lesson publish
→ COMMIT

then ingestion
→ success OR failure
```

If ingestion fails:

```text
Lesson remains PUBLISHED
knowledge build records failure
retry remains possible
```

Do not revert Lesson to DRAFT solely because RAG preprocessing failed.

Business content lifecycle and knowledge-processing lifecycle are separate concerns.

---

# Synchronous Lesson Processing

V0 may process Published Lesson ingestion synchronously after publish commit.

Because Lesson source data is already structured, this should be relatively lightweight.

Do not introduce a queue solely for Lesson ingestion.

If latency becomes unacceptable later, orchestration implementation may move behind a durable worker without changing the application-level workflow contract.

---

# KnowledgeSource Identity

Preserve one logical KnowledgeSource per logical source.

```text
1 Document
→ 1 KnowledgeSource

1 Lesson
→ 1 KnowledgeSource
```

Do not create a new KnowledgeSource each time the same source is rebuilt.

Reprocessing/rebuild creates a new:

```text
KnowledgeVersion
```

under the existing source.

---

# KnowledgeVersion Creation

A new knowledge build creates:

```text
KnowledgeVersion
status = PROCESSING
```

Do not mutate an existing ACTIVE version.

Do not reuse an old FAILED/SUPERSEDED version as the new build.

The exact version-number allocation must follow current repository/database conventions and remain race-safe.

---

# KnowledgeVersion Failure

If any post-version-creation stage fails, such as Chunking:

```text
KnowledgeVersion
PROCESSING
→ FAILED
```

Do not expose partial Chunks as active retrieval knowledge.

If an older ACTIVE version exists, it remains ACTIVE.

---

# No Activation in Step 5.6

Successful chunking results in:

```text
KnowledgeVersion = PROCESSING
Chunks = complete
```

not:

```text
KnowledgeVersion = ACTIVE
```

Activation occurs only after required embeddings are successfully created in Phase 6.

Do not bypass that gate.

---

# Intermediate Artifact References

Orchestration should pass stable artifact identities/references between stages.

Preferred conceptual flow:

```text
RawArtifactRef
→ ParsingService
→ ParsedArtifactRef
→ TransformationService
→ TransformedArtifactRef
→ ChunkingService
```

Do not depend on one giant in-memory Python object that must survive the entire pipeline.

Persisted stage outputs enable:

- debugging;
- retries;
- restartability;
- stage isolation.

---

# Fail-fast Dependency Rules

A downstream stage must not run if its prerequisite stage failed.

Examples:

```text
Parsing FAILED
→ Transformation NOT RUN
→ Chunking NOT RUN
```

```text
Transformation FAILED
→ Chunking NOT RUN
```

Do not attempt to create partial downstream artifacts.

---

# Retry Policy in Step 5.6

Support manual safe retry only.

Examples:

```text
Document FAILED
→ Admin retries processing
```

```text
Lesson knowledge build failed
→ Admin/system retry action
```

Do not implement:

```text
automatic exponential retry
scheduled retry
retry daemon
dependency-aware incremental rerun
```

These belong to later reprocessing/operations work.

---

# Concurrency Rule

V0 allows at most one active processing operation per source.

Equivalent:

```text
same Document/Lesson
AND processing already active
→ reject second trigger
```

Use a stable error equivalent to:

```text
PROCESSING_ALREADY_IN_PROGRESS
```

Prevent:

- duplicate KnowledgeVersions;
- duplicate Chunk builds;
- artifact races;
- conflicting state transitions.

Use database constraints/locking/transaction logic appropriate to the existing architecture.

---

# Transaction Boundaries

Do not wrap the entire ingestion pipeline in one giant database transaction.

Each stage/service should persist state with short transactions.

Equivalent:

```text
stage work
→ short transaction
→ commit stage result
```

The orchestrator coordinates committed stage outputs.

Do not keep a transaction open while performing:

- file I/O;
- PDF/DOCX parsing;
- long transformations;
- other slow processing.

---

# Chunk Persistence Failure

If Chunking fails after a KnowledgeVersion exists:

```text
PROCESSING
→ FAILED
```

Chunking itself should preserve its atomic-persistence rules from Step 5.5.

Do not leave a half-valid Chunk set and then treat the version as successful.

---

# No Generic IngestionRun Table in V0

Do not introduce a generic:

```text
IngestionRun
PipelineRun
StageRun
```

entity solely for this step.

Current V0 state can be represented by:

- Document processing/review status;
- persisted intermediate artifacts;
- KnowledgeVersion status;
- structured logs.

A durable execution-history model may be added later if monitoring/orchestration requirements justify it.

---

# Internal Stages Are Not Public Admin APIs

Do not expose normal frontend endpoints such as:

```text
POST /parse
POST /transform
POST /chunk
```

as the primary Admin workflow.

Admin-facing actions should be use-case oriented:

```text
upload document
process document
preview document
approve document
reject document
retry document processing
publish lesson
retry lesson knowledge build
```

Internal stage services should remain directly unit/integration testable.

---

# Suggested Admin Actions

Equivalent actions may include:

```text
POST /api/v1/admin/documents
POST /api/v1/admin/documents/{id}/process
GET  /api/v1/admin/documents/{id}/preview
POST /api/v1/admin/documents/{id}/approve
POST /api/v1/admin/documents/{id}/reject
POST /api/v1/admin/documents/{id}/retry
```

and Lesson behavior through the existing Lesson publish API plus an optional retry action.

Do not invent duplicate endpoints if current Admin APIs already provide equivalent use cases.

---

# Orchestrator Responsibilities

The orchestrator may:

- validate source state;
- enforce lifecycle gates;
- select the next stage;
- call stage services;
- persist/update processing state;
- create/reuse KnowledgeSource;
- create KnowledgeVersion;
- mark failed version state;
- stop downstream execution;
- enforce retry/concurrency rules;
- emit structured logs.

The orchestrator must not:

- parse PDFs itself;
- implement cleaning rules;
- create canonical block formatting logic;
- implement text splitting;
- calculate embeddings;
- run retrieval;
- contain frontend behavior.

---

# ETL Mental Model

Map this project to classic ETL as:

```text
Source
→ Raw Storage
→ Extract
→ Transform
→ Load
```

Where:

```text
EXTRACT
= Parse/Clean raw artifacts

TRANSFORM
= canonical TransformedDocument
  + deterministic Chunk plan

LOAD
= persist validated Chunk records
  to PostgreSQL
```

Do not rename all internal services merely to match ETL terminology.

This is a conceptual Data Engineering model.

---

# Structured Logging

Add structured logs sufficient to diagnose stage failures.

Include fields equivalent to:

```text
source_id
source_type
stage
status
knowledge_version_id optional
error_code optional
duration_ms
```

Useful stages:

```text
raw
parse
transform
chunk
review
```

Do not introduce a metrics/observability platform solely for this step.

Full monitoring belongs to later phases.

---

# Suggested Business Errors

Use the current normalized API error contract.

Stable errors may include equivalents of:

```text
DOCUMENT_NOT_PREVIEW_READY
DOCUMENT_ALREADY_APPROVED
PROCESSING_ALREADY_IN_PROGRESS
INGESTION_PROCESSING_FAILED
KNOWLEDGE_BUILD_FAILED
INVALID_SOURCE_STATE
KNOWLEDGE_VERSION_NOT_PROCESSING
```

Reuse existing codes if equivalent codes already exist.

Do not expose internal stack traces to clients.

---

# State Transition Validation

Enforce valid transitions.

Examples:

```text
UPLOADED
→ PROCESSING
→ PREVIEW_READY
```

or:

```text
UPLOADED
→ PROCESSING
→ FAILED
```

Retry:

```text
FAILED
→ PROCESSING
```

Review:

```text
PENDING
→ APPROVED
```

or:

```text
PENDING
→ REJECTED
```

Do not allow arbitrary client-controlled state mutation.

State transitions belong in backend services.

---

# Document Approval Idempotency

Approval should be safe against duplicate requests.

If the same already-approved Document receives the same approval request again:

- do not create duplicate KnowledgeSources;
- do not create duplicate concurrent processing versions accidentally;
- either return current state idempotently or a stable business error according to existing API style.

Prefer behavior that cannot duplicate the knowledge build.

---

# Lesson Publish Idempotency

If the existing Lesson publish action is idempotent, preserve that behavior.

Do not trigger duplicate concurrent ingestion when the same already-published Lesson publish action is repeated.

The orchestration layer must check active processing state before starting a new build.

---

# Rebuild Boundary

Do not design the full "when should a source be rebuilt?" policy in Step 5.6.

This step only needs a safe operation to build a version when explicitly requested/triggered.

Questions such as:

```text
document changed?
chunking version changed?
parser changed?
embedding model changed?
which stage can be skipped?
```

belong to Step 5.7.

---

# Tests

Add focused tests covering at least:

## Document upload/process

- upload stores Raw and does not parse automatically;
- process action transitions UPLOADED → PROCESSING;
- successful parse/transform produces PREVIEW_READY;
- processing failure produces FAILED;
- parsing failure prevents Transformation;
- transformation failure prevents later stages;
- failed processing remains retryable.

## Document review

- only PREVIEW_READY Document may be approved;
- approve creates/reuses exactly one KnowledgeSource;
- approve creates one new PROCESSING KnowledgeVersion;
- approve runs Chunking;
- successful Chunking leaves version PROCESSING;
- approve does not generate embeddings;
- reject creates no knowledge build;
- rejected artifact remains retained according to prior policy;
- duplicate approval cannot create duplicate source/version races.

## Preview

- preview reads TransformedDocument;
- preview does not depend on Chunk output;
- invalid/non-ready Document cannot be previewed as final normalized knowledge.

## Lesson publishing

- successful publish commits Lesson before ingestion runs;
- Published Lesson triggers ingestion;
- Lesson ingestion creates Raw Snapshot;
- Lesson flow parses/transforms/chunks successfully;
- Lesson uses one existing/reused KnowledgeSource;
- ingestion failure does not unpublish the Lesson;
- failed Lesson knowledge build is retryable;
- repeated publish does not create duplicate concurrent ingestion.

## KnowledgeVersion

- new build starts PROCESSING;
- chunking failure marks version FAILED;
- old ACTIVE version remains ACTIVE after new failure;
- successful chunking does not activate the new version;
- Step 5.6 never mutates ACTIVE Chunk data.

## Concurrency

- second active processing trigger for same source is rejected;
- concurrent requests cannot silently create duplicate processing builds.

## Transactions

- no pipeline-wide long-lived DB transaction;
- stage failure preserves already committed upstream artifacts;
- failed downstream work does not corrupt upstream stage state.

## API boundary

- Admin endpoints are use-case oriented;
- frontend does not need public parse/transform/chunk endpoints;
- orchestrator delegates stage-specific work.

## Logging

- stage start/success/failure logs contain source identity;
- knowledge_version_id is logged when available;
- safe error_code is logged on failure.

---

# Out of Scope

Do not implement in Step 5.6:

```text
Embedding
EmbeddingProfile execution
Vector Storage
Vector Indexing
Semantic Retrieval
Filtering
Reranking
Prompt Construction
LLM Generation
automatic KnowledgeVersion activation
full incremental reprocessing policy
source-change detection
parser-version invalidation
chunk-version invalidation
embedding-model migration
automatic retry scheduler
Airflow
Prefect
Dagster
Celery
Kafka
Redis queue
generic IngestionRun execution-history subsystem
production metrics stack
```

---

# Acceptance Criteria

- [ ] An `IngestionOrchestrator` or equivalent application boundary exists.
- [ ] Orchestrator delegates actual stage implementation.
- [ ] V0 orchestration remains inside the FastAPI modular monolith.
- [ ] No workflow/queue infrastructure is introduced prematurely.
- [ ] Step 5.6 stops after Chunk persistence.
- [ ] Document upload stops at Raw Stored.
- [ ] Document process action performs Parse/Clean → Transform.
- [ ] Successful Document processing reaches PREVIEW_READY.
- [ ] Processing status and review status remain separate concerns.
- [ ] Only PREVIEW_READY Documents can be approved.
- [ ] Admin previews TransformedDocument, not Chunk output.
- [ ] Document approval creates/reuses KnowledgeSource.
- [ ] Document approval creates a new PROCESSING KnowledgeVersion.
- [ ] Approved Document is chunked.
- [ ] Rejected Document does not enter internal knowledge build.
- [ ] Published Lesson automatically triggers ingestion after publish commit.
- [ ] Lesson ingestion failure does not undo the PUBLISHED business state.
- [ ] One logical source maps to one KnowledgeSource.
- [ ] Rebuilds create new KnowledgeVersions.
- [ ] Persisted artifact references connect stages.
- [ ] Failure is fail-fast and blocks dependent stages.
- [ ] Manual safe retry is supported.
- [ ] At most one active processing operation exists per source in V0.
- [ ] No giant transaction spans the pipeline.
- [ ] Failed knowledge build marks PROCESSING version FAILED.
- [ ] Old ACTIVE version remains available after new build failure.
- [ ] Successful Chunking does not activate KnowledgeVersion.
- [ ] Internal parse/transform/chunk actions are not exposed as frontend orchestration APIs.
- [ ] Structured logs identify source, stage, status, errors, and duration.
- [ ] Step 6.1 can continue from PROCESSING KnowledgeVersions with complete Chunk sets.

# Expected Deliverable

Pipeline orchestration foundation plus documentation:

```text
docs/data/
└── step-5.6-pipeline-orchestration.md
```

Next Step:

**Step 5.7 — Incremental / Reprocessing Strategy**
