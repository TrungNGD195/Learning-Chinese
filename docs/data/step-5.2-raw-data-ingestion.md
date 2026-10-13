# Step 5.2 — Raw Data Ingestion

## Objective

Safely acquire accepted Document and published Lesson sources and store immutable raw artifacts for later processing.

## Why

Raw bytes and source-state snapshots must remain reproducible and traceable. Ingestion is a separate boundary from human approval, processing, and knowledge activation.

## Mental Model

```text
Accepted source → validated input → immutable raw artifact → RawArtifactRef
```

This Step ends at `Source → Raw Stored`.

## Core Knowledge

- Documents use the accepted Step-5.1 provenance contract and explicit `domain_allowed` attestation.
- Original PDF, DOCX, TXT, and MD bytes are validated and stored unchanged.
- Published Lessons become deterministic `raw_lesson_snapshot/v1` artifacts ordered by their curriculum `order_index` values.
- Raw ingestion does not approve Documents or activate knowledge.

## Data Flow

```text
Admin multipart upload
→ source-policy and file validation
→ bounded stream, byte count, and SHA-256
→ private temporary artifact
→ atomic finalization
→ short Document transaction
→ safe response / internal RawArtifactRef
```

```text
Published Lesson + HSK + ordered Vocabulary/Grammar
→ canonical snapshot bytes
→ SHA-256 keyed immutable artifact
→ RawArtifactRef
```

## Key Design Decisions

- D-049 keeps legacy provenance and raw metadata nullable; new uploads still require valid provenance.
- D-050 fixes the Admin transport as multipart with `python-multipart`; D-051 requires explicit, non-persisted `domain_allowed=true`.
- D-005 keeps ingestion synchronous and bounded by `DOCUMENT_MAX_UPLOAD_MB`, default 20.
- Migration `0005_raw_document_metadata` adds only nullable raw metadata, exact-hash uniqueness, and the positive file-size check.
- Slow upload I/O stays outside the database transaction. Failed persistence rolls back and removes that request’s artifact.
- Local storage is private and configurable; API responses never expose storage references or filesystem paths.
- No parsing, transformation, chunking, embeddings, retrieval, worker, object storage, or Lesson publish trigger is part of this Step.

## Cách tiếp cận bài toán tương tự trong project khác

Define the raw boundary first. Validate provenance and format before persisting, stream into temporary storage while calculating identity, then finalize the immutable artifact before a short metadata transaction. Use compensating cleanup across storage and database failures. For mutable source records, serialize only source state in stable order and hand downstream work an artifact reference rather than a live database query.

## Common Mistakes

- Treating upload completion as successful persistence.
- Holding a database transaction open during a client upload.
- Trusting client filenames for storage paths or exposing local paths in responses.
- Rewriting source bytes or hashing a transformed representation.
- Treating duplicate pre-checks as a substitute for the database unique constraint.
- Confusing raw ingestion with approval, processing, or knowledge activation.

## Definition of Done

- Supported Admin uploads persist exact raw bytes and metadata with bounded streaming and duplicate-race protection.
- Failed validation or persistence leaves no temporary or finalized artifact and no successful Document row.
- Only PUBLISHED Lessons produce deterministic, hash-addressed snapshots.
- Migration and downgrade preserve the prior schema and legacy data.
- Focused, migration, and full backend tests pass; Alembic is at `0005_raw_document_metadata` with no metadata drift.
- The Data Engineering Specialist reviews the implementation before PM acceptance.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Raw Data Ingestion | DE | 5.2 | Captures accepted source content at the raw boundary. |
| Raw Artifact | DE | 5.2 | Gives later processing a stable stored input. |
| Data Immutability | DE | 5.2 | Preserves original Document bytes and Lesson snapshots. |
| Data Provenance | DE | 5.2 | Connects new Documents to validated source metadata. |
| Content Hash / SHA-256 | DE | 5.2 | Identifies and verifies raw content. |
| Exact Duplicate Detection | DE | 5.2 | Rejects byte-identical Documents under a race-safe database constraint. |
| Storage Abstraction | DE | 5.2 | Keeps ingestion independent of local filesystem details. |
| Deterministic Snapshot | DE | 5.2 | Produces repeatable Lesson source artifacts. |
| Schema Evolution | DE | 5.2 | Adds raw metadata through a forward migration. |
| Raw-to-Processed Contract | BOTH | 5.2 | Hands immutable bytes and metadata to later processing. |
| Streaming I/O | SYSTEM | 5.2 | Bounds memory while receiving uploads. |
| Filesystem Safety | SYSTEM | 5.2 | Prevents traversal and storage-root escape. |
| Authorization | SYSTEM | 5.2 | Restricts raw Document upload to Admins. |
| Transaction Boundary | SYSTEM | 5.2 | Keeps slow upload work outside database transactions. |
| Compensating Cleanup | SYSTEM | 5.2 | Removes finalized artifacts if database persistence fails. |
| Validation Boundary | SYSTEM | 5.2 | Separates metadata, attestation, type, signature, and size checks. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| FastAPI | SYSTEM | 5.2 | Defines the Admin multipart endpoint and request contract. |
| python-multipart | SYSTEM | 5.2 | Parses multipart form uploads. |
| PostgreSQL | DE | 5.2 | Enforces persisted metadata and exact-hash uniqueness. |
| SQLAlchemy | DE | 5.2 | Maps and persists Document metadata. |
| Alembic | DE | 5.2 | Applies and verifies migration 0005. |
| Pydantic | SYSTEM | 5.2 | Validates typed settings, source metadata, and handoff schemas. |
| pathlib / os | SYSTEM | 5.2 | Resolves safe storage paths and atomically finalizes files. |
| hashlib | SYSTEM | 5.2 | Calculates streaming SHA-256 identities. |
| zipfile | SYSTEM | 5.2 | Checks DOCX package structure without extracting text. |
| pytest | SYSTEM | 5.2 | Verifies ingestion, storage, migration, and regression behavior. |
| uv | SYSTEM | 5.2 | Resolves dependencies and runs backend verification. |
