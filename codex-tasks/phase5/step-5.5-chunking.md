# Codex Task — Step 5.5 Chunking

## Task Identity

**Project:** LLM + RAG Web App học tiếng Trung cho người mới bắt đầu  
**Phase:** 5 — Data Engineering  
**Step:** 5.5 — Chunking  
**Owner:** Data Engineering Specialist  
**Task status:** FROZEN / READY FOR CODEX AFTER PM REVIEW  
**Implementation mode:** One Codex task = this Step only

Do not redesign architecture. Do not expand scope. Treat the current accepted repository state plus frozen decisions D-056, D-057, D-058 and D-059 as authoritative.

Do **not** implement production code outside this Step.

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

Step 5.4
→ PM ACCEPTED / CLOSED
```

Current Alembic head:

```text
0007_transformation_runs
```

Accepted Step-5.4 output boundary:

```text
TransformedArtifactRef
+
FileStorage
→ persisted transformed_document/v1
→ typed TransformedDocument
→ ordered canonical Blocks
```

Step 5.5 must consume this boundary only.

Do not:

```text
reparse raw PDF/DOCX/TXT/MD
rerun cleaning
rerun transformation
reread live Lesson/Vocabulary/Grammar content
rediscover latest/current TransformationRun
```

---

# 2. Objective

Implement deterministic structure-aware chunking from:

```text
TransformedDocument
└── ordered canonical Blocks
```

into:

```text
KnowledgeVersion(status = PROCESSING)
└── ordered flat Chunk[]
```

Each Chunk is a retrieval unit.

Step 5.5 ends at persisted Chunk rows.

Embedding begins later in Step 6.1.

Mental model:

```text
TransformedArtifactRef
→ load persisted TransformedDocument
→ deterministic chunk plan
→ validate complete plan
→ atomic replacement inside PROCESSING KnowledgeVersion
→ persisted flat Chunk[]
```

Chunking decides retrieval units.

It does **not** own source/version lifecycle creation or activation.

---

# 3. Input Contract Freeze

Step 5.5 receives:

```text
TransformedArtifactRef
+
knowledge_version_id
+
FileStorage
+
DB/session dependencies
```

Internal primitive equivalent to:

```text
build_chunks(
    transformed_artifact: TransformedArtifactRef,
    knowledge_version_id: UUID,
    ...
) -> chunk build result
```

Exact function names/signatures may follow repository conventions.

Step 5.5 must load the exact persisted:

```text
transformed_document/v1
```

through the existing Step-5.4 loader.

Do not rerun:

```text
parsing
cleaning
transformation
```

Do not expose ORM objects through chunk-planning interfaces.

---

# 4. Input Lineage Freeze

Before chunk planning validate the exact supplied transformed lineage.

Required checks:

```text
TransformationRun exists
status = SUCCEEDED
transformed_storage_reference matches TransformedArtifactRef.storage_key
source_type matches
source_id matches document_id / lesson_id
schema_version matches transformed_document/v1
```

Do not query:

```text
latest TransformationRun
current TransformationRun
active TransformationRun
```

Then validate KnowledgeVersion lineage:

```text
KnowledgeVersion exists
status = PROCESSING

KnowledgeVersion
→ KnowledgeSource
→ same logical source as TransformedArtifactRef
```

Reject mismatched source lineage explicitly.

No fuzzy/latest lookup.

---

# 5. KnowledgeVersion Ownership Freeze

Step 5.5 receives an already-existing:

```text
KnowledgeVersion(status = PROCESSING)
```

Step 5.5 does **not** create:

```text
KnowledgeSource
KnowledgeVersion
```

Step 5.6 orchestration owns:

```text
KnowledgeSource creation/reuse
KnowledgeVersion creation
version-number allocation
pipeline failure propagation
later activation flow
```

Step 5.5 does not activate a KnowledgeVersion.

Step 5.5 does not mark a KnowledgeVersion `FAILED`.

---

# 6. Frozen D-056 — Persistence Contract

Create exactly one forward migration:

```text
backend/migrations/versions/0008_chunking_contract.py
```

with:

```text
revision = 0008_chunking_contract
down_revision = 0007_transformation_runs
```

Do not modify migrations:

```text
0001–0007
```

---

# 7. KnowledgeVersion Config Freeze

Reuse existing fields:

```text
chunking_strategy
→ structure_aware

chunk_size
→ target_chars = 1200

chunk_overlap
→ overlap_chars = 150
```

Add nullable-for-legacy:

```text
chunking_version TEXT
chunk_max_chars INTEGER
```

For newly chunked PROCESSING KnowledgeVersions, application logic requires exactly:

```text
chunking_strategy = structure_aware
chunking_version  = v1
chunk_size        = 1200
chunk_max_chars   = 1800
chunk_overlap     = 150
```

Physical nullability remains nullable for legacy compatibility.

Do not invent/backfill values for legacy rows.

Do not create a second JSON config field that duplicates these values.

Do not duplicate full config on every Chunk.

---

# 8. Chunk Schema Freeze

Reuse existing stable fields:

```text
id UUID
knowledge_version_id
content
content_type
chunk_index
token_count
page_number
section
lesson_id
metadata JSONB
created_at
```

Keep existing unique order constraint equivalent to:

```text
UNIQUE(
  knowledge_version_id,
  chunk_index
)
```

Add nullable-for-legacy:

```text
content_hash TEXT
```

For newly created Step-5.5 Chunk rows:

```text
content_hash
→ logically required
```

Do not use `content_hash` as primary key.

Do not add:

```text
Embedding schema
parent_chunk_id
child chunks
hierarchical chunk fields
separate provenance table
KnowledgeVersion activation fields
```

---

# 9. Chunk Metadata Freeze

Reuse:

```text
Chunk.metadata JSONB
```

for variable provenance.

Freeze logical metadata schema equivalent to:

```text
chunk_metadata/v1

schema_version

section_path

block_start_order
block_end_order

source_ranges[]
  block_order
  source_locator
  char_start nullable
  char_end nullable

