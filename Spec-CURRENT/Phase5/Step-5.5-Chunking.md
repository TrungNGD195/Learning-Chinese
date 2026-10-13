# Step 5.5 — Chunking

## Goal

Implement deterministic, structure-aware chunking from the canonical `TransformedDocument` produced by Step 5.4 into retrieval-ready `Chunk` records for a `PROCESSING` `KnowledgeVersion`.

The step must:

- use different chunking behavior by semantic `content_type`;
- preserve semantic and structural boundaries;
- keep Vocabulary and Grammar as atomic semantic units by default;
- merge/split textual Blocks deterministically;
- preserve source traceability and ordering;
- persist chunking strategy/configuration on the relevant KnowledgeVersion;
- persist Chunk records atomically;
- support safe deterministic reruns for a `PROCESSING` version;
- avoid modifying chunks belonging to an `ACTIVE` version;
- produce stable Chunk records that Step 6.1 can embed.

Do not implement embeddings, vector storage, retrieval, reranking, prompts, or LLM generation in this step.

---

# Input Boundary

Step 5.5 consumes only:

```text
TransformedDocument
└── ordered canonical Blocks
```

from Step 5.4.

Do not:

```text
reparse raw PDF/DOCX/TXT/MD
rerun cleaning
reread live Lesson state
```

Chunking should be source-format agnostic.

---

# Output Boundary

Step 5.5 creates:

```text
KnowledgeVersion (PROCESSING)
└── Chunk[]
```

Each chunk is a retrieval unit.

Embedding starts only in Step 6.1.

---

# Existing Chunk Data Model

Preserve the existing logical Chunk model and current project conventions.

Core fields include equivalents of:

```text
id UUID
knowledge_version_id
content
content_type
chunk_index
token_count nullable
page_number nullable
section nullable
lesson_id nullable
metadata JSONB nullable
created_at
```

The exact schema may already contain additional/renamed fields.

Inspect the existing model before adding migrations.

Do not replace the current data model unnecessarily.

---

# Supported Content Types

Reuse exactly the V0 content types:

```text
DOCUMENT_TEXT
VOCABULARY
GRAMMAR
LESSON_GENERAL
```

Do not add speculative content types in this step.

---

# Chunking Strategy Overview

Use hybrid structure-aware chunking:

```text
DOCUMENT_TEXT
→ structure-aware merge/split

VOCABULARY
→ atomic vocabulary chunk

GRAMMAR
→ atomic grammar chunk

LESSON_GENERAL
→ structure-aware merge/split
```

Do not use one blind fixed-character window across all content types.

---

# Hard Semantic Boundary: Content Type

Never merge Blocks with different `content_type` values into one Chunk.

Invalid:

```text
VOCABULARY + GRAMMAR
→ one chunk
```

Invalid:

```text
LESSON_GENERAL + VOCABULARY
→ one chunk
```

`content_type` is a hard chunk boundary.

---

# Section Boundary

For textual content, explicit section changes are hard merge boundaries.

Equivalent behavior:

```text
same content_type
AND same section_path
→ may merge if size allows

section_path changes
→ flush current chunk
```

Do not cross clearly different semantic sections solely to reach target size.

If a source has no reliable section path, do not fabricate one.

---

# Page Boundary

A PDF page boundary is not automatically a semantic chunk boundary.

Allow a textual chunk to span adjacent pages when:

```text
same semantic section
same content_type
source order is continuous
size remains acceptable
```

Preserve aggregate page trace:

```text
page_start
page_end
```

or equivalent locator metadata.

Do not lose page provenance.

---

# Vocabulary Chunking

Default:

```text
1 Vocabulary entity
→ 1 Chunk
```

Keep together the deterministic text representation of:

```text
hanzi
pinyin
meaning
part_of_speech
example
note
```

when available.

Do not:

```text
merge many vocabulary entries into one chunk
split one normal vocabulary entry into multiple chunks
```

A short Vocabulary chunk is valid.

Target character size does not force Vocabulary merging.

---

# Grammar Chunking

Default:

```text
1 Grammar entity
→ 1 Chunk
```

Keep together:

```text
name
structure
explanation
usage
examples
note
```

when available.

Do not split normal Grammar entities merely to hit target size.

Only use deterministic fallback splitting if a Grammar entity is exceptionally large beyond a safety limit.

Fallback splitting must preserve source trace and semantic identity.

---

# Lesson General Chunking

