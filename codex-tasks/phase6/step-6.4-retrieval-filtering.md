# Step 6.4 — Retrieval Filtering / Retrieval Scope

**Status:** FROZEN / READY_FOR_PM_TASK_REVIEW

> This is a JIT-pre-reviewed execution task. Do not implement until PM explicitly marks this task CODEX-READY.

## 1. Repository reconciliation

Accepted repository baseline:

- Step 6.3 is PM-accepted DONE/CLOSED.
- Alembic head remains `0012_vector_storage_readiness`.
- No Step 6.4 migration is expected.
- `SemanticRetrievalService.retrieve(query_text)` currently:
  - preprocesses the query;
  - resolves exactly one ACTIVE `EmbeddingProfile`;
  - verifies exact provider/profile semantic identity;
  - calls `EmbeddingProvider.embed_query()` outside DB transactions;
  - validates the query vector;
  - calls Step-6.2 `VectorStorageService.nearest_vectors(...)`;
  - hydrates normalized Chunk / KnowledgeVersion / KnowledgeSource provenance;
  - returns ranked `RetrievalCandidate[]`.
- Step 6.2 `nearest_vectors(session, query_vector, embedding_profile_id, limit)` currently owns:
  - `EmbeddingProfile.status = ACTIVE`;
  - `KnowledgeVersion.status = ACTIVE`;
  - exact cosine distance;
  - ordering by distance ASC, then `Chunk.id` ASC;
  - LIMIT.
- Current durable knowledge model includes:
  - `KnowledgeSource.source_type = DOCUMENT | LESSON`;
  - `KnowledgeSource.document_id` / `lesson_id` target invariant;
  - `KnowledgeVersion.knowledge_source_id`;
  - `Chunk.knowledge_version_id`;
  - `Chunk.content_type`;
  - nullable `Chunk.lesson_id` provenance;
  - `Document.source_category` with canonical `CURRICULUM_MATERIAL | INTERNAL_AUTHORED`;
  - `Document.source_language` with canonical `vi | zh | en`;
  - `Lesson.hsk_level_id → HSKLevel.level_number` canonical curriculum identity.
- V0 Conversation is Lesson-scoped and `Conversation.lesson_id` is backend-owned / NOT NULL.

### Reconciliation conclusions

1. No persistent schema change is required.
2. No new index is required for V0. Corpus is small and vector search remains exact; do not add speculative filter indexes in this step.
3. `CURRENT_LESSON` is strict LESSON-source retrieval only. It does not include Document sources.
4. `Chunk.lesson_id` is provenance / candidate metadata, not the canonical retrieval-scope predicate. Canonical lesson eligibility is `KnowledgeSource.source_type + KnowledgeSource.lesson_id`.
5. Step 6.4 requires one backward-compatible extension to the Step-6.2 vector-search interface so filter SQL executes before vector ordering / LIMIT.
6. Step 6.3 behavior with no filter must remain unchanged.

---

## 2. Problem

Step 6.3 retrieves global semantic Top-K from all ACTIVE internal knowledge.

For Lesson Chat, applying lesson/context filtering afterward in Python is incorrect:

```text
global Top-K
→ Python filter
```

Relevant lesson chunks may never enter the global Top-K and therefore cannot be recovered after filtering.

Correct flow:

```text
trusted retrieval eligibility
→ SQL predicates
→ cosine ORDER BY
→ LIMIT candidate_k
```

Step 6.4 must add typed, backend-owned scope/filter constraints without weakening ACTIVE lifecycle safety or absorbing reranking/fallback behavior.

---

## 3. Objective

Implement internal retrieval scoping/filtering so semantic candidates are selected from the eligible ACTIVE corpus before Top-K truncation.

Required outcomes:

- typed `RetrievalFilter`;
- lightweight `RetrievalScope` with `CURRENT_LESSON` and `INTERNAL_KB`;
- trusted Lesson scope derivation boundary;
- SQL predicate pushdown before cosine ordering/LIMIT;
- backward-compatible unfiltered Step-6.3 behavior;
- unchanged `RetrievalCandidate` semantic contract;
- no reranking, thresholding, fallback, schema migration, or public retrieval route.

---

## 4. Why this Step exists

Without Step 6.4:

```text
Question
→ global semantic Top-K
```

may return semantically close but product-ineligible knowledge.