page_start nullable
page_end nullable

vocabulary_id nullable UUID
grammar_id nullable UUID

semantic_part_index nullable
semantic_part_count nullable

# where needed for semantic split details:
field_lineage nullable / structured
list/item split lineage where applicable
```

Core required fields for ordinary Chunks:

```text
schema_version = chunk_metadata/v1
section_path
block_start_order
block_end_order
source_ranges
page_start
page_end
vocabulary_id
grammar_id
```

For unsplit source Blocks:

```text
char_start = null
char_end = null
```

For forced split:

```text
char_start
char_end
```

must record exact deterministic source-text character ranges.

Do not flatten heterogeneous source locators into one misleading locator.

Do not create a separate provenance table.

Use typed Pydantic internal models for chunk plan/metadata if consistent with repository conventions.

---

# 10. Frozen D-057 — Chunk Content Hash

For every new Step-5.5 Chunk:

```text
content_hash
→ SHA-256
```

Hash canonical JSON equivalent to:

```json
{
  "content": "<exact persisted Chunk.content>",
  "content_type": "<exact V0 content type>"
}
```

Serialization:

```text
UTF-8
sorted keys
compact separators
```

Equivalent:

```python
payload = {
    "content": chunk.content,
    "content_type": chunk.content_type,
}

canonical = json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")

content_hash = hashlib.sha256(canonical).hexdigest()
```

Include only:

```text
content
content_type
```

Exclude:

```text
Chunk.id
knowledge_version_id
chunk_index
section
section_path
page_number
page ranges
source locators
lesson_id
vocabulary_id
grammar_id
timestamps
all provenance metadata
```

Meaning:

```text
hash equality
→ same canonical chunk payload
```

It does **not** mean:

```text
same Chunk identity
same provenance
deduplicate row
```

Never deduplicate rows by `content_hash`.

Two Chunks may have the same hash and different provenance.

---

# 11. Content Types Freeze

Reuse exact V0 values:

```text
DOCUMENT_TEXT
VOCABULARY
GRAMMAR
LESSON_GENERAL
```

Do not add speculative content types.

Hard rule:

```text
Chunk must never merge Blocks across content_type
```

Invalid examples:

```text
VOCABULARY + GRAMMAR
→ one Chunk
```

```text
LESSON_GENERAL + VOCABULARY
→ one Chunk
```

---

# 12. Chunking Strategy Freeze

Freeze:

```text
chunking_strategy = structure_aware
chunking_version  = v1
```

Dispatch:

```text
DOCUMENT_TEXT
→ structure-aware merge/split

VOCABULARY
→ atomic

GRAMMAR
→ atomic normally
→ D-058 exceptional fallback

LESSON_GENERAL
→ structure-aware merge/split
```

Do not use a single blind fixed-character sliding window for all content types.

Do not use embeddings or LLMs to choose boundaries.

---

# 13. Size Config Freeze

Centralized V0 values:

```text
target_chars  = 1200
max_chars     = 1800
overlap_chars = 150
```

Measurement:

```text
Unicode character count
```

Do not use model tokenizer.

Do not couple Step 5.5 to embedding model tokenization.

Meanings:

```text
target_chars
→ approximate merge/split target
→ not an exact cut point

max_chars
→ upper guard for generic textual chunks

overlap_chars
→ used only during forced split of one oversized textual unit
```

Do not scatter magic numbers.

Provide a central configuration/model/constants module.

---

# 14. Section Boundary Freeze

For mergeable textual content:

```text
same content_type
+
same section_path
+
continuous canonical source order
→ may merge if size allows
```

If:

```text
section_path changes
```

then:

```text
flush current Chunk
```

Do not cross section boundaries just to fill target size.

If `section_path` is empty:

```text
do not fabricate one
```

---

# 15. Section Persistence Freeze

Existing relational:

```text
Chunk.section TEXT
```

Projection:

```text
section_path = []
→ section = NULL

section_path = ["A", "B"]
→ section = "A > B"
```

Also preserve the full structured `section_path` in:

```text
Chunk.metadata
```

Do not rely on the flattened relational string as the only hierarchy representation.

---

# 16. Page Behavior Freeze

PDF page boundary alone is **not** a Chunk boundary.

Adjacent PDF Blocks may merge when:

```text
same content_type
same section_path
continuous canonical order
size allows
```

Preserve aggregate page provenance:

```text
page_start
page_end
```

Existing:

```text
Chunk.page_number
```

rules:

```text
page_start == page_end
→ page_number = that page

