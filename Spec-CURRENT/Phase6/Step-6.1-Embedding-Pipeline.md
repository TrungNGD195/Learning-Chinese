# Step 6.1 — Embedding Pipeline

## Goal

Implement the first Phase 6 AI/Data pipeline stage:

```text
Chunk
→ EmbeddingInputFormatter
→ EmbeddingProvider
→ dense vector
→ Embedding row
```

The implementation must convert persisted `Chunk` records belonging to a `PROCESSING` `KnowledgeVersion` into embeddings for a selected `EmbeddingProfile`.

V0 uses a local multilingual dense embedding model:

```text
BAAI/bge-m3
```

with:

```text
provider   = LOCAL
dimensions = 1024
```

Use only the dense embedding output in V0.

Do not implement vector search, retrieval, filtering, reranking, prompting, or LLM generation in this step.

---

# Core Boundary

Input:

```text
KnowledgeVersion PROCESSING
└── Chunk[]
```

Output:

```text
KnowledgeVersion PROCESSING
├── Chunk[]
└── Embedding[] complete for target EmbeddingProfile
```

Step 6.1 does not activate the KnowledgeVersion.

Step 6.2 is responsible for vector storage/search readiness before safe activation.

---

# EmbeddingProfile

Reuse the existing logical `EmbeddingProfile` model.

Required logical fields remain equivalent to:

```text
id
provider
model_name
model_version nullable
dimensions
status
created_at
```

V0 profile:

```text
provider    = LOCAL
model_name  = BAAI/bge-m3
dimensions  = 1024
status      = INACTIVE initially
```

Do not hard-code the active profile inside retrieval/business logic.

Do not overwrite historical embeddings when a new profile is introduced.

---

# Provider Abstraction

Define an abstraction equivalent to:

```python
class EmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...
```

Keep document and query embedding methods separate.

Reason:

- some models/providers may use different input formatting for passage vs query;
- Step 6.3 will use query embedding;
- future provider changes should not require rewriting retrieval/business services.

V0 implementation:

```text
SentenceTransformerEmbeddingProvider
→ BAAI/bge-m3
```

Do not expose the sentence-transformers object outside the provider layer.

---

# Model Dependency

Use:

```text
sentence-transformers
transformers
PyTorch
```

Do not introduce LangChain or LlamaIndex solely for embedding.

The embedding abstraction is small enough to own directly.

Pin compatible dependency versions in the project's dependency management files.

---

# Model Lifecycle

Load the local model once per backend/application process.

Do not:

```text
each batch
→ load model
→ encode
→ unload model
```

Use an application/provider lifecycle equivalent to a singleton/provider instance.

Device is configurable:

```text
EMBEDDING_DEVICE=auto
```

Supported logical behavior:

```text
auto
→ CUDA when available
→ MPS when supported
→ CPU fallback
```

Do not hard-code GPU assumptions.

Expose device choice through configuration.

---

# Dense Embedding Only

BGE-M3 supports more than one retrieval representation, but V0 uses only:

```text
dense embeddings
```

Do not implement:

```text
sparse lexical vectors
multi-vector retrieval
hybrid BGE-M3 modes
```

in Step 6.1.

Keep the provider boundary extensible without exposing unused capabilities.

---

# Embedding Input Formatter

Create a deterministic boundary equivalent to:

```text
EmbeddingInputFormatter
```

Flow:

```text
Chunk
↓
EmbeddingInputFormatter/v1
↓
embedding_text
↓
EmbeddingProvider
```

Do not mutate `Chunk.content`.

`Chunk.content` remains the canonical source-derived retrieval content.

The formatter creates model input only.

---

# Embedding Input Version

Use:

```text
embedding_input_version = "v1"
```

Persist/associate this version with the embedding build/profile/config in a way compatible with the current schema.

The formatter must be deterministic.

Changing the formatter version later means:

```text
same Chunk[]
→ re-embed only
```

according to Step 5.7.

Do not force reparse/retransform/rechunk for formatter-only changes.

