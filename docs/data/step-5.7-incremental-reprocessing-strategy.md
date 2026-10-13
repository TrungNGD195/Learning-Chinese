# Step 5.7 — Incremental / Reprocessing Strategy

## Objective

Choose the earliest stale ingestion stage for a Document or published Lesson and reuse only validated artifacts from its exact persisted lineage. Rebuild work uses a new `KnowledgeVersion`; the existing ACTIVE version remains available.

## Why

Documents require human review before a changed artifact can replace approved knowledge. Published Lessons need an explicit maintenance action when their canonical snapshot changes. Comparing desired processing identities with causal lineage avoids repeating valid upstream work without guessing from timestamps or newest-run ordering.

## Mental Model

```text
desired processing identity
→ compare to exact persisted causal lineage
→ first stale stage
→ reuse only valid upstream artifacts
→ rebuild downstream
→ preserve old ACTIVE
→ NO_OP when already satisfied
```

For a Document re-review, approved artifact A remains authoritative while candidate B waits for review. For a Lesson, explicit maintenance compares the current canonical snapshot hash with the exact baseline raw hash.

## Core Knowledge

- `ReprocessingPlanner` makes a typed, read-only decision. `ReprocessingService` replans for every execution and then invokes the earliest required accepted stage.
- Parse identity includes source fingerprint, parser name/version, and cleaning strategy/version. Transformation identity includes the exact parsed bytes and transformation strategy/version. Chunk identity includes exact transformed bytes and the chunking configuration.
- Reuse follows foreign keys and approved/active pointers through TransformationRun, ParsingRun, and exact artifact references. It never selects the newest run.
- Artifact reuse requires persisted object validation plus relational source and hash checks. Invalid or missing artifacts select the earliest safe stage that can be proven.
- Document candidate B updates the review pointer only. The approved pointer A and old ACTIVE version remain intact until B is approved. Rejecting B restores the approved state. A failed candidate attempt can be retried while preserving A and its approval metadata.
- Lesson edits do not start ingestion automatically. Explicit maintenance snapshots the current canonical Lesson and creates a new PROCESSING version when work is required.
- Changed chunk output uses a new `KnowledgeVersion`. The old ACTIVE version and its Chunks are not changed or activated by this step.
- Migration 0010 adds the approved-artifact pointer and version-to-transformation lineage. It backfills only the already-authoritative valid approved Document pointer; legacy KnowledgeVersion lineage stays NULL unless it can be proven directly.

## Data Flow

```text
Document or published Lesson
→ read source identity and exact baseline lineage
→ validate raw / parsed / transformed artifacts and baseline Chunks
→ NO_OP | FROM_PARSE | FROM_TRANSFORM | FROM_CHUNK | FROM_EMBED
→ for Document: preview candidate and wait for human approval when Parse/Transform changes
→ for Lesson or approved Document Chunk rebuild: claim a new PROCESSING KnowledgeVersion
→ commit short claim transaction
→ execute only required stages from exact artifact references
→ persist exact transformation_run_id with the Chunk set
```

`FROM_EMBED` is policy-only here; it performs no embedding, vector, or KnowledgeVersion work.

## Key Design Decisions

- Kept planning and maintenance as internal service boundaries with no public reprocessing route or persistent plan table.
- Used derived fingerprints in Python instead of storing redundant fingerprint columns.
- Added migration `0010_incremental_reprocessing_contract` after `0009_pipeline_orchestration_contract`; earlier migrations remain unchanged.
- Set `approved_transformation_run_id` to `ON DELETE SET NULL`, because the approved pointer is optional if history is deleted. Set `KnowledgeVersion.transformation_run_id` to `ON DELETE RESTRICT`, preserving exact build lineage.
- Backfilled a Document approved pointer only when its approved review pointer references a successful Document TransformationRun with a transformed artifact and no error.
- Kept legacy KnowledgeVersion lineage NULL rather than infer it from ACTIVE status, timestamps, or the Document approval pointer.
- Used Document row locks for candidate claims, KnowledgeSource row locks plus the partial unique constraint for version allocation, and short transactions around durable state changes.
- Reused accepted raw snapshot, parsing, transformation, storage, and chunking implementations.

## Reusable Approach