page_start != page_end
→ page_number = NULL
```

Full page range remains in `chunk_metadata/v1`.

Never lose exact page trace.

---

# 17. Chunk Ordering Freeze

Assign:

```text
chunk_index = 0,1,2,...
```

according to canonical source order inside one KnowledgeVersion.

Do not reorder by:

```text
length
topic
content_hash
future retrieval score
```

Existing unique constraint remains final DB safety net:

```text
UNIQUE(knowledge_version_id, chunk_index)
```

---

# 18. Vocabulary Freeze

Default:

```text
1 Vocabulary Block
→ 1 Chunk
```

Ignore generic target size.

Do not:

```text
merge multiple Vocabulary entities
split normal Vocabulary entities
delete short Vocabulary content
```

Preserve:

```text
Chunk.content_type = VOCABULARY
Chunk.lesson_id
metadata.vocabulary_id
block range
source locator/entity lineage
```

Target size does not force Vocabulary merging.

Vocabulary may exceed generic target.

V0 does not apply forced generic split to normal Vocabulary entities.

---

# 19. Grammar Freeze

Normal Grammar:

```text
1 Grammar entity
→ 1 Chunk
```

Do not split merely because:

```text
len(content) > target_chars
```

Preserve:

```text
content_type = GRAMMAR
lesson_id
grammar_id
canonical Grammar content
entity/source lineage
```

Exceptional behavior follows D-058 exactly.

---

# 20. Frozen D-058 — Exceptional Oversized Grammar

Fallback activates only when:

```text
len(canonical Grammar content) > max_chars
```

V0:

```text
max_chars = 1800
```

First split at complete canonical Grammar field boundaries in this stable order:

```text
name
structure
explanation
usage
example
note
```

Pack complete fields into Chunk parts while respecting:

```text
max_chars
```

Do not rearrange fields.

Do not merge different Grammar entities.

If one individual Grammar field itself exceeds `max_chars`:

```text
use deterministic forced oversized-text splitter
overlap_chars = 150
only within that same oversized field
```

Every resulting Grammar Chunk part preserves:

```text
content_type = GRAMMAR
lesson_id
grammar_id
entity/source lineage
field lineage
semantic_part_index
semantic_part_count
stable part order
```

Rules:

```text
no truncation
no LLM
no semantic chunking
no splitting normal Grammar merely for target size
```

When multiple fields are packed into one part, Chunk.content must remain deterministic and source-derived using the same canonical field text labels/order already established by Step 5.4.

Do not invent new grammar wording.

---

# 21. Document Text Freeze

Applies:

```text
content_type = DOCUMENT_TEXT
```

Expected flow:

```text
ordered compatible Blocks
→ respect section boundary
→ merge adjacent small compatible Blocks
→ target-sized Chunk
→ forced split only for oversized textual unit
```

Do not flatten the full document into one giant string first.

Do not semantic-deduplicate repeated source content.

Do not infer source-format-specific meaning beyond canonical Step-5.4 fields.

---

# 22. Lesson-General Freeze

Applies:

```text
content_type = LESSON_GENERAL
```

Use the same structure-aware generic textual strategy as DOCUMENT_TEXT:

```text
same content_type
same section_path
continuous canonical order
size allows
→ merge
```

Do not merge LESSON_GENERAL with:

```text
VOCABULARY
GRAMMAR
```

Do not reread live Lesson data.

---

# 23. Generic Text Merge Freeze

Applies to:

```text
DOCUMENT_TEXT
LESSON_GENERAL
```

Deterministic equivalent:

```text
current empty
→ start with Block

current length >= target_chars
→ flush before next normal Block

current + "\n\n" + next <= max_chars
AND same section_path
AND same content_type
AND continuous order
→ merge

adding next would exceed max_chars
→ flush current
→ process next independently
```

`target_chars`:

```text
merge target
not exact cut point
```

`max_chars`:

```text
generic upper guard
```

Semantic/source boundaries beat size filling.

Do not impose a global minimum Chunk length.

Short meaningful content is valid.

---

# 24. Heading Freeze

Canonical Markdown heading behavior from Step 5.4 is authoritative.

A:

```text
HEADING
```

may start the current textual candidate.

Following Block may merge forward if:

```text
same section_path
same content_type
continuous order
combined length <= max_chars
```

Do not merge heading backward across a previous section boundary.

If no compatible following content exists:

```text
standalone short heading Chunk is allowed
```

Avoid crossing semantic boundaries merely to avoid a tiny heading.

Keep heading text in Chunk.content when merged.

`section_path` remains provenance separately.

---

# 25. Frozen D-059 — DOCX TABLE Chunking

Canonical TABLE reliably contains only:

```text
table_index
rows[]
  row_index
  text
```

There is no authoritative:

```text
header flag
header identity
cells[]
```

Therefore:

### Small TABLE

If deterministic table representation fits:

```text
<= max_chars
```

then:

```text
one TABLE
→ one Chunk
```

### Large TABLE

Split only between complete ordered row groups.

Preserve:

```text
table_index
row_index
row order
row text
source lineage
```

Do not repeat a header row.

Do not assume:

```text
row_index = 0
→ header
```

Do not fabricate:

```text
cells[]
```

Do not split row text as though cell semantics exist.

### One oversized row

If one retained row itself exceeds:

```text
max_chars
```

then:

```text
CHUNK_TOO_LARGE
```

or the exact frozen stable equivalent.

Do not split the row.

Do not reopen Step 5.4.

---

# 26. TABLE Chunk.content

Chunk.content for a TABLE must remain deterministic and source-derived from retained row text.

Use a narrow stable representation such as:

```text
row 0 text
row 1 text
...
```

without fabricating header/cell structure.

Exact delimiter/newline representation must be centralized and tested.

Do not add synthetic “Table:”/“Header:” labels solely for embeddings.

Preserve detailed row structure in `metadata`.

---

# 27. LIST Freeze

Canonical LIST provides:

```text
list_kind
items[]
```

### Normal LIST

If deterministic list representation fits:

```text
<= max_chars
```

then:

```text
one LIST
→ one Chunk
```

### Oversized LIST

Pack complete items in source order into groups:

```text
each Chunk <= max_chars
```

Break grouping only between items first.

If one individual item exceeds `max_chars`:

```text
forced text splitter
```

may split inside that item as final fallback.

Preserve:

```text
list_kind
item order
part order
source lineage
exact split char ranges
```

Do not use generic sliding-window behavior across the whole list.

---

# 28. Forced Text Split Freeze

Used only when one textual unit itself exceeds:

```text
max_chars
```

Examples:

```text
oversized DOCUMENT_TEXT Block
oversized LESSON_GENERAL Block
oversized LIST item
oversized Grammar field under D-058
```

Separator preference, in order:

```text
paragraph boundary
→ line boundary
→ sentence punctuation:
   。！？.!?；;
