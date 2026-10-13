# Step 6.3 — Semantic Retrieval

## Goal

Implement the baseline internal semantic retrieval service for Phase 6.

The service converts a user query into a query embedding using the single ACTIVE `EmbeddingProfile`, searches ACTIVE knowledge vectors through the Step 6.2 pgvector repository primitive, and returns ranked `RetrievalCandidate` objects for downstream filtering, reranking, context construction, and citation.

Core flow:

```text
User Question
↓
QueryPreprocessor
↓
resolve ACTIVE EmbeddingProfile
↓
EmbeddingProvider.embed_query(...)
↓
exact pgvector search
↓
RetrievalCandidate[]
```

Do not implement metadata filtering, reranking, external retrieval, prompt construction, LLM generation, conversation memory, or citation rendering in this step.

---

# Core Boundary

Input:

```text
query_text: str
```

Output:

```text
RetrievalCandidate[]
```

Baseline retrieval scope:

```text
all ACTIVE internal knowledge
```

Step 6.4 will add metadata/context filtering.

---

# SemanticRetrievalService

Create an application/service boundary equivalent to:

```text
SemanticRetrievalService
```

Responsibilities:

- preprocess query text;
- resolve the exactly-one ACTIVE EmbeddingProfile;
- obtain the matching EmbeddingProvider;
- validate query length;
- generate query embedding;
- validate query vector;
- request nearest ACTIVE vectors from the repository;
- convert storage distance to retrieval score;
- create deterministic ranks;
- return retrieval candidates;
- distinguish empty results from technical failures;
- emit structured logs.

Do not put query embedding + vector SQL orchestration directly inside:

```text
Router
ConversationService
LLM Service
```

---

# Query Input

V0 retrieval input is:

```text
query_text: str
```

Do not accept from frontend/user:

```text
raw query vector
embedding_profile_id
distance metric
storage-specific options
```

Embedding space and retrieval internals remain backend-owned.

---

# QueryPreprocessor

Create a small deterministic component equivalent to:

```text
QueryPreprocessor
```

V0 preprocessing:

```text
trim leading/trailing whitespace
Unicode NFC normalization
light whitespace normalization
```

Do not:

```text
translate
spell-correct with LLM
summarize
query-expand
extract keywords
paraphrase
rewrite semantic intent
```

in Step 6.3.

The purpose is to establish a clean semantic-retrieval baseline.

---

# Empty Query

After preprocessing:

```text
query == ""
```

must fail explicitly with an error equivalent to:

```text
EMPTY_RETRIEVAL_QUERY
```

Do not embed an empty string.

---

# Query Length Validation

Validate the actual query input using the target embedding model/tokenizer.

If the query exceeds the model-supported limit:

```text
RETRIEVAL_QUERY_TOO_LONG
```

Do not silently truncate.

Although user queries are normally short, the guard must still exist.

---

# Active EmbeddingProfile Resolution

Production retrieval must always use:

```text
the single ACTIVE EmbeddingProfile
```

Flow:

```text
resolve ACTIVE profile
↓
resolve matching provider/model
↓
embed_query(...)
```

If there is no ACTIVE profile:

```text
ACTIVE_EMBEDDING_PROFILE_NOT_FOUND
```

If there are multiple ACTIVE profiles:

```text
MULTIPLE_ACTIVE_EMBEDDING_PROFILES
```

Treat both as configuration/system integrity errors.

Do not accept a profile override from normal frontend requests.

---

# Query Embedding Contract

Query vectors must use the same EmbeddingProfile configuration as document vectors.

If the profile specifies:

```text
normalize_embeddings = true
```

then both sides must be normalized:

```text
document vectors
query vectors
```

Do not let query and document encoding drift.

---

# Query-specific Model Instructions

If the embedding model/provider requires:

```text
query prefix
instruction
prompt name
model-specific query formatting
```

that behavior belongs inside:

```text
EmbeddingProvider.embed_query(...)
```

not inside `SemanticRetrievalService`.

The retrieval service must stay provider-agnostic.

---

# No Metadata Prefix in Query at Step 6.3

Do not prepend:

```text
HSK level
lesson id/title
content type
source category
```

to the user query string in Step 6.3.

Example:

```text
"Tại sao 了 dùng ở cuối câu?"
```

is embedded as the semantic query.

Lesson/HSK/content restrictions are handled by Step 6.4 filtering, not by silently modifying query semantics here.

---

# Candidate Count

V0 baseline:

```text
candidate_k = 20
```

Configuration:

```text
RAG_RETRIEVAL_CANDIDATE_K=20
```

Do not hard-code `20` across service code.

Internal test/evaluation code may override this where appropriate.

