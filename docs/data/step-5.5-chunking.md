# Step 5.5 — Chunking

## Objective

Convert the source-independent canonical Blocks from Step 5.4 into deterministic retrieval units stored as flat `Chunk` rows on an existing `PROCESSING` `KnowledgeVersion`.

## Why

Retrieval operates on bounded, traceable units. Chunk planning therefore stays separate from transformation, embedding, retrieval, and `KnowledgeVersion` activation. Step 5.5 stores chunks only; Step 6.1 owns embedding.

## Mental Model

```text
TransformedDocument
→ deterministic Chunk plan
→ validate complete plan
→ atomic replacement
→ persisted Chunk[]
```

## Core Knowledge

- Content type selects the strategy: document and Lesson-General text use structure-aware grouping; Vocabulary stays one entity per chunk; Grammar stays atomic except for D-058 oversized fallback.
- Unicode character counts make the v1 size policy independent of any future embedding tokenizer.
- Each chunk carries ordered block/entity/page provenance. TABLE, LIST, and field-aware Grammar subchunks narrow their canonical locator to only represented rows, members, or fields. Forced parts record zero-based, start-inclusive/end-exclusive offsets into the canonical source text.
- A content hash fingerprints only the canonical JSON pair `{content, content_type}`. Equal hashes do not identify rows and never cause deduplication.
- A chunk rebuild is a transactional replacement guarded by the `KnowledgeVersion` row lock and the `PROCESSING` status.

## Data Flow

`build_chunks()` validates the supplied `TransformedArtifactRef` against its exact successful `TransformationRun`, then checks that the existing `KnowledgeVersion` is `PROCESSING` and its `KnowledgeSource` points to the same logical source. It loads the persisted `transformed_document/v1` through the Step-5.4 loader, validates and plans all chunks before beginning replacement. The short write transaction locks and rechecks the version and lineage, deletes that version's previous chunks, inserts the complete ordered plan, saves the frozen configuration, and commits.

Reruns replace the same version's set. Any persistence failure rolls back the transaction and leaves the previous complete set intact. `ACTIVE` and all other non-`PROCESSING` versions are rejected before planning and rechecked under the lock. No source/version creation, failure propagation, or activation occurs.

## Key Design Decisions

- **D-056:** migration `0008_chunking_contract` adds nullable-for-legacy `KnowledgeVersion.chunking_version`, `KnowledgeVersion.chunk_max_chars`, and `Chunk.content_hash`. New builds persist `structure_aware/v1`, target 1200, max 1800, overlap 150. Existing `Chunk.metadata` stores `chunk_metadata/v1` provenance.
- **D-057:** SHA-256 uses UTF-8 `json.dumps` with `ensure_ascii=False`, sorted keys, and compact separators over only `content` and `content_type`. Rows are never deduplicated by hash.
- **D-058:** Grammar is normally one entity per chunk. Only content above 1800 characters is packed at canonical field boundaries; a single oversized field uses the deterministic forced splitter and 150-character overlap.
- **D-059:** a table uses only retained row text and identity. Small tables remain whole; larger tables group complete rows. No header is inferred, repeated, or fabricated, and an oversized row fails with `CHUNK_TOO_LARGE`.
- `DOCUMENT_TEXT` and `LESSON_GENERAL` merge only across consecutive Blocks of the same content type and section path. Section changes flush. PDF page changes do not; page ranges are preserved and `page_number` is null for multi-page chunks.
- Headings start a forward candidate. Vocabulary entities stay atomic. Lists group complete items first and split only an oversized item as a last resort.
- The splitter prefers paragraph, line, sentence-punctuation, then whitespace boundaries near the target; it enforces the max and applies overlap only within parts of the same textual unit.
- `token_count` remains null. There is no tokenizer, embedding, vector write, retrieval, LLM, public chunking API, or Step-5.6 orchestration.

## Reusable Approach

For another ingestion stage, load one immutable typed artifact reference, validate its exact lifecycle lineage, create and validate a deterministic plan outside the write transaction, then atomically replace the target's durable output under a locked state check.

## Common Mistakes

