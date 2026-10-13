# Codex Task — Step 5.3 Parsing & Cleaning

## Task Identity

**Project:** LLM + RAG Web App học tiếng Trung cho người mới bắt đầu  
**Phase:** 5 — Data Engineering  
**Step:** 5.3 — Parsing & Cleaning  
**Owner:** Data Engineering Specialist  
**Task status:** FROZEN / READY FOR CODEX AFTER PM REVIEW  
**Implementation mode:** One Codex task = this Step only

Do not redesign architecture. Do not expand scope. Treat the current accepted repository state plus the frozen decisions in this task as authoritative.

---

# 1. Accepted Project State

Before this task:

```text
Step 5.1
→ PM ACCEPTED / CLOSED

Step 5.2
→ PM ACCEPTED / CLOSED
```

Current migration head:

```text
0005_raw_document_metadata
```

Accepted Step-5.2 boundary:

```text
Source
→ Raw Stored
```

Available internal input contract:

```text
RawArtifactRef
├── source_type
├── source_id
├── storage_key
├── file_format
├── mime_type
├── file_size_bytes
└── content_hash
```

Step 5.3 must consume stored immutable raw artifacts.

For `LESSON`, do **not** re-read live Lesson/Vocabulary/Grammar source state. Read the stored deterministic:

```text
raw_lesson_snapshot/v1
```

---

# 2. Objective

Implement deterministic parsing and conservative cleaning for Step-5.2 raw artifacts.

Supported inputs:

```text
DOCUMENT
├── PDF
├── DOCX
├── TXT
└── MD

LESSON
└── raw_lesson_snapshot/v1 JSON
```

Required outcome:

```text
Raw Artifact
→ Parse
→ Conservative Clean
→ Persist Parsed/Cleaned Artifact
```

Step 5.3 must:

1. choose the correct parser;
2. extract source content;
3. preserve source structure/order where useful;
4. clean only technical extraction noise;
5. preserve source locators/provenance;
6. validate stored Raw Lesson Snapshot;
7. persist deterministic `ParsedCleanedArtifact/v1`;
8. persist parser identity/version;
9. persist cleaning identity/version;
10. persist parsing lifecycle/failure state in PostgreSQL;
11. preserve Raw Artifact on every failure;
12. return a specific `ParsedArtifactRef` for Step 5.4.

Do **not** implement Step 5.4 transformation.

---

# 3. Frozen D-052 — Parsed Artifact & Parsing Lifecycle

Use one minimal relational:

```text
ParsingRun
```

for Step-5.3 lifecycle/metadata in PostgreSQL.

Persist successful parsed content as:

```text
ParsedCleanedArtifact/v1
```

deterministic JSON through existing:

```text
FileStorage / LocalFileStorage
```

Each parsing invocation gets one `ParsingRun`.

Step 5.3 does **not** define a global:

```text
current parse
latest parse
active parse
canonical parse
preferred parse
```

A successful invocation returns one specific:

```text
ParsedArtifactRef
```

for Step 5.4.

---

# 4. ParsingRun Schema Freeze

Create a model equivalent to:

```text
ParsingRun
├── id
├── source_type
├── document_id nullable
├── lesson_id nullable
├── raw_storage_reference
├── raw_content_hash
├── parser_name
├── parser_version
├── cleaning_strategy
├── cleaning_version
├── status
├── parsed_storage_reference nullable
├── error_code nullable
├── error_detail nullable
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

Use repository conventions for SQLAlchemy types and CHECK constraints rather than introducing DB enum infrastructure.

## Source invariant

```text
source_type = DOCUMENT
→ document_id IS NOT NULL
→ lesson_id IS NULL

source_type = LESSON
→ lesson_id IS NOT NULL
→ document_id IS NULL
```

No other source type is allowed in Step 5.3.

## Success invariant

```text
status = SUCCEEDED
→ parsed_storage_reference IS NOT NULL
→ error_code IS NULL
```

## Failure invariant

```text
status = FAILED
→ parsed_storage_reference IS NULL
→ error_code IS NOT NULL
```

## Safe diagnostics

`error_detail` must be safe.

Do not persist:

```text
stack trace
secret
credential
raw DB exception
internal absolute filesystem path
raw library exception dump
```

A short sanitized diagnostic is allowed.

---

# 5. Document.processing_status Freeze

`Document.processing_status` remains coarse overall pipeline state.

Required behavior:

```text
parse starts
→ Document.processing_status = PROCESSING

parse succeeds
→ Document remains PROCESSING

parse fails
→ Document.processing_status = FAILED
```

Step 5.3 must **not** set:

```text
PREVIEW_READY
```

Step 5.4 or a later accepted stage owns that transition.

Do not reinterpret `PREVIEW_READY` as parsing success.

---

# 6. ParsedCleanedArtifact/v1 Freeze

Schema identity:

```text
parsed_cleaned_artifact/v1
```

Logical deterministic content:

```text
ParsedCleanedArtifact
├── schema_version
├── source_type
├── source_id
├── raw_content_hash
├── parser_name
├── parser_version
├── cleaning_strategy
├── cleaning_version
└── units[]
    ├── order
    ├── text
    └── source_locator