→ whitespace
→ hard character boundary
```

Rules:

```text
target_chars = preferred split vicinity
max_chars = absolute generic upper guard
overlap_chars = 150
```

Preserve stable source order.

No NLP sentence tokenizer.

No third-party semantic splitter.

No LLM.

---

# 29. Overlap Freeze

Normal neighboring Chunks:

```text
NO overlap
```

Overlap is only for:

```text
forced split parts of the SAME oversized textual unit
```

Use:

```text
overlap_chars = 150
```

Do not implement a global sliding-window overlap.

Do not overlap independently merged neighboring chunks.

---

# 30. Split-Range Provenance Freeze

When forced-splitting source text:

```text
source_ranges[].char_start
source_ranges[].char_end
```

must refer to deterministic character offsets in the original canonical source text represented by that source Block/field/item.

Define one offset convention and test it.

Recommended:

```text
0-based
start inclusive
end exclusive
```

Do not count synthetic separators added only between merged independent Blocks as source-text ranges.

Overlap means adjacent split parts may have overlapping char ranges from the same source text.

For unsplit source units:

```text
char_start = null
char_end = null
```

---

# 31. Chunk.content Freeze

Chunk.content must remain:

```text
source-derived
deterministic
```

Do not prepend synthetic retrieval/embedding-only metadata such as:

```text
Document: ...
Section: ...
Page: ...
```

Store title/source/section/provenance separately.

Step 6.1 may later decide how embedding input is formatted without mutating canonical Chunk.content.

---

# 32. Provenance Freeze

Every Chunk must remain traceable to canonical source.

Stable relational fields:

```text
knowledge_version_id
chunk_index
content_type
section
page_number
lesson_id
```

Variable provenance in:

```text
chunk_metadata/v1
```

must retain equivalent:

```text
section_path
block_start_order
block_end_order
source_ranges
page_start
page_end
vocabulary_id
grammar_id
split char ranges
semantic part information where applicable
```

Do not rely on text matching.

Do not discard detailed locator lineage just because relational fields exist.

---

# 33. Locator Aggregation Freeze

When merging canonical Blocks:

```text
block_start_order
→ first Block.order

block_end_order
→ last Block.order
```

Aggregate source ranges deterministically in canonical source order.

If multiple locators are present:

```text
preserve ordered source_ranges[]
```

Do not flatten them into one false locator.

For PDF:

```text
page_start = minimum represented page
page_end   = maximum represented page
```

For Vocabulary:

```text
metadata.vocabulary_id
```

For Grammar:

```text
metadata.grammar_id
```

For semantic Grammar parts:

```text
semantic_part_index
semantic_part_count
field lineage
```

must remain deterministic.

---

# 34. Token Count Freeze

Existing:

```text
Chunk.token_count
```

must remain:

```text
NULL
```

for Step-5.5-created chunks unless an already-accepted repository convention explicitly owns it.

Do not define embedding tokenizer semantics here.

Embedding token semantics belong later.

---

# 35. Rerun / Idempotency Freeze

The same PROCESSING KnowledgeVersion may be safely rebuilt.

Do not:

```text
rerun
→ append duplicate Chunk set
```

Freeze:

```text
build complete deterministic plan
→ validate complete plan
→ atomically replace persisted Chunk set
```

Retry must mean:

```text
replace
not append
```

No source-change policy is implemented here.

---

# 36. Atomic Persistence Freeze

Build and validate complete Chunk plan before DB write transaction where practical.

Write transaction:

```text
BEGIN

SELECT KnowledgeVersion ... FOR UPDATE

recheck:
  status = PROCESSING
  KnowledgeSource identity matches transformed source

DELETE existing Chunks
WHERE knowledge_version_id = supplied version

INSERT full deterministic Chunk replacement set

persist KnowledgeVersion chunk config:
  chunking_strategy
  chunking_version
  chunk_size
  chunk_max_chars
  chunk_overlap

COMMIT
```

If persistence/config update fails:

```text
ROLLBACK
```

Expected result:

```text
previous complete Chunk set remains intact
```

No half-replaced set.

Do not hold the DB transaction across unnecessary FileStorage reads or chunk-plan computation.

---

# 37. Concurrency / Row-Lock Freeze

Use:

```text
SELECT KnowledgeVersion ... FOR UPDATE
```

or existing SQLAlchemy equivalent inside write transaction.

Purpose:

```text
serialize rebuilds of one KnowledgeVersion
recheck status/source identity
prevent stale PROCESSING read from mutating ACTIVE version
```

Do not globally serialize chunking across all versions.

Different KnowledgeVersions should not require a global lock.

---

# 38. ACTIVE Protection Freeze

Before planning/persistence and again inside the locked write transaction:

```text
KnowledgeVersion.status != PROCESSING
→ KNOWLEDGE_VERSION_NOT_PROCESSING
```

ACTIVE:

```text
never rebuilt
never deleted
never modified
```

SUPERSEDED/FAILED similarly are not valid chunk-build targets unless future policy explicitly changes.

Step 5.5 never activates version.

Step 5.5 never marks version FAILED.

Step 5.6 owns pipeline-stage failure propagation.

---

# 39. Chunk Plan Validation Freeze

Before persistence validate at least:

```text
content non-empty
content_type exact V0 value
chunk_index valid and consecutive
stable source ordering
valid chunk_metadata/v1
source trace present
no cross-content-type merge
no cross-section merge for mergeable text
size rules obeyed where applicable
content_hash present and correct
lesson/entity lineage valid where required
page range coherent
split ranges coherent
```

Semantic exceptions:

```text
Vocabulary may be short
normal Grammar may exceed target_chars
```

Do not silently truncate oversized semantic units.

---

# 40. Error Contract Freeze

Freeze exact stable codes:

```text
CHUNKING_FAILED
INVALID_CHUNKING_INPUT
KNOWLEDGE_VERSION_NOT_PROCESSING
INVALID_CHUNK
CHUNK_TOO_LARGE
```

Semantics:

### INVALID_CHUNKING_INPUT

Use for:

```text
missing/malformed transformed artifact
TransformationRun lineage mismatch
source mismatch
KnowledgeSource source mismatch
unsupported transformed canonical structure required by V0
```

### KNOWLEDGE_VERSION_NOT_PROCESSING

Use when supplied KnowledgeVersion is not:

```text
PROCESSING
```

### INVALID_CHUNK

Use when generated Chunk plan violates a Step-5.5 invariant.

### CHUNK_TOO_LARGE

Use when source structure cannot be truthfully split under frozen rules, e.g.:

```text
one DOCX table row > max_chars
```

### CHUNKING_FAILED

Use for unexpected/persistence technical failure.

Do not expose:

```text
raw DB exception
filesystem path
stack trace
internal Pydantic dump
```

No public HTTP route is required in Step 5.5.

---

# 41. Dependency Freeze

No new runtime dependency.

Use existing / standard-library:

```text
Python hashlib
Python json
Pydantic
SQLAlchemy
PostgreSQL
Alembic
FileStorage
pytest
uv
```

Do not add:

```text
tokenizer
LangChain
LlamaIndex
NLP sentence splitter
LLM SDK
semantic chunking package
queue/worker framework
```

---

# 42. Repository Boundary

Extend existing ingestion/data repository only where needed.

Likely responsibilities:

```text
load KnowledgeVersion with KnowledgeSource
lock KnowledgeVersion FOR UPDATE
delete chunks for version
bulk/add replacement Chunk rows
persist chunking config
```

Do not put chunking strategy logic in repository.

Do not put file loading in repository.

Do not create KnowledgeVersion in Step 5.5.

---

# 43. Chunking Package Boundary

Recommended structure equivalent to:

```text
backend/app/ingestion/chunking/
├── __init__.py
├── models.py
├── config.py
├── text_splitter.py
├── locator.py
├── strategy.py
└── service.py
```

Responsibilities:

```text
models.py
→ typed Chunk plan / metadata models