Filtering after Top-K creates both correctness and retrieval-quality problems.

Mental distinction:

```text
ACTIVE gate
= may this persisted knowledge ever be searched in production?

Retrieval filter/scope
= is this ACTIVE knowledge eligible for this retrieval request?

Semantic ranking
= among eligible knowledge, which chunks are nearest?
```

---

## 5. Prerequisites

Must preserve accepted behavior from:

- Step 6.1 query embedding boundary;
- Step 6.2 ACTIVE profile/version safety and exact pgvector search;
- Step 6.3 deterministic preprocessing, query vector validation, candidate_k, score/rank semantics, candidate DTO, transaction/inference separation.

Accepted candidate count:

```text
RAG_RETRIEVAL_CANDIDATE_K
 default = 20
 min     = 1
 max     = 100
```

No new candidate-count setting.

---

## 6. Mental Model

```text
Trusted Business Context
        ↓
RetrievalScope
        ↓
RetrievalFilter
        ↓
Query Embedding
        ↓
ACTIVE gates
+ filter predicates
        ↓
exact cosine ranking
        ↓
Top-K inside eligible corpus
        ↓
RetrievalCandidate[]
```

Important:

```text
Scope/filter decides eligibility.
Cosine distance decides semantic order.
Reranker is a later step.
```

---

## 7. Exact Data Flow

### Unfiltered Step-6.3-compatible retrieval

```text
query_text
→ QueryPreprocessor
→ ACTIVE profile
→ provider identity check
→ embed_query()
→ vector validation
→ nearest_vectors(filter=None, limit=config candidate_k)
→ ACTIVE global internal corpus
→ metadata hydration
→ distance / retrieval_score / rank
→ RetrievalCandidate[]
```

### CURRENT_LESSON retrieval boundary

Later business/RAG orchestration owns the trusted Conversation lookup and authorization:

```text
validated Conversation
→ Conversation.lesson_id
→ RetrievalScope.CURRENT_LESSON
→ build_scope_filter(... trusted_lesson_id ...)
→ RetrievalFilter(
     lesson_ids={conversation.lesson_id},
     source_types={LESSON},
   )
→ SemanticRetrievalService.retrieve(query_text, retrieval_filter=...)
→ filtered nearest_vectors SQL
→ Top-K only inside that Lesson source corpus
```

Step 6.4 must not query Conversation itself and must not trust a raw frontend filter object.

---

## 8. Trusted scope derivation boundary

Add a pure internal boundary equivalent to:

```python
build_scope_filter(
    scope: RetrievalScope,
    *,
    trusted_lesson_id: UUID | None = None,
) -> RetrievalFilter | None
```

Rules:

### `CURRENT_LESSON`

Requires a backend-owned trusted Lesson ID.

```text
trusted_lesson_id is None
→ INVALID_RETRIEVAL_SCOPE
```

Returns equivalent filter:

```text
source_types = {LESSON}
lesson_ids   = {trusted_lesson_id}
```

### `INTERNAL_KB`

Means all ACTIVE internal knowledge.

Equivalent filter:

```text
None
```

No automatic CURRENT_LESSON → INTERNAL_KB fallback is allowed in Step 6.4.

### Ownership rule

Normal learner flow later must derive the trusted lesson ID from `Conversation.lesson_id` after business/auth validation.

Do not expose `RetrievalScope`, `RetrievalFilter`, or arbitrary lesson IDs as a new public HTTP retrieval API in this step.

---

## 9. RetrievalScope / RetrievalFilter contract

### RetrievalScope

Use only:

```text
CURRENT_LESSON
INTERNAL_KB
```

Do not add speculative scopes.

### RetrievalFilter

Create one immutable typed data object equivalent to:

```python
RetrievalFilter(
    lesson_ids: frozenset[UUID] | None = None,
    hsk_levels: frozenset[int] | None = None,
    content_types: frozenset[str] | None = None,
    source_types: frozenset[str] | None = None,
    source_categories: frozenset[str] | None = None,
    source_languages: frozenset[str] | None = None,
)
```

Canonical values:

```text
content_types:
DOCUMENT_TEXT
VOCABULARY
GRAMMAR
LESSON_GENERAL

source_types:
DOCUMENT
LESSON

source_categories:
CURRICULUM_MATERIAL
INTERNAL_AUTHORED

source_languages:
vi
zh
en
```