Frontend should not freely control unbounded candidate counts.

---

# Fewer Available Candidates

If:

```text
available candidates < candidate_k
```

return all available candidates.

Example:

```text
candidate_k = 20
available = 12
→ return 12
```

This is not an error.

---

# No Similarity Threshold Yet

Do not discard candidates with an arbitrary score/distance threshold in Step 6.3.

Avoid rules such as:

```text
similarity < 0.6
→ drop
```

until retrieval evaluation provides evidence.

Step 6.3 returns the nearest semantic candidates.

Quality thresholds/fallback policy belong to later RAG/evaluation work.

---

# Empty Retrieval Result

Valid retrieval may return:

```text
[]
```

when the search executes successfully but no eligible ACTIVE internal knowledge exists.

Do not fabricate/pad results.

Distinguish:

```text
successful search with zero candidates
```

from:

```text
retrieval infrastructure failure
```

---

# Retrieval Score

Step 6.2 returns cosine distance:

```text
smaller = better
```

Step 6.3 defines:

```text
retrieval_score = 1 - cosine_distance
```

which is cosine similarity.

Semantics:

```text
higher = better
```

For normalized vectors, the normal mathematical range is approximately:

```text
[-1, 1]
```

Do not clamp the score to 0..1.

---

# Ranking

Baseline semantic ranking:

```text
cosine_distance ASC
```

equivalent to:

```text
retrieval_score DESC
```

Assign:

```text
rank = 1..N
```

after semantic retrieval.

Do not introduce:

```text
source priority boost
HSK boost
recency boost
content_type boost
business priority reranking
```

in Step 6.3.

Those belong to later filtering/reranking/policy.

---

# RetrievalCandidate

Return a logical DTO equivalent to:

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
├── section / source locator metadata
├── distance
└── retrieval_score
```

Include enough resolved source metadata for downstream:

```text
Step 6.4 filtering
Step 6.5 reranking
Step 6.6 context construction
Step 6.10 citation
```

Do not return only `chunk_id`.

---

# No Vector in Candidate by Default

Do not expose the 1024-dimensional stored/query vector in normal `RetrievalCandidate`.

Downstream RAG stages generally need:

```text
content
metadata
score
provenance
```

not the raw embedding vector.

Keep vector values internal unless a future algorithm explicitly needs them.

---

# Keep chunk_index

Include `chunk_index` in the internal result contract.

It may later help with:

```text
source-order reconstruction
neighbor expansion
debugging
citation trace
context ordering
```

Ranking itself still follows semantic similarity.

---

# Database Normalization vs DTO Resolution

Do not duplicate Chunk/source metadata into the `Embedding` database row.

The retrieval repository/service may JOIN normalized entities and construct a richer DTO.

Database remains:

```text
Embedding
→ Chunk
→ KnowledgeVersion
→ KnowledgeSource
```

while runtime result may expose resolved metadata.

---

# Retrieval Scope

Step 6.3 baseline searches:

```text
all ACTIVE internal knowledge
```

Do not hard-code Lesson Chat scope here.

Step 6.4 will add context-aware metadata filtering such as:

```text
lesson
HSK
content_type
source category
```

The semantic retrieval engine itself remains reusable.

---

# Lesson Chat Boundary

Product policy ultimately prioritizes:

```text
Current Lesson Context
> Internal approved KB
> External Retrieval
```

Step 6.3 does not implement that complete policy.

It provides the general internal semantic retrieval layer.

Lesson-aware narrowing begins in Step 6.4 and the full policy is assembled later in the end-to-end RAG pipeline.

---

# No External Retrieval

Do not call web/external knowledge sources inside `SemanticRetrievalService`.

Step 6.3 is:

```text
internal semantic retrieval only
```

External retrieval is a later fallback controlled by RAG/application policy when internal knowledge is insufficient.

---

# Query Embedding Failure

If query embedding generation fails:

```text
QUERY_EMBEDDING_FAILED
```

or an equivalent normalized error.

Do not return:

```text
[]
```

for a technical model/provider failure.

---

# Vector Retrieval Failure

If pgvector/database search fails:

```text
VECTOR_RETRIEVAL_FAILED
```

Do not convert technical storage failure into a normal empty result.

---

# No Query Embedding Cache in V0

Do not add:

```text
Redis
query embedding cache
semantic cache
```

for Step 6.3.

V0 query volume does not justify this complexity.

---

# Do Not Persist Query Vector

Query vector is runtime intermediate data:

```text
query
→ query vector
→ search
→ discard vector
```

Do not persist every query embedding to PostgreSQL.

Persist retrieval traces later through the existing `MessageRetrieval` model where appropriate.

---

# MessageRetrieval Boundary

The existing data model supports:

```text
message_retrievals
├── message_id
├── chunk_id
├── rank
├── retrieval_score
└── rerank_score nullable
```

`SemanticRetrievalService` should remain independent from Conversation/message persistence.

It returns enough information to persist:

```text
chunk_id
rank
retrieval_score
```

A higher-level RAG/application orchestration layer with `message_id` will persist the trace.

Do not make low-level retrieval depend on Conversation.

---

# Semantic Rank vs Rerank Score

Step 6.3 semantic rank is:

```text
rank = 1..N
```

based on retrieval score.

Step 6.5 may later compute:

```text
rerank_score
```

and change final context ordering.

Do not overwrite or destroy the original semantic retrieval trace needed for evaluation/debugging.

---

# Suggested Module Structure

Equivalent:

```text
ai/
├── embeddings/
│   └── ...
└── retrieval/
    ├── service.py
    ├── query_preprocessor.py
    ├── schemas.py
    └── errors.py
