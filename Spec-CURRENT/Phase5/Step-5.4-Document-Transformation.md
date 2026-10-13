# Step 5.4 — Document Transformation

## Goal

Implement deterministic transformation from the Parsed/Cleaned Artifact produced by Step 5.3 into one canonical document representation for downstream chunking.

The step must:

- normalize all supported source types into one `TransformedDocument` model;
- preserve source provenance and ordering;
- preserve explicit section hierarchy when it is known;
- distinguish semantic `content_type` from structural `block_kind`;
- retain structured learning data for Vocabulary/Grammar instead of flattening everything irreversibly;
- generate deterministic textual representations for structured blocks;
- preserve source locators for traceability;
- persist the transformed artifact;
- validate the canonical artifact before marking transformation successful;
- provide Step 5.5 with source-agnostic ordered canonical Blocks.

Do not implement chunking, embedding, retrieval, or pipeline orchestration in this step.

---

# Input Boundary

Step 5.4 consumes only the persisted output of Step 5.3:

```text
Parsed/Cleaned Artifact
```

Do not parse the original PDF/DOCX/TXT/MD again.

Do not reread live Lesson data instead of using the parsed Lesson artifact.

---

# Canonical Transformation Model

All supported parsed sources must be transformed into one common logical representation:

```text
Parsed PDF ───────┐
Parsed DOCX ──────┤
Parsed TXT ───────┤
Parsed MD ────────┤
Parsed Lesson ────┤
                  ↓
        TransformedDocument
```

Downstream Step 5.5 should not need format-specific knowledge about:

```text
PyMuPDF
python-docx
Markdown parser
raw Lesson snapshot format
```

---

# TransformedDocument

Use a canonical logical model equivalent to:

```text
TransformedDocument
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

`source_category` may be null/not applicable for LESSON sources.

Exact field names may follow current codebase conventions.

Do not create duplicate fields when an equivalent existing representation already exists.

---

# Block vs Chunk

Use:

```text
Block
```

for the structural units produced by Step 5.4.

Do not call these units `Chunk`.

Boundary:

```text
Step 5.4
Document
→ canonical Blocks

Step 5.5
canonical Blocks
→ retrieval Chunks
```

Chunk size, overlap, splitting, and block combination belong exclusively to Step 5.5.

---

# Canonical Block

Each Block should contain logical fields equivalent to:

```text
order
content_type
block_kind
text
section_path
source_locator
structured_data
metadata
```

Where:

```text
order
→ deterministic source order

content_type
→ semantic knowledge type

block_kind
→ source/document structural type

text
→ deterministic textual representation

section_path
→ explicit section hierarchy when known

source_locator
→ trace back to original source location/entity

structured_data
→ structured source fields when meaningful

metadata
→ small auxiliary fields only
```

Do not use one opaque JSON metadata object for every core field when explicit fields are stable and important.

---

# Content Type

Reuse the V0 semantic content types already defined in the AI/RAG data model:

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

Do not invent additional semantic content types unless there is a concrete product requirement.

---

# Block Kind

Keep `block_kind` separate from `content_type`.

Example structural kinds:

```text
HEADING
PARAGRAPH
LIST
TABLE
VOCABULARY_ITEM
GRAMMAR_SECTION
LESSON_GENERAL
```

Meaning:

```text
content_type
= what kind of knowledge is this?