`hsk_levels` uses canonical `HSKLevel.level_number` integer identity. Do not accept free-form HSK strings.

Do not build a generic query DSL or Boolean-expression tree.

### Validation

For each collection dimension:

```text
None
→ unrestricted

explicit empty collection
→ INVALID_RETRIEVAL_FILTER
```

Unknown enum/string values:

```text
→ INVALID_RETRIEVAL_FILTER_VALUE
```

Validate only contradictions provable from the current model.

Minimum required contradiction:

```text
source_types = {DOCUMENT}
+
lesson_ids is not None
→ INVALID_RETRIEVAL_FILTER_COMBINATION
```

Do not build a generic constraint solver.

---

## 10. Exact CURRENT_LESSON eligibility predicate

Canonical safety/product predicate:

```sql
knowledge_sources.source_type = 'LESSON'
AND knowledge_sources.lesson_id = :trusted_lesson_id
```

This is the Step-6.4 `CURRENT_LESSON` contract.

### Role of Chunk.lesson_id

`Chunk.lesson_id` is nullable and is preserved as fine-grained provenance for Lesson-derived chunks.

It is **not** the canonical scope predicate and must not be used to widen CURRENT_LESSON eligibility.

Do not require `Chunk.lesson_id` as an additional mandatory predicate in V0, because the accepted canonical source relation is `KnowledgeSource.lesson_id` and valid Chunk provenance is nullable at schema level.

Candidate hydration may continue to expose `chunk_lesson_id` for diagnostics/provenance.

---

## 11. Document / curriculum knowledge policy

### CURRENT_LESSON

Strictly excludes Document sources.

Do not automatically include:

```text
CURRICULUM_MATERIAL
INTERNAL_AUTHORED
```

simply because a Document is pedagogically related to the current Lesson.

### INTERNAL_KB

Includes all ACTIVE internal KnowledgeSources, including:

```text
published Lesson knowledge
approved CURRICULUM_MATERIAL Documents
approved INTERNAL_AUTHORED Documents
```

The fact that a KnowledgeVersion is ACTIVE remains the production-availability gate; Step 6.4 does not reimplement document approval or activation logic.

---

## 12. Filter-before-vector-Top-K integration design

The accepted Step-6.2 search primitive must receive an optional typed filter so SQL filtering occurs before `ORDER BY` / `LIMIT`.

Backward-compatible interface equivalent to:

```python
VectorStorageService.nearest_vectors(
    query_vector,
    embedding_profile_id,
    limit,
    *,
    retrieval_filter: RetrievalFilter | None = None,
)
```

Repository equivalent:

```python
repository.nearest_vectors(
    session,
    query_vector,
    profile_id,
    limit,
    *,
    retrieval_filter: RetrievalFilter | None = None,
)
```

Existing unfiltered callers pass/receive `None` behavior automatically.

The same repository query must preserve:

```text
EmbeddingProfile.status = ACTIVE
KnowledgeVersion.status = ACTIVE
Embedding.embedding_profile_id = requested ACTIVE profile
```

and add filter predicates to the same SQL statement before:

```sql
ORDER BY distance ASC, chunks.id ASC
LIMIT :candidate_k
```

Do not implement:

```text
global nearest_vectors()
→ Python filter
```

### Dependency rule

`RetrievalFilter` must be a data-only module (`app.ai.retrieval.filters`) with no dependency on `vector_storage.service` or retrieval service orchestration.

`vector_storage.repository` may depend only on this data-only filter contract for predicate translation. Do not create a vector_storage → retrieval.service import cycle.

Do not duplicate pgvector SQL/ACTIVE gates inside a second retrieval-specific vector query.

---

## 13. Step-6.2 / Step-6.3 interface impact

### Step 6.2

Narrow backward-compatible interface extension only:

```text
nearest_vectors(...)
→ nearest_vectors(..., retrieval_filter=None)
```

No lifecycle behavior changes.

No change to:

```text
cosine metric
exact scan
ACTIVE gates
profile resolution
activation/readiness
result = chunk_id + distance
```

### Step 6.3

Extend service equivalent to:

```python
SemanticRetrievalService.retrieve(
    query_text: str,
    *,
    retrieval_filter: RetrievalFilter | None = None,
) -> list[RetrievalCandidate]
```

Do **not** add a `candidate_k` request/method override. Continue using backend setting `RAG_RETRIEVAL_CANDIDATE_K`.

