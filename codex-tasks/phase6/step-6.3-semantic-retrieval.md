# Codex Task — Step 6.3 Semantic Retrieval

**Status: FROZEN / READY_FOR_PM_TASK_REVIEW**

> PM decision `6.3-D1 = B` is frozen. `RAG_RETRIEVAL_CANDIDATE_K` has default `20`, minimum `1`, and maximum `100`.
>
> This packet is JIT-pre-reviewed and frozen for PM task review. Do not run Codex until PM separately authorizes implementation.

## 1. Context / repository reconciliation

Accepted prerequisites:

- Step 6.1 Embedding Pipeline: DONE/CLOSED.
- Step 6.2 Vector Storage: DONE/CLOSED.
- Current Alembic head: `0012_vector_storage_readiness`.
- No Step 6.3 production module exists yet.
- No schema migration is required for Step 6.3.

Actual accepted Step 6.1 embedding boundary:

```text
app/ai/embeddings/provider.py

EmbeddingProvider
├── identity: EmbeddingProviderIdentity
├── embed_documents(texts, batch_size)
└── embed_query(text)

get_embedding_provider()
→ cached SentenceTransformerEmbeddingProvider
→ BAAI/bge-m3
```

Actual provider semantic identity fields:

```text
provider
provider_version
model_name
model_version
dimensions
embedding_input_version
normalize_embeddings
```

Actual V0 provider behavior:

- `embed_query(text)` is distinct at the application boundary.
- Current SentenceTransformer implementation delegates query embedding through its provider-owned encoding path.
- tokenizer length validation uses special tokens, `truncation=False`, and raises `EMBEDDING_INPUT_TOO_LONG` before encode.
- V0 output is dense, normalized, 1024 dimensions for BGE-M3.
- provider-specific future query instructions/prefixes belong inside `embed_query()`, not Retrieval.

Actual accepted Step 6.2 storage boundary:

```python
nearest_vectors(
    session,
    query_vector,
    embedding_profile_id,
    limit,
)
→ NearestVectorResult[]
```

Where:

```text
NearestVectorResult
├── chunk_id
└── distance
```

Storage invariants:

```text
EmbeddingProfile.status = ACTIVE
KnowledgeVersion.status = ACTIVE
requested profile = global ACTIVE profile
cosine distance
ORDER BY distance ASC, Chunk.id ASC
exact scan only
```

Actual persistence metadata available for candidate hydration:

```text
KnowledgeSource
├── id
├── source_type = DOCUMENT | LESSON
├── document_id nullable
└── lesson_id nullable

KnowledgeVersion
├── id
├── knowledge_source_id
└── status

Chunk
├── id
├── knowledge_version_id
├── content
├── content_type
├── chunk_index
├── page_number
├── section
├── lesson_id nullable
└── metadata JSONB nullable
```

Actual Step 6.1 joins also prove current repository can resolve:

```text
Document.title
Lesson.title
HSKLevel.level_number
KnowledgeSource.document_id / lesson_id
```

Accepted Conversation/product state:

```text
Conversation.lesson_id NOT NULL
V0 Conversation scope = LESSON only
```

This durable data is sufficient for Step 6.4 to implement strict lesson scope later; Step 6.3 must not implement that filter yet.

---

# 2. Problem

Step 6.2 can search a vector only when the caller already has a valid query vector and knows the active profile.

The application still needs a semantic-retrieval boundary that turns human query text into a ranked set of internal knowledge candidates without leaking embedding/vector-storage mechanics into Conversation or later LLM code.

Problem to solve:

```text
query text
→ deterministic normalization
→ active embedding-space resolution
→ query embedding
→ exact ACTIVE vector search
→ resolved Chunk/source metadata
→ semantic candidates
```

Step 6.3 must establish this baseline without prematurely implementing lesson filtering, reranking, thresholds, prompts, LLM generation, external fallback, memory, or citations.

---

# 3. Objective

Implement a concrete internal `SemanticRetrievalService` that:

1. accepts `query_text: str`;
2. preprocesses it deterministically;
3. resolves the single ACTIVE `EmbeddingProfile`;
4. verifies the configured `EmbeddingProvider.identity` exactly matches that profile;
5. calls `EmbeddingProvider.embed_query()`;
6. validates the query vector;
7. invokes the accepted Step 6.2 ACTIVE-gated vector primitive;
8. hydrates normalized Chunk/source provenance;
9. converts cosine distance to `retrieval_score = 1 - distance`;
10. returns deterministic `RetrievalCandidate[]`.

No public HTTP route is required.

---

# 4. Why this Step exists

Without Step 6.3, higher RAG layers would need to understand:

- model/tokenizer boundaries;
- active embedding profiles;
- query-vector validation;
- pgvector distance semantics;
- normalized relational joins;
- rank/score semantics.

That would couple Conversation, filtering, reranking, and generation directly to infrastructure.

Step 6.3 creates one stable semantic retrieval boundary for later Steps 6.4–6.10.

---

# 5. Prerequisites

Must preserve:

- Step 6.1 exact provider/model identity and `embed_query()` boundary.
- Step 6.2 exactly-one-active-profile retrieval model.
- Step 6.2 repository ACTIVE gates.
- cosine distance and exact scan.
- request-scoped `AsyncSession` convention.
- repository does not own `commit()`.
- existing `ApplicationError` conventions.

No dependency upgrade is expected.

---

# 6. Mental Model

```text
Query text
≠ query vector
≠ storage distance
≠ final RAG evidence
```

Step 6.3 owns only:

```text
text
→ query vector
→ nearest ACTIVE semantic candidates
```

The resulting candidates are **candidates**, not proven evidence.

No semantic threshold is applied here.

Product Lesson Chat policy is a later composition:

```text
Semantic Retrieval (6.3)
→ Retrieval Scope / Filtering (6.4)
→ Reranking (6.5)
→ Context (6.6)
→ ...
```

---

# 7. Exact Data Flow

```text
query_text
↓
QueryPreprocessor
  trim
  → Unicode NFC
  → collapse repeated whitespace to one ASCII space
↓
normalized_query
↓
short DB read transaction
  VectorStorageService.resolve_active_profile()
  → copy semantic profile identity into immutable runtime snapshot
end DB transaction
↓
get_embedding_provider()
↓
exact provider.identity == ACTIVE profile semantic identity ?
  no → QUERY_EMBEDDING_FAILED
  yes
↓
EmbeddingProvider.embed_query(normalized_query)
  EMBEDDING_INPUT_TOO_LONG
  → RETRIEVAL_QUERY_TOO_LONG
  other provider technical failure
  → QUERY_EMBEDDING_FAILED
↓
validate query vector
  exact dimensions
  finite values
  if normalize_embeddings=true: L2 norm ≈ 1 within 1e-3
↓
Step 6.2 VectorStorageService.nearest_vectors(
    query_vector,
    active_profile_id,
    candidate_k,
)
↓
Step 6.2 re-resolves current ACTIVE profile
  profile switched during embedding?
  → request fails safely; never search a vector in the wrong space
↓
NearestVectorResult[]
  chunk_id + cosine distance
↓
RetrievalRepository.load_candidate_metadata(chunk_ids)
↓
merge metadata back in original vector-result order
↓
for each row:
  validate finite distance
  retrieval_score = 1 - distance
  rank = position + 1
↓
RetrievalCandidate[]
```

If vector result is `[]`, return `[]` without candidate padding.

If any returned `chunk_id` cannot be hydrated, fail as technical retrieval integrity error; do not silently drop it and renumber results.

---

# 8. Step 6.2 → Step 6.3 interface

Do not modify Step 6.2 behavior for Step 6.3.

Reuse:

```text
VectorStorageService.resolve_active_profile()
VectorStorageService.nearest_vectors(...)
```

`nearest_vectors()` remains responsible for:

```text
ACTIVE profile gate
ACTIVE KnowledgeVersion gate
active-profile coherence
query dimension check
pgvector technical normalization
exact cosine ordering
```

Step 6.3 must not duplicate activation lifecycle logic.

Step 6.3 converts the storage result:

```text
chunk_id + distance
```

into the richer semantic DTO through normalized relational hydration.

---

# 9. Query embedding boundary

## 9.1 Provider selection

Normal retrieval accepts no profile/model/provider override.

Flow:

```text
single ACTIVE EmbeddingProfile
→ get configured provider
→ exact identity comparison
→ embed_query()
```

Compare **all** semantic identity fields:

```text
provider
provider_version
model_name
model_version
dimensions
embedding_input_version
normalize_embeddings
```

`status` is not semantic identity.

If the active profile does not exactly match the configured provider identity, fail safely with `QUERY_EMBEDDING_FAILED` and a non-sensitive configuration-integrity message.

Do not dynamically invent/load a second model/provider in Step 6.3.

## 9.2 Query formatting

There is no `EmbeddingInputFormatter` call for queries.

Do not format a query as a document Chunk.

Step 6.3 passes only the normalized semantic query to:

```text
EmbeddingProvider.embed_query()
```

Any BGE/provider-specific query instruction remains provider-owned.

## 9.3 Length handling

Do not pre-count with `Chunk.token_count`.

Use the provider/model tokenizer contract already owned by Step 6.1.

Map:

```text
EMBEDDING_INPUT_TOO_LONG
→ RETRIEVAL_QUERY_TOO_LONG
```

No silent truncation.

## 9.4 Query vector validation

Require:

```text
vector exists
len(vector) == active_profile.dimensions
all values finite
no NaN/Inf
if profile.normalize_embeddings == true:
    abs(L2_norm(vector) - 1.0) <= 1e-3
```

Failure:

```text
INVALID_QUERY_EMBEDDING
```

Do not persist query vectors.

---

# 10. Lesson-scope boundary

## Product requirement

V0 learner chat is Lesson-scoped and `Conversation.lesson_id` is backend-owned.

## Actual durable knowledge relation

The accepted schema can later derive strict lesson eligibility through:

```text
KnowledgeSource.source_type = LESSON
AND
KnowledgeSource.lesson_id = Conversation.lesson_id
```

`Chunk.lesson_id` is also present as durable chunk metadata.

Therefore **no schema change is required** for lesson-scoped RAG.

## Step ownership

Step 6.3 MUST NOT apply Lesson/HSK metadata scope.

Its baseline corpus is:

```text
all ACTIVE internal knowledge
```

Step 6.4 owns:

```text
RetrievalScope.CURRENT_LESSON
RetrievalFilter
SQL filtering before vector ORDER BY/LIMIT
trusted Conversation.lesson_id scope derivation
```

This distinction is intentional:

```text
ACTIVE gates
= mandatory storage safety, Step 6.2/6.3 always enforced

lesson/HSK/content/source metadata constraints
= retrieval eligibility policy, Step 6.4
```

Do not accept `lesson_id` in the Step 6.3 `retrieve()` interface.

Invalid/missing Lesson scope is therefore **not a Step 6.3 error path**. It belongs to backend business validation / Step 6.4 scope construction / Step 6.8 orchestration.

---

# 11. Retrieval candidate policy

Frozen baseline (`6.3-D1 = B`):

```text
setting = RAG_RETRIEVAL_CANDIDATE_K
default = 20
minimum = 1
maximum = 100
```

Equivalent config contract:

```python
rag_retrieval_candidate_k: int = Field(
    default=20,
    ge=1,
    le=100,
)
```

The setting is backend-owned.

Normal frontend/user input cannot override it.

Internal tests/evaluation may inject/construct a service with a controlled override only if that follows existing test conventions and remains within `1..100`.

Behavior:

```text
available < candidate_k
→ return all available

available == 0
→ []
```

No padding.

No quality threshold.

No source/HSK/content boost.

`100` is an operational/configuration safety bound only. It is not a semantic relevance threshold, `RAG_MIN_RERANK_SCORE`, retrieval-quality cutoff, or reranker threshold.

---

# 12. Distance / score semantics

Step 6.2 returns:

```text
cosine distance
smaller = better
```

Step 6.3 additionally exposes:

```text
retrieval_score = 1.0 - distance
```

Meaning:

```text
retrieval_score = cosine similarity
higher = better
```

Do not clamp to `[0, 1]`.

For normalized dense embeddings, values may legitimately be negative.

Preserve both:

```text
distance
retrieval_score
```

for diagnostics/evaluation.

Ranking remains based on Step 6.2 deterministic order:

```text
distance ASC
Chunk.id ASC tie break
```

Assign `rank = 1..N` in that exact returned order.

Do not re-sort using rounded scores.

---

# 13. Result schemas

Create immutable internal DTOs equivalent to:

```text
ActiveEmbeddingProfileSnapshot
├── id: UUID
├── provider: str
├── provider_version: str
├── model_name: str
├── model_version: str
├── dimensions: int
├── embedding_input_version: str
└── normalize_embeddings: bool
```

```text
CandidateMetadata
├── chunk_id: UUID
├── chunk_index: int
├── content: str
├── content_type: str
├── knowledge_version_id: UUID
├── knowledge_source_id: UUID
├── source_type: str
├── source_document_id: UUID | None
├── source_lesson_id: UUID | None
├── chunk_lesson_id: UUID | None
├── document_title: str | None
├── lesson_title: str | None
├── hsk_level_number: int | None
├── page_number: int | None
├── section: str | None
└── locator_metadata: dict | None
```

```text
RetrievalCandidate
├── rank: int
├── chunk_id: UUID
├── chunk_index: int
├── content: str
├── content_type: str
├── knowledge_version_id: UUID
├── knowledge_source_id: UUID
├── source_type: str
├── source_document_id: UUID | None
├── source_lesson_id: UUID | None
├── chunk_lesson_id: UUID | None
├── document_title: str | None
├── lesson_title: str | None
├── hsk_level_number: int | None
├── page_number: int | None
├── section: str | None
├── locator_metadata: dict | None
├── distance: float
└── retrieval_score: float
```