block_kind
= how is this unit structurally represented?
```

Example:

```text
content_type = DOCUMENT_TEXT
block_kind   = PARAGRAPH
```

Do not collapse these concepts into one enum.

---

# Structured Data Preservation

Do not irreversibly flatten structured learning data.

Vocabulary should preserve fields equivalent to:

```text
hanzi
pinyin
meaning_vi
part_of_speech
example
note
```

Grammar should preserve fields equivalent to:

```text
name
structure
explanation
usage
examples
note
```

These fields should remain accessible in `structured_data` or an equivalent typed representation.

The canonical text representation exists in addition to structured data, not instead of it.

---

# Deterministic Vocabulary Text

Generate Vocabulary text deterministically from structured fields.

Equivalent representation:

```text
Từ: 你好
Pinyin: nǐ hǎo
Nghĩa: xin chào
Từ loại: ...
Ví dụ: ...
Ghi chú: ...
```

Omit unavailable optional fields deterministically.

Do not use an LLM to generate or rewrite this text.

Do not paraphrase the source content.

---

# Deterministic Grammar Text

Generate Grammar text deterministically.

Equivalent representation:

```text
Ngữ pháp: ...
Cấu trúc: ...
Giải thích: ...
Cách dùng: ...
Ví dụ: ...
Ghi chú: ...
```

Preserve original semantic fields.

Do not use an LLM formatter.

---

# Document Structure

For parsed documents, preserve explicit structural information that Step 5.3 already identified.

Examples:

```text
Heading
Paragraph
List
Table
```

Do not infer complex semantic structure that the parser did not actually provide.

---

# Section Hierarchy

When explicit headings/structure exist, maintain a `section_path`.

Example:

```text
[
  "Chapter 1",
  "Grammar",
  "把 sentence"
]
```

A block should inherit the current explicit section path according to source order.

This information is useful later for:

- chunking;
- citation;
- filtering;
- debugging.

---

# Unknown Section Structure

If a source such as a PDF does not expose reliable heading hierarchy:

```text
section_path = []
```

or equivalent null/empty representation.

Do not:

```text
guess headings aggressively
infer fake chapters
use an LLM to invent document structure
```

Reliable page/source locators are preferable to fabricated hierarchy.

---

# Document Title

Use the canonical `title` from source metadata defined in earlier ingestion steps.

Do not automatically replace the source metadata title with:

```text
first line
first heading
parser guess
```

Parser headings remain content/structure, not authoritative document identity.

---

# Document Provenance

Preserve document-level provenance from Step 5.1/5.2.

Logical fields may include:

```text
source_type
source_id
title
source_language
source_category
source_origin
author / organization
publisher
edition / version
original_reference
usage_rights_note
```

Optional fields remain optional.

Transformation must not discard provenance already collected upstream.

---

# Block-level Metadata

Keep block-level metadata limited to information that genuinely belongs to that block.

Core block-level information includes:

```text
source_locator
section_path
content_type
block_kind
order
```

Do not copy all document-level provenance into every block.

Avoid unnecessary metadata duplication.

---

# Source Locator

Normalize source locators into one logical model while preserving source-specific fields.

Equivalent optional fields:

```text
page_number
block_index
heading
lesson_id
vocabulary_id
grammar_id
```

Populate only fields that make sense for the source.

Examples:

```text
PDF block
→ page_number = 12

Vocabulary block
→ lesson_id = ...
→ vocabulary_id = ...

Grammar block
→ lesson_id = ...
→ grammar_id = ...
```

Do not require every source to have a page number.

---

# Stable Lesson Entity References

Preserve stable entity relationships for transformed Lesson content.

Vocabulary block:

```text
lesson_id
vocabulary_id
```

Grammar block:

```text
lesson_id
grammar_id
```

Do not rely on text matching to recover the source entity later.

This traceability must survive downstream chunking/citation.

---

# Lesson Section Paths

Use simple deterministic section paths for Lesson content.

Equivalent:

```text
Vocabulary
→ ["Vocabulary"]

Grammar
→ ["Grammar", "<grammar name>"]

Lesson General
→ ["Lesson"]
```

Do not create unnecessary deep hierarchy for Lesson content.

---

# Tables

When the parsed artifact contains an explicit structured table:

```text
block_kind = TABLE
```

Preserve:

```text
rows
cells
cell order
```

in structured data.

Also generate a deterministic textual representation for downstream processing.

Example:

```text
Word | Pinyin | Meaning
你好 | nǐ hǎo | xin chào
```

Do not discard table structure.

For PDFs where no reliable table structure was extracted, keep content as normal `DOCUMENT_TEXT` blocks.

Do not infer tables from uncertain text layouts.

---

# Lists

When Step 5.3 explicitly identified a list:

```text
block_kind = LIST
```

Preserve item order in structured data.

Generate deterministic textual representation.

Do not infer list structure from ambiguous PDF text.

---

# No Paragraph Merge

Do not merge separate parsed paragraphs merely to make larger blocks.

Preserve source semantic blocks.

Boundary:

```text
Transformation
→ normalize structure

