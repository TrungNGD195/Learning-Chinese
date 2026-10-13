# Codex Task — Step 5.4 Document Transformation

## Task Identity

**Project:** LLM + RAG Web App học tiếng Trung cho người mới bắt đầu  
**Phase:** 5 — Data Engineering  
**Step:** 5.4 — Document Transformation  
**Owner:** Data Engineering Specialist  
**Task status:** FROZEN / READY FOR CODEX AFTER PM REVIEW  
**Implementation mode:** One Codex task = this Step only

Do not redesign architecture. Do not expand scope. Treat the current accepted repository state plus frozen decisions D-053, D-054 and D-055 as authoritative.

---

# 1. Accepted Project State

Before this task:

```text
Step 5.1
→ PM ACCEPTED / CLOSED

Step 5.2
→ PM ACCEPTED / CLOSED

Step 5.3
→ PM ACCEPTED / CLOSED
```

Current Alembic head:

```text
0006_parsing_runs
```

Accepted Step-5.3 boundary:

```text
Raw Artifact
→ parsing / conservative cleaning
→ persisted ParsedCleanedArtifact/v1
→ specific ParsedArtifactRef
```

Exact persisted schema identity:

```text
parsed_cleaned_artifact/v1
```

Step 5.4 must consume the persisted parsed artifact.

Do **not**:

```text
reparse PDF/DOCX/TXT/MD
reread Raw Artifact as transformation source
reconstruct Lesson from live Lesson/Vocabulary/Grammar DB state
```

---

# 2. Objective

Implement deterministic transformation from:

```text
ParsedCleanedArtifact/v1
```

into one canonical:

```text
TransformedDocument
```

persisted as:

```text
transformed_document/v1
```

for downstream Step 5.5 chunking.

Mental model:

```text
Parsed/Cleaned Artifact
→ deterministic structural/semantic normalization
→ TransformedDocument Artifact
→ specific TransformedArtifactRef
→ Step 5.5 Chunking
```

Transformation is **not** chunking.

---

# 3. Frozen D-053 — Transformation Lifecycle Persistence

Use a dedicated minimal relational:

```text
TransformationRun
```

in PostgreSQL.

One transformation invocation:

```text
→ one TransformationRun
```

Do not extend/reuse:

```text
ParsingRun
```

for transformation lifecycle.

Do not use `Document.processing_status` as the complete cross-source transformation lifecycle.

---

# 4. TransformationRun Schema Freeze

Create a model equivalent to:

```text
TransformationRun
├── id
├── source_type
├── document_id nullable
├── lesson_id nullable
├── parsing_run_id
├── parsed_storage_reference
├── transformation_strategy
├── transformation_version
├── status
├── transformed_storage_reference nullable
├── error_code nullable
├── error_detail nullable
├── source_metadata_snapshot
├── created_at
└── updated_at
```

Statuses:

```text
PENDING
PROCESSING
SUCCEEDED
FAILED
```

Use existing SQLAlchemy/PostgreSQL conventions.

Do not introduce DB enum infrastructure if repository conventions use string + CHECK constraints.

---

## 4.1 Source invariant

```text
source_type = DOCUMENT
→ document_id IS NOT NULL
→ lesson_id IS NULL

source_type = LESSON
→ lesson_id IS NOT NULL
→ document_id IS NULL
```

No additional source type is allowed in Step 5.4.

---

## 4.2 Success invariant

```text
status = SUCCEEDED
→ transformed_storage_reference IS NOT NULL
→ error_code IS NULL
```

---

## 4.3 Failure invariant

```text
status = FAILED
→ transformed_storage_reference IS NULL
→ error_code IS NOT NULL
```

---

## 4.4 Parsing lineage

Every TransformationRun must reference the specific successful Step-5.3 run that produced its input:

```text
parsing_run_id
```

Do not infer "latest parsing run".

Do not create active/current selection semantics.

---

## 4.5 Source metadata snapshot

`source_metadata_snapshot` must persist the accepted transformation-time metadata snapshot defined by D-054.

Use a structured JSON representation compatible with current PostgreSQL/SQLAlchemy conventions.

Do not store the entire transformed document in PostgreSQL.

---

## 4.6 Safe diagnostics

`error_detail` must be safe.

Do not persist:

```text
stack trace
secret
credential
raw DB exception
internal absolute filesystem path
raw serializer/Pydantic exception dump
```

A short sanitized diagnostic is allowed.

---

# 5. Rerun Semantics

Every new transformation invocation creates a new:

```text
TransformationRun
```

Step 5.4 does **not** define:

```text
current
latest
active
canonical
preferred
```

transformation run.

Do not add:

```text
is_active
superseded_by
current_transformation_run_id
unique active transformation run
```

Selection/reprocessing policy belongs to later orchestration/reprocessing Steps.

---

# 6. Document Coarse processing_status Freeze

For `DOCUMENT`:

```text
transformation starts
→ Document.processing_status = PROCESSING

transformation succeeds
AND canonical artifact validation succeeds
→ Document.processing_status = PREVIEW_READY

transformation fails
→ Document.processing_status = FAILED
```

Step 5.4 **owns** successful transition to:

```text
PREVIEW_READY
```

For `LESSON`:

```text
no Document row
→ no Document status update
```

Do not set APPROVED/ACTIVE state.

`PREVIEW_READY` means a valid canonical transformed artifact exists for later preview/review workflow.

---

# 7. Migration Freeze

Create exactly one forward migration:

```text
backend/migrations/versions/0007_transformation_runs.py
```

Required:

```text
revision identity:
0007_transformation_runs

down_revision:
0006_parsing_runs
```

Do not modify:

```text
0001
0002
0003
0004
0005
0006
```

Do not create:

```text
relational Block table
Chunk migration
KnowledgeVersion lifecycle migration
```

Do not modify:

```text
KnowledgeSource
KnowledgeVersion
Chunk
```

for Step 5.4.

---

# 8. TransformationRun Physical Constraints

Migration/ORM must enforce at least:

```text
source_type IN ('DOCUMENT','LESSON')

status IN ('PENDING','PROCESSING','SUCCEEDED','FAILED')
```