No raw vector in any normal result DTO.

Do not persist this DTO directly.

Later `MessageRetrieval` persistence can consume:

```text
chunk_id
rank
retrieval_score
```

and Step 6.5 may add `rerank_score` separately without destroying semantic rank/score.

---

# 14. Repository / service responsibilities

## RetrievalRepository

Own only relational candidate hydration SQL.

Required helper equivalent to:

```python
load_candidate_metadata(
    session: AsyncSession,
    chunk_ids: Sequence[UUID],
) -> list[CandidateMetadata]
```

Query joins normalized entities:

```text
Chunk
→ KnowledgeVersion
→ KnowledgeSource
→ optional Document
→ optional Lesson
→ optional HSKLevel
```

It does not:

- compute embeddings;
- calculate vector distance;
- decide ACTIVE lifecycle;
- filter by lesson/HSK policy;
- rerank;
- commit/rollback.

## SemanticRetrievalService

Own:

- query preprocessing;
- short active-profile read boundary;
- provider/profile identity coherence;
- query embedding orchestration;
- query vector validation;
- candidate-count configuration;
- call to Step 6.2 nearest-vector primitive;
- candidate hydration + integrity validation;
- score conversion;
- rank assignment;
- error normalization;
- structured timing/logging.

## QueryPreprocessor

Own only deterministic text normalization.

No model/DB calls.

## Do not create

- generic `Retriever` hierarchy;
- vector-store abstraction;
- LangChain/LlamaIndex wrapper;
- public retrieval router.

---

# 15. Error / failure behavior

Use existing `ApplicationError` conventions and safe public messages.

Freeze Step 6.3 error equivalents:

```text
EMPTY_RETRIEVAL_QUERY              → 422
RETRIEVAL_QUERY_TOO_LONG           → 422
ACTIVE_EMBEDDING_PROFILE_NOT_FOUND → reuse Step 6.2 semantics/status
MULTIPLE_ACTIVE_EMBEDDING_PROFILES → reuse Step 6.2 semantics/status
QUERY_EMBEDDING_FAILED             → 500
INVALID_QUERY_EMBEDDING            → 500
VECTOR_RETRIEVAL_FAILED            → 500
SEMANTIC_RETRIEVAL_FAILED          → 500
```

Normalization rules:

```text
empty normalized query
→ EMPTY_RETRIEVAL_QUERY
→ no provider call

provider EMBEDDING_INPUT_TOO_LONG
→ RETRIEVAL_QUERY_TOO_LONG

provider/profile identity mismatch
→ QUERY_EMBEDDING_FAILED

other provider/model failure
→ QUERY_EMBEDDING_FAILED

query dimension / NaN / Inf / invalid norm
→ INVALID_QUERY_EMBEDDING

Step 6.2 vector query technical failure
→ VECTOR_RETRIEVAL_FAILED

successful vector search returns zero rows
→ []

candidate hydration missing one or more vector-result Chunk IDs
→ SEMANTIC_RETRIEVAL_FAILED
```

Do not convert technical failures to `[]`.

Do not expose raw provider/SQL exception strings.

Do not log traceback/exception text that can contain raw query/vector/SQL parameters.

---

# 16. Transaction / session behavior

Step 6.3 is read-only and must not persist query vectors or retrieval traces.

Critical rule:

```text
NO database transaction remains open during embedding model inference.
```

Required shape:

```text
short DB read transaction
→ resolve active profile
→ copy required scalar profile fields
→ end transaction

model/tokenizer inference
→ no DB transaction

short DB read transaction(s)
→ nearest vector query
→ hydrate candidate metadata
→ end transaction
```

Repository methods never commit/rollback.

Service owns any explicit transaction boundaries required to guarantee no transaction spans model inference.

Do not call `session.rollback()` merely as a generic cleanup if that would interfere with a caller-owned transaction. The Step 6.3 service is expected to be invoked outside higher-level write transactions; tests must enforce/document this boundary.

No DB locks are required for normal retrieval.

Step 6.2 ACTIVE gates make concurrent activation/profile switches safe. In particular, Step 6.2 re-resolves the active profile before vector search, so a profile switch between embedding and search cannot search the query vector in a different embedding space.

---

# 17. Logging / observability

Structured fields equivalent to:

```text
embedding_profile_id
query_length_chars
candidate_k
returned_count
top_distance optional
top_retrieval_score optional
embedding_duration_ms
vector_query_duration_ms
metadata_hydration_duration_ms optional
total_retrieval_duration_ms
status
error_code optional
```