config.py
→ frozen V0 configuration

text_splitter.py
→ deterministic forced splitter

locator.py
→ source-range/page/entity aggregation

strategy.py
→ content-type dispatch and block → planned chunks

service.py
→ lineage validation + persisted artifact load + atomic DB replacement
```

Exact file organization may follow current repository style.

Do not build a framework/plugin system.

---

# 44. Migration 0008 Freeze

Create exactly:

```text
backend/migrations/versions/0008_chunking_contract.py
```

Upgrade adds only:

```text
knowledge_versions.chunking_version
knowledge_versions.chunk_max_chars
chunks.content_hash
```

All nullable physically for legacy compatibility.

Do not backfill invented values.

Downgrade removes only Step-5.5 additions and restores 0007-compatible schema.

Do not modify:

```text
0001–0007
```

Do not add unrelated schema.

---

# 45. ORM Freeze

Update actual ORM to match migration.

`KnowledgeVersion`:

```text
chunking_version: nullable str
chunk_max_chars: nullable int
```

Practical DB CHECK constraints may be added only if consistent with repository conventions and the frozen semantics, e.g. positive numeric values when non-null.

Do not make new fields physically NOT NULL because legacy rows exist.

`Chunk`:

```text
content_hash: nullable str
```

Application logic requires it for Step-5.5 writes.

Do not add unique constraint on content_hash.

---

# 46. Expected Files — Modify

Likely modify:

```text
backend/app/database/models/knowledge.py
backend/app/ingestion/repository.py

backend/tests/test_database.py
backend/tests/test_migration_preservation.py
```

May also modify existing package exports/model registry if actual repository conventions require it.

Do not perform unrelated refactors.

---

# 47. Expected Files — Create

Likely create:

```text
backend/app/ingestion/chunking/
    __init__.py
    models.py
    config.py
    text_splitter.py
    locator.py
    strategy.py
    service.py

backend/migrations/versions/
    0008_chunking_contract.py

backend/tests/test_step55_chunking.py
backend/tests/test_step55_chunking_service.py

docs/data/
    step-5.5-chunking.md
```

Do not create:

```text
HTTP routes
frontend files
Embedding code
Step-5.6 orchestrator
worker/queue
```

---

# 48. Test Freeze — Strategy Dispatch

Cover:

```text
DOCUMENT_TEXT
→ structure-aware

VOCABULARY
→ atomic

GRAMMAR
→ atomic normally / D-058 fallback

LESSON_GENERAL
→ structure-aware
```

Cross-content merge:

```text
forbidden
```

---

# 49. Test Freeze — Vocabulary

Cover:

```text
1 entity → 1 Chunk
short entity retained
target size does not cause merge
multiple Vocabulary entities not merged
lesson_id preserved
vocabulary_id preserved in metadata
source locator lineage preserved
block range preserved
content_hash deterministic
```

Duplicate Vocabulary text with different provenance:

```text
both rows retained
```

---

# 50. Test Freeze — Grammar

Normal Grammar:

```text
1 entity → 1 Chunk
semantic fields remain together
lesson_id preserved
grammar_id preserved
source/entity lineage preserved
target_chars does not force split
```

Oversized Grammar:

```text
len(content) > 1800
→ D-058 field-aware fallback

complete field boundaries used first
stable field order
semantic_part_index/count
field lineage
no truncation
```

Oversized individual field:

```text
forced splitter
overlap = 150
only within that field
exact char ranges retained
```

No merge across Grammar entities.

---

# 51. Test Freeze — Generic Document Text

Cover:

```text
compatible small Blocks merge
section change flushes
cross-content-type merge forbidden
page change alone does not flush
multi-page chunk preserves page_start/page_end
page_number set only for single-page range
heading merges forward when compatible
heading never merges backward across previous section
standalone heading allowed
oversized paragraph splits deterministically
no semantic dedup
no global minimum
```

---

# 52. Test Freeze — Lesson General

Cover:

```text
compatible LESSON_GENERAL Blocks merge
section boundary flushes
does not merge with Vocabulary
does not merge with Grammar
oversized text forced split deterministic
provenance retained
```

---

# 53. Test Freeze — TABLE

Cover:

```text
small table → one Chunk
large table → ordered complete row groups
table_index retained
row_index retained
row order retained
row text retained
no cells[]
no header repetition
row_index=0 not treated as header
```

One oversized row:

```text
→ CHUNK_TOO_LARGE
```

No row splitting.

No fake cell semantics.

---

# 54. Test Freeze — LIST

Cover:

```text
normal LIST together
ordered/unordered list_kind preserved
large LIST splits between complete items
item order retained
one oversized item forced-splits deterministically
overlap only inside oversized item
item/source lineage retained
```

Do not split normal items unnecessarily.

---

# 55. Test Freeze — Size Semantics

Cover:

```text
target_chars guides merging
target is not exact cut
max_chars enforced for generic text
no global minimum
normal neighboring chunks have no overlap
forced split uses overlap_chars = 150
natural separator preference applied
hard character fallback works
Unicode character counting
```

No tokenizer.

---

# 56. Test Freeze — Forced Split Separator Preference

Create focused deterministic inputs proving preference order:

```text
paragraph boundary
before
line boundary