Chunking
→ combine/split content for retrieval
```

---

# No Long-block Splitting

Do not split long paragraphs/blocks according to character/token limits in Step 5.4.

For example, do not:

```text
5000-char paragraph
→ five 1000-char blocks
```

solely because it is large.

Splitting policy belongs to Step 5.5.

---

# No Semantic Deduplication

Do not remove repeated/similar content across a source.

Do not run:

```text
semantic similarity dedup
near-duplicate removal
LLM duplicate detection
```

Repeated source content may be meaningful.

Exact duplicate raw-file rejection was handled earlier in Step 5.2.

---

# Empty Block Removal

Drop a block only when it contains no meaningful data:

```text
text empty
AND
structured_data empty
```

Do not remove a valid short block merely because its text is small.

Examples such as short headings or single vocabulary items must remain.

---

# No LLM Metadata Enrichment

Do not add LLM-generated metadata such as:

```text
topic
difficulty
grammar_category
semantic tags
summary
keywords
```

in Step 5.4.

Transformation metadata must come from:

- source metadata;
- explicit parsed structure;
- existing Lesson/Vocabulary/Grammar data;
- deterministic transformation logic.

---

# No Per-block Language Detection

Do not add automatic language detection for each block in V0.

Use document/source-level:

```text
source_language
```

and existing structured multilingual fields.

Per-block language classification may be introduced later only if retrieval/filtering creates a concrete requirement.

---

# Transformation Version

Persist:

```text
transformation_strategy
transformation_version
```

V0 equivalent:

```text
canonical_document
v1
```

The purpose is reproducibility and future Step 5.7 reprocessing decisions.

Do not build a plugin management framework.

---

# Deterministic Transformation

For the same:

```text
Parsed/Cleaned Artifact
+
transformation_version
```

the logical transformed output must remain deterministic.

Preserve stable block ordering.

Do not allow random ordering or AI-generated values to affect canonical output.

Artifact timestamps/IDs may exist as metadata but must not alter content semantics.

---

# Transformed Artifact Persistence

Persist the `TransformedDocument` as an intermediate pipeline artifact.

Pipeline:

```text
Raw Artifact
↓
Parsed/Cleaned Artifact
↓
TransformedDocument Artifact
↓
Step 5.5 Chunking
```

Step 5.5 must not rerun parsing/transformation merely to obtain input.

V0 may store the transformed artifact as structured JSON using the ingestion storage abstraction.

---

# No Relational Block Table in V0

Do not introduce a new relational table for every TransformedDocument Block unless the existing implementation already requires it for a concrete reason.

The transformed representation is intermediate pipeline data.

V0 approach:

```text
structured JSON artifact
+
artifact identity/metadata
```

is sufficient.

The durable retrieval model remains:

```text
KnowledgeSource
→ KnowledgeVersion
→ Chunk
→ Embedding
```

Chunk records belong to Step 5.5.

---

# No Chunk Creation

Do not create:

```text
Chunk
```

database records in Step 5.4.

Do not create placeholder/preliminary chunks.

Boundary:

```text
Step 5.4
Parsed units
→ canonical Blocks

