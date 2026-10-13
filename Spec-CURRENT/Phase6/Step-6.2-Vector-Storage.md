# Step 6.2 — Vector Storage

## Goal

Implement the vector storage layer for persisted `Embedding` rows produced by Step 6.1.

The physical architecture for V0 is:

```text
PostgreSQL
+
pgvector
```

This step must make embeddings durable, queryable with a consistent distance metric, and safely searchable only when both the `EmbeddingProfile` and `KnowledgeVersion` are ACTIVE.

Do not implement semantic retrieval policy, metadata filtering, reranking, prompting, or LLM generation in this step.

---

# Core Boundary

Input:

```text
KnowledgeVersion PROCESSING
├── Chunk[]
└── Embedding[] complete for target EmbeddingProfile
```

Output:

```text
pgvector-backed Embedding storage
+
vector readiness validation
+
safe activation primitives
```

Step 6.3 will consume the storage primitive to perform semantic retrieval.

---

# Physical Vector Store

Use:

```text
PostgreSQL
+
pgvector
```

Do not introduce:

```text
Pinecone
Qdrant
Milvus
Weaviate
Chroma
standalone vector database service
```

for V0.

The current corpus size does not justify a separate vector database.

---

# pgvector Extension

Manage the pgvector extension through Alembic migration.

Equivalent migration:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Do not rely on undocumented/manual schema setup outside the normal migration chain.

The local/dev/test/prod PostgreSQL runtime must support pgvector.

---

# Embedding Entity

Keep `Embedding` as a separate entity from `Chunk`.

Logical relation:

```text
Chunk
↓
Embedding
```

Required logical fields remain equivalent to:

```text
id UUID PK
chunk_id UUID NOT NULL FK → chunks.id
embedding_profile_id UUID NOT NULL FK → embedding_profiles.id
vector VECTOR NOT NULL
created_at
```

Preserve:

```text
UNIQUE(
  chunk_id,
  embedding_profile_id
)
```

Do not move vectors into `chunks`.

A Chunk may have embeddings from multiple profiles over its lifetime.

---

# Vector Dimension Strategy

Do not hard-code the database schema to:

```text
vector(1024)
```

solely because the first profile is BGE-M3.

Use variable-dimension pgvector storage compatible with the current schema/runtime.

The required dimension is validated against:

```text
EmbeddingProfile.dimensions
```

at embedding generation and readiness validation.

Reason:

```text
EmbeddingProfile A → 1024
future Profile B  → 768 / 1536 / other
```

should not require a table schema redesign merely because the embedding model changed.

Do not treat model changes as database-schema changes.

---

# Vector Precision

Use standard pgvector:

```text
vector
```

with normal float precision.

Do not use:

```text
halfvec
quantized vectors
binary vectors
```

in V0.

The corpus is small enough that storage savings do not justify reduced precision/extra complexity.

---

# Similarity Metric

V0 retrieval distance metric is:

```text
cosine distance
```

pgvector operator equivalent:

```sql
embedding <=> :query_vector
```

Mental model:

```text
smaller distance
→ greater semantic similarity
```

Keep:

```text
distance_metric = cosine
```

as a fixed V0 contract.

Do not let arbitrary callers choose distance metrics per request.

---

# Why Cosine

Step 6.1 produces L2-normalized dense embeddings.

Cosine is the clearest semantic retrieval contract for V0.

Do not mix:

```text
cosine
L2
inner product
```

across different code paths.

If the metric changes later, it should be a deliberate retrieval/profile migration decision.

---

# Exact Search in V0

Do not create HNSW or IVFFlat in V0.

Use exact nearest-neighbor scan:

```sql
ORDER BY vector <=> :query_vector
LIMIT :limit
```

Reasons:

```text
small corpus
exact ranking
no ANN recall loss
no HNSW tuning
no IVFFlat list/probe tuning
simpler migration/debugging
```

Add approximate ANN indexes only when measured data size/latency requires them.

---

# Relational Indexes

Maintain minimal relational indexes required by the current access pattern:

```text
UNIQUE(chunk_id, embedding_profile_id)
INDEX(embedding_profile_id)
```

Preserve existing PK/FK indexes.

Do not add speculative metadata indexes in Step 6.2.

Metadata/filter indexes belong to Step 6.4 after actual filter queries are defined.

---

# No Metadata Duplication in Embedding Rows

Do not duplicate fields such as:

```text
lesson_id
content_type
page_number
section
knowledge_version_id
source_type
```

into `Embedding`.

Canonical relation remains:

```text
Embedding
→ Chunk
→ KnowledgeVersion
→ KnowledgeSource
```

Join through the relational model.

The V0 corpus is small, and early denormalization would add integrity risk.