---

# Document Embedding Input

For `DOCUMENT_TEXT`, format equivalent to:

```text
Title: <document title>
Section: <section path when available>

<Chunk.content>
```

Include only semantically useful source context.

Do not prepend:

```text
UUID
storage key
upload timestamp
page number
usage-rights metadata
database identifiers
```

into the embedding text.

Page/locator data remains metadata for citation/filtering.

---

# Lesson Embedding Input

For Lesson-derived chunks, format equivalent to:

```text
HSK: <level>
Lesson: <lesson title>
Type: <VOCABULARY | GRAMMAR | LESSON_GENERAL>

<Chunk.content>
```

Use deterministic labels/order.

Do not include runtime-only IDs unless semantically necessary.

---

# No Semantic Rewrite Before Embedding

Do not:

```text
summarize
translate
paraphrase
grammar-correct
LLM-rewrite
```

the Chunk before embedding.

The multilingual embedding model must represent the source content directly.

This preserves provenance and deterministic behavior.

---

# Vector Normalization

Enable L2 normalization for V0 dense vectors.

Equivalent provider configuration:

```text
normalize_embeddings = True
```

Result:

```text
||vector||₂ ≈ 1
```

Store the normalized vector output.

Normalization is part of the profile/provider configuration and should not be an accidental hidden behavior.

Exact similarity/index operator belongs to Step 6.2.

---

# Model Input Length Validation

Do not silently truncate oversized embedding input.

Flow:

```text
embedding_text
↓
model tokenizer
↓
validate against model-supported input length
```

If too long:

```text
EMBEDDING_INPUT_TOO_LONG
```

Then fail the build safely.

Do not:

```text
take first N tokens
discard tail
continue silently
```

If Chunk size is unsuitable, adjust chunking and use the Step 5.7 `FROM_CHUNK` reprocessing path.

---

# Chunk.token_count

The existing nullable:

```text
Chunk.token_count
```

must not be treated as a model-independent source of truth.

Token counts depend on tokenizer/model.

V0 may leave:

```text
Chunk.token_count = NULL
```

Embedding pipeline should tokenize the actual formatted input for the target model when validating limits.

Do not write model-specific token counts into a field and later assume they apply to every EmbeddingProfile.

---

# Batch Encoding

Encode chunks in batches.

V0 baseline:

```text
embedding_batch_size = 32
```

This value must be configurable.

Do not call the model once per Chunk unless a single-item remainder batch is unavoidable.

Do not tune batch size to one specific development GPU in code.

---

# Batch Ordering

Load required Chunks in deterministic order:

```text
chunk_index ASC
```

Build:

```text
Chunk[]
→ EmbeddingInput[]
→ batches
```

Preserve input/output alignment.

Provider output index must correspond exactly to input index.

---

# Sequential Batches in V0

Process batches sequentially:

```text
batch 1
→ batch 2
→ batch 3
```

Do not parallelize multiple model batches in V0.

Reasons:

- avoid GPU/CPU contention;
- reduce OOM risk;
- easier deterministic failure handling;
- current corpus is small.

The model itself already vectorizes each batch.

---

# Embedding Persistence

Use short DB transactions per completed batch.

Preferred flow:

```text
load Chunk batch
↓
format embedding inputs
↓
validate input lengths
↓
model inference
↓
validate vectors
↓
short DB transaction
↓
persist Embedding rows
↓
commit
```

Do not hold a DB transaction open during model inference.

Do not keep the complete corpus vectors in memory before writing all rows.

---

# Embedding Idempotency

Reuse the existing logical uniqueness:

```text
UNIQUE(
  chunk_id,
  embedding_profile_id
)
```

For each Chunk:

```text
embedding already exists for target profile
→ skip
```

This enables safe retry.

Example:

```text
100 chunks
60 embeddings already persisted

retry
→ skip 60
→ embed remaining 40
```

Do not overwrite an existing historical embedding row for the same Chunk/Profile unless the current data model explicitly supports a safe replacement mode.