For `LESSON_GENERAL`:

```text
ordered Blocks
→ merge adjacent compatible small Blocks
→ respect section boundaries
→ split oversized textual Blocks if necessary
```

Do not merge Lesson General text into Vocabulary or Grammar chunks.

---

# Document Text Chunking

For `DOCUMENT_TEXT`:

```text
ordered canonical Blocks
↓
respect content_type
↓
respect explicit section boundaries
↓
merge compatible adjacent small Blocks
↓
target-size chunk
↓
split oversized Block deterministically when needed
↓
Chunk[]
```

Do not flatten the full document into one giant string before chunking.

---

# Heading Behavior

Do not emit tiny standalone heading chunks by default.

Preferred behavior:

```text
HEADING
+
following related content Blocks
→ same chunk
```

when section/content boundaries and size rules allow it.

Keep heading text in chunk content when it helps preserve semantic context.

The section path should remain in metadata regardless.

---

# Table Chunking

When Step 5.4 produced a structured Table Block:

## Small table

```text
table
→ one Chunk
```

if it fits safely.

## Large table

Split by complete row groups:

```text
header + rows group A
header + rows group B
...
```

If a header row exists, repeat it deterministically in each split table chunk.

Do not split arbitrarily in the middle of a cell.

Do not attempt PDF table reconstruction that was not already available from Step 5.4.

---

# List Chunking

For explicit List Blocks:

```text
small/normal list
→ keep list items together
```

If too large:

```text
split between complete list items
```

Do not split inside a list item until required as a final oversized-text fallback.

---

# Size Measurement

V0 chunk budgeting is model-independent.

Use:

```text
Unicode character count
```

rather than an embedding-model tokenizer.

Do not couple Step 5.5 to a model/tokenizer that is selected in Step 6.1.

After Step 6.1, the chosen embedding model may validate whether the chunk sizing strategy needs adjustment.

---

# V0 Size Configuration

Use defaults equivalent to:

```text
target_chars = 1200
max_chars = 1800
overlap_chars = 150
```

Semantics:

```text
target_chars
→ desired approximate size for merge decisions

max_chars
→ upper guard for normal generic textual chunks

overlap_chars
→ used only when splitting oversized textual Blocks
```

Do not treat `target_chars` as a mandatory exact cut point.

Prefer semantic boundaries over exact character counts.

Configuration must be centralized/configurable, not scattered magic numbers.

---

# No Hard Global Minimum

Do not impose one minimum Chunk length across all content.

Short semantic chunks such as:

```text
Vocabulary
short Grammar
short section
```

can be valid.

For generic document text, merge compatible adjacent Blocks to avoid needless tiny chunks, but do not delete valid knowledge solely because it is short.

---

# Overlap Policy

Do not use blind overlap between normal neighboring chunks.

Normal structure-aware merge output:

```text
Chunk A
Chunk B
```

has no duplicated overlap by default.

Use overlap only when splitting one oversized textual Block.

V0:

```text
overlap_chars = 150
```

This avoids unnecessary duplicate retrieval content while still preserving local continuity in forced splits.

---

# Oversized Text Splitting

When a single textual Block exceeds safe size and cannot remain atomic, split deterministically using natural separators in priority order.

Equivalent strategy:

```text
paragraph boundary
↓
line boundary
↓
sentence punctuation:
  。！？.!?
  ；;
↓
whitespace
↓
hard character boundary
```

The exact implementation may use a deterministic recursive splitter.

Do not introduce an NLP sentence-boundary model solely for V0.

Do not use LLM-based splitting.

---

# Oversized Semantic Units

Vocabulary:

```text
normally atomic
```

Grammar:

```text
normally atomic
```

If a semantic unit exceeds an unreasonable safety threshold, use a deterministic fallback while preserving:

```text
content_type
lesson/entity identity
source locator
part ordering
```

Do not silently truncate content.

---

# No Semantic Chunking in V0

Do not use:

```text
sentence embeddings
similarity-drop boundaries
topic segmentation models
semantic chunking frameworks
```

in V0.

Reasons:

- embedding model is not selected until Step 6.1;
- current source types are highly structured;
- deterministic behavior is easier to inspect and evaluate;
- model-dependent chunking would increase reprocessing complexity.

Semantic chunking may be evaluated later if Phase 7 shows a measurable need.

---

# No LLM Chunking

Do not call an LLM to decide chunk boundaries.

Chunking must remain deterministic and reproducible.