Behavior:

```text
retrieval_filter=None
→ identical Step 6.3 behavior
```

Filtering is validated before expensive provider inference.

Candidate hydration and score/rank construction remain Step-6.3 behavior.

---

## 14. Result / input schemas

### Input

Internal service input only:

```text
query_text: str
retrieval_filter: RetrievalFilter | None
```

No public HTTP route.

No raw frontend `RetrievalFilter` endpoint contract.

### Output

Preserve accepted `RetrievalCandidate` exactly unless an implementation-only non-breaking field is required:

```text
rank
chunk_id
chunk_index
content
content_type
knowledge_version_id
knowledge_source_id
source_type
source_document_id
source_lesson_id
chunk_lesson_id
document_title
lesson_title
hsk_level_number
page_number
section
locator_metadata
distance
retrieval_score
```

Do not expose raw vector.

Do not persist retrieval scope/filter metadata.

Do not add `rerank_score` to this runtime candidate just for Step 6.4.

---

## 15. Repository / service responsibilities

### `filters.py`

Own:

- typed `RetrievalFilter`;
- canonical value validation;
- None vs empty semantics;
- obvious contradiction validation.

No SQL.

### `scopes.py`

Own:

- `RetrievalScope`;
- pure translation from trusted business context to `RetrievalFilter`;
- `CURRENT_LESSON` / `INTERNAL_KB` semantics.

No Conversation DB access.

### `SemanticRetrievalService`

Continue owning:

- preprocessing;
- active profile/provider resolution;
- query embedding/vector validation;
- backend candidate_k;
- call to filtered Step-6.2 search;
- candidate hydration;
- retrieval score/rank;
- normalized error/logging behavior.

It does not own business authorization or Conversation lookup.

### Vector storage repository/service

Own:

- ACTIVE gates;
- relational SQL predicate translation;
- cosine ordering;
- LIMIT;
- raw `chunk_id + distance` result.

Do not commit.

---

## 16. Exact SQL filter semantics

Use AND across dimensions, OR/IN within one dimension.

Equivalent predicates:

```text
lesson_ids
→ KnowledgeSource.lesson_id IN (...)

hsk_levels
→ Lesson → HSKLevel.level_number IN (...)

content_types
→ Chunk.content_type IN (...)

source_types
→ KnowledgeSource.source_type IN (...)

source_categories
→ Document.source_category IN (...)

source_languages
→ Document.source_language IN (...)
```

Join normalized relational entities as needed.

Do not denormalize filter fields into `Embedding`.

Do not use JSONB for stable filter fields that already have relational columns.

Do not add page/section generic filtering in V0.

No source-priority weighting.

---

## 17. Failure / error semantics

Use current `ApplicationError` / retrieval error conventions.

Required stable behavior equivalent to:

```text
INVALID_RETRIEVAL_FILTER
INVALID_RETRIEVAL_FILTER_VALUE
INVALID_RETRIEVAL_FILTER_COMBINATION
INVALID_RETRIEVAL_SCOPE
```

Validation failures must occur before embedding/vector work where possible.

### Missing trusted Lesson scope

```text
scope = CURRENT_LESSON
trusted_lesson_id = None
→ INVALID_RETRIEVAL_SCOPE
```

### Invalid/malformed filter

Reject explicitly. Never silently ignore invalid values and broaden retrieval.

### Valid Lesson UUID / filter but zero ACTIVE eligible knowledge

```text
→ []
```

No extra Lesson existence DB round-trip is required solely for retrieval filtering.

### Technical DB/vector failure

Preserve Step-6.3 normalized technical failure (`VECTOR_RETRIEVAL_FAILED` or the already accepted equivalent).

Never convert technical failure to `[]`.

Do not log raw SQL exception text.

---

## 18. Transaction / session behavior

Preserve Step 6.3 transaction model:

```text
short DB read → active profile snapshot
commit/end

embed_query()
NO DB transaction

short DB read
→ ACTIVE + filter predicates
→ cosine ORDER BY / LIMIT
→ metadata hydration
end
```

Filter validation/scope translation is pure and should run before model inference.

No write transaction.

No persistence of:

```text
query vector
RetrievalFilter
RetrievalScope
MessageRetrieval
```

---

## 19. Logging

Extend structured retrieval logs with filter shape only when useful:

```text
retrieval_scope optional
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

Do not log:

```text
raw query text
query vector
Chunk.content
raw SQL/driver exception
```

Do not log every lesson/document UUID list by default; counts/enum shapes are sufficient unless current project identifier policy explicitly allows more.

---

## 20. Expected files

### New

```text
backend/app/ai/retrieval/filters.py
backend/app/ai/retrieval/scopes.py

backend/tests/test_step64_retrieval_filters.py
backend/tests/test_step64_filtered_vector_repository.py
backend/tests/test_step64_retrieval_scope.py
backend/tests/test_step64_retrieval_service.py

docs/ai/step-6.4-retrieval-filtering.md
```

A focused shared test helper may be added under existing test conventions if needed.

### Modify

```text
backend/app/ai/retrieval/service.py
backend/app/ai/vector_storage/repository.py
backend/app/ai/vector_storage/service.py
```

Modify `backend/app/ai/retrieval/schemas.py` only if a genuinely required non-breaking runtime type change is needed. Prefer keeping `RetrievalCandidate` unchanged.

### Must not change

```text
Alembic migrations
database models/schema
embedding provider/model config
RAG_RETRIEVAL_CANDIDATE_K contract
Conversation public API/frontend
```

---

## 21. Testing matrix

### A. RetrievalFilter validation

- all dimensions `None` → valid unrestricted filter;
- explicit empty `lesson_ids` → `INVALID_RETRIEVAL_FILTER`;
- explicit empty list/set for every supported dimension → invalid;
- invalid content type → `INVALID_RETRIEVAL_FILTER_VALUE`;
- invalid source type → error;
- invalid source category → error;
- invalid source language → error;
- HSK free-form string is not accepted as canonical internal identity;
- `source_types={DOCUMENT}` + non-null `lesson_ids` → `INVALID_RETRIEVAL_FILTER_COMBINATION`;
- supported multi-value collections remain valid.

### B. Filter composition SQL semantics

Use real PostgreSQL/pgvector tests.

Prove:

```text
AND across dimensions
OR/IN within one dimension
```

Example:

```text
lesson_ids={L1}
AND content_types={GRAMMAR,VOCABULARY}
```

returns only L1 and either allowed type.

### C. Filter-before-Top-K proof

Construct data where:

```text
candidate_k = 1

global nearest candidate = Lesson 2
second-nearest candidate = Lesson 1
```

Then:

```text
CURRENT_LESSON(L1)
→ Lesson 1 candidate is returned rank 1
```

This test must fail under global-Top1-then-Python-filter behavior.

### D. CURRENT_LESSON

- trusted L1 → only `KnowledgeSource.source_type=LESSON` + `KnowledgeSource.lesson_id=L1`;
- L2 excluded;
- semantically related Document excluded even if category is CURRICULUM_MATERIAL;
- a Chunk under an L2 KnowledgeSource is excluded from CURRENT_LESSON(L1) even if `Chunk.lesson_id=L1`;
- a Chunk under an L1 KnowledgeSource remains eligible when nullable `Chunk.lesson_id` is NULL; canonical source predicate remains KnowledgeSource-based;
- missing trusted Lesson ID → `INVALID_RETRIEVAL_SCOPE` before provider call.

### E. INTERNAL_KB

- scope maps to unrestricted filter/all ACTIVE internal knowledge;
- can return Lesson and approved active Document knowledge;
- no external retrieval;
- no automatic fallback logic.

### F. lesson_ids generic filter

- one Lesson ID returns that Lesson only;
- multiple Lesson IDs return either;
- unrelated Lesson excluded;
- valid but non-matching UUID returns `[]`;
- no extra existence query required solely to validate the ID.

### G. HSK filter

- canonical `HSKLevel.level_number` filters Lesson knowledge correctly;
- multiple levels are OR within dimension;
- no free-form `"HSK 2"` normalization;
- no HSK filter by default.

### H. content_type

- `GRAMMAR` excludes VOCABULARY / DOCUMENT_TEXT;
- `{GRAMMAR,VOCABULARY}` returns either;
- no new content types.

### I. source_type

- DOCUMENT excludes LESSON;
- LESSON excludes DOCUMENT.

### J. Document source category

- CURRICULUM_MATERIAL selectable;
- INTERNAL_AUTHORED selectable;
- category filter naturally excludes Lesson sources;
- no numeric source trust score/boost.

### K. source language

- `zh` returns eligible zh Documents;
- `vi` / `en` are supported;
- no language filter allows multilingual candidates;
- Vietnamese query may retrieve Chinese knowledge when unrestricted.

### L. ACTIVE safety

Under every relevant filter:

- PROCESSING excluded;
- FAILED excluded;
- SUPERSEDED excluded;
- INACTIVE profile excluded;
- caller cannot place lifecycle statuses in RetrievalFilter;
- Step-6.2 repository remains final ACTIVE gate.

### M. Candidate / ranking compatibility

- `RetrievalCandidate` fields remain Step-6.3 compatible;
- raw vector absent;
- distance unchanged;
- `retrieval_score = 1 - distance` unchanged;
- score not clamped;
- rank starts at 1 inside filtered corpus;
- deterministic distance/Chunk.id ordering retained.

### N. Step-6.3 compatibility

`retrieve(query_text, retrieval_filter=None)` must match previous Step-6.3 behavior.

No frontend/caller candidate_k override is added.

### O. Failure behavior

- invalid filter fails before provider/vector call;
- missing CURRENT_LESSON trusted ID fails before provider call;
- valid filter + no candidate returns `[]`;
- vector/DB technical failure stays technical error, not `[]`;
- safe logs do not contain query/vector/content/raw DB exception.

### P. Scope / non-goals

Assert no:

```text
reranker/cross-encoder call
RAG_MIN_RERANK_SCORE
similarity threshold
source boost
automatic CURRENT_LESSON→INTERNAL_KB fallback
external retrieval
prompt/LLM call
public retrieval route
schema migration
ANN index
```

---

## 22. Verification commands

From `backend/` using the accepted dedicated PostgreSQL/pgvector test environment:

```bash
uv lock --check