---

# No knowledge_version_id Denormalization

Do not add:

```text
Embedding.knowledge_version_id
```

in V0.

It is already derivable:

```text
Embedding.chunk_id
→ Chunk.knowledge_version_id
```

Avoid duplicate state that can become inconsistent.

Revisit only if profiling proves the join is a real bottleneck.

---

# ACTIVE Retrieval Safety Rule

Production vector search must never use knowledge from:

```text
PROCESSING
FAILED
SUPERSEDED
```

KnowledgeVersions.

Hard rule:

```text
KnowledgeVersion.status = ACTIVE
```

for production retrieval.

Physical rows may remain stored for history/debug/retry, but they are not production-searchable.

---

# ACTIVE EmbeddingProfile Rule

Production vector search must use only:

```text
EmbeddingProfile.status = ACTIVE
```

Do not search an INACTIVE profile by accident.

This prevents mixing incompatible semantic spaces.

---

# Low-level Search Must Enforce Both Gates

The storage/repository layer must enforce:

```text
KnowledgeVersion.status = ACTIVE
AND
EmbeddingProfile.status = ACTIVE
```

before distance ordering.

Equivalent relational flow:

```text
Embedding
JOIN Chunk
JOIN KnowledgeVersion
JOIN EmbeddingProfile
WHERE KnowledgeVersion.status = ACTIVE
  AND EmbeddingProfile.status = ACTIVE
ORDER BY Embedding.vector <=> :query_vector
LIMIT :limit
```

Do not depend on Step 6.3 callers remembering these safety filters.

---

# Storage Primitive

Step 6.2 may expose a low-level repository operation equivalent to:

```python
nearest_vectors(
    query_vector,
    embedding_profile_id,
    limit,
)
```

Technical result:

```text
chunk_id
distance
```

Do not yet handle:

```text
user question
query preprocessing
query embedding orchestration
lesson context
candidate policy
threshold policy
fallback policy
```

Those belong to Step 6.3.

---

# Distance vs Retrieval Score

The storage layer returns:

```text
distance
```

Do not invent a product-level:

```text
retrieval_score
```

mapping in Step 6.2.

Step 6.3 may define how to transform/use distance during retrieval.

Keep storage semantics simple and explicit.

---

# Vector Readiness

A `KnowledgeVersion` is vector-ready for a target profile only when all conditions pass:

```text
KnowledgeVersion.status = PROCESSING
AND
all required Chunks exist
AND
exactly one Embedding exists per required Chunk/profile
AND
all vector dimensions match EmbeddingProfile.dimensions
AND
vector rows are non-null/valid
AND
a technical pgvector query probe succeeds
```

Do not infer readiness from row count alone.

---

# No READY Status

Do not add a new:

```text
READY
```

KnowledgeVersion status.

Keep the existing state machine:

```text
PROCESSING
ACTIVE
SUPERSEDED
FAILED
```

Readiness is a derived validation result:

```text
is_vector_ready(...)
```

If readiness passes, the activation service may transition PROCESSING → ACTIVE.

---

# KnowledgeVersion Activation

When a replacement version is fully vector-ready:

```text
old version ACTIVE
new version PROCESSING
```

perform one short transaction:

```text
BEGIN

new PROCESSING → ACTIVE
old ACTIVE     → SUPERSEDED

COMMIT
```

If the transaction fails:

```text
ROLLBACK
```

The old ACTIVE state remains unchanged.

Do not perform the two status changes in separate independent commits.

---

# No Availability Gap

Replacement activation must never create:

```text
old version SUPERSEDED
↓
gap
↓
new version ACTIVE
```

The swap must be atomic.

There should always be an ACTIVE version available for a source until the replacement is ready.

---

# Initial Bootstrap

Initial system state may have:

```text
no ACTIVE EmbeddingProfile
no ACTIVE KnowledgeVersion
```

After the required initial corpus has:

```text
Chunk complete
Embedding complete
vector readiness pass
```

run a controlled activation operation:

```text
EmbeddingProfile INACTIVE → ACTIVE
initial KnowledgeVersions PROCESSING → ACTIVE
```

Do not activate a profile while only part of the intended initial corpus is ready.

---

# EmbeddingProfile Migration

When changing embedding model/profile:

```text
old profile ACTIVE
new profile INACTIVE
```

Step 5.7 + 6.1:

```text
reuse Chunk[]
→ generate new-profile Embeddings
```

Step 6.2:

```text
verify new-profile vector readiness
```

then atomically switch:

```text
old profile → INACTIVE
new profile → ACTIVE
```

KnowledgeVersions do not need to change merely because the EmbeddingProfile changed.

---

# Exactly One ACTIVE EmbeddingProfile in V0