Source-target CHECK equivalent to:

```text
(
  source_type = 'DOCUMENT'
  AND document_id IS NOT NULL
  AND lesson_id IS NULL
)
OR
(
  source_type = 'LESSON'
  AND lesson_id IS NOT NULL
  AND document_id IS NULL
)
```

Success CHECK equivalent to:

```text
status <> 'SUCCEEDED'
OR (
  transformed_storage_reference IS NOT NULL
  AND error_code IS NULL
)
```

Failure CHECK equivalent to:

```text
status <> 'FAILED'
OR (
  transformed_storage_reference IS NULL
  AND error_code IS NOT NULL
)
```

Add only practical indexes justified by direct source/run lookup, e.g.:

```text
document_id
lesson_id
parsing_run_id
status
```

Do not create current/latest uniqueness constraints.

---

# 9. Frozen D-054 — Reproducible Source Metadata Snapshot

Transformation deterministic input is:

```text
ParsedCleanedArtifact/v1
+
source_metadata_snapshot
+
canonical_document/v1
```

Do not rely only on mutable live metadata during the transformation after the snapshot has been established.

---

# 10. DOCUMENT Metadata Snapshot Freeze

At `TransformationRun` creation for DOCUMENT:

```text
load authoritative persisted Document metadata once
→ validate required fields
→ persist source_metadata_snapshot
```

Snapshot equivalent fields actually available:

```text
source_type
source_id
title
source_language
source_category
source_origin
usage_rights_note
original_filename   # optional auxiliary provenance if useful
```

Required:

```text
title
source_language
source_category
source_origin
```

according to accepted new-ingestion policy.

Canonical Document title must come from:

```text
source_metadata_snapshot.title
```

Do not infer title from:

```text
first parsed line
first heading
parser output guess
filename fallback
```

If a legacy Document lacks required provenance and cannot form a valid transformation snapshot:

```text
fail transformation explicitly
```

Do not invent missing metadata.

---

# 11. LESSON Metadata Snapshot Freeze

For LESSON:

```text
use persisted ParsedCleanedArtifact as authoritative content source
```

Lesson title:

```text
derive from persisted LESSON title parsed unit
```

Do not query live Lesson row merely to obtain title.

Freeze:

```text
source_category = null
source_language = null
```

when no authoritative single source-level language exists.

Do not invent:

```text
zh
vi
en
mixed
```

Do not run language detection.

Persist a TransformationRun `source_metadata_snapshot` shape sufficient to reproduce the same transformation invocation, e.g.:

```text
source_type
source_id
title
source_language = null
source_category = null
```

plus only other authoritative persisted fields actually available from the parsed artifact if needed.

Do not reopen Step 5.3 to add metadata.

---

# 12. Canonical TransformedDocument Schema Freeze

Schema identity:

```text
transformed_document/v1
```

Logical typed model:

```text
TransformedDocument
├── schema_version = transformed_document/v1
├── source_type
├── source_id
├── title
├── source_language
├── source_category
├── transformation_strategy
├── transformation_version
├── provenance
└── blocks[]
```

Freeze:

```text
transformation_strategy = canonical_document
transformation_version  = v1
```

`source_language`:

```text
DOCUMENT
→ required

LESSON
→ nullable
```

`source_category`:

```text
DOCUMENT
→ required from snapshot

LESSON
→ null / not applicable
```

Do not place processing timestamps, random run IDs or TransformationRun IDs inside deterministic artifact content.

---

# 13. Canonical Provenance Freeze

`provenance` must contain source-level lineage necessary to understand the transformed document.

For DOCUMENT, include authoritative snapshot equivalents such as:

```text
source_origin
usage_rights_note
original_filename   # if accepted as auxiliary provenance
```

Do not duplicate core top-level fields unnecessarily.

For LESSON, preserve only source provenance actually available from accepted persisted data.

Do not invent publisher/author/trust/authority metadata.

Do not add AI-generated provenance.

---

# 14. Canonical Block Schema Freeze

Logical typed model:

```text
Block
├── order
├── content_type
├── block_kind
├── text
├── section_path
├── source_locator
├── structured_data
└── metadata
```

Core fields remain explicit.

Do not hide:

```text
content_type
block_kind
section_path
source_locator
```

inside one generic `metadata` JSON.

`order` must be deterministic and consecutive for emitted Blocks.

---

# 15. Content-Type Freeze

Reuse exact V0 strings:

```text
DOCUMENT_TEXT
VOCABULARY
GRAMMAR
LESSON_GENERAL
```

Mapping:

```text
Document content
→ DOCUMENT_TEXT

Lesson Vocabulary
→ VOCABULARY

Lesson Grammar
→ GRAMMAR

Other Lesson content
→ LESSON_GENERAL
```

Do not add new semantic content types.

Do not duplicate an existing repository constant/enum if an equivalent already exists.

---

# 16. Block-Kind Freeze

Freeze V0 values equivalent to:

```text
HEADING
PARAGRAPH
LIST
CODE_BLOCK
TABLE
VOCABULARY_ITEM
GRAMMAR_SECTION
LESSON_GENERAL
```

Keep:

```text
content_type
≠
block_kind
```

Example:

```text
content_type = DOCUMENT_TEXT
block_kind   = PARAGRAPH
```

---

# 17. Parsed-Locator → Block-Kind Mapping

## PDF

```text
PDF_PAGE
→ PARAGRAPH
```

Preserve page locator.

Do not infer headings/sections.

---

## DOCX paragraph

```text
DOCX_PARAGRAPH
→ PARAGRAPH
```

---

## DOCX table rows

```text
DOCX_TABLE_ROW
→ group compatible rows by table_index
→ TABLE
```

Use D-055 row-level contract only.

---

## TXT

```text
TEXT_BLOCK
→ PARAGRAPH
```

---

## Markdown heading

```text
MARKDOWN_BLOCK
block_kind = HEADING
→ HEADING
```

---

## Markdown paragraph

```text
MARKDOWN_BLOCK
block_kind = PARAGRAPH
→ PARAGRAPH
```

---

## Markdown list item