Do not send source content to an LLM for:

```text
"split this into good chunks"
summarization before chunking
rewriting
semantic tagging
```

---

# Chunk Content

`Chunk.content` must remain source-derived deterministic content.

Do not prepend synthetic retrieval metadata into the persisted canonical content by default.

Avoid:

```text
Document: ...
Section: ...
Page: ...

<source content>
```

inside `Chunk.content` solely for embedding.

Store title/section/source context separately.

Step 6.1 may define an embedding-input formatter that combines metadata + Chunk.content without mutating canonical chunk content.

---

# Chunk Traceability

Every Chunk must retain enough information to trace back to source.

At minimum preserve equivalents of:

```text
knowledge_version_id
chunk_index
content_type
section_path / section
source locator
source block start/end
```

For Document-derived chunks, support equivalent metadata:

```text
page_start
page_end
```

when known.

For Lesson-derived chunks, preserve equivalent identity:

```text
lesson_id
vocabulary_id optional
grammar_id optional
```

Do not rely on text matching for provenance.

---

# Locator Aggregation

When a chunk merges multiple source Blocks, aggregate source trace deterministically.

Example:

```text
Block 5 → page 10
Block 6 → page 10
Block 7 → page 11
```

Chunk metadata:

```text
block_start_order = 5
block_end_order   = 7
page_start        = 10
page_end          = 11
```

If source locators cannot be reduced safely to one range, keep a compact ordered locator representation in metadata.

Do not discard exact provenance for convenience.

---

# Chunk Ordering

Assign:

```text
chunk_index = 0, 1, 2, ...
```

according to canonical source order within one KnowledgeVersion.

Do not reorder chunks by:

```text
length
topic
hash
future retrieval score
```

Preserve deterministic source ordering.

---

# Chunk Content Hash

Persist a SHA-256 hash for each Chunk if the current schema allows it cleanly, or store it in an explicit field added by migration.

Logical field:

```text
content_hash
```

The hash should represent canonical chunk content plus only semantic fields required to distinguish logically different chunk payloads.

Use it for:

- debugging;
- future incremental processing;
- detecting unchanged chunk content;
- Step 5.7 reprocessing decisions.

Do not use it as the primary key.

If the existing schema already has an equivalent hash/fingerprint field, reuse it.

---

# Chunk Identity

Keep:

```text
Chunk.id = UUID
```

Do not derive Chunk IDs directly from content hashes.

Two chunks may contain identical text while belonging to different:

```text
sources
sections
versions
provenance
```

Identity is not the same as content equality.

Within one KnowledgeVersion, stable logical ordering is represented by:

```text
knowledge_version_id + chunk_index
```

---

# Chunking Configuration / Version

Persist chunking configuration on the processing version using current KnowledgeVersion conventions.

V0 equivalent:

```text
chunking_strategy = "structure_aware"
chunking_version  = "v1"
target_chars      = 1200
max_chars         = 1800
chunk_overlap     = 150
```

The existing model may already contain:

```text
chunking_strategy
chunk_size
chunk_overlap
```

Reuse existing fields where possible.

Add only the minimum additional field needed to represent strategy version or max size if the existing schema cannot express the chosen contract.

Do not duplicate configuration across every Chunk unless required.

---

# Determinism

For the same:

```text
TransformedDocument
+
chunking strategy/version
+
chunking config
```

the logical sequence of chunks must be deterministic.

Requirements include:

```text
stable source ordering
stable merge decisions
stable split boundaries
stable locator aggregation
stable content formatting
stable hashes
```

No randomization.

No external AI calls.

---

# KnowledgeVersion Safety

Chunking must operate on a version that is:

```text
PROCESSING
```

Do not rebuild/mutate Chunk records belonging to an:

```text
ACTIVE
```

KnowledgeVersion.

Preserve the safe version lifecycle:

```text
old ACTIVE remains usable
→ build new PROCESSING version
→ chunk
→ later embed
→ activate only after processing succeeds
```

Step 5.5 does not activate the version.

---

# Re-run / Idempotent Build

Chunking must be safely re-runnable for the same `PROCESSING` KnowledgeVersion.

Do not:

```text
retry
→ append another duplicate set of chunks
```

Preferred behavior:

```text
PROCESSING version
→ validate eligibility
→ rebuild/replace incomplete chunk set deterministically
```

Use transaction-safe delete/recreate or equivalent approach according to current repository/service architecture.