V0 production retrieval uses:

```text
exactly one ACTIVE EmbeddingProfile
```

Do not support simultaneous production ranking across multiple embedding spaces.

Multi-profile experiments belong to offline evaluation.

Enforce this through application logic and, if cleanly feasible with the current schema, a database constraint/index pattern.

Do not overcomplicate schema solely for this if the existing architecture already has a reliable activation service.

---

# Profile Activation Atomicity

Profile switch should also occur in one short transaction:

```text
BEGIN

old ACTIVE profile → INACTIVE
new INACTIVE profile → ACTIVE

COMMIT
```

If validation/transaction fails, retain the previous ACTIVE profile.

---

# Vector Dimension Validation

Step 6.1 validates dimensions before persistence.

Step 6.2 validates again before readiness/activation:

```text
stored vector dimension
==
EmbeddingProfile.dimensions
```

Mismatch:

```text
VECTOR_DIMENSION_MISMATCH
```

Do not activate or search malformed profile/version data.

This is defense-in-depth.

---

# Vector NOT NULL

Use:

```text
Embedding.vector NOT NULL
```

If embedding generation has not completed, do not create a placeholder row with:

```text
vector = NULL
```

The absence of the Embedding row represents unfinished work.

---

# Delete Behavior

Recommended relation behavior:

```text
Chunk deleted
→ related Embeddings cascade delete
```

because an Embedding cannot exist independently from its Chunk.

For `EmbeddingProfile`:

```text
prefer ACTIVE / INACTIVE lifecycle
```

Do not freely delete a profile while historical embeddings still reference it.

Use restrictive FK behavior appropriate to the existing schema.

---

# Repository Boundary

Keep pgvector-specific persistence/query operations inside a repository/data-access boundary equivalent to:

```text
EmbeddingRepository
```

Possible responsibilities:

```text
persist embedding
count embeddings
validate completeness
validate dimensions
nearest_vectors
vector probe
```

A separate `VectorRepository` is acceptable if it fits the current codebase better.

Do not place raw pgvector SQL in:

```text
Router
ConversationService
AIChatService
```

---

# No Generic VectorStore Abstraction Yet

Do not prematurely create:

```text
VectorStore
├── PgVectorStore
├── PineconeVectorStore
├── QdrantVectorStore
└── ...
```

The architecture has already chosen PostgreSQL + pgvector for V0.

A repository boundary is enough.

Refactor to a generalized storage abstraction only when a real second backend requirement exists.

---

# top_k Boundary

The low-level storage primitive accepts:

```text
limit
```

but Step 6.2 does not decide the product retrieval default.

Example test:

```text
limit = 5
```

does not mean:

```text
RAG candidate_k = 5
```

Step 6.3 will define retrieval candidate counts.

---

# No Similarity Threshold in Storage

Do not add:

```text
distance < arbitrary_threshold
```

as a V0 storage policy.

The storage layer returns nearest vectors.

Whether a result is semantically relevant enough is a retrieval/evaluation concern.

Thresholds belong to later retrieval/evaluation design.

---

# Alembic Migration Requirements

Review and add migration changes needed for:

```text
pgvector extension
Embedding.vector physical type
NOT NULL
FK constraints
UNIQUE(chunk_id, embedding_profile_id)
INDEX(embedding_profile_id)
```

Do not trust Alembic autogenerate blindly for extension/vector-type details.

Review migration SQL manually.

---

# Runtime Requirement

Step 6.2 records:

```text
PostgreSQL runtime must support pgvector
```

Do not implement Docker Compose/containerization in this step.

Dockerized runtime belongs to Phase 8.

Local development must still use a PostgreSQL instance with pgvector available.

---

# Structured Logging

Log vector-storage/readiness events with fields equivalent to:

```text
embedding_profile_id
knowledge_version_id
vector_count
dimensions
distance_metric
readiness_status
query_probe_duration_ms
activation_action
status
error_code optional
```

Do not log full vectors.

---

# Suggested Errors

Use the current normalized backend error contract.

Stable errors may include equivalents of:

```text
PGVECTOR_NOT_AVAILABLE
VECTOR_DIMENSION_MISMATCH
VECTOR_STORAGE_NOT_READY
KNOWLEDGE_VERSION_NOT_PROCESSING
KNOWLEDGE_VERSION_NOT_VECTOR_READY
EMBEDDING_PROFILE_NOT_READY
ACTIVE_EMBEDDING_PROFILE_NOT_FOUND
MULTIPLE_ACTIVE_EMBEDDING_PROFILES
VECTOR_QUERY_FAILED
ACTIVATION_CONFLICT
```

Do not expose raw database exceptions to clients.

---

# Technical Query Probe