uv run --no-sync alembic current
uv run --no-sync alembic check

uv run --no-sync pytest -p no:cacheprovider \
  tests/test_step64_retrieval_filters.py \
  tests/test_step64_filtered_vector_repository.py \
  tests/test_step64_retrieval_scope.py \
  tests/test_step64_retrieval_service.py

uv run --no-sync pytest -p no:cacheprovider \
  tests/test_step63_query_preprocessor.py \
  tests/test_step63_retrieval_repository.py \
  tests/test_step63_retrieval_service.py \
  tests/test_step63_semantic_retrieval_smoke.py

uv run --no-sync pytest -p no:cacheprovider \
  tests/test_step62_vector_storage_migration.py \
  tests/test_step62_vector_repository.py \
  tests/test_step62_vector_readiness.py \
  tests/test_step62_activation.py

uv run --no-sync pytest -p no:cacheprovider \
  tests/test_step61_embedding_profile_migration.py \
  tests/test_step61_embedding_formatter.py \
  tests/test_step61_embedding_provider.py \
  tests/test_step61_embedding_service.py

uv run --no-sync pytest -p no:cacheprovider \
  tests/test_step55_chunking.py \
  tests/test_step55_chunking_service.py \
  tests/test_step56_document_pipeline.py \
  tests/test_step56_lesson_pipeline.py \
  tests/test_step56_orchestration_concurrency.py \
  tests/test_step57_reprocessing_planner.py \
  tests/test_step57_reprocessing_execution.py \
  tests/test_step57_reprocessing_concurrency.py