line boundary
before
sentence punctuation

sentence punctuation
before
whitespace

whitespace
before
hard character boundary
```

Include:

```text
Chinese punctuation
Vietnamese/Latin punctuation
```

Ensure no semantic/NLP tokenizer dependency.

---

# 57. Test Freeze — Provenance

Cover:

```text
section_path retained
block_start_order retained
block_end_order retained
source_ranges deterministic
source_locator retained
page_start/page_end retained
lesson_id retained
vocabulary_id retained
grammar_id retained
forced-split char ranges retained
Grammar semantic part fields retained
```

Do not rely on text matching in tests.

---

# 58. Test Freeze — Chunk Ordering

Cover:

```text
chunk_index = 0,1,2,...
```

in canonical source order.

Verify rerun produces equivalent logical ordering.

Do not derive ordering from UUID/hash.

---

# 59. Test Freeze — Hash

Verify exact D-057 contract:

```text
content + content_type
→ SHA-256
```

Prove excluded data does not affect hash:

```text
chunk_index differs
section differs
page differs
lesson_id differs
provenance differs
→ same hash if content + content_type equal
```

Prove semantic content type matters:

```text
same content
DOCUMENT_TEXT vs GRAMMAR
→ different hash
```

Verify:

```text
Chunk UUID independent from hash
```

Verify equal hashes do not cause dedup.

---

# 60. Test Freeze — Input Lineage

Cover:

```text
exact TransformedArtifactRef accepted
TransformationRun missing → INVALID_CHUNKING_INPUT
TransformationRun not SUCCEEDED → INVALID_CHUNKING_INPUT
storage reference mismatch → INVALID_CHUNKING_INPUT
source_type mismatch → INVALID_CHUNKING_INPUT
source target mismatch → INVALID_CHUNKING_INPUT
transformed payload source mismatch → INVALID_CHUNKING_INPUT
KnowledgeSource logical source mismatch → INVALID_CHUNKING_INPUT
```

No latest/current lookup.

---

# 61. Test Freeze — KnowledgeVersion Lifecycle

Cover:

```text
PROCESSING
→ accepted

ACTIVE
→ KNOWLEDGE_VERSION_NOT_PROCESSING
→ untouched

SUPERSEDED
→ rejected

FAILED
→ rejected
```

Step 5.5:

```text
does not create KnowledgeVersion
does not activate KnowledgeVersion
does not mark KnowledgeVersion FAILED
```

---

# 62. Test Freeze — Rerun / Idempotency

Given one PROCESSING KnowledgeVersion:

```text
first build
→ Chunk set A

second build same deterministic input
→ replaces Chunk set
→ no append duplicates
```

Verify:

```text
row count equals planned count
chunk_index unique
content/provenance deterministic
config remains frozen values
```

Do not require same Chunk UUIDs across rebuild unless actual repository behavior deliberately preserves them; UUID identity is not part of deterministic chunk payload.

---

# 63. Test Freeze — Atomic Persistence

Prepare an existing complete Chunk set.

Inject failure during:

```text
replacement insert
or
chunk-config persistence
```

Verify:

```text
transaction rolls back
previous complete Chunk set remains
no partial new set
KnowledgeVersion remains PROCESSING
no activation
```

Do not commit delete separately from inserts.

---

# 64. Test Freeze — ACTIVE Protection Race

Where practical, verify status is rechecked under row lock.

At minimum:

```text
initially read PROCESSING
status becomes ACTIVE before write transaction
write transaction locks/reloads
→ rejects
→ existing ACTIVE chunks untouched
```

If exact concurrency integration test is impractical in repository test style, isolate the locked persistence boundary and prove it rejects a non-PROCESSING state.

Do not weaken the lock requirement.

---

# 65. Test Freeze — KnowledgeVersion Config

After successful build verify:

```text
chunking_strategy = structure_aware
chunking_version = v1
chunk_size = 1200
chunk_max_chars = 1800
chunk_overlap = 150
```

Legacy rows may retain NULL for new fields.

New Step-5.5 builds may not.

---

# 66. Test Freeze — token_count

Verify Step-5.5-created Chunk rows keep:

```text
token_count = NULL
```

No embedding tokenizer semantics.

---

# 67. Test Freeze — Step-6.1 Boundary

Verify successful Step 5.5 yields:

```text
KnowledgeVersion
status = PROCESSING

complete persisted flat Chunk[]
```

and nothing more.

No:

```text
Embedding rows
vector values
retrieval index updates
KnowledgeVersion activation
```

Step 6.1 must be able to consume persisted Chunk rows later.

Do not implement Step 6.1.

---

# 68. Test Freeze — Migration

Verify:

```text
0007 → 0008 upgrade
legacy KnowledgeVersion rows survive
legacy Chunk rows survive

new columns:
knowledge_versions.chunking_version
knowledge_versions.chunk_max_chars
chunks.content_hash

new fields nullable for legacy rows
new ORM matches DB