```

Main dependency shape:

```text
SemanticRetrievalService
├── QueryPreprocessor
├── EmbeddingProvider
└── EmbeddingRepository / vector repository
```

Exact filenames may follow the existing repository convention.

---

# No Generic Retriever Hierarchy Yet

Do not introduce speculative abstractions such as:

```text
Retriever
├── VectorRetriever
├── BM25Retriever
└── HybridRetriever
```

V0 currently implements dense semantic retrieval only.

Use a concrete `SemanticRetrievalService`.

Refactor to a generic retrieval interface if a real lexical/hybrid implementation is introduced later.

---

# No LangChain Retriever Dependency

Do not introduce LangChain/LlamaIndex retriever wrappers solely for Step 6.3.

The project already owns:

```text
EmbeddingProvider
pgvector repository
SemanticRetrievalService
```

which provides a clearer, smaller architecture.

---

# Structured Logging

Log fields equivalent to:

```text
embedding_profile_id
query_length_chars
query_token_count
candidate_k
returned_count
top_distance optional
top_retrieval_score optional
embedding_duration_ms
vector_query_duration_ms
total_retrieval_duration_ms
status
error_code optional
```

Do not log full raw user query by default in infrastructure logs when the Conversation/message layer already persists content.

Do not log query vectors.

---

# Latency Measurement

Measure separately:

```text
query embedding latency
vector query latency
total retrieval latency
```

Do not set a hard latency SLA in Step 6.3.

Phase 7/10 can establish thresholds based on measured behavior.

---

# Configuration

Add/reuse setting:

```text
RAG_RETRIEVAL_CANDIDATE_K=20
```

Validate it as a positive bounded integer.

Do not allow arbitrary huge frontend-supplied values.

The active EmbeddingProfile and distance metric remain backend-controlled.

---

# Suggested Errors

Use the project's normalized error contract.

Stable errors may include equivalents of:

```text
EMPTY_RETRIEVAL_QUERY
RETRIEVAL_QUERY_TOO_LONG
ACTIVE_EMBEDDING_PROFILE_NOT_FOUND
MULTIPLE_ACTIVE_EMBEDDING_PROFILES
QUERY_EMBEDDING_FAILED
INVALID_QUERY_EMBEDDING
VECTOR_RETRIEVAL_FAILED
SEMANTIC_RETRIEVAL_FAILED
```

Do not expose raw model/database exceptions to clients.

---

# Smoke-test Corpus

Create a small semantic retrieval smoke-test dataset of known chunks.

Examples:

```text
Grammar: 了
Vocabulary: 学习
Vocabulary: 苹果
Grammar: 比
...
```

Example Vietnamese query:

```text
"cách dùng 了"
```

Expected behavior:

```text
relevant 了 chunk
∈ top K
```

This proves the semantic pipeline is wired correctly.

It does not prove production retrieval quality.

---

# No Arbitrary Quality Threshold in Smoke Test

Do not assert:

```text
retrieval_score > 0.72
```

without an evaluated dataset.

Use coarse assertions such as:

```text
expected relevant chunk appears in top K
```

Detailed retrieval quality evaluation belongs to Phase 7.

---

# Tests

Add focused tests covering at least:

## Query preprocessing

- leading/trailing whitespace removed;
- NFC normalization deterministic;
- light repeated whitespace normalization;
- empty result fails;
- no LLM rewrite/translation occurs.

## Active profile resolution

- exactly one ACTIVE profile is used;
- no ACTIVE profile fails explicitly;
- multiple ACTIVE profiles fail explicitly;
- frontend cannot override profile through normal retrieval request.

## Query embedding

- `embed_query()` is used rather than document embedding path;
- query normalization matches profile contract;
- provider-specific instructions remain inside provider;
- oversized query fails explicitly;
- query vector dimension/finite values are validated.

## Candidate count

- default candidate_k = 20;
- configuration override works;
- fewer available candidates returns fewer rows;
- no fake padding;
- zero valid candidates returns [].

## Search safety

- only ACTIVE KnowledgeVersions appear;
- only ACTIVE EmbeddingProfile is used;
- PROCESSING/FAILED/SUPERSEDED knowledge is never returned;
- storage safety gates remain enforced by repository.

## Score/ranking

- cosine distance is converted with `1 - distance`;
- higher retrieval_score ranks earlier;
- score is not clamped to 0..1;
- semantic ranks are deterministic for deterministic DB ordering.

## RetrievalCandidate

- contains required content/provenance fields;
- includes chunk_index;
- excludes full vector by default;
- DB metadata is resolved through JOIN rather than Embedding denormalization.

## Failure behavior

- query embedding failure returns technical error;
- vector DB failure returns technical error;
- successful empty result remains [];
- infrastructure error is never silently converted to [].

## Persistence boundary

- query vector is not persisted;
- SemanticRetrievalService does not require message_id;
- result provides chunk_id/rank/retrieval_score for later MessageRetrieval persistence.

## Scope

- Step 6.3 baseline can search all ACTIVE internal knowledge;
- no Lesson/HSK metadata filtering is applied yet;
- no external retrieval occurs;
- no reranking occurs;
- no prompt/LLM call occurs.

## Smoke test

- seeded semantically relevant chunk appears in expected top K for a known query;
- test does not require an arbitrary hard similarity threshold.

---

# Verification Flow

Required technical demo:

```text
query_text
↓
QueryPreprocessor
↓
ACTIVE EmbeddingProfile
↓
EmbeddingProvider.embed_query()
↓
query vector validation
↓
EmbeddingRepository.nearest_vectors(...)
↓
top semantic ACTIVE chunks
↓
RetrievalCandidate[]
```

Verify:

```text
candidate_k = 20 default
retrieval_score = cosine similarity
rank = semantic order
```

and:

```text
technical failure ≠ empty result
```

No metadata filtering/reranking/LLM/external retrieval is allowed in the Step 6.3 verification path.

---

# Out of Scope

Do not implement in Step 6.3:

```text
metadata filtering
lesson/HSK scoping policy
content_type filtering
source-priority boost
similarity threshold tuning
reranking
query expansion
LLM query rewrite
external retrieval
prompt construction
LLM generation
end-to-end RAG orchestration
conversation memory
citation rendering
query embedding cache
semantic cache
BM25
hybrid retrieval
generic Retriever framework
```

These belong to later Phase 6/7 work.

---

# Acceptance Criteria

- [ ] `SemanticRetrievalService` exists.
- [ ] Query preprocessing is deterministic and minimal.
- [ ] Empty queries fail explicitly.
- [ ] Oversized queries fail without silent truncation.
- [ ] Exactly one ACTIVE EmbeddingProfile is resolved internally.
- [ ] Query embedding uses `EmbeddingProvider.embed_query()`.
- [ ] Query/document normalization contracts match.
- [ ] No lesson/HSK metadata is silently prepended to query text.
- [ ] Provider-specific query instructions remain in provider code.
- [ ] Default `candidate_k` is configurable and equals 20.
- [ ] Fewer available candidates are returned normally.
- [ ] No similarity threshold is applied.
- [ ] Valid search may return [].
- [ ] `retrieval_score = 1 - cosine_distance`.
- [ ] Score is not clamped to 0..1.
- [ ] Semantic rank is deterministic.
- [ ] `RetrievalCandidate` carries content/provenance/score metadata.
- [ ] Raw vectors are not returned in candidates.
- [ ] chunk_index is retained.
- [ ] Baseline retrieval searches all ACTIVE internal knowledge.
- [ ] External retrieval is excluded.
- [ ] Query embedding failure is distinct from empty retrieval.
- [ ] Vector DB failure is distinct from empty retrieval.
- [ ] Query vectors are not persisted.
- [ ] Retrieval service is independent from Conversation persistence.
- [ ] Results can later populate `MessageRetrieval`.
- [ ] Latency is measured but no hard SLA is introduced.
- [ ] Smoke test verifies a known relevant chunk appears in top K.
- [ ] Step 6.4 can consume this result contract and add filtering.

# Expected Deliverable

Semantic retrieval foundation plus documentation:

```text
docs/ai/
└── step-6.3-semantic-retrieval.md
```

Next Step:

**Step 6.4 — Retrieval Filtering**
