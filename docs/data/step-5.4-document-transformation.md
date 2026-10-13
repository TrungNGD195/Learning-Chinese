# Step 5.4 — Document Transformation

## Objective

Build one canonical deterministic document model from persisted parsed artifacts.

## Why

Downstream chunking needs one stable source-independent contract instead of parser-specific structures.

## Mental Model

```text
Parsed/Cleaned Artifact
+ source metadata snapshot
→ canonical structural normalization
→ TransformedDocument
→ persisted transformed artifact
→ TransformedArtifactRef
```

## Core Knowledge

- The transformation maps ordered parsed units and the invocation's source metadata snapshot to typed canonical Blocks.
- `content_type` identifies semantic knowledge; `block_kind` identifies structural shape.
- Document source locators preserve PDF pages, DOCX paragraphs/table rows, text blocks and Markdown blocks. Lesson locators preserve entity and field lineage.
- `TransformationRun` records one invocation and its exact successful `ParsingRun`; transformed JSON is stored through existing private `FileStorage`.
- D-054 makes the run's source metadata snapshot part of the deterministic input. D-055 preserves DOCX table rows without claiming cell boundaries.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Canonical Data Model | DE | 5.4 | Gives downstream stages one normalized source-independent document contract. |
| Structural Normalization | DE | 5.4 | Maps parsed locators to stable headings, paragraphs, lists, code blocks, tables or Lesson structures. |
| Semantic Content Type | DE | 5.4 | Distinguishes document text, vocabulary, grammar and general Lesson knowledge. |
| Structural Block Kind | DE | 5.4 | Preserves how each canonical unit is represented independently of its semantic type. |
| Structured Data Preservation | DE | 5.4 | Keeps Vocabulary, Grammar and truthful DOCX row data available alongside canonical text. |
| Source Metadata Snapshot | DE | 5.4 | Makes transformation reproducible after live Document metadata changes. |
| Data Provenance | DE | 5.4 | Retains source-level metadata and block locators for later review and citation. |
| Section Hierarchy | DE | 5.4 | Carries explicit Markdown headings without inventing structure for other formats. |
| Deterministic Transformation | DE | 5.4 | Produces equivalent canonical JSON for identical parsed content and snapshots. |
| Intermediate Artifact | DE | 5.4 | Persists transformed output separately from lifecycle metadata for the next stage. |
| Transformation Lifecycle | DE | 5.4 | Records each independent transformation attempt and its safe result. |
| Data Lineage | DE | 5.4 | Links transformed output to its exact parsed artifact and source. |
| Parsed-to-Transformed Contract | BOTH | 5.4 | Defines the persisted boundary consumed by Step 5.5. |
| Typed Validation | SYSTEM | 5.4 | Rejects malformed canonical structures before marking a run successful. |
| Compensating Cleanup | SYSTEM | 5.4 | Removes partial or orphan transformed files after storage/DB failures. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| PostgreSQL | DE | 5.4 | Persists TransformationRun state and enforces source/status invariants. |
| SQLAlchemy | DE | 5.4 | Maps TransformationRun and owns short application transactions. |
| Alembic | DE | 5.4 | Adds and verifies migration 0007. |
| Pydantic | SYSTEM | 5.4 | Validates persisted parsed input and canonical transformed output. |
| Python `json` | SYSTEM | 5.4 | Serializes deterministic sorted compact UTF-8 artifact bytes. |
| FileStorage / LocalFileStorage | DE | 5.4 | Persists immutable transformed artifacts using the existing private storage abstraction. |
| pytest | SYSTEM | 5.4 | Exercises mappings, lifecycle, database constraints and migrations. |
| uv | SYSTEM | 5.4 | Synchronizes the backend environment and runs verification. |

## Data Flow

### Document

The service validates a specific `ParsedArtifactRef`, loads only its persisted `parsed_cleaned_artifact/v1` bytes and confirms the matching successful ParsingRun. It snapshots authoritative Document metadata once, creates a new TransformationRun, marks both it and the Document `PROCESSING`, transforms outside a long transaction, validates canonical JSON, finalizes the artifact and marks the run `SUCCEEDED` and the Document `PREVIEW_READY`.

### Lesson

The service uses only persisted Lesson parsed units. It derives the title from the parsed title field and groups Vocabulary/Grammar fields by entity locator and `order_index`. It creates a TransformationRun without a Document row or Document status update.

### Success and failure

Every valid invocation receives a separate run; no current/latest selection is defined. A transformation or validation failure records a stable error code and safe short detail, clears the output reference and marks a Document `FAILED` where applicable. Storage finalization failure removes temporary/partial output. If the DB success transaction fails after finalization, the service deletes the orphan artifact and makes a best effort to persist `FAILED`. Raw and parsed artifacts remain intact.

## Key Design Decisions

- D-053: one PostgreSQL `TransformationRun` per invocation; exact `parsing_run_id` lineage; string status plus CHECK constraints; no active/current/latest semantics.
- D-054: Document title, language, category, origin and usage note come from a persisted invocation snapshot; Lesson title comes from persisted parsed content, with language and category null.
- D-055: a DOCX table preserves `table_index`, ordered `row_index` and row text only. No `cells[]` or delimiter-based reconstruction is claimed.
- `transformed_document/v1` uses `canonical_document` strategy/version `v1`; its sorted compact UTF-8 JSON excludes run IDs and timestamps.
- Canonical Blocks keep order, content type, block kind, text, section path, source locator, structured data and auxiliary metadata explicit.
- PDF, DOCX and TXT retain empty section paths. Markdown heading stacks create explicit hierarchy; adjacent compatible list units form one list block. Paragraphs are not merged or split for retrieval size, and duplicate content remains.
- Lesson title is document-level metadata, not a duplicate title Block. Persisted description, Vocabulary and Grammar appear in parsed source order. Fixed Vietnamese labels make structured learning text deterministic.
- Document transformation owns `PREVIEW_READY`; it does not approve or activate content.
- The existing `FileStorage` persists one run-specific transformed file. `TransformedArtifactRef` is sufficient to load validated output without re-parsing or re-transforming.

## Reusable Approach

For another source pipeline, persist extracted units with stable locators, snapshot mutable metadata at the stage boundary, map formats into a typed canonical intermediate model, validate before success, and keep artifact bytes separate from short lifecycle records. Pass the next stage a specific immutable artifact reference.

## Common Mistakes

- Chunking during transformation, or merging/splitting blocks for retrieval size.
- Flattening structured Lesson content or conflating content type with block kind.
- Inventing DOCX cells by splitting row text on tabs.
- Reading mutable metadata again after establishing the run snapshot.
- Inventing PDF sections or using language detection.
- Deduplicating repeated source content or adding AI enrichment.
- Marking a Document `APPROVED` or content `ACTIVE` before later workflow owns those states.
- Storing canonical JSON inside the lifecycle row or reusing ParsingRun for another stage.

## Definition of Done

- `0007_transformation_runs` follows `0006_parsing_runs`, and ORM metadata matches the PostgreSQL schema.
- PDF, DOCX, TXT, Markdown and persisted Lesson units map to the same validated `TransformedDocument` contract.
- Document snapshots, Lesson grouping, deterministic bytes, lifecycle transitions and partial failure cleanup have focused coverage.
- Transformation and database constraints, migration upgrade/downgrade, full backend regression, Alembic current/check all pass before specialist review.
- No Step 5.5 behavior is included.
