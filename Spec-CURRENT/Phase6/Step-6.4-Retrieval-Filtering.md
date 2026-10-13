# Step 6.4 — Retrieval Filtering

## Goal

Implement metadata/context-aware filtering for internal semantic retrieval.

Step 6.3 already provides baseline retrieval:

```text
Question
→ Query Embedding
→ exact vector search over ACTIVE internal knowledge
→ RetrievalCandidate[]
```

Step 6.4 adds backend-owned retrieval scope and metadata constraints so vector ranking occurs inside the eligible subset rather than globally.

Core flow:

```text
Question
↓
Query Embedding
↓
RetrievalScope / RetrievalFilter
↓
SQL predicates
↓
cosine ranking inside eligible corpus
↓
Top-K filtered RetrievalCandidate[]
```

Do not implement reranking, automatic tier fallback, prompt construction, LLM generation, external retrieval, or citation rendering in this step.

---

# Core Principle

Apply filters before vector ranking.

Correct:

```sql
WHERE <metadata predicates>
ORDER BY embedding <=> :query_vector
LIMIT :candidate_k
```

Do not:

```text
global top-K
→ Python filter afterward
```

because globally top-ranked candidates can crowd out relevant candidates from the desired scope.

---

# RetrievalFilter

Create a typed object equivalent to:

```text
RetrievalFilter
├── lesson_ids?
├── hsk_levels / canonical HSK identities?
├── content_types?
├── source_types?
├── source_categories?
└── source_languages?
```

Use current canonical enums/identities from the codebase.

Do not pass a growing list of unrelated filter parameters through every method.

---

# Frontend Ownership

The frontend must not construct arbitrary retrieval internals.

Preferred flow:

```text
Frontend
→ business context
→ backend validates context
→ backend derives RetrievalScope / RetrievalFilter
→ SemanticRetrievalService
```

Examples:

```text
Conversation.lesson_id
→ CURRENT_LESSON scope

broader AI policy
→ INTERNAL_KB scope
```

Do not trust a client-supplied arbitrary filter object as the source of truth.

---

# SemanticRetrievalService Contract

Extend Step 6.3 behavior to support:

```python
retrieve(
    query_text,
    retrieval_filter=None,
    candidate_k=None,
)
```

Equivalent scope-aware helper methods are acceptable if they fit the codebase better.

Behavior:

```text
retrieval_filter = None
→ preserve Step 6.3 behavior
→ search all ACTIVE internal knowledge
```

Do not break the existing result contract.

---

# Supported V0 Filter Dimensions

## lesson_ids

Support a set/list:

```text
lesson_ids: set[UUID]
```

instead of only one lesson ID.

This supports:

```text
single Lesson Chat now
multi-lesson context later
```

without changing the contract.

## HSK identity / level

Use the canonical curriculum identity already present in the domain/schema.

Do not accept free-form variants such as:

```text
"hsk2"
"HSK 2"
"level2"
```

as the internal normalized value.

## content_types

Use existing canonical values:

```text
DOCUMENT_TEXT
VOCABULARY
GRAMMAR
LESSON_GENERAL
```

Do not add speculative content types.

## source_types

Use:

```text
DOCUMENT
LESSON
```

## source_categories

Support current Document categories:

```text
CURRICULUM_MATERIAL
INTERNAL_AUTHORED
```

Do not add numeric trust weighting.

## source_languages

Support:

```text
vi
zh
en
```

but do not apply a language filter by default.

Multilingual retrieval must continue to support:

```text
Vietnamese query
→ Chinese knowledge
```

when no explicit language restriction is requested.

---

# Fields Not Required as V0 Filters

Do not add generic filters for:

```text
page_number
section string
```

Page/section primarily support citation and provenance.

Do not invent:

```text
grammar_topic: free-text
```

only because the roadmap lists grammar topic as an example.

If existing persisted provenance exposes stable:

```text
grammar_id
vocabulary_id
```

the implementation may support them as optional fine-grained filters.

Do not add a large schema migration solely for this optional capability.

---

# Filter Semantics

Use:

```text
AND across filter dimensions
OR within one dimension
```

Example:

```text
lesson_id IN (L1)
AND
content_type IN (GRAMMAR, VOCABULARY)
```

This means:

```text
lesson dimension
AND content-type dimension
```

while values inside each `IN (...)` are OR alternatives.

---

# None vs Empty List

Semantics:

```text
None
→ unrestricted dimension
```

but:

```text
[]
→ invalid request
```

Do not interpret an empty explicit list as "remove the filter".