Default behavior is skip.

---

# Partial Failure Behavior

If a batch fails:

```text
already-persisted previous batches
→ keep

current/remaining batches
→ stop
```

Then:

```text
KnowledgeVersion → FAILED
```

Do not delete successful prior Embedding rows.

The FAILED version is not retrieval-active, so partial persisted embeddings are safe and useful for retry.

---

# Retry of Failed Embedding Build

A FAILED KnowledgeVersion may be retried in-place only when all relevant fingerprints remain unchanged:

```text
source
Chunk set
Chunk content/order
EmbeddingProfile
embedding_input_version
provider/model configuration
```

Retry flow:

```text
FAILED
→ validate fingerprint compatibility
→ PROCESSING
→ skip existing Embeddings
→ generate missing Embeddings
```

If any relevant dependency changed:

```text
ReprocessingPlanner
→ compute a new plan
```

Do not reuse a stale failed candidate blindly.

---

# Embedding Output Validation

Validate every provider result before persistence.

Required checks:

```text
output vector count == input count
vector dimensions == EmbeddingProfile.dimensions
all values finite
no NaN
no Inf
```

For normalized embeddings also validate that norm is approximately expected within a reasonable numerical tolerance.

On invalid output:

```text
INVALID_EMBEDDING_OUTPUT
```

Do not persist malformed vectors.

---

# No Embedding Dedup Cache in V0

Do not deduplicate embeddings globally using:

```text
Chunk.content_hash
```

If:

```text
Chunk A content_hash = X
Chunk B content_hash = X
```

still create/maintain the normal Embedding relation per Chunk.

Do not introduce:

```text
global vector cache
cross-version embedding-copy layer
content-hash embedding table
```

in V0.

Step 5.7 already defers cross-version per-chunk reuse.

---

# Profile Activation

A newly created EmbeddingProfile starts:

```text
INACTIVE
```

Do not switch retrieval to it merely because some vectors exist.

Profile activation should happen only after the corpus required by the application has been built and Step 6.2 confirms vector storage/search readiness.

Do not mark the new profile ACTIVE prematurely.

---

# KnowledgeVersion State After Step 6.1

Even if all required Chunk embeddings are successfully persisted:

```text
KnowledgeVersion
= PROCESSING
```

at the end of Step 6.1.

Do not activate yet.

Step 6.2 will make vectors search-ready and participate in the final safe activation boundary.

---

# Completeness Check

A successful Step 6.1 build must verify:

```text
for every required Chunk
there is exactly one Embedding
for the target EmbeddingProfile
```

Equivalent completeness criterion:

```text
count(required_chunks)
==
count(embeddings for target profile)
```

with uniqueness preserved.

Do not infer completeness solely from "last batch succeeded".

---

# Embedding Service Boundary

Use a service equivalent to:

```text
EmbeddingService
```

Responsibilities:

- validate KnowledgeVersion eligibility;
- resolve target EmbeddingProfile;
- load ordered missing Chunks;
- build embedding inputs;
- validate model limits;
- batch provider calls;
- validate output vectors;
- persist Embedding rows;
- support idempotent retry;
- compute/verify completion;
- update build failure state;
- emit structured logs.

Do not make the repository or router call the model directly.

---

# Suggested Module Structure

Equivalent:

```text
ai/
└── embeddings/
    ├── provider.py
    ├── sentence_transformer_provider.py
    ├── formatter.py
    ├── service.py
    ├── schemas.py
    └── errors.py
```

Exact filenames may follow current repository conventions.

Keep provider/model-specific code isolated from application orchestration.

---

# Configuration

Add explicit application settings equivalent to:

```text
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_DEVICE=auto
EMBEDDING_BATCH_SIZE=32
EMBEDDING_INPUT_VERSION=v1
EMBEDDING_NORMALIZE=true
```

Do not hard-code operational configuration inside provider/service classes.

---

# Structured Logging

Log at minimum:

```text
knowledge_version_id
embedding_profile_id
model_name
batch_index
batch_size
duration_ms
embedded_count
skipped_count
device
status
error_code optional
```