uv run --no-sync pytest -p no:cacheprovider
uv run --no-sync python -m compileall app
```

If environment execution conventions differ, use the accepted equivalent commands and report exactly what was run. Never claim a command passed unless actually executed.

No Alembic revision after `0012_vector_storage_readiness` should be created.

---

## 23. Scope / non-goals

Do not implement:

- automatic CURRENT_LESSON → INTERNAL_KB fallback;
- "insufficient evidence" threshold;
- similarity threshold;
- `RAG_MIN_RERANK_SCORE`;
- source/category weighting;
- reranking / cross-encoder;
- context packing;
- prompt construction;
- LLM generation;
- external retrieval;
- conversation memory;
- citation rendering;
- page-number/section generic filtering;
- free-text grammar taxonomy;
- BM25/hybrid retrieval;
- ANN indexes;
- cache/Redis/queue;
- MessageRetrieval filter-history persistence;
- public retrieval/filter API;
- frontend scope/filter controls;
- schema migration.

Step 6.5 owns reranking.
Step 6.8 owns automatic retrieval-tier fallback/orchestration.

---

## 24. Step Note

Create:

```text
docs/ai/step-6.4-retrieval-filtering.md
```

Include:

### Objective
Constrain semantic retrieval to backend-authorized eligible knowledge before vector Top-K.

### Why
Global Top-K followed by filtering can lose relevant in-scope candidates and violate Lesson-scoped product policy.

### Mental Model

```text
ACTIVE safety
→ eligibility filter
→ semantic ranking
→ reranking later
```

### Core Knowledge

- predicate pushdown;
- trusted context vs caller-controlled filter;
- RetrievalScope vs RetrievalFilter;
- AND across dimensions / OR within dimension;
- empty filter collection fail-closed;
- active lifecycle gates remain separate from filtering.

### Data Flow
Use the exact CURRENT_LESSON and INTERNAL_KB flows from this task.

### Key Design Decisions

- CURRENT_LESSON = strict LESSON KnowledgeSource + trusted lesson ID;
- Documents excluded from CURRENT_LESSON;
- INTERNAL_KB = all ACTIVE internal sources;
- `Chunk.lesson_id` is provenance, not canonical scope ownership;
- SQL filtering occurs before vector `ORDER BY/LIMIT`;
- no schema migration/index explosion;
- Step 6.3 unfiltered behavior preserved.

### Reusable approach
Separate:

```text
production availability
business eligibility
ranking
```

and push eligibility predicates into the data query before Top-K.

### Common Mistakes

- trusting frontend lesson/filter IDs as authoritative;
- filtering global Top-K in Python;
- treating ACTIVE as optional filter;
- including all curriculum Documents in CURRENT_LESSON;
- using empty list as unrestricted;
- adding score boosts in filtering step;
- inventing a generic query DSL;
- duplicating metadata into vectors.

### Definition of Done
Mirror the acceptance criteria below and actual implementation.

---

## 25. Concepts Discovered

Record only after actual implementation.

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Retrieval Scope | AI | 6.4 | Represents backend-owned knowledge tier such as CURRENT_LESSON or INTERNAL_KB. |
| Retrieval Filter | AI | 6.4 | Typed eligibility constraints applied before vector ranking. |
| Predicate Pushdown | BOTH | 6.4 | Applies relational eligibility inside SQL before Top-K, preserving retrieval quality and DB efficiency. |
| Trusted Context Derivation | SYSTEM | 6.4 | Prevents the learner/frontend from inventing authoritative retrieval scope. |
| Filter Composition | AI | 6.4 | Defines AND-across-dimensions / OR-within-dimension retrieval semantics. |
| Fail-closed Filter Validation | SYSTEM | 6.4 | Prevents malformed/empty filters from silently broadening retrieval scope. |
| ACTIVE Retrieval Gate | BOTH | 6.4 | Reuses production lifecycle safety independently from request-specific filtering. |

Do not add concepts not actually implemented.

---

## 26. Tools Used

Record only after actual implementation.

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| PostgreSQL | DE | 6.4 | Executes relational filter predicates before vector Top-K. |
| pgvector | BOTH | 6.4 | Preserves exact cosine ranking inside the filtered eligible corpus. |
| SQLAlchemy async | DE | 6.4 | Builds joins/predicates and preserves repository/session conventions. |
| pytest | SYSTEM | 6.4 | Verifies scope, SQL semantics, ACTIVE safety, and regressions. |

No new runtime dependency is expected.

---

## 27. Acceptance Criteria

- [ ] `RetrievalFilter` exists as a typed internal constraint object.
- [ ] Supported V0 dimensions are exactly lesson IDs, canonical HSK level numbers, content types, source types, Document source categories, and Document source languages.
- [ ] `None` means unrestricted for a dimension.
- [ ] An explicit empty collection is invalid and never widens retrieval.
- [ ] Invalid canonical values fail explicitly.
- [ ] Obvious current-model contradictions fail explicitly.
- [ ] Filter composition is AND across dimensions / OR within one dimension.
- [ ] `RetrievalScope` has exactly CURRENT_LESSON and INTERNAL_KB for V0.
- [ ] CURRENT_LESSON requires a trusted backend Lesson ID.
- [ ] CURRENT_LESSON predicate is `KnowledgeSource.source_type=LESSON AND KnowledgeSource.lesson_id=trusted lesson_id`.
- [ ] CURRENT_LESSON excludes Document sources, including CURRICULUM_MATERIAL and INTERNAL_AUTHORED.
- [ ] INTERNAL_KB means all ACTIVE internal knowledge; it does not include external retrieval.
- [ ] `Chunk.lesson_id` is not used to widen/canonicalize source scope.
- [ ] Normal learner retrieval scope is derived later from validated `Conversation.lesson_id`, not raw frontend filter input.
- [ ] Step-6.2 nearest-vector interface is extended only backward-compatibly with an optional filter.
- [ ] ACTIVE KnowledgeVersion/Profile predicates remain mandatory under every filter.
- [ ] Caller cannot override ACTIVE lifecycle predicates through RetrievalFilter.
- [ ] Filters are applied in SQL before cosine `ORDER BY` and `LIMIT`.
- [ ] A test proves filter-before-Top-K rather than Python post-filtering.
- [ ] No duplicate vector-search implementation bypasses Step-6.2 ACTIVE gates.
- [ ] Step-6.3 `retrieve(query_text, retrieval_filter=None)` preserves unfiltered behavior.
- [ ] `RAG_RETRIEVAL_CANDIDATE_K` remains default 20, range 1..100, backend-owned.
- [ ] No new per-request candidate_k override is exposed.
- [ ] Distance remains cosine distance.
- [ ] `retrieval_score = 1 - distance` remains unchanged and unclamped.
- [ ] Rank is recomputed from filtered semantic order, starting at 1.
- [ ] `RetrievalCandidate` remains compatible with Step 6.3 and exposes no vector.
- [ ] Valid scope/filter with zero ACTIVE match returns `[]`.
- [ ] Technical DB/vector failure remains distinct from `[]`.
- [ ] Invalid/missing trusted scope fails before expensive AI work where possible.
- [ ] No extra Lesson existence lookup is required solely for a valid typed Lesson ID.
- [ ] No schema migration is added; Alembic head remains `0012_vector_storage_readiness`.
- [ ] No speculative filter index explosion is added.
- [ ] No source-priority boost, threshold, reranking, cross-encoder, RAG_MIN_RERANK_SCORE, or evidence decision is added.
- [ ] No automatic CURRENT_LESSON→INTERNAL_KB fallback is added.
- [ ] No public retrieval/filter route or frontend filter ownership is added.
- [ ] Step 6.5 can consume the filtered `RetrievalCandidate[]` directly.
- [ ] Focused and required regression tests pass.
- [ ] Step Note reflects actual implementation.

---

## 28. Codex completion-report format

Return exactly enough evidence for independent specialist review:

```text
Step:
6.4 — Filtering / Retrieval Scope