Step 5.5
canonical Blocks
→ Chunk records
```

---

# KnowledgeVersion Lifecycle

Do not independently create, supersede, or activate KnowledgeVersion lifecycle in the transformation function.

Transformation operates within the processing context supplied by the pipeline.

Lifecycle/orchestration for:

```text
create version
run stages
activate
supersede previous version
```

belongs to later orchestration/reprocessing steps and existing KnowledgeVersion rules.

---

# Schema Validation

Define a typed schema/model for the canonical artifact.

Pydantic is appropriate because it is already part of the backend stack.

Before marking transformation successful, validate at least:

```text
source identity exists
title/source metadata shape is valid
blocks are ordered
content_type values are valid
block_kind values are valid
required text/structured data constraints are met
source_locator has a valid shape
```

Invalid canonical output must fail transformation explicitly.

---

# Transformation Status

Use stage states equivalent to:

```text
PENDING
PROCESSING
SUCCEEDED
FAILED
```

This is a logical processing state, not a background-job requirement.

If transformation fails:

```text
Parsed/Cleaned Artifact remains available
Transformed artifact is not exposed downstream
```

Do not delete upstream artifacts.

---

# Admin Preview Basis

The `TransformedDocument` is the canonical basis for future Admin Preview/Review because it:

```text
is cleaned
has normalized structure
retains provenance
retains source locations
is not yet chunked
```

Do not implement a full frontend preview UI in this step.

Ensure the transformed artifact contains enough information for later API/UI preview work.

---

# Suggested Module Boundaries

Equivalent structure:

```text
ingestion/
├── transformation/
│   ├── models
│   ├── service
│   ├── document_transformer
│   ├── lesson_transformer
│   └── formatters
└── artifacts/
```

Exact filenames may differ.

Do not create a separate microservice.

---

# Suggested Error Codes

Use the existing normalized backend error contract.

Add stable codes where useful, equivalent to:

```text
TRANSFORMATION_FAILED
INVALID_TRANSFORMED_DOCUMENT
UNSUPPORTED_CONTENT_TYPE
INVALID_SOURCE_LOCATOR
```

Do not expose internal serializer/schema exceptions directly to the client.

---

# Tests

Add focused tests covering at least:

## Canonical model

- parsed PDF transforms into `TransformedDocument`;
- parsed DOCX transforms into the same canonical model;
- parsed TXT/MD use the same canonical model;
- parsed Lesson uses the same downstream document boundary;
- stable source ordering is preserved.

## Content type

- Document blocks map to `DOCUMENT_TEXT`;
- Vocabulary maps to `VOCABULARY`;
- Grammar maps to `GRAMMAR`;
- other Lesson content maps to `LESSON_GENERAL`;
- unsupported content type fails explicitly.

## Block kind

- heading and paragraph remain distinguishable;
- table/list block kinds are preserved when explicitly parsed;
- `block_kind` remains independent from `content_type`.

## Vocabulary

- structured Vocabulary fields are preserved;
- canonical text is deterministic;
- optional fields may be omitted safely;
- lesson/vocabulary source references are retained.

## Grammar

- structured Grammar fields are preserved;
- canonical text is deterministic;
- lesson/grammar source references are retained.

## Provenance

- source metadata survives transformation;
- source locator survives transformation;
- PDF page number remains available;
- section paths remain when explicitly known;
- unknown PDF structure does not create invented headings.

## Structure

- paragraphs are not merged automatically;
- long blocks are not split by retrieval-size rules;
- repeated content is not semantically deduplicated;
- truly empty blocks are removed;
- short valid blocks remain.

## Determinism / versioning

- same parsed artifact + transformation version produces equivalent logical output;
- transformation strategy/version are persisted;
- no LLM enrichment is called;
- no per-block language detector is introduced.

## Artifact behavior

- transformed artifact is persisted;
- schema validation runs before success;
- invalid artifact produces FAILED status;
- parsed artifact survives transformation failure;
- no Chunk records are created by Step 5.4.

---

# Out of Scope

Do not implement in Step 5.4:

```text
chunk size
chunk overlap
token-aware splitting
semantic chunking
Chunk database creation
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
automatic KnowledgeVersion activation
pipeline orchestration
incremental/reprocessing policy
admin preview frontend
```

These belong to later steps/phases.

---

# Acceptance Criteria

- [ ] All parsed source types transform into one canonical `TransformedDocument`.
- [ ] Step 5.5 does not need source/parser-specific logic to consume transformed input.
- [ ] The internal unit is called Block, not Chunk.
- [ ] `DOCUMENT_TEXT`, `VOCABULARY`, `GRAMMAR`, and `LESSON_GENERAL` are reused.
- [ ] `block_kind` is distinct from `content_type`.
- [ ] Vocabulary/Grammar structured fields are preserved.
- [ ] Structured fields have deterministic text representations.
- [ ] Explicit section hierarchy is preserved.
- [ ] Unknown structure is not fabricated.
- [ ] Document title and provenance come from source metadata.
- [ ] Document-level metadata is not duplicated unnecessarily into every block.
- [ ] Source locators remain traceable.
- [ ] Lesson blocks retain stable entity references.
- [ ] Table/list structures are preserved when explicitly known.
- [ ] Transformation does not perform chunk merge/split logic.
- [ ] No semantic deduplication occurs.
- [ ] Empty blocks are removed only when truly empty.
- [ ] No LLM enrichment/tagging occurs.
- [ ] No per-block language detection is added.
- [ ] Transformation strategy/version are persisted.
- [ ] Transformation is deterministic.
- [ ] Transformed artifact is persisted.
- [ ] No unnecessary relational Block table is introduced.
- [ ] No Chunk records are created.
- [ ] Canonical artifact is schema-validated.
- [ ] Transformation failure preserves upstream artifacts.
- [ ] TransformedDocument is suitable as the basis for future Admin Preview.
- [ ] Step 5.5 can consume the transformed artifact directly.

# Expected Deliverable

Document-transformation foundation plus documentation:

```text
docs/data/
└── step-5.4-document-transformation.md
```

Next Step:

**Step 5.5 — Chunking**
