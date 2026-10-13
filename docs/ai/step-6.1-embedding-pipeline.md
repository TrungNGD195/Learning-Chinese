# Step 6.1 — Embedding Pipeline

## Objective

Convert persisted canonical Chunks into deterministic, validated, version-identified dense embeddings without activating retrieval.

## Why

Semantic retrieval requires vector representations, but safe AI/data pipelines also require reproducible model/input identity, idempotent persistence, and explicit failure/retry semantics.

## Mental Model

```text
Chunk
→ semantic input formatter/version
→ model tokenizer boundary
→ embedding provider/model revision
→ normalized vector
→ durable Chunk/Profile row
```

Profile identity includes provider and package version, model and immutable revision, dimensions, formatter version, and normalization. Lifecycle status is not semantic identity.

## Core Knowledge

- Dense vectors only; no sparse or multi-vector representation.
- Canonical Chunk content is never changed. Formatter v1 adds only the required Document or Lesson context.
- BGE-M3 model revision and Sentence Transformers package version are pinned in the profile identity.
- Provider tokenization explicitly disables truncation and rejects overlength input.
- PostgreSQL uniqueness protects one Embedding per Chunk/Profile. Persistence is conflict-safe and idempotent.
- Successful batches remain committed if a later batch fails; the KnowledgeVersion becomes FAILED and retries preserve prior rows.
- A failed retry proves compatibility in order: source, parser/cleaning/transformation lineage, chunking configuration, ordered Chunk content/provenance, then prior profile evidence. Stale upstream lineage is handed to the existing Step 5.7 planner with both embedding-change flags false, even when profile evidence is missing or stale.
- With current upstream lineage, an input-version-only mismatch is classified separately from a model/profile mismatch. Missing profile evidence conservatively requests embedding-stage reprocessing; no planner result is executed by the retry operation.
- Retry claims are serialized under the KnowledgeSource lock. A concurrent retry observes PROCESSING and returns the existing conflict. Exact Chunk/Profile insert conflicts use the named SQL constraint path; unrelated database integrity failures remain build failures.
- Database transactions end before tokenization and inference. A successful Step 6.1 build leaves the KnowledgeVersion PROCESSING and the target profile INACTIVE.

## Data Flow

```text
KnowledgeVersion
→ ordered Chunk[] and persisted source context
→ EmbeddingInputFormatter/v1
→ local BAAI/bge-m3 dense inference
→ normalized vector validation
→ conflict-safe Embedding rows
```

## Key Design Decisions

- Local BAAI/bge-m3 baseline, 1024 dimensions, normalized output.
- `sentence-transformers==6.1.0` and immutable model revision `5617a9f61b028005a4858fdac845db406aefb181`.
- Nullable migration fields preserve incomplete legacy profiles; new profiles have complete semantic identity and start INACTIVE.
- Model loads lazily once per cached provider process instance. `auto` delegates device choice to Sentence Transformers.
- Configurable sequential batch persistence; no global vector cache or overwrite path.
- SentenceTransformer receives the immutable Hub revision as its top-level `revision` constructor argument; automatic device resolution remains `device=None`.
- No activation, vector search, retrieval, reranking, prompt construction, or LLM generation.

## Reusable Approach

Expensive derived ML artifacts should carry enough durable semantic identity to prove whether reuse remains safe after model, input, or configuration changes.

## Common Mistakes

- Using a model name without an immutable revision.
- Mixing formatter versions under one profile.
- Holding a database transaction during inference.
- Silently truncating model input or treating `Chunk.token_count` as model-independent.
- Overwriting historical Embeddings or assuming the final batch proves corpus completeness.
- Retrying FAILED work without durable compatibility evidence.

## Definition of Done

- Forward migration 0011 adds only nullable EmbeddingProfile identity fields and their semantic uniqueness constraint; migration tests cover legacy-row preservation and downgrade.
- Configuration, provider, formatter, persistence service, failure handling, and explicit retry are implemented within the Step 6.1 boundary.
- Verification evidence is recorded in the implementation handoff. Retry classification and exact duplicate-insert behavior have dedicated regression coverage. No PM acceptance is implied.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Dense Embedding | AI | 6.1 | Represents Chunk semantics as dense vectors for later retrieval |
| Embedding Provider Boundary | AI | 6.1 | Isolates model/library-specific inference behavior |
| Embedding Input Formatting | AI | 6.1 | Creates deterministic semantic model input without mutating canonical Chunk content |
| Model Revision Pinning | AI | 6.1 | Gives model artifacts immutable/reproducible identity |
| L2 Normalization | AI | 6.1 | Produces consistent normalized dense vectors for later similarity semantics |
| Model-specific Token Boundary | AI | 6.1 | Prevents silent truncation and model-length misuse |
| Embedding Input Versioning | BOTH | 6.1 | Connects AI input semantics to re-embedding/invalidation |
| Processing Lineage | BOTH | 6.1 | Proves whether expensive derived data may be safely reused |
| Completeness Invariant | BOTH | 6.1 | Proves every required Chunk has exactly one target-profile Embedding |
| Idempotency | SYSTEM | 6.1 | Makes retry/re-execution safe without duplicate rows |
| Transaction Boundary | SYSTEM | 6.1 | Prevents DB transactions from spanning expensive inference |
| Partial Failure Semantics | SYSTEM | 6.1 | Preserves committed work and supports safe retry |
| Durable Processing Claim | SYSTEM | 6.1 | Reuses source locking/status to prevent conflicting retries |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| BAAI/bge-m3 | AI | 6.1 | V0 multilingual dense embedding model |
| sentence-transformers | AI | 6.1 | Local model/tokenizer inference library |
| PostgreSQL + pgvector | BOTH | 6.1 | Durable vector persistence already used by the project |
| SQLAlchemy async | DE | 6.1 | Async persistence, transactions, locks, and completeness queries |
| Alembic | DE | 6.1 | Forward migration for durable EmbeddingProfile semantic identity |