`query_token_count` may be logged only if the existing provider exposes it safely without reaching into private SentenceTransformer internals. Do **not** extend the accepted provider API solely to obtain a logging metric.

Do not log:

- full user query;
- query vector;
- Chunk content;
- raw SQL;
- raw model/driver exception text.

Measure latency, but introduce no SLA.

---

# 18. Expected files

Create only what is required, equivalent to:

```text
backend/app/ai/retrieval/
├── __init__.py
├── errors.py
├── query_preprocessor.py
├── repository.py
├── schemas.py
└── service.py
```

Modify:

```text
backend/app/core/config.py
backend/.env.example                 # only if current repository convention lists runtime settings there
```

Tests, equivalent to:

```text
backend/tests/test_step63_query_preprocessor.py
backend/tests/test_step63_retrieval_repository.py
backend/tests/test_step63_retrieval_service.py
backend/tests/test_step63_semantic_retrieval_smoke.py
```

Documentation:

```text
docs/ai/step-6.3-semantic-retrieval.md
```

Do not add a migration.

Do not add a router/API endpoint.

Do not modify accepted Step 6.1/6.2 production behavior unless a test proves a genuine defect and PM approves any material contract change.

---

# 19. Testing matrix

## A. Query preprocessing

- trim leading/trailing whitespace;
- Unicode NFC deterministic;
- repeated whitespace (`space/tab/newline`) collapses to one ASCII space;
- already-normal text stable;
- whitespace-only input → `EMPTY_RETRIEVAL_QUERY`;
- no translation, rewrite, keyword extraction, or LLM call.

## B. Active profile resolution

- one ACTIVE profile resolves;
- zero ACTIVE → `ACTIVE_EMBEDDING_PROFILE_NOT_FOUND`;
- multiple ACTIVE resolver path → `MULTIPLE_ACTIVE_EMBEDDING_PROFILES` even though DB normally prevents it;
- caller cannot supply/override profile ID through normal `retrieve(query_text)` interface.

## C. Provider/profile coherence

Parametrize mismatches for:

- provider;
- provider_version;
- model_name;
- model_version;
- dimensions;
- embedding_input_version;
- normalize_embeddings.

Each exact mismatch:

```text
→ QUERY_EMBEDDING_FAILED
→ no vector search
```

Exact identity match proceeds.

## D. Query embedding

- `embed_query()` called exactly once;
- `embed_documents()` never used by Retrieval;
- provider receives normalized query only;
- provider-specific query behavior is not reimplemented in Retrieval;
- provider `EMBEDDING_INPUT_TOO_LONG` → `RETRIEVAL_QUERY_TOO_LONG`;
- other provider failure → `QUERY_EMBEDDING_FAILED`;
- raw provider exception detail not leaked.

## E. Query vector validation

- exact dimension accepted;
- wrong dimension → `INVALID_QUERY_EMBEDDING`;
- NaN rejected;
- +Inf/-Inf rejected;
- normalized profile + unit vector accepted;
- normalized profile + norm outside `1e-3` rejected;
- invalid vector never reaches vector search.

## F. No transaction during inference

Instrument session/provider boundary and prove:

```text
provider.embed_query()
→ session has no active DB transaction
```

No write/commit happens during inference.

## G. Candidate count

Freeze explicit configuration tests for `6.3-D1 = B`:

- default `20` accepted;
- `1` accepted;
- `100` accepted;
- `0` rejected;
- negative rejected;
- `101` rejected;
- backend configuration override within `1..100` accepted;
- normal frontend retrieval cannot set or override `candidate_k`;
- fewer rows returned normally;
- zero rows → `[]`;
- no fake padding.

## H. Step 6.2 ACTIVE search safety

Integration test with real PostgreSQL/pgvector:

- ACTIVE KnowledgeVersion + ACTIVE profile included;
- PROCESSING excluded;
- FAILED excluded;
- SUPERSEDED excluded;
- INACTIVE profile excluded;
- Step 6.3 does not bypass repository safety gates.

## I. Profile switch race safety

Arrange:

```text
resolve P1 ACTIVE
→ embed query under P1
→ switch global active profile to P2 before vector search
```

Expected:

```text
search refuses profile mismatch / technical retrieval failure
no P1 query vector is searched under P2
```

No automatic retry required.

## J. Score / rank

- distance `0.0` → score `1.0`;
- distance `0.2` → score `0.8`;
- distance `1.3` → score `-0.3` (no clamp);
- result order exactly follows Step 6.2 distance/Chunk-ID order;
- rank = 1..N;
- no score threshold;
- no source/HSK/content boost.

Use approximate floating comparison where required.

## K. Candidate hydration