- Applying a blind sliding window, merging different content types, or crossing explicit section boundaries.
- Splitting short or long Vocabulary entries, or splitting ordinary Grammar to reach the target size.
- Guessing DOCX headers/cells, splitting a retained table row, or adding synthetic labels to chunk content.
- Applying overlap to ordinary neighboring chunks or deduplicating by hash.
- Reading live source records, selecting a latest TransformationRun, or holding a database transaction during artifact I/O and chunk planning.
- Appending on retry, mutating an `ACTIVE` version, activating a version, or adding embedding behavior in Step 5.5.

## Definition of Done

- [x] Exact persisted transformation lineage and matching `PROCESSING` source/version are enforced.
- [x] Deterministic content-type strategies, narrowed source ranges, hashes, and chunk order are covered.
- [x] Migration 0008 is reversible and preserves legacy rows; ORM metadata matches PostgreSQL.
- [x] Same-version rerun replaces chunks; failed replacement preserves the prior set; `ACTIVE` is protected.
- [x] Focused, database/migration, full backend, and Alembic verification pass.
- [x] No Step 5.6 or Step 6.1 behavior is introduced.

Verification evidence for the focused rework: `uv sync` completed without changing `uv.lock`; the focused chunking/service run passed 44 tests; the database/migration run passed 21 tests; the full backend run passed 304 tests; Alembic current is `0008_chunking_contract` and `alembic check` found no pending operations. Tests prove narrowed TABLE row, LIST member, and Grammar field locators; exact forced-text offsets; rejection of malformed typed locators and table provenance; all exact TransformationRun lineage failure branches; preservation of the old chunk set and frozen configuration on both insert-stage and final-flush rollback; separator precedence through the hard-boundary fallback; and unexpected planning exceptions classified as `CHUNKING_FAILED`/500. The full run reported the existing Starlette/httpx deprecation and a Windows pytest cache-directory permission warning; neither affected test results.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Structure-Aware Chunking | DE | 5.5 | Uses canonical semantic and structural boundaries to build retrieval units. |
| Character Budget | DE | 5.5 | Keeps chunk sizing deterministic and independent of an embedding tokenizer. |
| Forced Text Splitting and Overlap | DE | 5.5 | Bounds one oversized text unit while preserving exact ranges and local continuity. |
| Chunk Provenance | DE | 5.5 | Keeps each chunk traceable to source blocks, entities, pages, and split offsets. |
| Content Hash | DE | 5.5 | Fingerprints canonical chunk payload without conflating content with row identity. |
| Idempotent Rebuild | DE | 5.5 | Makes retries replace one version's chunk set instead of appending duplicates. |
| Atomic Persistence | DE | 5.5 | Prevents partial chunk sets from becoming visible after a failed replacement. |
| Transformed-to-Chunk Contract | BOTH | 5.5 | Connects the persisted Step-5.4 artifact to the durable chunk representation. |
| Row Locking and State Recheck | SYSTEM | 5.5 | Protects a version from stale or concurrent writes and preserves active data. |
| Typed Validation | SYSTEM | 5.5 | Rejects invalid transformed structures and chunk metadata before persistence. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| Python | SYSTEM | 5.5 | Implements deterministic planning, validation, and orchestration. |
| Pydantic | SYSTEM | 5.5 | Validates transformed artifacts, chunk plans, and `chunk_metadata/v1`. |
| Python `hashlib` and `json` | SYSTEM | 5.5 | Produce the exact canonical SHA-256 content fingerprint. |
| FileStorage / LocalFileStorage | DE | 5.5 | Loads the exact persisted transformed artifact through the existing adapter. |
| SQLAlchemy | DE | 5.5 | Validates lineage and atomically replaces chunk rows under a row lock. |
| PostgreSQL | DE | 5.5 | Persists chunks/configuration and enforces the version/order invariant. |
| Alembic | DE | 5.5 | Adds and verifies the forward migration 0008. |
| pytest | SYSTEM | 5.5 | Exercises chunk strategies, lifecycle safety, persistence, and migrations. |
| uv | SYSTEM | 5.5 | Runs backend verification in the managed environment. |