downgrade 0008 → 0007
Step-5.5 columns removed
0007 schema remains usable
revision returns to 0007
```

Do not rewrite old migrations.

Run final:

```text
alembic current
alembic check
```

---

# 69. Full Backend Regression

Run:

```text
uv run pytest
```

All required tests must pass.

Do not claim completion if required verification is blocked or fails.

Report unrelated warnings separately.

---

# 70. Step Note

Create:

```text
docs/data/step-5.5-chunking.md
```

Required headings:

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

---

## Objective

Explain that Step 5.5 converts source-independent canonical Blocks into deterministic retrieval units stored as flat Chunk rows.

---

## Why

Explain why retrieval requires chunk units, but chunking must remain separate from:

```text
transformation
embedding
retrieval
KnowledgeVersion activation
```

---

## Mental Model

Use:

```text
TransformedDocument
→ deterministic Chunk plan
→ validate complete plan
→ atomic replacement
→ persisted Chunk[]
```

---

## Core Knowledge

Only concepts actually used.

---

## Data Flow

Cover:

```text
TransformedArtifactRef
→ TransformationRun validation
→ TransformedDocument load
→ KnowledgeVersion validation
→ content-type dispatch
→ complete Chunk plan
→ validation
→ atomic replacement
```

Also cover:

```text
rerun
failure rollback
ACTIVE rejection
```

---

## Key Design Decisions

Include:

```text
D-056 persistence contract
D-057 content hash
D-058 Grammar fallback
D-059 TABLE contract

structure_aware/v1
1200/1800/150
no tokenizer
content-type dispatch
section boundaries
page range behavior
Vocabulary atomic semantics
Grammar exceptional field-aware fallback
truthful table row groups
list item grouping
forced splitter
chunk_metadata/v1
atomic replace
FOR UPDATE ACTIVE protection
token_count deferred
```

---

## Reusable Approach

Explain reusable pipeline pattern:

```text
canonical intermediate artifact
→ deterministic chunk plan
→ validate plan
→ atomic durable replacement
```

---

## Common Mistakes

Include:

```text
blind fixed sliding window
merging across content types
crossing explicit sections
splitting Vocabulary because it is short/long
splitting normal Grammar for target size
fabricating DOCX headers/cells
global overlap
synthetic embedding metadata in content
hash-based dedup
using tokenizer before embedding model ownership
appending on rerun
mutating ACTIVE version
holding transaction across file I/O/chunk planning
activating KnowledgeVersion in chunking
embedding inside Step 5.5
```

---

## Definition of Done

Reflect actual implementation and verification evidence.

---

# 71. Concepts Discovered Format

Use:

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|

Likely concepts if actually used:

```text
Chunking — DE
Structure-Aware Chunking — DE
Semantic Boundary — DE
Character Budget — DE
Overlap — DE
Forced Text Splitting — DE
Chunk Provenance — DE
Locator Aggregation — DE
Content Hash — DE
Idempotent Rebuild — DE
Atomic Persistence — DE
KnowledgeVersion Safety — DE
Transformed-to-Chunk Contract — BOTH
Row Locking — SYSTEM
Typed Validation — SYSTEM
```

Only record concepts actually present.

---

# 72. Tools Used Format

Use:

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|

Likely tools if actually used:

```text
PostgreSQL — DE
SQLAlchemy — DE
Alembic — DE
Pydantic — SYSTEM
Python hashlib — SYSTEM
Python json — SYSTEM
FileStorage / LocalFileStorage — DE
pytest — SYSTEM
uv — SYSTEM
```

Only record tools actually used.

No new runtime dependency should appear.

---

# 73. Scope Guardrails

Do not implement:

```text
KnowledgeSource creation
KnowledgeVersion creation
KnowledgeVersion activation
KnowledgeVersion FAILED propagation
Step 5.6 orchestration

embedding generation
embedding tokenizer coupling
vector storage
semantic retrieval
metadata filtering
reranking
prompt/context construction

semantic chunking
LLM chunking
LLM calls

parent-child chunks
hierarchical chunks
multi-vector parent retrieval

source-change/reprocessing policy
Step 5.7