Do not log full Chunk/embedding input text in normal production logs.

Do not log full vectors.

---

# Suggested Errors

Use the current normalized backend error contract.

Stable errors may include equivalents of:

```text
EMBEDDING_PROFILE_NOT_FOUND
EMBEDDING_PROFILE_INVALID
KNOWLEDGE_VERSION_NOT_PROCESSING
EMBEDDING_INPUT_TOO_LONG
EMBEDDING_PROVIDER_FAILED
INVALID_EMBEDDING_OUTPUT
EMBEDDING_BUILD_FAILED
EMBEDDING_FINGERPRINT_MISMATCH
```

---

# Tests

Add focused tests for:

- deterministic formatter output;
- Document/Lesson semantic context formatting;
- Chunk.content immutability;
- provider document/query interfaces;
- expected 1024 dimensions;
- L2 normalization;
- model input length validation with no silent truncation;
- chunk_index ordering;
- configurable batch size;
- sequential batches;
- no DB transaction during inference;
- skip existing Chunk/Profile Embedding;
- partial failure retention;
- FAILED KnowledgeVersion state;
- retry only missing embeddings when fingerprints match;
- wrong vector count/dimension/NaN/Inf rejection;
- completeness check;
- final KnowledgeVersion remains PROCESSING;
- EmbeddingProfile remains INACTIVE;
- no vector search/retrieval/reranking/LLM calls.

Use mocks/fakes for fast unit tests where loading the real model would be expensive.

---

# Out of Scope

Do not implement in Step 6.1:

```text
pgvector indexing/search configuration
similarity search
query retrieval pipeline
metadata filtering
reranking
prompt construction
LLM generation
RAG orchestration
conversation memory
citations
sparse BGE-M3 retrieval
multi-vector BGE-M3 retrieval
global embedding cache
cross-version vector-copy optimization
parallel batch workers
Celery/queue infrastructure
KnowledgeVersion activation
```

---

# Acceptance Criteria

- [ ] BAAI/bge-m3 is the V0 local multilingual EmbeddingProfile.
- [ ] V0 uses dense vectors only.
- [ ] Dimensions are 1024.
- [ ] `EmbeddingProvider` separates document and query embedding.
- [ ] SentenceTransformers implementation is isolated behind the provider.
- [ ] Model is loaded once per process/provider lifecycle.
- [ ] Device is configurable with safe CPU fallback.
- [ ] `EmbeddingInputFormatter/v1` exists and is deterministic.
- [ ] Chunk.content remains unchanged.
- [ ] Document semantic metadata is included minimally in embedding input.
- [ ] Lesson semantic metadata is included minimally in embedding input.
- [ ] No LLM/translation/summarization occurs before embedding.
- [ ] Dense vectors are L2-normalized.
- [ ] Oversized inputs fail explicitly; no silent truncation.
- [ ] `Chunk.token_count` is not treated as cross-model truth.
- [ ] Embeddings are produced in configurable batches, baseline 32.
- [ ] Batches run sequentially in V0.
- [ ] DB transactions do not span model inference.
- [ ] Existing same Chunk/Profile embeddings are skipped.
- [ ] Partial successful batches are retained after later failure.
- [ ] Failed build marks KnowledgeVersion FAILED.
- [ ] Safe retry fills only missing embeddings when fingerprints are unchanged.
- [ ] Vector count/dimension/finite-value checks run before persistence.
- [ ] No global content-hash embedding cache is added.
- [ ] New EmbeddingProfile begins INACTIVE.
- [ ] Successful Step 6.1 leaves KnowledgeVersion PROCESSING.
- [ ] Completeness is verified for every required Chunk.
- [ ] Step 6.2 can consume the persisted vectors directly.

# Expected Deliverable

Embedding pipeline foundation plus documentation:

```text
docs/ai/
└── step-6.1-embedding-pipeline.md
```

Next Step:

**Step 6.2 — Vector Storage**
