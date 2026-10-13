# Step 6.2 — Vector Storage

## Objective

Persist dense vectors against the exact Chunk and EmbeddingProfile identities, prove that each KnowledgeVersion/profile pair is technically ready, and provide controlled activation and exact cosine-query foundations.

## Why

Embedding persistence alone does not prove a corpus is complete or queryable. Vector Storage adds database constraints, readiness checks, and atomic lifecycle operations so later retrieval can use a single coherent embedding space.

## Mental Model

```text
KnowledgeVersion + EmbeddingProfile
→ count required Chunks and matching Embeddings
→ validate profile, vector dimensions, and persisted cosine query
→ activate a complete cohort or replace one active version atomically
→ exact cosine query scoped to the global active profile
```

## Core Knowledge

- Each Embedding belongs to one Chunk and one EmbeddingProfile. Chunk deletion cascades to its Embeddings; profile deletion remains restricted while referenced.
- A partial unique index allows at most one globally ACTIVE EmbeddingProfile. Read paths still detect zero or multiple active profiles defensively.
- Readiness is status-agnostic for KnowledgeVersion. It requires at least one required Chunk, exactly one matching persisted Embedding per Chunk, profile-complete identity, matching dimensions, and a persisted cosine probe whose distance is finite and within `1e-6` of zero.
- Nearest-vector reads use exact cosine distance, only rows for the globally active profile, and deterministic distance then Chunk-ID ordering. No ANN index or public API is introduced.
- Bootstrap locks profiles, sources, and candidate versions in stable order, checks the whole source cohort, and activates the profile and every candidate in one transaction with one timestamp.
- Normal version activation checks readiness before superseding the prior ACTIVE version. Profile migration checks the full ACTIVE-version cohort before atomically switching profile status; it does not rewrite Embeddings or KnowledgeVersion lifecycle.
- Service operations own short transactions and repositories do not commit. Safe application error codes and structured logs omit driver details and vector contents.

## Data Flow

```text
EmbeddingProfile ─┐
                  ├→ VectorStorageService → VectorStorageRepository → AsyncSession / PostgreSQL + pgvector
KnowledgeVersion ─┘                                                   ├→ readiness probe
                                                                      ├→ activation lifecycle
                                                                      └→ exact cosine query
```

## Key Design Decisions

- Forward migration `0012_vector_storage_readiness` follows `0011_embedding_profile_identity`; migrations `0001`–`0011` remain unchanged.
- The migration adds a profile-first B-tree index, a partial unique ACTIVE-profile index, and `ON DELETE CASCADE` for the Embedding-to-Chunk foreign key while preserving the exact constraint name `fk_embeddings_chunk_id_chunks` across upgrade and downgrade.
- Embedding vectors remain variable-dimension at the column level. Profile-specific dimensions are enforced by readiness and query validation.
- Readiness probes persisted vectors using the pgvector cosine operator; query results are scoped to exact version/profile identity.
- Activation/profile switching use deterministic lock ordering and one database transaction. Existing active data remains unchanged when candidate readiness fails.
- No embedding provider, vector-index strategy, activation API route, retrieval workflow, or Step 6.3 behavior is added.

## Reusable Approach

Before publishing derived data, prove completeness and technical usability against its full semantic identity. Lock the lifecycle owners in a stable order, validate every member of the target cohort, and commit the state change atomically.

## Common Mistakes

- Treating a row count alone as proof that vectors can be queried.
- Comparing readiness only for ACTIVE KnowledgeVersions when PROCESSING versions also need validation before activation.
- Resolving a current profile/version implicitly instead of querying the exact requested identity.
- Holding partial activation changes after one cohort member fails readiness.
- Adding ANN structures before an explicit retrieval/indexing step.
- Logging database driver errors, vector payloads, or other sensitive data in application responses.

## Definition of Done

- Migration `0012_vector_storage_readiness` upgrades, downgrades, and re-upgrades while enforcing the ACTIVE-profile invariant and the exact foreign-key contract.
- Readiness, exact cosine query, bootstrap activation, normal version activation, and profile migration have focused PostgreSQL integration coverage, including conflict and atomicity cases.
- Step 6.1, Phase 5.5–5.7, and full backend regressions pass; Alembic reports head `0012_vector_storage_readiness` with no metadata drift.
- Verification evidence is recorded in the implementation handoff. No PM acceptance is implied.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Vector Readiness | BOTH | 6.2 | Proves persisted vectors are complete, dimensionally valid, and usable by the database query operator |
| Cosine Distance | AI | 6.2 | Defines the similarity operator used by the readiness probe and exact query |
| Exact Vector Search | BOTH | 6.2 | Establishes deterministic retrieval semantics without approximate indexes |
| Global Embedding Space | AI | 6.2 | Ensures a single active profile defines the vectors eligible for query |
| Production Activation Gate | SYSTEM | 6.2 | Prevents incomplete or technically unusable vector cohorts from becoming active |
| Atomic Version Swap | SYSTEM | 6.2 | Replaces one active KnowledgeVersion without exposing a partial lifecycle state |
| Atomic Profile Switch | SYSTEM | 6.2 | Changes the active embedding space only after the whole active corpus passes readiness |
| Partial Unique Index | DE | 6.2 | Enforces at most one globally ACTIVE EmbeddingProfile in PostgreSQL |
| Lock Ordering | SYSTEM | 6.2 | Makes concurrent activation and profile migration serialize predictably |
| Defense-in-depth Validation | BOTH | 6.2 | Combines relational constraints, profile checks, dimension checks, and a real pgvector probe |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| PostgreSQL | DE | 6.2 | Enforces foreign keys, partial unique indexes, transactions, and stable row locks |
| pgvector | BOTH | 6.2 | Stores vectors and executes persisted cosine-distance probes and exact queries |
| SQLAlchemy async | DE | 6.2 | Implements async repositories, lock ordering, and transaction-owned lifecycle operations |
| Alembic | DE | 6.2 | Applies the forward-only Step 6.2 schema contract |