```

Do not include inside deterministic artifact content:

```text
processing timestamp
random UUID
ParsingRun id
created_at
updated_at
temporary path
runtime-only IDs/noise
```

Canonical serialization must preserve:

```text
UTF-8
sorted object keys
compact deterministic separators
stable unit ordering
```

Equivalent serialization may use:

```python
json.dumps(
    data,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")
```

Do not add content hashing rules that depend on non-deterministic runtime metadata.

---

# 7. ParsedArtifactRef Freeze

Internal Step-5.4 handoff:

```text
ParsedArtifactRef
├── parsing_run_id
├── source_type
├── source_id
├── storage_key
└── schema_version = parsed_cleaned_artifact/v1
```

Step 5.4 receives:

```text
ParsedArtifactRef
+
FileStorage
```

and reads the persisted parsed artifact.

Step 5.4 must **not** reparse the Raw Artifact when a successful `ParsedArtifactRef` is provided.

This is an internal contract, not a public HTTP response.

---

# 8. Migration Freeze

Create exactly one forward migration:

```text
backend/migrations/versions/0006_parsing_runs.py
```

Required:

```text
revision identity:
0006_parsing_runs

down_revision:
0005_raw_document_metadata
```

Do not modify:

```text
0001
0002
0003
0004
0005
```

Do not modify in Step 5.3:

```text
KnowledgeSource
KnowledgeVersion
Chunk
```

No extra migration is allowed unless a direct implementation contradiction is found. If so, stop and report rather than silently creating another schema path.

---

# 9. ParsingRun Physical Constraints

Migration/ORM must enforce at least:

```text
source_type IN ('DOCUMENT','LESSON')

status IN ('PENDING','PROCESSING','SUCCEEDED','FAILED')
```

Source-target CHECK equivalent to:

```text
(source_type = 'DOCUMENT'
 AND document_id IS NOT NULL
 AND lesson_id IS NULL)

OR

(source_type = 'LESSON'
 AND lesson_id IS NOT NULL
 AND document_id IS NULL)
```

Success CHECK equivalent to:

```text
status <> 'SUCCEEDED'
OR (
  parsed_storage_reference IS NOT NULL
  AND error_code IS NULL
)
```

Failure CHECK equivalent to:

```text
status <> 'FAILED'
OR (
  parsed_storage_reference IS NULL
  AND error_code IS NOT NULL
)
```

Use repository naming conventions.

Add practical indexes only where directly justified for source/run lookup, e.g.:

```text
document_id
lesson_id
status
```

Do not invent an `active` or `current` uniqueness rule.

Do not enforce a single ParsingRun per source.

---

# 10. Existing Raw Storage Must Be Reused

Reuse existing:

```text
FileStorage
LocalFileStorage
```

Do not introduce a second storage subsystem.

Raw Artifact remains immutable.

Parsed/Cleaned Artifact is stored separately from Raw Artifact.

Step 5.3 must never overwrite or delete Raw Artifact as part of parsing cleanup.

---

# 11. Parsed Artifact Storage Layout

Use server-generated storage keys.

Recommended logical layout:

```text
parsed/
├── documents/
│   └── <document_id>/
│       └── <parsing_run_id>/
│           └── parsed_cleaned.json
│
└── lessons/
    └── <lesson_id>/
        └── <parsing_run_id>/
            └── parsed_cleaned.json
```

Equivalent layout that follows current storage conventions is acceptable if all properties below hold:

```text
server generated
private
root-contained
separate from raw
one successful artifact per ParsingRun
no client-provided path components
stable storage reference
```

Do not encode `latest`, `active`, or `current` into the storage path.

---

# 12. Parser Architecture Freeze

Preserve separated parser boundaries equivalent to:

```text
backend/app/ingestion/parsing/
├── __init__.py
├── base.py
├── pdf.py
├── docx.py
├── text.py
├── markdown.py
└── lesson.py
```

plus:

```text
backend/app/ingestion/cleaning.py
backend/app/ingestion/parsing_service.py
```

Core abstraction:

```text
DocumentParser
→ parse(raw input)
→ ordered parsed units
```

Selection:

```text
DOCUMENT/PDF  → PdfParser
DOCUMENT/DOCX → DocxParser
DOCUMENT/TXT  → TxtParser
DOCUMENT/MD   → MarkdownParser
LESSON/JSON   → LessonSnapshotParser
```

Do not build one giant format-specific `if/elif` parser function.

A small parser selector/registry is acceptable.

Do not create plugin discovery infrastructure.

---

# 13. Parser Output Internal Shape

Before final artifact serialization, format-specific parsers should produce an ordered internal structure equivalent to:

```text
ParsedUnit
├── order
├── text
└── source_locator
```

`order` must be stable and consecutive for the emitted units.

Do not introduce Step-5.4 canonical Knowledge Block semantics here.

Do not add embedding/retrieval fields.

---

# 14. PDF Freeze

Parser:

```text
PyMuPDF
```

Read raw bytes only through existing `FileStorage`.

Requirements:

```text
text-based PDFs only
extract by page
preserve page order
preserve page number
1-based page_number
```

Output:

```text
one ordered parsed unit per page with useful extracted text
```

Locator:

```text
kind = PDF_PAGE
page_number
```

Do not flatten all pages into one untraceable string.

## NO_EXTRACTABLE_TEXT rule

Do not use an arbitrary character threshold.

Required deterministic rule:

```text
extract all pages
→ conservative cleaning
→ if every page has zero non-whitespace cleaned text
→ NO_EXTRACTABLE_TEXT
```

A page containing only technical control/whitespace noise does not count as extractable text.

A real short page is not rejected only because it is short.

No OCR.

No PDF image interpretation.

No header/footer heuristic.

No hyphen repair heuristic.

No table framework.

No complex layout reconstruction.

---

# 15. DOCX Freeze

Parser:

```text
python-docx
```

Critical invariant:

```text
paragraph
→ table
→ paragraph
```

must remain source ordered.

Do **not** implement:

```text
document.paragraphs
→ all paragraphs

then

document.tables
→ all tables
```

as independent passes.

Use document body-order iteration.

## Paragraph unit

Locator equivalent to:

```text
kind = DOCX_PARAGRAPH
block_index
```

One logical unit per paragraph where useful content exists after conservative cleaning.

## Table representation

Minimum:

```text
one parsed unit per table row
```

Preserve cell text in stable left-to-right order.

A deterministic delimiter such as tab may be used between cell values.

Locator:

```text
kind = DOCX_TABLE_ROW
block_index
table_index
row_index
```

Index bases must be documented and consistently tested. Prefer 0-based internal indices except human-facing PDF page number remains 1-based.

Do not reconstruct visual Word layout.

Do not implement rich formatting reconstruction.

---

# 16. TXT Freeze

Supported decoding:

```text
UTF-8
UTF-8 BOM
```

Use BOM-aware behavior equivalent to:

```text
utf-8-sig
```

Invalid decoding:

```text
TEXT_DECODING_FAILED
```

Do not silently replace invalid bytes.

Do not add broad encoding detection.

Do not add chardet/charset-normalizer solely for this Step.

Preserve logical blocks and original source order.

Locator:

```text
kind = TEXT_BLOCK
block_index
```

---

# 17. Markdown Freeze

Do not implement:

```text
Markdown
→ HTML
→ stripped text
```

Use Markdown source directly.

No runtime Markdown dependency is required unless a real implementation blocker is found.

Minimum block kinds:

```text
HEADING
PARAGRAPH
LIST_ITEM
CODE_BLOCK
```

Preserve block order.

Locator:

```text
kind = MARKDOWN_BLOCK
block_index
block_kind
heading_level?   # only for HEADING
list_kind?       # ordered / unordered where relevant
```

No Step-5.4 canonical Block model.

## Markdown code blocks

Fenced code blocks must preserve meaningful content whitespace/indentation.

Do not apply prose repeated-space collapsing inside code blocks.

Do not convert code blocks to HTML.

---

# 18. Raw Lesson Snapshot Parser Freeze

Input:

```text
stored raw_lesson_snapshot/v1 JSON bytes
```

Do not query live:

```text
Lesson
Vocabulary
Grammar
LessonVocabulary
LessonGrammar
```

as source-of-truth during parsing.

Deserialize stored bytes.

Validate:

```text
schema_version == raw_lesson_snapshot/v1
expected object structure
required Lesson identity
Lesson.status == PUBLISHED
Vocabulary list
Grammar list
required entity identifiers
required order_index
```

Malformed or incompatible snapshot:

```text
INVALID_LESSON_SNAPSHOT
```

Do not "repair" a malformed snapshot using live database values.

---

# 19. Lesson Parsed Units

Use a conservative representation:

```text
one unit per textual source field
```

Locator:

```text
kind = LESSON_FIELD
section = LESSON | VOCABULARY | GRAMMAR
entity_id
field
order_index?  # where applicable
```

Preserve original Vocabulary/Grammar ordering from the stored snapshot.

Do not invent canonical vocabulary/grammar sentence templates for Step 5.4.

Do not merge multiple source fields into semantic chunks.

Examples of fields that may become units where non-empty:

```text
Lesson:
title
description

Vocabulary:
hanzi
pinyin
vietnamese_meaning
part_of_speech
note
example

Grammar:
name
structure
explanation
usage
note
example
```

Only use fields actually present in the stored Step-5.2 snapshot.

---

# 20. Cleaning Freeze

Freeze identities:

```text
cleaning_strategy = basic_text_cleaning
cleaning_version  = v1
```

Cleaning must be:

```text
deterministic
conservative
technical
non-semantic
```

Purpose:

```text
remove extraction/technical noise
```

Not:

```text
rewrite source knowledge
```

## Allowed operations

Equivalent deterministic operations:

```text
CRLF / CR → LF
Unicode NFC normalization
remove NUL
remove defined unwanted control characters
trim trailing whitespace
conservatively collapse pathological repeated ASCII spaces
reduce excessive blank lines
```

Implementation must define exactly which control characters are removed.

Preserve useful:

```text
\t
\n
```

when the parser/block type requires them.

## Preserve

```text
paragraph structure
headings
lists
Chinese punctuation
Chinese characters
Vietnamese diacritics
English lexical content
meaningful spaces
source order
```

## Do not perform

```text
Chinese grammar correction
source typo correction based on meaning
translation
paraphrasing
example rewriting
Simplified ↔ Traditional conversion
LLM cleaning
semantic normalization
```

---

# 21. Block-Sensitive Cleaning

Cleaning may apply different whitespace handling by block kind only where technically necessary.

Required:

```text
CODE_BLOCK
→ preserve meaningful indentation / repeated spaces

DOCX table row
→ preserve deterministic cell delimiter

normal prose
→ may apply conservative repeated-ASCII-space collapse
```

Do not let prose cleaning corrupt structured content.

---

# 22. Source Locator Freeze

Use source-specific discriminated representations equivalent to:

## PDF

```text
kind = PDF_PAGE
page_number
```

## DOCX paragraph

```text
kind = DOCX_PARAGRAPH
block_index
```

## DOCX table row

```text
kind = DOCX_TABLE_ROW
block_index
table_index
row_index
```

## TXT

```text
kind = TEXT_BLOCK
block_index
```

## Markdown

```text
kind = MARKDOWN_BLOCK
block_index
block_kind
heading_level?
list_kind?
```

## Lesson

```text
kind = LESSON_FIELD
section
entity_id
field
order_index?
```

Use typed Pydantic models/unions if that matches current schema style.

Do not prematurely create Step-5.4 canonical Block entities.

---

# 23. Version Tracking Freeze

Persist parser identity/version on every `ParsingRun` and inside the deterministic parsed artifact.

## PDF

```text
parser_name = pymupdf
parser_version = installed PyMuPDF package version
```

Resolve external package version using package metadata, not a separately hand-maintained patch constant.

## DOCX

```text
parser_name = python-docx
parser_version = installed python-docx package version
```

Use installed package metadata.

## TXT

```text
parser_name = txt_utf8
parser_version = v1
```

## Markdown

```text
parser_name = markdown_blocks
parser_version = v1
```

## Lesson

```text
parser_name = raw_lesson_snapshot
parser_version = v1
```

## Cleaning

All parsers:

```text
cleaning_strategy = basic_text_cleaning
cleaning_version = v1
```

No plugin/version-management framework.

---

# 24. Runtime Dependencies

Add:

```text
PyMuPDF
python-docx
```

according to existing backend dependency conventions.

Update:

```text
backend/pyproject.toml
backend/uv.lock
```

Do not PM-freeze patch versions manually.

Exact resolved versions belong in `uv.lock`.

Do not add a Markdown dependency unless an actual blocker proves one necessary.

Do not add:

```text
OCR libraries
Camelot
Tabula
image/VLM libraries
LLM SDK for cleaning
workflow orchestrators
worker/queue packages
```

---

# 25. Parsing Service Primitive

No public HTTP endpoint is required.

Freeze internal primitive equivalent to:

```text
parse_raw_artifact(
    raw_artifact: RawArtifactRef,
    ...
) -> ParsedArtifactRef
```

Exact parameters may include existing session/storage dependencies according to repository conventions.

Do not expose ORM objects across parser interfaces.

Do not add:

```text
POST /admin/documents/{id}/parse
```

Do not add Admin UI behavior.

Step 5.6 may orchestrate this primitive later.

---

# 26. Parsing Invocation Lifecycle

Each call creates one new `ParsingRun`.

Recommended state flow:

```text
create ParsingRun(PENDING)
→ persist/commit

transition → PROCESSING
→ persist/commit

read Raw Artifact
→ parse
→ clean
→ construct deterministic artifact
→ finalize parsed artifact

transition → SUCCEEDED
→ set parsed_storage_reference
→ clear error_code/error_detail
→ persist/commit

return ParsedArtifactRef
```

Exact number of short transactions may follow repository conventions, but do not keep a DB transaction open across slow parsing/file work.

---

# 27. Document Coarse Status During Parsing

For `source_type=DOCUMENT`:

At parsing start:

```text
Document.processing_status
→ PROCESSING
```

On success:

```text
Document.processing_status
→ remains PROCESSING
```

On failure:

```text
Document.processing_status
→ FAILED
```

Do not set `PREVIEW_READY`.

For `LESSON`, there is no Document coarse status update.

---

# 28. Failure Semantics

Raw Artifact survives all Step-5.3 failures.

Parsing failure:

```text
Raw Artifact remains
→ ParsingRun = FAILED
→ stable error_code persisted
→ safe error_detail persisted
→ parsed_storage_reference = NULL
→ no successful ParsedArtifactRef returned
```

Do not delete Raw Artifact.

Do not create a false successful parsed artifact reference.

---

# 29. Partial Failure — Parsed Artifact Finalization Failure

If parsing/cleaning succeeded but parsed artifact finalization/storage fails:

```text
Raw Artifact remains
→ ParsingRun = FAILED
→ stable safe failure persisted
→ no successful parsed_storage_reference
→ no ParsedArtifactRef returned
```

Any temporary parsed artifact must be discarded.

Canonical code may use:

```text
PARSING_FAILED
```

unless a more specific existing storage error code is reused consistently. Do not invent a broad new error hierarchy.

---

# 30. Partial Failure — DB Success-State Persistence Failure

If parsed artifact finalization succeeded but the final DB update to `SUCCEEDED` fails:

```text
delete orphan parsed artifact
→ do not report success
→ best-effort persist FAILED
→ log persistence failure safely if FAILED persistence also fails
→ Raw Artifact remains
```

Do not delete Raw Artifact.

Do not leave a false `SUCCEEDED` row referencing a missing artifact.

Do not leave an unreferenced successful parsed artifact intentionally.

---

# 31. Parsing Errors

Freeze stable equivalents:

```text
PARSING_FAILED
NO_EXTRACTABLE_TEXT
UNSUPPORTED_PARSER
INVALID_LESSON_SNAPSHOT
TEXT_DECODING_FAILED
```

Use existing `ApplicationError` conventions where an error crosses an application boundary.

At the parsing service/internal layer, typed internal exceptions are acceptable if translated consistently to stable codes for `ParsingRun`.

Do not persist raw stack traces.

---

# 32. Safe error_detail

Use short diagnostic messages such as:

```text
"No extractable text was found in the PDF."
"Stored lesson snapshot schema_version is not supported."
"Text input is not valid UTF-8."
```

Do not include:

```text
C:\...
/home/...
storage root
DB DSN
SQL query
traceback
library internal state dump
secret
```

---

# 33. Rerun Semantics

Parsing is re-runnable.

Every new call:

```text
parse(raw_artifact)
→ new ParsingRun
```

Step 5.3 does not decide which run is:

```text
latest
active
canonical
preferred
current
```

Do not add:

```text
is_active
superseded_by
current_parsing_run_id
unique active parsing run
```

That belongs to later reprocessing/orchestration policy.

---

# 34. Repository Boundary

Extend current ingestion repository only where needed for persistence.

Responsibilities may include:

```text
create ParsingRun
update ParsingRun state
load ParsingRun if tests require it
update Document.processing_status
```

Do not put parsing logic in repository.

Do not put filesystem work in repository.

Do not query live Lesson source state for Lesson parsing.

---

# 35. Storage Extension

Modify `backend/app/ingestion/storage.py` only if a narrow helper is required to store/read parsed artifacts.

Prefer reusing existing generic methods:

```text
create temp
write
finalize
open
delete
```

Do not create a second `ParsedStorage` abstraction if `FileStorage` already suffices.

Do not weaken existing root/path safety.

---

# 36. Schemas

Extend:

```text
backend/app/ingestion/schemas.py
```

or current schema conventions with internal models equivalent to:

```text
ParsedUnit
ParsedCleanedArtifact
ParsedArtifactRef
source locator variants
```

Use strict validation where practical.

Parsed artifact `schema_version` must be:

```text
parsed_cleaned_artifact/v1
```

Do not create public API response schemas because no public Step-5.3 route exists.

---

# 37. Logging

Follow current repository logging conventions.

Log only operationally useful safe information.

Allowed examples:

```text
parsing_run_id
source_type
source_id
stable error_code
```

Avoid:

```text
raw source text
full extracted document text
absolute file path
stack trace at INFO
credentials
secrets
```

Exception stack traces may be logged at an appropriate internal error/debug level only if current project conventions allow them and they are not persisted/exposed to clients.

---

# 38. Expected Files — Modify

Likely modify:

```text
backend/pyproject.toml
backend/uv.lock

backend/app/database/models/__init__.py
backend/app/ingestion/schemas.py
backend/app/ingestion/repository.py
backend/app/ingestion/storage.py   # only if narrowly required

backend/tests/test_database.py
backend/tests/test_migration_preservation.py
```

If current model import conventions use another aggregation file, make only the narrow required change and report it.

---

# 39. Expected Files — Create

Likely create:

```text
backend/app/database/models/ingestion.py

backend/app/ingestion/parsing/
    __init__.py
    base.py
    pdf.py
    docx.py
    text.py
    markdown.py
    lesson.py

backend/app/ingestion/cleaning.py
backend/app/ingestion/parsing_service.py

backend/migrations/versions/
    0006_parsing_runs.py

backend/tests/test_step53_parsers.py
backend/tests/test_step53_cleaning.py
backend/tests/test_step53_parsing_service.py

docs/data/
    step-5.3-parsing-cleaning.md
```

Exact filenames may be narrowed to repository conventions, but do not merge all parser code into one giant module.

Do not create an HTTP router merely for Step 5.3.

---

# 40. Config / Env

No new environment configuration is required by default.

Do not add:

```text
OCR threshold
PDF text threshold
parser timeout
worker count
queue URL
retry count
Markdown engine config
```

unless a real implementation blocker is found and approved.

---

# 41. Test Freeze — Parser Selection

Cover:

```text
PDF  → PdfParser
DOCX → DocxParser
TXT  → TxtParser
MD   → MarkdownParser
LESSON JSON → LessonSnapshotParser
unsupported → UNSUPPORTED_PARSER
```

Do not test only implementation class names; verify correct behavior selection.

---

# 42. Test Freeze — PDF

Cover:

1. text PDF parses successfully;
2. page numbers preserved;
3. multiple pages remain ordered;
4. page numbers are 1-based;
5. whitespace/control-only extracted output results in `NO_EXTRACTABLE_TEXT`;
6. no arbitrary character-count threshold;
7. no OCR invoked/dependency present;
8. raw artifact remains after parse failure;
9. source locator survives artifact persistence;
10. parser name/version persisted.

Use small deterministic test fixtures created in tests where practical.

Do not depend on external network files.

---

# 43. Test Freeze — DOCX

Cover:

1. paragraph order;
2. table row/cell content;
3. paragraph → table → paragraph interleaving;
4. block indices stable;
5. table/row indices stable;
6. cell order stable;
7. source locator survives artifact persistence;
8. parser version persisted.

A fixture equivalent to:

```text
paragraph A
table row
paragraph B
```

must prove the final unit order remains A → table → B.

---

# 44. Test Freeze — TXT

Cover:

```text
UTF-8
UTF-8 BOM
invalid UTF-8 → TEXT_DECODING_FAILED
logical block order
source locators
raw artifact remains on failure
```

Do not silently use replacement decoding.

---

# 45. Test Freeze — Markdown

Cover:

```text
HEADING
PARAGRAPH
LIST_ITEM
CODE_BLOCK
source order
heading level
ordered/unordered list identity
no HTML conversion
code whitespace preserved
```

Also verify no Markdown parsing runtime dependency was added unless justified.

---

# 46. Test Freeze — Lesson Snapshot

Cover:

1. valid `raw_lesson_snapshot/v1`;
2. malformed JSON rejected;
3. wrong `schema_version` rejected;
4. invalid object shape rejected;
5. non-PUBLISHED stored snapshot rejected;
6. Vocabulary order preserved;
7. Grammar order preserved;
8. textual source fields become units conservatively;
9. locators preserve section/entity/field/order;
10. stored snapshot is used instead of live Lesson DB source.

Important test:

```text
store raw_lesson_snapshot/v1
→ mutate live Lesson/Vocabulary/Grammar DB values
→ Step 5.3 parses stored snapshot
→ output reflects stored snapshot, not live DB mutation
```

Do not "refresh" from live data.

---

# 47. Test Freeze — Cleaning

Cover:

```text
CRLF / CR → LF
Unicode NFC
NUL removal
defined control removal
trailing whitespace trim
excessive blank-line reduction
conservative repeated ASCII spaces
Chinese punctuation preserved
Chinese characters preserved
Vietnamese diacritics preserved
paragraph boundaries preserved
no translation
no linguistic correction
no Simplified/Traditional conversion
```

Also:

```text
CODE_BLOCK whitespace preserved
table delimiter preserved
```

Cleaning must be deterministic.

---

# 48. Test Freeze — Deterministic Artifact

For identical:

```text
Raw Artifact bytes
parser identity/version
cleaning identity/version
```

verify equivalent canonical artifact bytes.

The deterministic artifact must not contain:

```text
ParsingRun id
timestamp
random UUID
runtime-only value
```

Two distinct ParsingRuns over identical raw input may therefore persist byte-equivalent `ParsedCleanedArtifact/v1` content even though their storage keys/run IDs differ.

Do not introduce deduplication/current selection policy.

---

# 49. Test Freeze — ParsingRun Lifecycle

Cover valid statuses:

```text
PENDING
PROCESSING
SUCCEEDED
FAILED
```

Verify DB rejects invalid status.

Verify source invariants.

Verify:

```text
SUCCEEDED
→ parsed_storage_reference required
→ error_code NULL
```

Verify:

```text
FAILED
→ parsed_storage_reference NULL
→ error_code required
```

Verify invalid combinations fail at DB boundary.

---

# 50. Test Freeze — Document Coarse Status

For Document parsing:

```text
start
→ PROCESSING

success
→ remains PROCESSING

failure
→ FAILED
```

Explicitly test that Step 5.3 never sets:

```text
PREVIEW_READY
```

---

# 51. Test Freeze — Lesson Lifecycle

Verify Lesson parsing uses `ParsingRun` without a Document row.

No Document status update is required for Lesson.

No duplicate Lesson-specific lifecycle model is allowed.

---

# 52. Test Freeze — Failure Persistence

For parser failure:

```text
Raw Artifact remains
ParsingRun = FAILED
error_code persisted
safe error_detail persisted
parsed_storage_reference NULL
no successful ParsedArtifactRef
```

Verify `error_detail` does not contain an injected absolute test storage path if a raw exception includes one.

---

# 53. Test Freeze — Parsed Artifact Finalization Failure

Inject storage finalization failure.

Verify:

```text
Raw Artifact remains
temporary parsed artifact cleaned
ParsingRun = FAILED
no parsed_storage_reference
no successful ParsedArtifactRef
```

Do not delete Raw Artifact.

---

# 54. Test Freeze — DB Success-State Failure

Inject a DB failure after parsed artifact finalization but before/while marking the run `SUCCEEDED`.

Verify:

```text
finalized parsed artifact deleted
Raw Artifact remains
no false SUCCEEDED
best-effort FAILED / safe failure state according to implementation
no successful ParsedArtifactRef
```

If persisting FAILED also fails, verify safe logging and no success result.

---

# 55. Test Freeze — Step 5.4 Handoff

Verify a successful `ParsedArtifactRef` plus `FileStorage` is sufficient to load:

```text
ParsedCleanedArtifact/v1
```

without reparsing Raw Artifact.

A focused test should make reparsing impossible/observable and prove Step-5.4-style loading still succeeds from stored parsed JSON.

Do not implement Step 5.4 transformation.

---

# 56. Test Freeze — Migration

Verify:

```text
0005 → 0006 upgrade
existing current data survives
parsing_runs table exists
source_type constraint
status constraint
source invariant
success invariant
failure invariant
indexes/foreign keys
downgrade 0006 → 0005
0005 schema remains usable
Alembic revision returns to 0005 after downgrade test
```

Do not rewrite migration history.

Run final:

```text
alembic current
alembic check
```

---

# 57. Full Backend Regression

Run full backend pytest.

Required:

```text
all tests PASS
```

Do not claim Step complete if required verification is blocked.

Warnings unrelated to Step correctness should be reported separately.

---

# 58. Step Note

Create:

```text
docs/data/step-5.3-parsing-cleaning.md
```

Required structure:

## Objective

Implement deterministic parsing and conservative cleaning over immutable raw sources.

## Why

Separate source acquisition from extraction/cleaning so downstream transformation receives reproducible persisted input.

## Mental Model

```text
Raw Artifact
→ format parser
→ ordered extracted units
→ conservative cleaning
→ persisted Parsed/Cleaned Artifact
→ ParsedArtifactRef
```

## Core Knowledge

Only concepts actually used.

## Data Flow

Cover:

```text
Document flow
Lesson snapshot flow
success
failure
partial failure
```

## Key Design Decisions

Include:

```text
ParsingRun
ParsedCleanedArtifact/v1
ParsedArtifactRef
coarse Document processing_status
separated parsers
PyMuPDF
python-docx
UTF-8-only TXT
source Markdown scanner
cleaning v1
source locators
deterministic JSON
no current/latest parse policy
```

## Reusable Approach

Explain how to design raw → parsed intermediate stages in another data pipeline.

## Common Mistakes

Include:

```text
re-reading mutable source state
mixing parsing with semantic transformation
flattening source locators
over-cleaning text
setting PREVIEW_READY too early
storing only transient parsed data
putting huge parsed JSON in lifecycle rows
adding active/latest semantics prematurely
deleting Raw Artifact on parser failure
holding DB transactions during parsing
```

## Definition of Done

Reflect actual implementation/tests.

---

# 59. Concepts Discovered

If actually used, likely:

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Parsing | DE | 5.3 | Converts raw source bytes into structured extracted content |
| Conservative Cleaning | DE | 5.3 | Removes technical noise without rewriting knowledge |
| Intermediate Artifact | DE | 5.3 | Persists stable input between pipeline stages |
| Source Locator | DE | 5.3 | Preserves traceability to source position |
| Parser Versioning | DE | 5.3 | Makes extraction behavior reproducible |
| Cleaning Versioning | DE | 5.3 | Makes cleaning behavior reproducible |
| Deterministic Processing | DE | 5.3 | Same raw input + versions yields equivalent output |
| Stage Lifecycle | DE | 5.3 | Tracks parsing attempt status/failure |
| Data Lineage | DE | 5.3 | Connects raw source → parsing run → parsed artifact |
| Raw-to-Parsed Contract | BOTH | 5.3 | Stable boundary consumed by Step 5.4 |
| Unicode Normalization | SYSTEM | 5.3 | Safe multilingual text normalization |
| Parser Abstraction | SYSTEM | 5.3 | Separates format-specific parsing |
| Compensating Cleanup | SYSTEM | 5.3 | Handles cross-storage/DB partial failure |

Only record concepts actually present in implementation.

---

# 60. Tools Used

If actually used, likely:

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| PyMuPDF | DE | 5.3 | Page-aware PDF text extraction |
| python-docx | DE | 5.3 | DOCX ordered body parsing |
| PostgreSQL | DE | 5.3 | ParsingRun lifecycle persistence |
| SQLAlchemy | DE | 5.3 | ParsingRun ORM/repository |
| Alembic | DE | 5.3 | `0006` forward migration |
| Pydantic | SYSTEM | 5.3 | Internal artifact/locator contracts |
| Python json | SYSTEM | 5.3 | Deterministic parsed artifact serialization |
| unicodedata | SYSTEM | 5.3 | Unicode NFC normalization |
| importlib.metadata | SYSTEM | 5.3 | Installed parser-version identity |
| pytest | SYSTEM | 5.3 | Verification |
| uv | SYSTEM | 5.3 | Runtime/dependency workflow |

Only record tools actually used.

---

# 61. Out of Scope / Non-Goals

Do not implement:

```text
Step 5.4 TransformedDocument
canonical Knowledge Blocks
chunking
chunk size/overlap
embedding
vector storage
retrieval
filtering
reranking
prompt construction
LLM generation
OCR
image captioning
VLM
website/URL ingestion
automatic parser retry scheduler
worker/queue
pipeline orchestration
current/latest parse policy
active/canonical parse selection
incremental/reprocessing strategy
aggressive PDF layout heuristics
specialized PDF table extraction
LLM cleaning
linguistic correction
Simplified/Traditional conversion
Admin parse HTTP endpoint
Admin parse UI
KnowledgeVersion creation
```

Step 5.3 ends at:

```text
persisted Parsed/Cleaned Artifact
+
specific ParsedArtifactRef
```

---

# 62. Acceptance Criteria

Step 5.3 is acceptable only when all are true:

- [ ] `ParsingRun` exists in PostgreSQL.
- [ ] One forward migration `0006_parsing_runs` follows `0005`.
- [ ] Migrations `0001–0005` are unchanged.
- [ ] `KnowledgeSource`, `KnowledgeVersion`, and `Chunk` are unchanged.
- [ ] `ParsingRun` supports DOCUMENT and LESSON targets.
- [ ] Source-target invariant is DB-enforced.
- [ ] Status values are DB-enforced.
- [ ] Success invariant is DB-enforced.
- [ ] Failure invariant is DB-enforced.
- [ ] Every parsing invocation creates a new `ParsingRun`.
- [ ] No current/latest/active/canonical parse semantics were introduced.
- [ ] Document parse start sets coarse status to PROCESSING.
- [ ] Document parse success leaves coarse status PROCESSING.
- [ ] Document parse failure sets coarse status FAILED.
- [ ] Step 5.3 never sets PREVIEW_READY.
- [ ] Successful parsed content is stored through existing `FileStorage`.
- [ ] `ParsedCleanedArtifact/v1` is deterministic JSON.
- [ ] Artifact contains no run ID/timestamp/random runtime noise.
- [ ] `ParsedArtifactRef` is returned on success.
- [ ] Step 5.4-style consumer can read artifact without reparsing raw source.
- [ ] PDF uses PyMuPDF.
- [ ] PDF preserves 1-based page locator.
- [ ] PDF all-empty/whitespace extraction fails with `NO_EXTRACTABLE_TEXT`.
- [ ] No OCR is added.
- [ ] DOCX uses python-docx.
- [ ] DOCX preserves paragraph/table interleaving.
- [ ] TXT supports UTF-8 and UTF-8 BOM.
- [ ] Invalid TXT decoding fails explicitly.
- [ ] Markdown preserves minimal source blocks without HTML conversion.
- [ ] Code-block whitespace survives cleaning.
- [ ] Lesson parser reads stored `raw_lesson_snapshot/v1`.
- [ ] Lesson parser does not reconstruct source from live DB.
- [ ] Vocabulary/Grammar ordering is preserved.
- [ ] Cleaning uses `basic_text_cleaning/v1`.
- [ ] Cleaning is deterministic, conservative, and non-semantic.
- [ ] Source locators are persisted.
- [ ] Parser identity/version is persisted.
- [ ] Cleaning identity/version is persisted.
- [ ] Raw Artifact survives every parsing failure.
- [ ] Parser failure persists safe FAILED state.
- [ ] Parsed artifact finalization failure creates no false success.
- [ ] DB success-state failure cleans orphan parsed artifact.
- [ ] No raw filesystem path/stack trace/secrets are persisted/exposed as diagnostics.
- [ ] PyMuPDF and python-docx are the only new parser runtime dependencies unless an approved blocker changes that.
- [ ] No Markdown runtime dependency was added without a documented blocker.
- [ ] Focused parser tests pass.
- [ ] Focused cleaning tests pass.
- [ ] Parsing service/lifecycle tests pass.
- [ ] Migration upgrade/downgrade tests pass.
- [ ] Full backend regression passes.
- [ ] Alembic current/check pass.
- [ ] Step Note is complete.
- [ ] Concepts/Tools tables reflect actual implementation only.
- [ ] No Step 5.4+ behavior was implemented.

---

# 63. Suggested Verification Commands

Use repository-standard commands.

Dependency sync:

```text
uv sync
```

Focused Step-5.3 tests:

```text
uv run pytest \
  tests/test_step53_parsers.py \
  tests/test_step53_cleaning.py \
  tests/test_step53_parsing_service.py \
  -vv
```

Migration/schema tests:

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

Do not run destructive migration tests against production data.

---

# 64. Codex Constraints

Codex must:

```text
inspect current accepted Step-5.2 implementation before editing
reuse RawArtifactRef
reuse FileStorage / LocalFileStorage
follow existing ORM/migration naming conventions
follow existing repository/session transaction conventions
follow existing ApplicationError/logging conventions
keep parser modules separated
keep DB transactions short
persist lifecycle separately from parsed JSON
preserve Raw Artifact on failure
```

Codex must NOT:

```text
change D-052
change Step-5.2 raw contracts without a direct bug
add a public parsing endpoint
add frontend parsing controls
add worker/queue
add OCR
add LLM cleaning
add active/latest/current parsing selection
create KnowledgeVersion
create Step-5.4 transformed structures
perform unrelated refactors
```

If actual repository state materially contradicts this frozen task, stop and report the contradiction instead of choosing a new architecture.

---

# 65. Required Codex Completion Handoff

Return:

```text
Step:
Status:

What was done:
- ...

D-052 preserved:
- ...

Files/components changed:
- ...

ParsingRun:
- schema
- constraints
- lifecycle

Migration:
- ...

ParsedCleanedArtifact/v1:
- ...

ParsedArtifactRef:
- ...

Parser implementations:
- PDF
- DOCX
- TXT
- Markdown
- Lesson snapshot

Cleaning:
- ...

Version tracking:
- ...

Failure / cleanup semantics:
- ...

Document processing_status behavior:
- ...

Concepts added:
- ...

Tools added:
- ...

Tests / verification:
- focused parsers
- cleaning
- parsing service
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

# 66. Definition of Done

The Codex implementation is ready for specialist review only when:

```text
requirements satisfied
D-052 preserved
ParsingRun migration verified
parsers implemented
cleaning deterministic
ParsedCleanedArtifact persisted
ParsedArtifactRef works
source locators preserved
failure state persisted safely
Raw Artifact preserved on failure
partial storage/DB cleanup verified
focused tests pass
migration upgrade/downgrade pass
full backend regression passes
Alembic current/check pass
Step Note complete
Concepts/Tools reflect actual implementation
no scope creep
```

After Codex completes, Data Engineering Specialist must review the actual implementation before PM acceptance.

Do not begin Step 5.4 automatically.