- every vector result resolves content/provenance fields;
- DB join uses normalized relations, not Embedding denormalization;
- preserves vector result order even if hydration SQL returns another order;
- `chunk_index` retained;
- document provenance fields populated for DOCUMENT candidate;
- lesson title/HSK/lesson IDs populated for LESSON candidate;
- raw vector absent from DTO;
- missing one returned Chunk during hydration → `SEMANTIC_RETRIEVAL_FAILED`, not silent drop.

## L. Lesson-scope boundary

- Step 6.3 with no filter may return candidates from multiple active sources/lessons;
- `retrieve()` does not accept lesson scope;
- no `WHERE lesson_id=...` added by Step 6.3;
- query text is not prefixed with Lesson/HSK metadata;
- schema evidence required by future Step 6.4 is present (`KnowledgeSource.lesson_id`, `Chunk.lesson_id`).

## M. Failure distinction

- successful no-row search → `[]`;
- query embedding failure ≠ `[]`;
- vector DB failure → `VECTOR_RETRIEVAL_FAILED`;
- hydration DB failure → `SEMANTIC_RETRIEVAL_FAILED`;
- infrastructure errors never silently become no-evidence semantics.

## N. Persistence boundary

- query vector not persisted;
- no `MessageRetrieval` inserted;
- no `message_id` required;
- result includes `chunk_id`, `rank`, `retrieval_score` for later persistence.

## O. Logging safety

- no full query text;
- no query vector;
- no Chunk content;
- injected provider/SQL sentinel detail absent from logs;
- success logs candidate count + timings;
- error logs normalized error code only.

## P. Semantic smoke test

Use a small known corpus with stable/fake query provider or real model only when locally available without network dependence.

Example corpus includes semantically distinct Chinese-learning chunks.

For query equivalent to:

```text
cách dùng 了
```

assert the expected `了` Chunk appears in top K.

Do not assert an arbitrary score threshold.

The test must remain deterministic in CI. A real-model smoke may be additional/optional if model artifacts are available locally; do not make CI depend on network/model download.

---

# 20. Verification commands

After PM authorizes Codex implementation, run from `backend/` using repository-standard `uv` workflow:

```bash
uv lock --check

uv run alembic upgrade head
uv run alembic current
uv run alembic check

uv run pytest \
  tests/test_step63_query_preprocessor.py \
  tests/test_step63_retrieval_repository.py \
  tests/test_step63_retrieval_service.py \
  tests/test_step63_semantic_retrieval_smoke.py

uv run pytest \
  tests/test_step62_vector_storage_migration.py \
  tests/test_step62_vector_repository.py \
  tests/test_step62_vector_readiness.py \
  tests/test_step62_activation.py

uv run pytest \
  tests/test_step61_embedding_profile_migration.py \
  tests/test_step61_embedding_formatter.py \
  tests/test_step61_embedding_provider.py \
  tests/test_step61_embedding_service.py

uv run pytest \
  tests/test_step55_chunking.py \
  tests/test_step55_chunking_service.py \
  tests/test_step56_document_pipeline.py \
  tests/test_step56_lesson_pipeline.py \
  tests/test_step56_orchestration_concurrency.py \
  tests/test_step57_reprocessing_planner.py \
  tests/test_step57_reprocessing_execution.py \
  tests/test_step57_reprocessing_concurrency.py

uv run pytest
uv run python -m compileall app
```

If the environment intentionally uses an already-synchronized lockfile environment and package-host connectivity is unavailable, follow the accepted repository verification convention; do not report `uv sync` as PASS unless actually run.

No migration beyond `0012_vector_storage_readiness` is expected.

---

# 21. Scope / non-goals

Do not implement:

- Step 6.4 `RetrievalFilter`;
- Step 6.4 `RetrievalScope`;
- Lesson/HSK/content/source metadata filtering;
- CURRENT_LESSON filtering;
- automatic lesson → internal-KB fallback;
- RAG semantic/evidence threshold;
- `RAG_MIN_RERANK_SCORE`;
- Step 6.5 reranker;
- rerank top-K;
- prompt/context packing;
- LLM calls;
- external retrieval;
- conversation memory;
- citation generation/validation;
- grading;
- assessment generation;
- BM25/hybrid search;
- query expansion/LLM rewrite;
- query cache/semantic cache/Redis;
- HNSW/IVFFlat/ANN;
- external vector DB;
- worker/queue;
- public retrieval HTTP endpoint;
- schema migration;
- generic Retriever framework.

---

# 22. Step Note

Create:

```text
docs/ai/step-6.3-semantic-retrieval.md
```

Required sections:

## Objective

Turn query text into deterministic ranked semantic candidates from ACTIVE internal knowledge.