Status:
READY_FOR_SPECIALIST_REVIEW | BLOCKED

Files changed:
<exact list>

Production code changed:
YES/NO

Migration changed:
NO expected

Schema changed:
NO expected

Dependencies changed:
NO expected

Accepted Alembic head:
0012_vector_storage_readiness

RetrievalScope:
CURRENT_LESSON
INTERNAL_KB

CURRENT_LESSON predicate:
KnowledgeSource.source_type = LESSON
AND KnowledgeSource.lesson_id = trusted lesson_id

Documents included in CURRENT_LESSON:
NO

Chunk.lesson_id role:
provenance / candidate metadata; not canonical scope predicate

RetrievalFilter dimensions:
lesson_ids
hsk_levels
content_types
source_types
source_categories
source_languages

Filter composition:
AND across dimensions
OR within one dimension

Filter-before-Top-K:
<exact SQL/repository behavior>

Step-6.2 ACTIVE gates preserved:
YES/NO

Step-6.3 unfiltered behavior preserved:
YES/NO

RAG_RETRIEVAL_CANDIDATE_K:
default = 20
min = 1
max = 100

Distance/score:
cosine distance
retrieval_score = 1 - distance
no threshold

Automatic scope fallback:
NO

Reranking / Step 6.5 work:
NO

Errors implemented/used:
<exact codes>

Verification commands actually run + exact results:
<commands and pass/fail/counts>

Warnings:
<exact warnings>

Problems/risks:
<none or exact issue>

Decisions needed:
<none expected; if material ambiguity appears, STOP and report>

Production source changed beyond frozen Step 6.4 scope:
NO expected

Step 6.5 started:
NO
```

Do not claim PM acceptance.