Fail with an error equivalent to:

```text
INVALID_RETRIEVAL_FILTER
```

This prevents accidental broadening when a caller expected zero eligible values.

---

# Invalid Values

Unknown enum/canonical values must fail validation.

Example:

```text
content_type = "GRAMMAR"
```

must not be silently ignored.

A filter typo must not widen retrieval scope.

---

# Contradictory Filters

Validate obvious impossible combinations.

Example:

```text
source_type = DOCUMENT
+
lesson_ids = {...}
```

is semantically contradictory in the current model.

Fail with an error equivalent to:

```text
INVALID_RETRIEVAL_FILTER_COMBINATION
```

rather than silently widening scope.

Use only contradictions that are provable from the current domain model.

Do not overbuild a generic SAT/constraint solver.

---

# RetrievalScope

Add a lightweight business-level abstraction:

```text
RetrievalScope
```

Keep it distinct from low-level `RetrievalFilter`.

V0 named scopes:

```text
CURRENT_LESSON
INTERNAL_KB
```

Do not invent many named scopes before product requirements need them.

---

# CURRENT_LESSON Scope

`CURRENT_LESSON` means:

```text
source_type = LESSON
AND
lesson_id = current lesson
```

This scope is strict.

It does not automatically include textbook/document chunks.

The purpose is to represent the actual current-lesson knowledge tier.

---

# INTERNAL_KB Scope

`INTERNAL_KB` means:

```text
all ACTIVE internal KnowledgeSources
```

including:

```text
Published Lesson knowledge
approved CURRICULUM_MATERIAL
approved INTERNAL_AUTHORED
```

It does not include external retrieval.

---

# Current Lesson > Internal KB Policy

The product policy is:

```text
Current Lesson Context
>
Internal approved KB
>
External Retrieval
```

Do not implement this as one query:

```text
WHERE current_lesson OR all_internal
ORDER BY similarity
```

because this does not preserve priority.

Correct mental model:

```text
Tier 1: CURRENT_LESSON
↓ if insufficient
Tier 2: INTERNAL_KB
```

Step 6.4 defines the scope/filter primitives only.

Step 6.8 will own automatic fallback/orchestration policy.

---

# No Automatic Scope Fallback Yet

If:

```text
retrieve(query, scope=CURRENT_LESSON)
```

returns:

```text
[]
```

Step 6.4 returns `[]`.

It does not automatically broaden to `INTERNAL_KB`.

A higher-level RAG policy may later use:

```text
0 results
→ broader scope
```

or quality-based fallback.

Do not invent an "insufficient" threshold in this step.

---

# Repository Filtering

Extend the low-level repository primitive equivalent to:

```python
nearest_vectors(
    query_vector,
    embedding_profile_id,
    retrieval_filter,
    limit,
)
```

The repository translates `RetrievalFilter` into SQL predicates.

It must still enforce all Step 6.2 invariants:

```text
KnowledgeVersion.status = ACTIVE
EmbeddingProfile.status = ACTIVE
```

regardless of caller filters.

---

# ACTIVE Gates Are Not Filters

Do not expose optional fields such as:

```text
knowledge_version_status
embedding_profile_status
```

inside `RetrievalFilter`.

ACTIVE version/profile constraints are hard retrieval invariants, not caller-configurable filters.

No caller may override them.

---

# Relational Predicates First

Prefer stable relational schema/joins for stable fields.

Examples:

```text
Chunk.lesson_id
Chunk.content_type
KnowledgeSource.source_type
Document.source_category
Document.source_language
canonical HSK relation
```

Use JSONB predicates only when a required optional provenance identity already lives there and no relational field exists.

Do not move all retrieval metadata into JSONB.

---

# SQL Shape

Equivalent query shape:

```sql
SELECT ...
FROM embeddings e
JOIN chunks c ...
JOIN knowledge_versions kv ...
JOIN knowledge_sources ks ...
...
WHERE
    kv.status = 'ACTIVE'
    AND ep.status = 'ACTIVE'
    AND <optional filter predicates>
ORDER BY e.vector <=> :query_vector
LIMIT :candidate_k;
```

Exact ORM/SQL implementation should follow the current SQLAlchemy repository conventions.

---

# Indexing Strategy

Do not automatically index every filterable field.

V0 corpus remains small and vector search is exact.

Before creating a new index:

```text
inspect current PK/FK/indexes
→ confirm query path
→ add only if useful and non-duplicate
```

Reasonable candidates, if not already indexed, may include:

```text
chunks.lesson_id
chunks.content_type
knowledge_sources.source_type
```