Adjacent compatible:

```text
MARKDOWN_BLOCK
block_kind = LIST_ITEM
```

may be structurally grouped into:

```text
LIST
```

Do not group across incompatible `list_kind` / source ordering boundaries.

---

## Markdown code block

```text
MARKDOWN_BLOCK
block_kind = CODE_BLOCK
→ CODE_BLOCK
```

Preserve code text.

---

## Lesson Vocabulary

```text
LESSON_FIELD
section = VOCABULARY
→ VOCABULARY_ITEM
```

---

## Lesson Grammar

```text
LESSON_FIELD
section = GRAMMAR
→ GRAMMAR_SECTION
```

---

## Other Lesson content

```text
LESSON_FIELD
section = LESSON
→ LESSON_GENERAL
```

---

# 18. Document Transformation Freeze

Every persisted parsed Document type:

```text
PDF
DOCX
TXT
MD
```

must converge to the same `TransformedDocument` model.

Document Blocks:

```text
content_type = DOCUMENT_TEXT
```

regardless of structural `block_kind`.

Do not merge ordinary paragraphs merely to make bigger retrieval units.

Do not split long Blocks by characters/tokens.

Do not semantically deduplicate repeated content.

Do not create Chunk rows.

---

# 19. Lesson Transformation Freeze

Use only persisted Lesson parsed units.

Do not query live:

```text
Lesson
Vocabulary
Grammar
LessonVocabulary
LessonGrammar
```

to reconstruct transformed content.

Reconstruct entities from:

```text
source_id = lesson_id
+
source_locator.section
+
source_locator.entity_id
+
source_locator.field
+
source_locator.order_index
+
unit.text
```

Preserve deterministic source ordering.

---

# 20. Vocabulary Grouping Freeze

Group Lesson parsed units by:

```text
section = VOCABULARY
entity_id = vocabulary_id
order_index
```

Use:

```text
lesson_id = artifact.source_id
vocabulary_id = source_locator.entity_id
```

Use only upstream fields actually present.

Expected structured_data equivalent to:

```text
lesson_id
vocabulary_id
hanzi
pinyin
vietnamese_meaning
part_of_speech
example
note
```

Do not invent missing values.

---

# 21. Vocabulary Canonical Text Freeze

Generate deterministic text equivalent to:

```text
Từ: <hanzi>
Pinyin: <pinyin>
Nghĩa: <vietnamese_meaning>
Từ loại: <part_of_speech>
Ví dụ: <example>
Ghi chú: <note>
```

Rules:

```text
fixed line order
missing optional value
→ omit that line deterministically

no empty placeholder text
no paraphrasing
no translation
no LLM
```

Block:

```text
content_type = VOCABULARY
block_kind   = VOCABULARY_ITEM
section_path = ["Vocabulary"]
```

Preserve source/entity locator.

---

# 22. Grammar Grouping Freeze

Group Lesson parsed units by:

```text
section = GRAMMAR
entity_id = grammar_id
order_index
```

Use:

```text
lesson_id = artifact.source_id
grammar_id = source_locator.entity_id
```

Expected structured_data equivalent to:

```text
lesson_id
grammar_id
name
structure
explanation
usage
example
note
```

Use only fields actually present upstream.

---

# 23. Grammar Canonical Text Freeze

Generate deterministic text equivalent to:

```text
Ngữ pháp: <name>
Cấu trúc: <structure>
Giải thích: <explanation>
Cách dùng: <usage>
Ví dụ: <example>
Ghi chú: <note>
```

Rules:

```text
fixed line order
missing optional value
→ omit that line deterministically

no paraphrasing
no translation
no LLM formatter
```

Block:

```text
content_type = GRAMMAR
block_kind   = GRAMMAR_SECTION
section_path = ["Grammar", "<grammar name>"]
```

Do not invent a grammar name if missing; invalid required structure should fail typed validation rather than fabricate data.

---

# 24. Lesson General Freeze

Other persisted LESSON textual fields become canonical:

```text
content_type = LESSON_GENERAL
block_kind   = LESSON_GENERAL
section_path = ["Lesson"]
```

Title is also used for document-level `TransformedDocument.title`.

Avoid accidental duplication if title is required only as document metadata and a separate title Block would create an unwanted duplicate representation.

Follow the accepted parsed-field model consistently and test the chosen behavior.

Do not invent summary/topic metadata.

---

# 25. Section-Path Freeze

## PDF

```text
[]
```

No reliable heading hierarchy.

---

## DOCX

```text
[]
```

unless explicit reliable structure already exists in accepted parsed locator data.

Do not infer Word headings from text/style guesses.

---

## TXT

```text
[]
```

---

## Markdown

Maintain heading stack from explicit parsed heading units.

Example:

```text
# A
## B
paragraph
```

Paragraph:

```text
section_path = ["A", "B"]
```

Heading Block itself should use a consistent deterministic convention, e.g. path before or including itself, and tests/documentation must freeze that exact rule.

Do not infer hierarchy from non-heading text.

---

## Lesson Vocabulary

```text
["Vocabulary"]
```

---

## Lesson Grammar

```text
["Grammar", "<grammar name>"]
```

---

## Lesson general

```text
["Lesson"]
```

---

# 26. Markdown Structural Normalization

Allowed:

```text
adjacent compatible Markdown LIST_ITEM units
→ one LIST Block
```

`structured_data` may retain:

```text
list_kind
items[]
```

in source order.

Do not merge unrelated list runs.

Do not merge list with paragraphs.

This is structural normalization, not retrieval chunking.

---

# 27. Frozen D-055 — Truthful DOCX Table Preservation

Preserve only structure actually retained by Step 5.3.

Reliable:

```text
table_index
row_index
row order
deterministic row text
```

Not reliably retained:

```text
cells[]
```

Do **not** reconstruct cells using:

```text
split(row_text, "\t")
```

as a supposedly lossless rule.

Do not reopen Step 5.3 for V0 solely for cell preservation.

---

# 28. Canonical DOCX TABLE Representation

Group consecutive/compatible parsed rows sharing:

```text
table_index
```

into one canonical `TABLE` Block.