## Why

Separate semantic retrieval from Conversation, filtering, reranking, and generation.

## Mental Model

```text
query
→ query embedding
→ vector distance
→ semantic candidate
```

Candidate is not final evidence.

## Core Knowledge

MUST KNOW:

- query vs document embedding boundary;
- embedding-space/profile coherence;
- cosine distance vs cosine similarity;
- exact Top-K semantic retrieval;
- ACTIVE safety gates;
- technical failure vs valid empty result;
- transaction boundary around model inference.

SHOULD KNOW:

- Unicode normalization;
- metadata hydration via normalized joins;
- semantic rank vs future rerank score.

AWARENESS ONLY:

- ANN indexes;
- hybrid/BM25 retrieval;
- future retrieval thresholds.

## Data Flow

Document the exact flow from section 7.

## Key Design Decisions

- all ACTIVE internal corpus baseline;
- lesson filtering deferred to 6.4;
- `candidate_k=20` default with frozen range `1..100`;
- `retrieval_score=1-distance`;
- no threshold;
- no query-vector persistence;
- provider/profile exact identity match;
- no DB transaction during query embedding.

## Reusable approach

Explain how to separate:

```text
storage search primitive
from semantic retrieval orchestration
from business filtering policy
```

## Common Mistakes

- calling `embed_documents()` for a query;
- searching under a mismatched profile;
- calling distance a relevance score without mapping;
- clamping cosine similarity;
- filtering global Top-K in Python;
- adding lesson scope prematurely in 6.3;
- returning [] for infrastructure failure;
- holding a DB transaction during inference;
- logging raw queries/vectors.

## Definition of Done

Mirror the Acceptance Criteria below and actual implementation.

---

# 23. Concepts Discovered

Record only concepts actually implemented after acceptance.

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Semantic Retrieval | AI | 6.3 | Converts query embeddings into nearest internal knowledge candidates. |
| Query Embedding | AI | 6.3 | Represents learner query in the same vector space as indexed documents/chunks. |
| Embedding-space Coherence | AI | 6.3 | Prevents searching a vector with a different model/profile than stored vectors. |
| Cosine Similarity | AI | 6.3 | User-facing semantic score mapping `1 - cosine_distance`. |
| Candidate Top-K | AI | 6.3 | Bounds baseline semantic candidates before later filtering/reranking stages. |
| Deterministic Query Preprocessing | BOTH | 6.3 | Stabilizes query input without changing semantic intent. |
| Candidate Hydration | DE | 6.3 | Resolves normalized Chunk/source provenance without denormalizing Embedding. |
| Read transaction / inference separation | SYSTEM | 6.3 | Avoids holding DB transactions during model inference. |
| Technical-empty distinction | BOTH | 6.3 | Prevents infrastructure failure from masquerading as no evidence. |

Do not add `RetrievalFilter`, `RetrievalScope`, reranking, prompting, or LLM concepts in Step 6.3.

---

# 24. Tools Used

Record only tools actually used after implementation.

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| Python | SYSTEM | 6.3 | Retrieval orchestration and validation. |
| SQLAlchemy async | DE | 6.3 | Candidate metadata hydration/read boundaries. |
| PostgreSQL | DE | 6.3 | Normalized knowledge/provenance reads. |
| pgvector | BOTH | 6.3 | Exact cosine nearest-neighbor storage primitive from Step 6.2. |
| sentence-transformers | AI | 6.3 | Existing Step 6.1 query-embedding provider runtime. |
| pytest | SYSTEM | 6.3 | Focused and regression tests. |

No new framework/tool dependency is expected.

---

# 25. Acceptance Criteria

Architecture / boundaries:

- [ ] `SemanticRetrievalService` exists as a concrete service.
- [ ] No public retrieval router is added.
- [ ] No generic Retriever hierarchy is added.
- [ ] Step 6.1 provider behavior is not redesigned.
- [ ] Step 6.2 ACTIVE search behavior is not redesigned.
- [ ] No schema migration is added.

Query preprocessing:

- [ ] deterministic trim + NFC + repeated-whitespace normalization.
- [ ] empty normalized query fails explicitly.
- [ ] no translation/rewrite/query expansion.

Embedding/profile:

- [ ] exactly one ACTIVE profile resolved internally.
- [ ] no frontend profile override.
- [ ] provider semantic identity exactly matches ACTIVE profile.
- [ ] `embed_query()` used; `embed_documents()` not used by Retrieval.
- [ ] oversized query fails without truncation.
- [ ] query vector dimension/finite/norm validated.
- [ ] no DB transaction spans query embedding inference.

Candidate policy:

- [ ] default `candidate_k=20`.
- [ ] `RAG_RETRIEVAL_CANDIDATE_K` is frozen as `1..100` with default `20`.
- [ ] config validation accepts `1`, `20`, and `100`; rejects `0`, negative values, and `101`.
- [ ] backend configuration override within `1..100` is accepted.
- [ ] frontend cannot supply arbitrary candidate_k.
- [ ] fewer available candidates returned normally.
- [ ] no fake padding.
- [ ] valid empty search returns `[]`.
- [ ] no similarity/evidence threshold.

Search safety:

- [ ] Step 6.2 repository ACTIVE profile/version gates remain authoritative.
- [ ] PROCESSING/FAILED/SUPERSEDED excluded.
- [ ] INACTIVE profile excluded.
- [ ] profile switch between embedding/search cannot produce cross-space query.

Score/rank:

- [ ] preserve raw cosine distance.
- [ ] `retrieval_score = 1 - distance`.
- [ ] no clamp to 0..1.
- [ ] deterministic order/rank retained from Step 6.2 search order.
- [ ] no source/lesson/HSK/content boost.

Result contract:

- [ ] RetrievalCandidate contains content + provenance + distance + score.
- [ ] `chunk_index` retained.
- [ ] Document/Lesson source identities are recoverable.
- [ ] raw vector excluded.
- [ ] hydration preserves search order.
- [ ] missing hydration row fails technically rather than silently dropping candidate.

Lesson/filter boundary:

- [ ] baseline can search all ACTIVE internal knowledge.
- [ ] no Lesson/HSK metadata filtering in Step 6.3.
- [ ] no lesson metadata prepended to query text.
- [ ] current schema is documented as sufficient for Step 6.4 strict lesson scope.

Failure behavior:

- [ ] query embedding failure distinct from empty result.
- [ ] vector DB failure distinct from empty result.
- [ ] hydration failure distinct from empty result.
- [ ] technical errors are normalized and do not expose raw internals.

Persistence/logging:

- [ ] query vector not persisted.
- [ ] no MessageRetrieval written.
- [ ] no message_id required.
- [ ] raw query/vector/content not logged.
- [ ] latency measured without SLA.

Scope:

- [ ] no Step 6.4 filter/scope implementation.
- [ ] no reranking.
- [ ] no RAG_MIN_RERANK_SCORE.
- [ ] no prompt/LLM/external/memory/citation behavior.
- [ ] no ANN/cache/external vector DB.

Verification:

- [ ] focused Step 6.3 tests pass.
- [ ] Step 6.2 regressions pass.
- [ ] Step 6.1 regressions pass.
- [ ] Phase 5.5–5.7 regressions pass.
- [ ] full backend passes.
- [ ] Alembic head remains `0012_vector_storage_readiness`.
- [ ] Alembic check reports no new operations.
- [ ] `compileall app` passes.
- [ ] Step Note reflects actual implementation.

---

# 26. Codex completion-report format

When Codex is eventually authorized, return exactly this information:

```text
Step:
6.3 — Semantic Retrieval

Status:
READY_FOR_SPECIALIST_REVIEW | BLOCKED

Files changed:

Production code changed:
YES/NO

Migration changed:
NO expected

Schema changed:
NO expected

Dependencies changed:
NO expected

RAG_RETRIEVAL_CANDIDATE_K:
default = 20
max = 100

Query preprocessing:

Active profile resolution:

Provider/profile identity behavior:

embed_query behavior:

Query-vector validation:

Step-6.2 nearest_vectors integration:

RetrievalCandidate shape:

Distance / retrieval_score behavior:

Candidate hydration:

Lesson-scope boundary:

Transaction/session behavior:

Failure behavior:

Logging:

Tests added/changed:

Verification commands actually run + exact results:
- uv lock --check:
- Alembic upgrade/current/check:
- Step 6.3 focused:
- Step 6.2 regression:
- Step 6.1 regression:
- Phase 5.5–5.7 regression:
- full backend:
- compileall app:

Warnings:

Problems / risks:

Decisions needed:

Step 6.4 started:
NO
```

Never claim commands passed unless actually run.

---

# 27. Frozen Decision — 6.3-D1

PM decision:

```text
6.3-D1 = B
RAG_RETRIEVAL_CANDIDATE_K
default = 20
minimum = 1
maximum = 100
```

Equivalent config contract:

```python
rag_retrieval_candidate_k: int = Field(
    default=20,
    ge=1,
    le=100,
)
```

This is an operational/configuration safety bound only. It is not a semantic relevance threshold, `RAG_MIN_RERANK_SCORE`, retrieval-quality cutoff, or reranker threshold.

Normal frontend requests cannot override `candidate_k`.