Do not touch an ACTIVE version.

The broader source-change/reprocessing policy remains Step 5.7.

---

# Atomic Persistence

Do not leave a partially valid chunk set.

Preferred flow:

```text
TransformedDocument
→ construct complete chunk plan in memory / processing layer
→ validate chunk plan
→ short DB transaction
→ replace/persist full Chunk set
→ commit
```

If persistence fails:

```text
rollback
→ no half-complete chunk set
```

Do not hold the DB transaction while doing slow external I/O.

Chunking itself is local deterministic processing and may happen before the persistence transaction.

---

# Chunk Validation

Validate every planned Chunk before persistence.

At minimum:

```text
content is non-empty
content_type is valid
chunk_index is valid
ordering is stable
source trace exists where applicable
generic textual size rules are respected
no unexpected cross-content-type merge occurred
no unexpected cross-section merge occurred
```

Vocabulary/Grammar may be shorter than the generic target.

Do not reject valid semantic chunks for being small.

Do not silently truncate oversized semantic units.

---

# Empty Chunk Policy

Do not create:

```text
empty
whitespace-only
```

chunks.

Short valid semantic knowledge remains.

---

# No Content Deduplication

Do not remove two chunks merely because:

```text
content_hash A == content_hash B
```

if provenance differs.

The same source text may legitimately occur in multiple:

```text
pages
sections
lessons
sources
```

Keep both occurrences.

The hash is for comparison, not automatic deduplication.

---

# Flat Chunks Only in V0

Do not implement parent-child/hierarchical chunking.

V0 remains:

```text
KnowledgeVersion
→ flat ordered Chunk[]
```

Do not add:

```text
parent_chunk_id
child_chunk hierarchy
section parent vectors
multi-vector parent retrieval
```

unless later evaluation demonstrates a concrete need.

---

# No Embedding in Step 5.5

Do not invoke embedding providers.

Boundary:

```text
Step 5.5
TransformedDocument
→ Chunk records
```

then:

```text
Step 6.1
Chunk
→ embedding input
→ Embedding
```

No vector operations occur here.

---

# Suggested Module Boundaries

Equivalent:

```text
ingestion/
├── chunking/
│   ├── models
│   ├── service
│   ├── strategy
│   ├── text_splitter
│   ├── vocabulary_chunker
│   ├── grammar_chunker
│   ├── document_chunker
│   └── locator
```

Exact filenames may differ.

Do not create a separate microservice.

Avoid unnecessary third-party chunking frameworks when the deterministic logic is simple enough to own directly.

---

# Suggested Errors

Use the project's normalized backend/business error contract.

Stable errors may include equivalents of:

```text
CHUNKING_FAILED
INVALID_CHUNKING_INPUT
KNOWLEDGE_VERSION_NOT_PROCESSING
INVALID_CHUNK
CHUNK_TOO_LARGE
```

Do not expose internal stack traces to API clients.

---

# Schema / Migration

Inspect current models and migrations first.

Existing KnowledgeVersion already logically stores chunk configuration and existing Chunk stores core content/provenance fields.

Only add schema fields if genuinely missing for the final contract, for example:

```text
chunking_version
content_hash
```

or a source-range field if existing metadata cannot represent it appropriately.

Prefer explicit relational columns for stable fields used frequently in filtering/citation.

Use JSON metadata only for less stable auxiliary source-locator details.

If schema changes are required:

- create a new Alembic migration;
- do not rewrite already-applied migrations;
- review generated migration manually.

Do not add Embedding-related schema in this step.

---

# Tests

Add focused tests covering at least:

## Strategy dispatch

- `DOCUMENT_TEXT` uses structure-aware document chunking.
- `VOCABULARY` uses atomic vocabulary chunking.
- `GRAMMAR` uses atomic grammar chunking.
- `LESSON_GENERAL` uses structure-aware lesson-general chunking.
- different content types are never merged.

## Vocabulary

- one normal Vocabulary entity becomes one Chunk.
- short vocabulary remains valid.
- structured deterministic text is preserved.
- lesson/vocabulary source identity remains traceable.
- multiple vocabulary entities are not merged together.

## Grammar

- one normal Grammar entity becomes one Chunk.
- grammar structure/explanation/examples remain together.
- lesson/grammar identity remains traceable.
- exceptional oversized grammar uses deterministic fallback or explicit safe failure.

## Document text