`structured_data` equivalent to:

```text
{
  "table_index": <int>,
  "rows": [
    {
      "row_index": <int>,
      "text": "<deterministic row text>"
    }
  ]
}
```

Do not expose:

```text
cells
```

Text representation must be deterministic and derived from the retained row text only.

Preserve row order.

Preserve enough source locator information to trace the canonical table back to the original parsed rows.

---

# 29. Source Locator Preservation

Canonical Blocks must preserve source traceability.

Do not replace locators with opaque new IDs.

For a one-to-one mapping:

```text
carry the original source_locator
```

For grouped structures such as:

```text
Markdown LIST
DOCX TABLE
Lesson entity
```

use a typed grouped locator/locator metadata shape that preserves sufficient source identity and range/member locators without fabricating unavailable details.

Do not discard:

```text
PDF page_number
DOCX table_index/row_index
Markdown block_index
Lesson entity_id/order_index/field lineage
```

Exact grouped locator shape must be deterministic and typed.

---

# 30. Empty Block Policy

Drop a Block only if:

```text
text is empty
AND
structured_data is empty
```

Short but meaningful content remains.

Do not add minimum text-length heuristics.

Do not remove repeated source content just because it appears duplicate.

---

# 31. No Long-Block Splitting

Do not split Blocks based on:

```text
characters
tokens
model context limits
retrieval limits
```

That belongs to Step 5.5.

A long source paragraph remains one Step-5.4 Block unless source structure itself creates multiple Blocks.

---

# 32. No Paragraph Merge

Do not merge independent parsed paragraphs to make larger Blocks.

Step 5.4:

```text
normalize source structure
```

Step 5.5:

```text
combine/split for retrieval
```

Keep the boundary strict.

---

# 33. No Semantic Deduplication

Do not perform:

```text
semantic similarity dedup
near-duplicate removal
LLM duplicate detection
```

Repeated source content may be meaningful.

---

# 34. No AI Enrichment

Do not generate through AI/LLM:

```text
topic
difficulty
grammar_category
semantic tags
summary
keywords
hierarchy
title
language
```

Transformation metadata comes only from:

```text
source_metadata_snapshot
explicit parsed structure
existing structured source fields
deterministic rules
```

---

# 35. No Per-Block Language Detection

Do not add language-detection tooling.

Use source-level:

```text
source_language
```

where authoritative.

For Lesson:

```text
source_language = null
```

Do not infer mixed/zh/vi.

---

# 36. Transformation Identity Freeze

Freeze:

```text
transformation_strategy = canonical_document
transformation_version  = v1
```

Persist both:

```text
TransformationRun
TransformedDocument
```

Do not create plugin/version-management infrastructure.

---

# 37. Determinism Freeze

Same:

```text
ParsedCleanedArtifact/v1
+
same source_metadata_snapshot
+
canonical_document/v1
```

must produce equivalent canonical transformed content.

Canonical serialization:

```text
UTF-8
stable Block order
sorted object keys
compact deterministic separators
```

Equivalent Python:

```python
json.dumps(
    data,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")
```

Do not include inside deterministic content:

```text
TransformationRun id
timestamp
random UUID
temporary path
runtime-only value
```

Two TransformationRuns over identical accepted inputs may therefore store byte-equivalent artifact content under different run-specific storage keys.

Do not introduce dedup/current selection behavior.

---

# 38. Typed Schema Validation

Use Pydantic following current repository conventions.

Before `SUCCEEDED`, validate at least:

```text
schema_version
source identity
title
source_language nullability
source_category nullability
provenance shape
transformation strategy/version
Blocks ordered
content_type
block_kind
text/structured_data validity
source_locator
section_path
```

Invalid canonical model:

```text
→ INVALID_TRANSFORMED_DOCUMENT
→ TransformationRun FAILED
→ no successful TransformedArtifactRef
```

Do not persist invalid artifact as successful downstream input.

---

# 39. Existing FileStorage Must Be Reused

Reuse:

```text
FileStorage
LocalFileStorage
```

Do not introduce:

```text
TransformedStorage
new filesystem abstraction
S3
MinIO
object store
```

unless an actual repository contradiction is found and reported as blocker.

Parsed artifact remains immutable upstream input.

Raw artifact remains untouched.

---

# 40. Transformed Artifact Storage Layout Freeze

Use server-generated storage keys.

Recommended layout equivalent to:

```text
transformed/
├── documents/
│   └── <document_id>/
│       └── <transformation_run_id>/
│           └── transformed_document.json
│
└── lessons/
    └── <lesson_id>/
        └── <transformation_run_id>/
            └── transformed_document.json
```

Properties:

```text
private
server generated
root-contained
one artifact per TransformationRun
no current/latest alias
```

Client/user text must not influence path.

---

# 41. TransformedArtifactRef Freeze

Internal Step-5.5 handoff:

```text
TransformedArtifactRef
├── transformation_run_id
├── source_type
├── source_id
├── storage_key
└── schema_version = transformed_document/v1
```

Step 5.5 receives:

```text
TransformedArtifactRef
+
FileStorage
```

and reads persisted canonical `TransformedDocument`.

Step 5.5 must not rerun:

```text
parsing
cleaning
transformation
```

when a successful ref is supplied.

Do not make Step 5.5 rediscover "latest/current".

---

# 42. Transformation Service Primitive

No public HTTP endpoint is required.

Freeze internal primitive equivalent to:

```text
transform_parsed_artifact(
    parsed_artifact: ParsedArtifactRef,
    ...
) -> TransformedArtifactRef
```

Exact dependency parameters may follow existing repository service/session/storage conventions.

Do not expose ORM objects through transformation interfaces.

Do not create:

```text
POST /admin/documents/{id}/transform
```

or frontend controls in Step 5.4.

---

# 43. Transformation Invocation Lifecycle

Recommended flow:

```text
validate ParsedArtifactRef
→ load persisted ParsedCleanedArtifact/v1
→ resolve/create source_metadata_snapshot
→ create TransformationRun(PENDING)
→ persist/commit

transition TransformationRun → PROCESSING
DOCUMENT → Document.processing_status = PROCESSING
→ commit

transform outside long DB transaction
→ typed TransformedDocument
→ deterministic JSON
→ write/finalize transformed artifact

transition TransformationRun → SUCCEEDED
→ transformed_storage_reference set
DOCUMENT → PREVIEW_READY
→ persist/commit

return TransformedArtifactRef
```

Exact number of short DB transactions may follow current conventions.

Do not hold a DB transaction open during slow transformation/file I/O.

---

# 44. Transformation Failure Semantics

On transformation failure:

```text
Raw Artifact remains
Parsed/Cleaned Artifact remains
TransformationRun → FAILED
stable error_code persisted
safe error_detail persisted
transformed_storage_reference = NULL
no successful TransformedArtifactRef
```

For DOCUMENT:

```text
Document.processing_status → FAILED
```

For LESSON:

```text
no Document status
```

Do not delete upstream artifacts.

---

# 45. Partial Failure — Transformed Artifact Finalization Failure

If canonical transformation succeeds but artifact finalization/storage fails:

```text
discard temporary transformed artifact
→ TransformationRun = FAILED
→ no transformed_storage_reference
→ no successful TransformedArtifactRef
→ preserve Parsed Artifact
→ preserve Raw Artifact
```

For Document:

```text
processing_status = FAILED
```

Do not report success.

---

# 46. Partial Failure — DB Success-State Persistence Failure

If transformed artifact finalization succeeds but final DB success-state persistence fails:

```text
delete orphan transformed artifact
→ do not report success
→ best-effort persist FAILED
→ safely log if FAILED persistence also fails
→ preserve Raw + Parsed artifacts
```

For Document, best-effort coarse state:

```text
FAILED
```

Do not leave:

```text
false SUCCEEDED
false PREVIEW_READY
orphan transformed artifact intentionally
```

Do not pretend PostgreSQL + filesystem are one atomic transaction.

---

# 47. Error Contract Freeze

Use stable equivalents:

```text
TRANSFORMATION_FAILED
INVALID_TRANSFORMED_DOCUMENT
UNSUPPORTED_CONTENT_TYPE
INVALID_SOURCE_LOCATOR
```

Use existing internal/ApplicationError conventions where errors cross application boundaries.

Do not expose or persist:

```text
raw Pydantic error dump
raw serializer exception
DB exception
filesystem path
stack trace
secret
```

No new broad error hierarchy.

---

# 48. Repository Boundary

Extend current ingestion repository only where needed.

Responsibilities may include:

```text
create TransformationRun
update TransformationRun state
load TransformationRun for tests
update Document.processing_status
load Document source metadata snapshot input
validate referenced ParsingRun where required
```

Do not put transformation formatting logic in repository.

Do not put filesystem work in repository.

Do not query live Lesson/Vocabulary/Grammar to reconstruct lesson content.

---

# 49. Transformation Package Boundary

Recommended separated structure equivalent to:

```text
backend/app/ingestion/transformation/
├── __init__.py
├── models.py
├── formatters.py
├── document_transformer.py
├── lesson_transformer.py
└── service.py
```

Do not build one giant transformation function containing:

```text
all source-specific mapping
all formatting
all persistence
all storage
all lifecycle
```

Keep structural mapping/formatting separate from lifecycle orchestration.

Do not build a plugin system.

---

# 50. Schemas

Extend current ingestion schemas or transformation-specific schemas with typed internal models equivalent to:

```text
TransformedDocument
Block
TransformedArtifactRef
content_type literals
block_kind literals
provenance model
structured-data variants
grouped source locator variants
source_metadata_snapshot model
```

No public API response schema is required.

---

# 51. No Relational Block Table

Blocks exist logically inside the canonical artifact.

Do not create:

```text
blocks table
block ORM model
one row per canonical Block
```

Persist transformed content as structured deterministic JSON.

Durable retrieval persistence remains later:

```text
KnowledgeSource
→ KnowledgeVersion
→ Chunk
→ Embedding
```

---

# 52. No KnowledgeVersion Work

Do not independently:

```text
create KnowledgeVersion
activate KnowledgeVersion
supersede KnowledgeVersion
select active KnowledgeVersion
```

inside transformation.

That belongs to later pipeline/version orchestration.

---

# 53. Runtime Dependency Freeze

Expected:

```text
NO new runtime dependency
```

Reuse:

```text
Pydantic
SQLAlchemy
PostgreSQL
Alembic
FileStorage
Python json
```

Do not add:

```text
language detector
Markdown library
table library
LLM SDK
workflow tool
queue package
```

If actual implementation proves a new runtime dependency necessary:

```text
STOP
→ report blocker
```

Do not silently add it.

---

# 54. Expected Files — Modify

Likely modify:

```text
backend/app/database/models/__init__.py

backend/app/ingestion/schemas.py
backend/app/ingestion/repository.py
backend/app/ingestion/storage.py   # only if narrow generic helper is required

backend/tests/test_database.py
backend/tests/test_migration_preservation.py
```

If current model import/registry conventions require another narrow existing file, make only the required change and report it.

Do not modify unrelated backend/frontend code.

---

# 55. Expected Files — Create

Likely create:

```text
backend/app/database/models/transformation.py

backend/app/ingestion/transformation/
    __init__.py
    models.py
    formatters.py
    document_transformer.py
    lesson_transformer.py
    service.py

backend/migrations/versions/
    0007_transformation_runs.py

backend/tests/test_step54_transformation.py
backend/tests/test_step54_transformation_service.py

docs/data/
    step-5.4-document-transformation.md
```

Exact names may follow current repository conventions.

Do not create:

```text
HTTP router
frontend files
Chunk implementation
```

---

# 56. Config / Env

No new configuration is required.

Do not add:

```text
chunk size
chunk overlap
language detector config
transformation worker count
queue URL
LLM provider config
```

---

# 57. Test Freeze — Canonical Model

Cover:

```text
PDF ParsedCleanedArtifact → TransformedDocument
DOCX → same canonical model
TXT → same canonical model
Markdown → same canonical model
Lesson → same canonical model
stable Block order
```

All persisted source types must converge to one typed downstream model.