Do not add complex composite indexes such as:

```text
(lesson_id, content_type, source_type, ...)
```

without profiling evidence.

---

# RetrievalCandidate Contract

Preserve the Step 6.3 DTO:

```text
RetrievalCandidate
├── rank
├── chunk_id
├── chunk_index
├── content
├── content_type
├── knowledge_version_id
├── knowledge_source_id
├── source_type
├── section / locator metadata
├── distance
└── retrieval_score
```

Optional internal metadata may include:

```text
retrieval_scope
```

for diagnostics/tracing.

Do not require a database migration merely to add runtime scope trace.

---

# Ranking After Filtering

Filtering happens before ranking.

Therefore:

```text
rank = 1..N
```

means rank within the eligible filtered corpus.

Example:

```text
CURRENT_LESSON
→ retrieve top 20 inside that Lesson
```

Do not preserve a meaningless prior global rank.

---

# No Source Priority Weighting

Step 6.4 is eligibility filtering:

```text
candidate allowed?
yes / no
```

Do not add:

```text
Lesson +0.2
Textbook +0.1
Internal note +0.0
```

or any other score boosts.

Ranking adjustments belong to Step 6.5 or the later RAG policy layer.

---

# Lesson Context Derivation

For Lesson Chat, derive lesson scope from trusted backend context.

Preferred source:

```text
Conversation.lesson_id
```

or equivalent backend-owned current context.

Do not blindly trust:

```text
request body lesson_id
```

when the Conversation already identifies its Lesson.

Business authorization/context validation happens before retrieval scope derivation.

---

# Lesson Existence Validation

Retrieval service does not need an extra database round-trip solely to confirm every filter ID exists.

Validate:

```text
type / UUID shape / canonical enum values
```

and let the filtered SQL naturally return:

```text
[]
```

for a valid but non-matching ID.

Do not confuse "no matching ACTIVE knowledge" with malformed filter input.

---

# Logging

Log filter shape rather than content.

Useful fields:

```text
retrieval_scope
lesson_filter_count
hsk_filter_count
content_types
source_types
source_categories
source_languages
candidate_k
returned_count
top_retrieval_score optional
duration_ms
status
error_code optional
```

Do not log full Chunk content.

Follow the project's current identifier logging policy for IDs.

---

# MessageRetrieval Persistence

Do not modify the existing `MessageRetrieval` schema solely to persist filter metadata in V0.

Continue to persist later:

```text
message_id
chunk_id
rank
retrieval_score
rerank_score
```

when the higher-level RAG orchestration owns a Message.

If Phase 7 evaluation later requires detailed retrieval-run metadata, add it there with a concrete evaluation requirement.

---

# Suggested Errors

Use the normalized backend error contract.

Stable errors may include equivalents of:

```text
INVALID_RETRIEVAL_FILTER
INVALID_RETRIEVAL_FILTER_VALUE
INVALID_RETRIEVAL_FILTER_COMBINATION
INVALID_RETRIEVAL_SCOPE
RETRIEVAL_FILTERING_FAILED
```

Preserve Step 6.3/6.2 errors for embedding/vector failures.

Do not expose raw SQL exceptions.

---

# Suggested Module Changes

Equivalent:

```text
ai/
└── retrieval/
    ├── service.py
    ├── query_preprocessor.py
    ├── filters.py
    ├── scopes.py
    ├── schemas.py
    └── errors.py
```

Repository/data-layer filter translation stays with the vector/embedding repository module.

Do not put SQL-building logic inside `ConversationService`.

---

# Tests

Add focused tests covering at least:

## RetrievalFilter validation

- `None` dimension means unrestricted;
- empty explicit list is invalid;
- invalid content/source/category/language enum fails;
- contradictory `DOCUMENT + lesson_ids` combination fails;
- supported multi-value dimension uses OR semantics.

## SQL semantics

- dimensions combine with AND;
- values inside one dimension combine as IN/OR;
- filters are applied before `ORDER BY ... LIMIT`;
- Python post-filtering of global top-K is not used.

## lesson_ids

- one lesson returns only that Lesson's eligible chunks;
- multiple lesson IDs return either lesson;
- unrelated Lesson chunks are excluded.

## content_type

- `GRAMMAR` excludes vocabulary/document-text chunks;
- multi-type `{GRAMMAR, VOCABULARY}` returns either.

## source_type

- `DOCUMENT` excludes LESSON;
- `LESSON` excludes DOCUMENT.

## source_category

