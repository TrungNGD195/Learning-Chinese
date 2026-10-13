# Step 5.6 — Pipeline Orchestration

## Objective

Coordinate the accepted Raw → Parse/Clean → Transform → Chunk services for Documents and Published Lessons. Stop when a `PROCESSING` KnowledgeVersion has a complete persisted Chunk set. Step 5.6 does not embed, activate, or retrieve knowledge.

## Why

Each source has a different business lifecycle, while both reuse the same persisted stage references and chunking service. The orchestrator keeps those lifecycle rules in one application boundary and gives retries durable claims without holding database transactions open during file or CPU work.

## Mental Model

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

## Core Knowledge

- `Document.review_transformation_run_id` identifies the exact successful artifact shown in Preview, approved by Admin, and used for Chunking.
- One Document and one Lesson each reuse a single KnowledgeSource. Each build gets a new version number.
- Lock the KnowledgeSource before checking for a PROCESSING version and allocating `MAX(version_number) + 1`.
- A Lesson’s PROCESSING version is committed before its Raw Snapshot. A Document’s review approval is committed before its knowledge build.
- A failed build marks only its newly claimed PROCESSING version FAILED. Existing ACTIVE versions and their Chunks remain intact.
- Migration 0009 adds the Step-5.6 application constraints and widens Alembic’s `version_num` column. Downgrade removes the application schema and intentionally keeps the 64-character migration column.

## Data Flow

Document processing claims `PROCESSING`, clears the review pointer, commits, then passes exact RawArtifactRef and ParsedArtifactRef values to the accepted parsing and transformation services. Transformation success commits the successful run, `PREVIEW_READY`, and the pointer together. Preview loads the pointer’s exact TransformedArtifactRef. Approval commits first, allocates a new PROCESSING version, and passes that same ref to Step-5.5 Chunking.

Lesson publish commits before the post-commit orchestration call. The orchestrator locks the published Lesson and KnowledgeSource, commits a new PROCESSING version, then creates the immutable Raw Snapshot and delegates Parse, Transform, and Chunk. A stage failure stops downstream work and marks the claimed version FAILED.

## Key Design Decisions

- Reused the accepted parsing, transformation, storage, and chunking services; orchestration contains only lifecycle gates, ordering, claims, error translation, and logging.
- Used short transactions for Document claims, review decisions, source/version allocation, Lesson claims, and failure propagation.
- Enforced one Document source and one PROCESSING version per source in PostgreSQL as well as in application checks.
- Kept human review state separate from processing state. Approval remains committed if its later knowledge build fails.
- Kept Lesson PUBLISHED if post-commit ingestion fails. Retry is an explicit Admin action that creates a new version.
- Added only migration `0009_pipeline_orchestration_contract`, following `0008_chunking_contract`; migrations 0001–0008 remain unchanged.
- Used Python logging with source, stage, status, elapsed time, optional version, and safe error code fields.

## Reusable Approach

Commit a durable source/business claim before slow work. Pass exact persisted references between accepted stage services. Keep stage-owned transactions short, and make a retry allocate a new version rather than reusing a failed attempt.

## Common Mistakes

- Selecting the newest TransformationRun instead of the Document’s pinned review run.
- Holding a transaction or row lock across file access, parsing, transformation, or Chunk planning.
- Chunking before Document approval or running Lesson ingestion inside the publish transaction.
- Reusing a FAILED/SUPERSEDED version or mutating an older ACTIVE version.
- Leaking storage paths, database details, or nested exception text through an orchestration error.
- Treating approval as a retry or treating repeated Lesson publish as a knowledge retry.

## Definition of Done

- Document Preview, Approval, and Chunking use one pinned successful TransformationRun.
- Document and Lesson lifecycles, durable claims, retry paths, fail-fast behavior, and failure propagation are covered by tests.
- Migration 0009 upgrade, downgrade, re-upgrade, and fresh-base paths pass; downgrade retains Alembic `VARCHAR(64)`.
- Focused Step-5.6 tests, database/migration tests, full backend regression, Alembic current, and Alembic check pass.
- No Embedding, Vector, Retrieval, activation, Step 5.7, queue, worker, or generic pipeline-run behavior is added.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Pipeline Orchestration | DE | 5.6 | Orders existing stages and enforces source lifecycle gates. |
| Stage Boundary | DE | 5.6 | Keeps parsing, transformation, and chunking algorithms in their accepted services. |
| Artifact Reference Chaining | DE | 5.6 | Carries exact persisted outputs to the next stage. |
| Business vs Processing State | DE | 5.6 | Keeps human review and machine processing transitions independent. |
| Durable Processing Claim | DE | 5.6 | Persists a Document or Lesson attempt before slow pipeline work. |
| KnowledgeSource Identity | DE | 5.6 | Keeps one reusable source row per Document or Lesson. |
| KnowledgeVersion Allocation | DE | 5.6 | Gives each build attempt a new monotonically allocated version. |
| Source-Level Concurrency | DE | 5.6 | Serializes version allocation on the KnowledgeSource row. |
| Failure Propagation | DE | 5.6 | Marks only the new failed attempt without undoing approval or publish. |
| Fail-Fast Pipeline | DE | 5.6 | Prevents downstream stages from running after an upstream failure. |
| Manual Retry Boundary | DE | 5.6 | Uses explicit source-specific actions to start new attempts. |
| ACTIVE-Version Protection | DE | 5.6 | Preserves the previously active version and its Chunks. |
| Short Transaction Boundary | BOTH | 5.6 | Commits state claims before file or CPU-bound work. |
| Partial Unique Index | DE | 5.6 | Enforces at most one PROCESSING KnowledgeVersion per source. |
| Row Locking | SYSTEM | 5.6 | Coordinates concurrent source claims and version allocation. |
| Use-Case API | SYSTEM | 5.6 | Exposes Admin lifecycle actions without public stage endpoints. |
| Structured Logging | SYSTEM | 5.6 | Makes source, stage, result, duration, and safe error code observable. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| FastAPI | SYSTEM | 5.6 | Exposes authorized Admin use-case routes. |
| PostgreSQL | DE | 5.6 | Enforces source identity, PROCESSING uniqueness, and row locks. |
| SQLAlchemy | DE | 5.6 | Persists short transactions and executes row-locked queries. |
| Alembic | DE | 5.6 | Applies and verifies migration 0009 and revision-column width behavior. |
| Pydantic | SYSTEM | 5.6 | Validates exact persisted artifact references and transformed output. |
| FileStorage / LocalFileStorage | DE | 5.6 | Persists and loads immutable Raw and transformed artifacts. |
| Python logging | SYSTEM | 5.6 | Emits structured stage success and failure records. |
| pytest | SYSTEM | 5.6 | Verifies lifecycle, concurrency, database invariants, and migrations. |
| uv | SYSTEM | 5.6 | Runs the project’s backend verification commands. |