- adjacent compatible small Blocks may merge.
- explicit section change flushes the current chunk.
- page change alone does not force a chunk boundary.
- chunk spanning pages stores page range.
- headings attach to related following content when size allows.
- oversized paragraph splits deterministically.

## Tables

- small table remains one chunk.
- large table splits between row groups.
- table header repeats in each row-group chunk when applicable.
- no cell is arbitrarily cut by normal table splitting.

## Lists

- normal list stays together.
- oversized list splits between items before splitting an item.

## Size / overlap

- target size guides merge behavior without forcing exact size.
- generic max-size constraints are respected.
- no hard minimum deletes short valid content.
- normal adjacent chunks do not overlap.
- forced oversized-text splitting applies the configured overlap.
- splitting prefers natural separators before hard character boundaries.

## Provenance

- section path is retained.
- source block start/end is retained.
- page start/end is retained when known.
- Lesson entity references survive chunking.
- merged Blocks aggregate locators deterministically.

## Ordering / hashing

- chunk_index follows source order.
- rerunning produces the same logical chunk sequence.
- content hash is deterministic.
- identical content with different provenance is not deduplicated.
- Chunk ID remains independent from content hash.

## KnowledgeVersion safety

- chunking refuses ACTIVE version mutation.
- PROCESSING version may be built.
- rerun does not append duplicate chunk rows.
- persistence failure rolls back partial chunk set.
- Step 5.5 does not activate KnowledgeVersion.

## Boundaries

- no embedding provider is called.
- no semantic-chunking embedding model is called.
- no LLM is called.
- no vector record is created.

---

# Out of Scope

Do not implement in Step 5.5:

```text
embedding generation
embedding tokenizer coupling
vector storage
semantic retrieval
metadata filtering
reranking
prompt/context construction
LLM generation
semantic chunking by embeddings
LLM-based chunking
parent-child chunking
hierarchical retrieval
synthetic metadata prefixing for embedding
automatic KnowledgeVersion activation
full pipeline orchestration
source-change/reprocessing policy
```

These belong to later steps/phases.

---

# Acceptance Criteria

- [ ] Step 5.5 consumes only TransformedDocument/Blocks.
- [ ] Chunking is source-format agnostic.
- [ ] V0 content types remain `DOCUMENT_TEXT`, `VOCABULARY`, `GRAMMAR`, `LESSON_GENERAL`.
- [ ] Vocabulary defaults to one entity per Chunk.
- [ ] Grammar defaults to one entity per Chunk.
- [ ] Document/Lesson-General text uses structure-aware merge/split.
- [ ] Chunks never cross content types.
- [ ] Chunks do not cross explicit section boundaries.
- [ ] Page boundaries are not unnecessarily treated as semantic boundaries.
- [ ] Page ranges remain traceable.
- [ ] Heading content is attached to related text when appropriate.
- [ ] Tables/lists use structure-aware split behavior.
- [ ] V0 character-based budget is model-independent.
- [ ] Default configuration is approximately target 1200 / max 1800 / forced-split overlap 150 chars.
- [ ] No hard global minimum removes valid short semantic chunks.
- [ ] Overlap is not applied to normal neighboring chunks.
- [ ] Oversized text splitting is deterministic and separator-aware.
- [ ] No embedding-based semantic chunking is used.
- [ ] No LLM chunking is used.
- [ ] Canonical Chunk.content is source-derived and is not polluted with embedding-only metadata prefixes.
- [ ] Chunk provenance remains traceable to source Blocks/entities/pages.
- [ ] chunk_index preserves source order.
- [ ] Chunk content hash is deterministic.
- [ ] Chunk IDs remain UUIDs rather than content hashes.
- [ ] Chunking strategy/version/config are persisted.
- [ ] Chunking output is deterministic.
- [ ] Only PROCESSING KnowledgeVersions may be rebuilt.
- [ ] ACTIVE chunk sets are never mutated by chunking.
- [ ] Rerun does not append duplicate chunks.
- [ ] Chunk persistence is atomic.
- [ ] Empty chunks are not created.
- [ ] Identical content with different provenance is not deduplicated.
- [ ] V0 uses flat Chunk records only.
- [ ] No embeddings/vector operations occur.
- [ ] Step 6.1 can consume persisted Chunk records directly.

# Expected Deliverable

Chunking foundation plus documentation:

```text
docs/data/
└── step-5.5-chunking.md
```

Next Step:

**Step 5.6 — Pipeline Orchestration**