Admin UI
worker/queue
new microservice
```

Step 5.5 ends at:

```text
PROCESSING KnowledgeVersion
+
complete persisted flat Chunk[]
+
persisted chunk config
```

---

# 74. Acceptance Criteria

Step 5.5 is acceptable only when all are true:

- [ ] Step-5.4 `TransformedArtifactRef` is the only transformation input boundary.
- [ ] Exact `transformed_document/v1` is loaded from existing FileStorage.
- [ ] No parsing/cleaning/transformation rerun occurs.
- [ ] Exact successful TransformationRun lineage is validated.
- [ ] No latest/current TransformationRun lookup exists.
- [ ] Step 5.5 consumes an existing PROCESSING KnowledgeVersion.
- [ ] Step 5.5 does not create KnowledgeSource.
- [ ] Step 5.5 does not create KnowledgeVersion.
- [ ] Step 5.5 does not activate KnowledgeVersion.
- [ ] Step 5.5 does not mark KnowledgeVersion FAILED.
- [ ] KnowledgeSource logical source identity is validated.
- [ ] Exactly one migration `0008_chunking_contract` follows `0007`.
- [ ] Migrations `0001–0007` remain unchanged.
- [ ] `knowledge_versions.chunking_version` is added nullable.
- [ ] `knowledge_versions.chunk_max_chars` is added nullable.
- [ ] `chunks.content_hash` is added nullable.
- [ ] No unrelated schema is added.
- [ ] New Step-5.5 builds require complete frozen config.
- [ ] Strategy is `structure_aware`.
- [ ] Version is `v1`.
- [ ] target_chars = 1200.
- [ ] max_chars = 1800.
- [ ] overlap_chars = 150.
- [ ] Size uses Unicode character count.
- [ ] No tokenizer dependency exists.
- [ ] Content types remain exact V0 values.
- [ ] Chunks never merge across content_type.
- [ ] Explicit section changes flush generic text.
- [ ] PDF page change alone does not force a boundary.
- [ ] Multi-page provenance is retained.
- [ ] `page_number` is populated only for a single-page Chunk.
- [ ] `section` projection is deterministic.
- [ ] Full `section_path` is retained in metadata.
- [ ] Metadata schema is `chunk_metadata/v1`.
- [ ] Source ranges are deterministic.
- [ ] Vocabulary is one entity → one Chunk.
- [ ] Vocabulary is not merged/split by generic sizing.
- [ ] Grammar is atomic normally.
- [ ] D-058 fallback activates only beyond max.
- [ ] Grammar splits at complete field boundaries first.
- [ ] Oversized Grammar field uses forced splitter with overlap 150.
- [ ] Grammar parts retain semantic part + field lineage.
- [ ] DOCUMENT_TEXT uses structure-aware merge/split.
- [ ] LESSON_GENERAL uses structure-aware merge/split.
- [ ] Heading merges forward only when compatible.
- [ ] Standalone heading remains valid.
- [ ] TABLE follows D-059.
- [ ] No table header repetition.
- [ ] No fake cells.
- [ ] Oversized table row fails with CHUNK_TOO_LARGE.
- [ ] LIST stays together when normal.
- [ ] Oversized LIST splits between items first.
- [ ] Oversized single list item may forced-split.
- [ ] Normal neighboring Chunks have no overlap.
- [ ] Overlap occurs only within forced split of one oversized unit.
- [ ] Natural separator preference is deterministic.
- [ ] Chunk.content remains source-derived.
- [ ] No synthetic embedding metadata prefix exists.
- [ ] `content_hash` follows exact D-057 contract.
- [ ] Equal content hashes do not trigger deduplication.
- [ ] Chunk UUID remains independent from hash.
- [ ] Chunk indexes are consecutive and source ordered.
- [ ] Existing `(knowledge_version_id, chunk_index)` uniqueness remains.
- [ ] Same PROCESSING version rerun replaces instead of appending.
- [ ] Replacement occurs atomically.
- [ ] Row lock/recheck protects ACTIVE versions.
- [ ] ACTIVE version is never mutated.
- [ ] `token_count` remains NULL.
- [ ] No Embedding/vector rows are created.
- [ ] Exact error contract is used.
- [ ] No raw DB/stack trace/internal path leaks.
- [ ] No new runtime dependency is added.
- [ ] Focused strategy tests pass.
- [ ] Forced-split tests pass.
- [ ] provenance/hash/order tests pass.
- [ ] lineage/lifecycle tests pass.
- [ ] rerun/atomicity tests pass.
- [ ] DB runtime/schema tests pass.
- [ ] migration upgrade/downgrade tests pass.
- [ ] full backend regression passes.
- [ ] Alembic current/check pass.
- [ ] Step Note is complete.
- [ ] Concepts/Tools tables use required project format.
- [ ] No Step 5.6 / Step 6.1 behavior is implemented.

---

# 75. Suggested Verification Commands

Use repository-standard commands.

Focused Step-5.5 tests:

```text
uv run pytest \
  tests/test_step55_chunking.py \
  tests/test_step55_chunking_service.py \
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

Do not run destructive migration tests against production data.

---

# 76. Codex Constraints

Codex must:

```text
inspect current accepted Step-5.4 implementation before editing
reuse TransformedArtifactRef
reuse load_transformed_artifact()
reuse FileStorage / LocalFileStorage
reuse current KnowledgeSource / KnowledgeVersion / Chunk models
preserve D-056 / D-057 / D-058 / D-059
follow existing ORM/migration naming conventions
follow existing repository/session/error/logging conventions
keep chunk planning outside long DB transaction
perform atomic replacement under row lock
preserve ACTIVE versions
```

Codex must NOT:

```text
change D-056
change D-057
change D-058
change D-059

create KnowledgeSource
create KnowledgeVersion
activate KnowledgeVersion
mark KnowledgeVersion FAILED

add embeddings
add tokenizer
add vector writes
add semantic chunking
add LLM
add parent/child chunks
add Step-5.6 orchestration
add source-change/reprocessing policy
add public Chunking HTTP API
add frontend
add worker/queue
add dependency without reporting blocker
perform unrelated refactors
```

If actual repository state materially contradicts this frozen task:

```text
STOP
→ report exact contradiction
```

Do not choose a new architecture silently.

---

# 77. Required Codex Completion Handoff

Return:

```text
Step:
Status:

What was done:
- ...

D-056 preserved:
- ...

D-057 preserved:
- ...

D-058 preserved:
- ...

D-059 preserved:
- ...

Files/components changed:
- ...

Migration 0008:
- ...

KnowledgeVersion config:
- ...

Chunk schema:
- ...

chunk_metadata/v1:
- ...

content_hash:
- ...

Input lineage:
- ...

KnowledgeVersion ownership:
- ...

Chunking strategy:
- ...

Size config:
- ...

Content-type dispatch:
- ...

Vocabulary:
- ...

Grammar:
- ...

Document text:
- ...

Lesson general:
- ...

Heading:
- ...

TABLE:
- ...

LIST:
- ...

Forced splitter:
- ...

Overlap:
- ...

Provenance / locator aggregation:
- ...

Chunk ordering:
- ...

Rerun/idempotency:
- ...

Atomic persistence:
- ...

ACTIVE protection:
- ...

Step-6.1 output boundary:
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
- focused chunking
- service/lifecycle
- rerun/atomicity
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

# 78. Definition of Done

The Codex implementation is ready for Data Engineering specialist review only when:

```text
requirements satisfied
D-056 preserved
D-057 preserved
D-058 preserved
D-059 preserved

migration 0008 verified
KnowledgeVersion config persisted
content_hash persisted
chunk_metadata/v1 implemented

exact transformed lineage verified
PROCESSING KnowledgeVersion verified
KnowledgeSource identity verified

content-type dispatch correct
Vocabulary atomic
Grammar fallback correct
generic text merge/split correct
heading behavior correct
TABLE truthful
LIST behavior correct
forced split deterministic
overlap restricted correctly

provenance complete
chunk order deterministic
hash deterministic
duplicate hash does not dedup

rerun replaces
atomic rollback works
ACTIVE protected
token_count deferred

focused tests pass
database/migration tests pass
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

Do not begin Step 5.6 automatically.