1. Resolve the exact source and baseline references from persisted relationships.
2. Compare desired identities from the source toward downstream stages.
3. Validate each reusable artifact before returning its typed reference.
4. Claim state and a new version in a short transaction, then commit before file or CPU work.
5. Execute only from the earliest stale stage, preserving the previous ACTIVE version on success or failure.
6. Re-run planning for every explicit maintenance request.

## Common Mistakes

- Selecting the latest TransformationRun or ParsingRun instead of following exact pointer and foreign-key lineage.
- Treating a filename as Document content identity or changing the accepted `raw_lesson_snapshot/v1` contract.
- Building Document knowledge before candidate B is approved.
- Using an unapproved review candidate for an approved Document Chunk-only rebuild.
- Erasing approved identity when rejecting a replacement candidate or retrying a failed re-review.
- Guessing legacy KnowledgeVersion lineage from approved pointers, ACTIVE status, or timestamps.
- Rebuilding automatically after a Lesson edit or using repeat publish as a maintenance trigger.
- Replacing an ACTIVE version's Chunk rows in place, creating a version for NO_OP or FROM_EMBED, or adding a scheduler/worker.

## Definition of Done

- Typed planner precedence, source identity, derived fingerprint, artifact integrity, and exact lineage behavior are covered.
- Document review candidates preserve approved identity; explicit failed re-review retry replans and preserves old ACTIVE knowledge.
- Lesson maintenance is explicit, produces a new version when required, and does not change Lesson PUBLISHED state or old ACTIVE knowledge on failure.
- Concurrent Document processing and KnowledgeVersion claims are protected.
- Migration upgrade, deterministic backfill, foreign-key delete semantics, and downgrade are verified.
- Focused Step-5.7, Step-5.6 regression, database/migration, full backend, and Alembic checks pass.
- No Step 5.8 or Phase 6 behavior is introduced.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Incremental Reprocessing | DE | 5.7 | Rebuilds only from the first stale ingestion stage. |
| First-Stale-Stage Planning | DE | 5.7 | Selects the earliest stage whose desired identity or artifact is no longer valid. |
| Derived Fingerprint | DE | 5.7 | Computes deterministic processing identity without redundant database state. |
| Causal Data Lineage | DE | 5.7 | Follows exact source, run, artifact, and KnowledgeVersion references. |
| Artifact Integrity | DE | 5.7 | Prevents missing, malformed, or mismatched persisted files from being reused. |
| NO_OP / Idempotency | DE | 5.7 | Avoids creating runs or versions when the persisted output already satisfies the request. |
| Document Re-review Candidate | DE | 5.7 | Separates a pending replacement from the currently approved artifact. |
| Approved Artifact Identity | DE | 5.7 | Keeps approved source material authoritative during re-review and retry. |
| Replacement KnowledgeVersion | DE | 5.7 | Isolates replacement chunks from the old ACTIVE version. |
| ACTIVE-Version Protection | DE | 5.7 | Keeps existing knowledge and chunks unchanged during replacement work. |
| Explicit Maintenance Boundary | DE | 5.7 | Makes Lesson reprocessing intentional rather than edit-triggered. |
| Source-Level Concurrency | DE | 5.7 | Prevents overlapping builds and serializes version allocation. |
| Row Locking | SYSTEM | 5.7 | Protects Document claims and KnowledgeSource version allocation. |
| Typed Planner Contract | SYSTEM | 5.7 | Represents action, reason, and exact reusable refs with validated types. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| Python `hashlib` / `json` | SYSTEM | 5.7 | Derives canonical stage fingerprints. |
| Pydantic | SYSTEM | 5.7 | Validates typed plans and persisted artifact structures. |
| SQLAlchemy | DE | 5.7 | Reads exact lineage and manages row-locked short transactions. |
| PostgreSQL | DE | 5.7 | Enforces foreign-key delete behavior and PROCESSING uniqueness. |
| Alembic | DE | 5.7 | Applies migration 0010 and verifies schema synchronization. |
| FileStorage / LocalFileStorage | DE | 5.7 | Reads and validates immutable raw, parsed, and transformed artifacts. |
| pytest | SYSTEM | 5.7 | Verifies planner, execution, migration, integrity, and concurrency behavior. |
| uv | SYSTEM | 5.7 | Runs backend verification commands in the locked environment. |