Readiness should include a small technical probe that confirms:

```text
pgvector operator executes
target profile vectors can be read
dimensions are compatible
query ordering succeeds
```

This probe is not Semantic Retrieval.

It may use one known stored vector or a safe test vector of matching dimensions.

Do not interpret the returned Chunk semantically in Step 6.2.

---

# Tests

Add focused tests covering at least:

## Migration / schema

- pgvector extension migration is present;
- vector column is NOT NULL;
- Chunk FK is correct;
- EmbeddingProfile FK is correct;
- unique Chunk/Profile constraint works;
- profile index exists;
- expected delete behavior works.

## Storage

- valid 1024-dimensional BGE-M3 vector persists;
- Embedding remains separate from Chunk;
- same Chunk/Profile duplicate is rejected/skipped;
- historical embeddings for multiple profiles may coexist.

## ACTIVE safety

- ACTIVE profile + ACTIVE KnowledgeVersion is searchable;
- PROCESSING version is excluded;
- FAILED version is excluded;
- SUPERSEDED version is excluded;
- INACTIVE profile is excluded;
- low-level repository enforces the gates itself.

## Distance

- cosine operator is used;
- smaller cosine distance sorts first;
- storage returns distance, not invented product score;
- arbitrary threshold is not applied.

## Exact search

- exact scan path works without HNSW/IVFFlat;
- no ANN index is required for V0.

## Readiness

- missing Chunk embedding fails readiness;
- duplicate/inconsistent embedding fails readiness;
- dimension mismatch fails readiness;
- query probe failure fails readiness;
- complete valid profile/version passes readiness;
- no READY enum/status is added.

## KnowledgeVersion activation

- new PROCESSING version becomes ACTIVE only after readiness passes;
- previous ACTIVE becomes SUPERSEDED in same transaction;
- failed transaction leaves old ACTIVE unchanged;
- no availability gap is observable.

## EmbeddingProfile activation

- new profile starts INACTIVE;
- incomplete profile cannot become ACTIVE;
- old profile stays ACTIVE while new profile builds;
- successful readiness permits atomic ACTIVE profile switch;
- KnowledgeVersion does not change solely because profile changed;
- V0 production retrieval sees exactly one ACTIVE profile.

## Boundaries

- no user-question preprocessing;
- no query embedding orchestration;
- no metadata filtering;
- no reranking;
- no prompt/LLM call;
- no similarity-threshold policy.

---

# Out of Scope

Do not implement in Step 6.2:

```text
HNSW
IVFFlat
ANN tuning
vector quantization
halfvec
standalone vector DB
query preprocessing
semantic retrieval policy
metadata filtering
similarity threshold policy
reranking
prompt construction
LLM generation
RAG orchestration
conversation memory
citations
Docker Compose
production performance tuning
```

These belong to later steps/phases.

---

# Acceptance Criteria

- [ ] PostgreSQL + pgvector is the V0 vector store.
- [ ] pgvector extension is managed through Alembic.
- [ ] Embedding remains a separate entity from Chunk.
- [ ] Vector storage is not hard-coded to one model dimension at schema level.
- [ ] Standard vector precision is used; no halfvec.
- [ ] Cosine distance is the fixed V0 metric.
- [ ] Exact vector scan is used; no HNSW/IVFFlat.
- [ ] Required relational indexes/uniqueness are present.
- [ ] Chunk metadata is not duplicated into Embedding.
- [ ] knowledge_version_id is not denormalized into Embedding.
- [ ] Production search enforces ACTIVE KnowledgeVersion.
- [ ] Production search enforces ACTIVE EmbeddingProfile.
- [ ] Low-level repository enforces both ACTIVE gates.
- [ ] Storage returns distance, not an invented retrieval score.
- [ ] Vector readiness validates completeness, dimensions, and query probe.
- [ ] No READY status is added.
- [ ] KnowledgeVersion activation is atomic.
- [ ] Initial corpus/profile bootstrap is controlled.
- [ ] EmbeddingProfile migration is atomic and does not require rechunk.
- [ ] V0 has exactly one ACTIVE EmbeddingProfile.
- [ ] Vector is NOT NULL.
- [ ] Chunk deletion removes dependent Embeddings.
- [ ] Repository boundary contains pgvector-specific access.
- [ ] No generic multi-provider VectorStore abstraction is added.
- [ ] top_k retrieval policy is deferred to Step 6.3.
- [ ] Similarity threshold is deferred.
- [ ] Step 6.3 can use `nearest_vectors(...)` safely.

# Expected Deliverable

Vector storage foundation plus documentation:

```text
docs/ai/
└── step-6.2-vector-storage.md
```

Next Step:

**Step 6.3 — Semantic Retrieval**