---

# 58. Test Freeze — Content Types

Verify exact mapping:

```text
Document
→ DOCUMENT_TEXT

Vocabulary
→ VOCABULARY

Grammar
→ GRAMMAR

other Lesson content
→ LESSON_GENERAL
```

Unsupported semantic content type:

```text
→ UNSUPPORTED_CONTENT_TYPE
```

Do not invent new content types in tests or runtime.

---

# 59. Test Freeze — Block Kinds

Verify:

```text
Markdown heading
→ HEADING

normal paragraph
→ PARAGRAPH

adjacent compatible Markdown list items
→ LIST

Markdown code block
→ CODE_BLOCK

DOCX table rows
→ TABLE

Vocabulary
→ VOCABULARY_ITEM

Grammar
→ GRAMMAR_SECTION

Lesson general
→ LESSON_GENERAL
```

Explicitly prove:

```text
content_type != block_kind
```

as independent concepts.

---

# 60. Test Freeze — Vocabulary

Cover:

```text
structured fields preserved
lesson_id preserved
vocabulary_id preserved
order_index/source order preserved
canonical text deterministic
missing optional fields deterministic
section_path = ["Vocabulary"]
source locator lineage preserved
```

No invented values.

No LLM.

---

# 61. Test Freeze — Grammar

Cover:

```text
structured fields preserved
lesson_id preserved
grammar_id preserved
order_index/source order preserved
canonical text deterministic
missing optional fields deterministic
section_path = ["Grammar", grammar_name]
source locator lineage preserved
```

No invented values.

---

# 62. Test Freeze — Metadata Snapshot / Provenance

DOCUMENT:

```text
title comes from metadata snapshot
source_language preserved
source_category preserved
source_origin preserved
usage_rights_note preserved
later live Document metadata mutation does not alter the already-established TransformationRun snapshot
```

Important reproducibility test:

```text
create TransformationRun/source_metadata_snapshot
→ mutate live Document metadata
→ complete/repeat transformation using the same run snapshot input
→ canonical content still reflects snapshot, not mutated live metadata
```

LESSON:

```text
title comes from persisted parsed Lesson title unit
source_language = null
source_category = null
no language detection
```

PDF:

```text
page source locator retained
no invented heading/section
```

---

# 63. Test Freeze — DOCX Table Truthfulness

Verify:

```text
rows grouped by table_index
row_index preserved
row order preserved
row text preserved
TABLE block emitted
no cells[] field
no split("\t") cell reconstruction
```

A row containing a tab-like/ambiguous delimiter case must not be presented as reliable cell structure.

---

# 64. Test Freeze — Markdown Section Hierarchy

Cover explicit heading stack.

Example:

```text
# A
paragraph 1
## B
paragraph 2
```

Verify deterministic section paths.

Also verify:

```text
PDF/TXT/DOCX
→ no invented hierarchy
```

unless explicit accepted upstream structure exists.

---

# 65. Test Freeze — Lists

Given adjacent compatible Markdown list-item units:

```text
preserve item order
preserve ordered/unordered identity
→ one LIST Block
```

Break grouping when:

```text
list_kind changes
non-list unit interrupts
source order changes
```

Do not use retrieval-size grouping.

---

# 66. Test Freeze — Code Blocks

Verify:

```text
CODE_BLOCK remains one structural Block
text preserved
not merged into paragraphs
not normalized as prose
```

No execution.

---

# 67. Test Freeze — Empty / Short / Duplicate Behavior

Verify:

```text
text empty + structured_data empty
→ drop

short meaningful text
→ keep

duplicate/repeated source content
→ keep

long source paragraph
→ keep unsplit
```

No semantic dedup.

No retrieval thresholds.

---

# 68. Test Freeze — Deterministic Artifact

For identical:

```text
ParsedCleanedArtifact bytes/content
source_metadata_snapshot
canonical_document/v1
```

verify equivalent canonical JSON bytes.

Artifact must not contain:

```text
TransformationRun id
created_at
updated_at
random UUID
runtime timestamp
temporary path
```

Two distinct runs may have different storage keys but byte-equivalent transformed content.

---

# 69. Test Freeze — TransformationRun Lifecycle

Cover statuses:

```text
PENDING
PROCESSING
SUCCEEDED
FAILED
```

DB runtime tests must prove invalid status is rejected.

Verify DOCUMENT/LESSON source invariants at DB boundary.

Verify:

```text
SUCCEEDED
→ transformed_storage_reference required
→ error_code NULL
```

Verify:

```text
FAILED
→ transformed_storage_reference NULL
→ error_code required
```

Invalid combinations must be rejected by PostgreSQL, not only Pydantic.

---

# 70. Test Freeze — Parsing Lineage

Verify:

```text
TransformationRun.parsing_run_id
```

references the accepted specific ParsingRun.

Do not discover latest ParsingRun automatically.

A supplied parsed artifact/ref must map to the intended run.

Reject inconsistent source identity/lineage explicitly.

---

# 71. Test Freeze — Document processing_status

Document transformation:

```text
start
→ PROCESSING

success + valid canonical artifact
→ PREVIEW_READY

failure
→ FAILED
```

Explicitly prove success owns:

```text
PREVIEW_READY
```

Do not set:

```text
APPROVED
ACTIVE
```

---

# 72. Test Freeze — Lesson Lifecycle

LESSON transformation:

```text
uses TransformationRun
does not require Document row
does not update Document status
```

No Lesson-specific duplicate lifecycle model.

---

# 73. Test Freeze — Invalid Canonical Artifact

Inject transformation producing an invalid canonical model.

Verify:

```text
typed validation fails
TransformationRun = FAILED
no transformed_storage_reference
no successful TransformedArtifactRef
Parsed Artifact remains
Raw Artifact remains
```

Stable:

```text
INVALID_TRANSFORMED_DOCUMENT
```

or exact accepted equivalent.

---

# 74. Test Freeze — Artifact Finalization Failure

Inject transformed artifact finalization failure.

Verify:

```text
temporary transformed artifact removed
TransformationRun = FAILED
no transformed_storage_reference
no successful TransformedArtifactRef
Parsed Artifact survives
Raw Artifact survives
Document = FAILED for DOCUMENT
```

No false success.

---

# 75. Test Freeze — DB Success-State Failure

Inject DB failure:

```text
after transformed artifact finalization
before/while marking TransformationRun SUCCEEDED
```

Verify:

```text
finalized transformed artifact deleted
no false SUCCEEDED
no false PREVIEW_READY
upstream Parsed Artifact remains
Raw Artifact remains
best-effort FAILED behavior
no TransformedArtifactRef
```

If FAILED persistence also fails:

```text
safe logging
still no success result
```

---

# 76. Test Freeze — Step 5.5 Handoff

Verify a successful:

```text
TransformedArtifactRef
+
FileStorage
```

is sufficient to load:

```text
transformed_document/v1
```

without rerunning:

```text
parsing
transformation
```

A focused test should make transformer invocation observable/impossible and prove persisted artifact loading still succeeds.

Do not implement Step 5.5 chunking.

---

# 77. Test Freeze — No Future Stage

Verify no Step-5.4 code creates or mutates:

```text
Chunk rows
chunk size
chunk overlap
KnowledgeVersion
KnowledgeVersion activation
Embeddings
```

No hidden chunking behavior.

---

# 78. Test Freeze — Migration

Verify:

```text
0006 → 0007 upgrade
existing data survives
transformation_runs exists
source_type constraint
status constraint
source invariant
success invariant
failure invariant
foreign keys
indexes
source_metadata_snapshot persistence
downgrade 0007 → 0006
0006 schema remains usable
revision returns to 0006 after downgrade test
```

Run final:

```text
alembic current
alembic check
```

Do not rewrite migration history.

---

# 79. Full Backend Regression

Run full backend tests.

Required:

```text
all pytest PASS
```

Do not claim the Step complete when required verification is blocked.

Report unrelated warnings separately.

---

# 80. Step Note

Create:

```text
docs/data/step-5.4-document-transformation.md
```

Required sections:

## Objective

Build one canonical deterministic document model from persisted parsed artifacts.

## Why

Downstream chunking must operate on one stable source-independent contract rather than parser-specific structures.

## Mental Model

```text
Parsed/Cleaned Artifact
+
source metadata snapshot
→ canonical structural normalization
→ TransformedDocument
→ persisted transformed artifact
→ TransformedArtifactRef
```

## Core Knowledge

Only concepts actually used.

## Data Flow

Cover:

```text
Document
Lesson
success
failure
storage failure
DB partial failure
```

## Key Design Decisions

Include at least:

```text
TransformationRun
D-054 metadata snapshot
transformed_document/v1
canonical Block
content_type vs block_kind
Vocabulary/Grammar structured_data
truthful DOCX table rows
explicit section hierarchy only
canonical_document/v1
PREVIEW_READY ownership
FileStorage persistence
TransformedArtifactRef
no current/latest semantics
```

## Reusable Approach

Explain how a data pipeline maps heterogeneous parsed sources to one canonical intermediate data model before chunking/indexing.

## Common Mistakes

Include:

```text
chunking during transformation
flattening structured Lesson data
inventing DOCX cells
querying mutable live metadata after snapshot
inventing PDF sections
merging paragraphs for retrieval size
splitting long Blocks
semantic dedup
AI metadata enrichment
setting APPROVED/ACTIVE too early
storing huge canonical JSON inside lifecycle row
reusing ParsingRun for another stage
```

## Definition of Done

Reflect actual implementation/test evidence.

## Concepts Discovered

Use project-required table.

## Tools Used

Use project-required table.

---

# 81. Concepts Discovered Format

Use:

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|

Likely concepts if actually used:

```text
Canonical Data Model — DE
Structural Normalization — DE
Semantic Content Type — DE
Structural Block Kind — DE
Structured Data Preservation — DE
Source Metadata Snapshot — DE
Data Provenance — DE
Section Hierarchy — DE
Deterministic Transformation — DE
Intermediate Artifact — DE
Transformation Lifecycle — DE
Data Lineage — DE
Parsed-to-Transformed Contract — BOTH
Typed Validation — SYSTEM
Compensating Cleanup — SYSTEM
```

Record only concepts actually used.

---

# 82. Tools Used Format

Use:

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|

Likely tools if actually used:

```text
PostgreSQL — DE
SQLAlchemy — DE
Alembic — DE
Pydantic — SYSTEM
Python json — SYSTEM
FileStorage / LocalFileStorage — DE
pytest — SYSTEM
uv — SYSTEM
```

Do not list unused/future tools.

No new runtime dependency is expected.

---

# 83. Scope Guardrails / Non-Goals

Do not implement:

```text
Step 5.5 chunking
Chunk DB rows
chunk size
chunk overlap
token-aware splitting
semantic chunking
embedding
vector storage
retrieval
filtering
reranking
prompt construction
LLM generation
LLM metadata enrichment
semantic tagging
per-block language detection
semantic deduplication
KnowledgeVersion creation
KnowledgeVersion activation
pipeline orchestration
incremental/reprocessing/current policy
Admin Preview frontend
worker/queue
microservice
relational Block table
new storage provider
```

Step 5.4 ends at:

```text
persisted TransformedDocument
+
specific TransformedArtifactRef
```

---

# 84. Acceptance Criteria

Step 5.4 is acceptable only when all are true:

- [ ] `TransformationRun` exists in PostgreSQL.
- [ ] Exactly one forward migration `0007_transformation_runs` follows `0006`.
- [ ] Migrations `0001–0006` are unchanged.
- [ ] No relational Block table exists.
- [ ] No Chunk/KnowledgeVersion schema behavior is added.
- [ ] Every invocation creates a new TransformationRun.
- [ ] No current/latest/active/canonical/preferred run semantics exist.
- [ ] ParsingRun remains Step-5.3-specific.
- [ ] DOCUMENT/LESSON source invariant is DB-enforced.
- [ ] Transformation status values are DB-enforced.
- [ ] Success invariant is DB-enforced.
- [ ] Failure invariant is DB-enforced.
- [ ] TransformationRun references the specific ParsingRun.
- [ ] Source metadata snapshot is persisted.
- [ ] Document metadata snapshot is loaded once at run creation.
- [ ] Document canonical title comes from snapshot.
- [ ] Lesson title comes from persisted parsed artifact.
- [ ] Lesson source_language is null.
- [ ] Lesson source_category is null.
- [ ] No language detection exists.
- [ ] Schema identity is exactly `transformed_document/v1`.
- [ ] Strategy is exactly `canonical_document`.
- [ ] Version is exactly `v1`.
- [ ] Canonical `Block` has explicit core fields.
- [ ] V0 content types remain exact.
- [ ] V0 block kinds remain exact.
- [ ] content_type and block_kind remain independent.
- [ ] PDF/DOCX/TXT/MD converge to same canonical model.
- [ ] Vocabulary structured fields are preserved.
- [ ] Grammar structured fields are preserved.
- [ ] lesson_id/vocabulary_id/grammar_id lineage is preserved.
- [ ] Vocabulary text is deterministic.
- [ ] Grammar text is deterministic.
- [ ] PDF does not invent hierarchy.
- [ ] TXT does not invent hierarchy.
- [ ] DOCX does not invent hierarchy.
- [ ] Markdown heading stack is deterministic.
- [ ] DOCX tables preserve table/row identity and text.
- [ ] No DOCX `cells[]` is fabricated.
- [ ] No tab-split cell reconstruction is used.
- [ ] Paragraphs are not merged for retrieval size.
- [ ] Long Blocks are not split for retrieval limits.
- [ ] Repeated source content is not semantically deduplicated.
- [ ] Empty-only Blocks are dropped.
- [ ] Short meaningful Blocks remain.
- [ ] No AI enrichment exists.
- [ ] No per-block language detection exists.
- [ ] Canonical artifact bytes/content are deterministic for the accepted deterministic input.
- [ ] Deterministic artifact contains no run ID/timestamp/random noise.
- [ ] Artifact persists through existing FileStorage.
- [ ] `TransformedArtifactRef` exists.
- [ ] Step 5.5-style loading works without rerunning transformation.
- [ ] DOCUMENT start → PROCESSING.
- [ ] DOCUMENT success → PREVIEW_READY.
- [ ] DOCUMENT failure → FAILED.
- [ ] LESSON uses TransformationRun without Document update.
- [ ] Parsed/Cleaned Artifact survives all Step-5.4 failures.
- [ ] Raw Artifact survives all Step-5.4 failures.
- [ ] Finalization failure produces no false success.
- [ ] DB success-state failure removes orphan transformed artifact.
- [ ] No raw DB/filesystem/Pydantic internals leak into diagnostics.
- [ ] No new runtime dependency was added.
- [ ] Focused transformation tests pass.
- [ ] Transformation service/lifecycle tests pass.
- [ ] DB runtime invariant tests pass.
- [ ] Migration upgrade/downgrade tests pass.
- [ ] Full backend regression passes.
- [ ] Alembic current/check pass.
- [ ] Step Note is complete.
- [ ] Concepts/Tools tables use project format.
- [ ] No Step 5.5+ behavior was implemented.

---

# 85. Suggested Verification Commands

Use repository-standard commands.

Focused Step-5.4 tests:

```text
uv run pytest \
  tests/test_step54_transformation.py \
  tests/test_step54_transformation_service.py \
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

Use the repository's dedicated test PostgreSQL configuration.

Do not run destructive tests against production data.

---

# 86. Codex Constraints

Codex must:

```text
inspect current accepted Step-5.3 implementation before editing
reuse ParsedArtifactRef
reuse ParsingRun as lineage only
reuse FileStorage / LocalFileStorage
preserve D-053 / D-054 / D-055
follow existing ORM/migration constraint naming conventions
follow existing repository/session/error/logging conventions
keep DB transactions short
validate canonical artifact before success
preserve upstream artifacts on failure
```

Codex must NOT:

```text
change D-053
change D-054
change D-055
reopen Step 5.3 artifact schema
add DOCX cells[]
infer source metadata
infer PDF hierarchy
add language detection
add Chunk creation
add KnowledgeVersion
add active/latest transformation selection
add public transformation API
add frontend UI
add dependencies without reporting blocker
perform unrelated refactors
```

If the actual accepted repository materially contradicts this task:

```text
STOP
→ report exact contradiction
```

Do not choose a new architecture.

---

# 87. Required Codex Completion Handoff

Return:

```text
Step:
Status:

What was done:
- ...

D-053 preserved:
- ...

D-054 preserved:
- ...

D-055 preserved:
- ...

Files/components changed:
- ...

TransformationRun:
- schema
- constraints
- lifecycle
- parsing lineage

Migration:
- ...

Source metadata snapshot:
- DOCUMENT
- LESSON

TransformedDocument/v1:
- ...

Canonical Block:
- ...

Content-type mapping:
- ...

Block-kind mapping:
- ...

Document transformation:
- ...

Lesson transformation:
- ...

Vocabulary:
- ...

Grammar:
- ...

Section-path:
- ...

DOCX table:
- ...

Transformation strategy/version:
- ...

Artifact persistence:
- ...

Document processing_status:
- ...

TransformedArtifactRef:
- ...

Failure / cleanup:
- ...

Error contract:
- ...

Dependencies:
- ...

Concepts added:
- ...

Tools added:
- ...

Tests / verification:
- focused transformation
- service/lifecycle
- DB invariants
- migration/schema
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

# 88. Definition of Done

The Codex implementation is ready for Data Engineering specialist review only when:

```text
requirements satisfied
D-053 preserved
D-054 preserved
D-055 preserved
TransformationRun verified
migration 0007 verified
source metadata snapshot reproducible
canonical model implemented
block model implemented
Vocabulary/Grammar structure preserved
truthful DOCX table contract preserved
determinism verified
artifact persisted
PREVIEW_READY ownership verified
failure/cleanup verified
TransformedArtifactRef works
focused tests pass
DB runtime invariant tests pass
migration upgrade/downgrade pass
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

Do not begin Step 5.5 automatically.