- CURRICULUM_MATERIAL can be selected;
- INTERNAL_AUTHORED can be selected;
- no numeric trust field/boost exists.

## source_language

- explicit `zh` returns eligible zh sources;
- default no-language filter can return multilingual candidates.

## RetrievalScope

- `CURRENT_LESSON` derives strict LESSON + lesson ID constraints;
- `INTERNAL_KB` permits all ACTIVE internal sources;
- CURRENT_LESSON does not automatically include documents;
- no automatic CURRENT_LESSON → INTERNAL_KB fallback occurs.

## ACTIVE safety

- PROCESSING/FAILED/SUPERSEDED knowledge remains excluded under all filters;
- INACTIVE EmbeddingProfile remains excluded;
- filters cannot override status gates.

## Ranking

- rank is computed after filtering;
- top-K belongs to the filtered corpus;
- no source/category score boost is applied.

## Result contract

- RetrievalCandidate shape remains compatible with Step 6.3;
- optional runtime retrieval_scope may be carried;
- no raw vectors are exposed.

## Lesson Chat context

- retrieval scope can be derived from backend Conversation.lesson_id;
- arbitrary request lesson_id does not override validated backend context.

## Empty result

- valid filter with no ACTIVE match returns [];
- malformed/invalid filter returns explicit error.

---

# Verification Dataset

Use a small test corpus such as:

```text
Lesson 1
├── Grammar A
└── Vocabulary A

Lesson 2
└── Grammar B

Document
└── related explanation of Grammar A
```

For a semantically related query verify:

```text
no filter
→ candidates can come from multiple sources
```

```text
CURRENT_LESSON(L1)
→ only Lesson 1 knowledge
```

```text
content_type = GRAMMAR
→ no VOCABULARY candidate
```

```text
source_type = DOCUMENT
→ no LESSON candidate
```

```text
source_language = zh
→ only explicitly eligible zh sources
```

and verify filtered ranking occurs before Top-K truncation.

---

# Out of Scope

Do not implement in Step 6.4:

```text
automatic CURRENT_LESSON → INTERNAL_KB fallback
"insufficient retrieval" threshold
source-priority weighting
reranking
cross-encoder scoring
prompt/context packing
LLM generation
external retrieval
conversation memory
citation rendering
generic section-text filtering
page-number retrieval policy
free-text grammar taxonomy
complex composite-index tuning
MessageRetrieval filter-history migration
```

These belong to later steps/phases.

---

# Acceptance Criteria

- [ ] `RetrievalFilter` exists as a typed retrieval constraint object.
- [ ] Backend derives filters from trusted business context.
- [ ] Frontend does not control arbitrary retrieval internals.
- [ ] SemanticRetrievalService accepts an optional filter without breaking Step 6.3 behavior.
- [ ] lesson_ids are supported.
- [ ] canonical HSK filtering is supported where schema/domain permits.
- [ ] content_types are supported.
- [ ] source_types are supported.
- [ ] current Document source_categories are supported.
- [ ] vi/zh/en source language filtering is supported.
- [ ] Language is unrestricted by default.
- [ ] page/section are not generic V0 retrieval filters.
- [ ] No speculative free-text grammar_topic is added.
- [ ] AND-across-dimensions / OR-within-dimension semantics are enforced.
- [ ] `None` means unrestricted.
- [ ] Empty explicit list is invalid.
- [ ] Invalid enum/value does not silently broaden scope.
- [ ] Obvious contradictory filters fail explicitly.
- [ ] `RetrievalScope` provides CURRENT_LESSON and INTERNAL_KB.
- [ ] CURRENT_LESSON is strict Lesson-only retrieval.
- [ ] INTERNAL_KB includes all ACTIVE internal knowledge only.
- [ ] Filtering happens in SQL before vector ranking/Top-K.
- [ ] ACTIVE KnowledgeVersion/Profile gates remain hard invariants.
- [ ] Caller cannot override ACTIVE gates.
- [ ] Stable metadata uses relational predicates.
- [ ] JSONB is used only for optional provenance when necessary.
- [ ] No speculative index explosion occurs.
- [ ] RetrievalCandidate contract remains compatible with Step 6.3.
- [ ] Rank is calculated inside the filtered corpus.
- [ ] No source-priority boost is applied.
- [ ] No automatic tier fallback is implemented.
- [ ] Step 6.5 can consume the filtered candidate set directly.

# Expected Deliverable

Retrieval filtering foundation plus documentation:

```text
docs/ai/
└── step-6.4-retrieval-filtering.md
```

Next Step:

**Step 6.5 — Reranking**
