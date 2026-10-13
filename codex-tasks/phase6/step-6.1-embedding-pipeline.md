# Codex Task — Step 6.1 Embedding Pipeline

## Task Identity

**Project:** LLM + RAG Web App học tiếng Trung cho người mới bắt đầu  
**Phase:** 6 — AI / RAG Engineering  
**Step:** 6.1 — Embedding Pipeline  
**Owner:** AI Engineering Specialist  
**Status:** FROZEN / READY FOR CODEX AFTER PM REVIEW  
**Implementation mode:** One Codex task = this Step only

Use the current accepted repository after Step 5.7 and the PM-frozen Step-6.1 decisions below.

Do **not** redesign architecture. Do **not** expand scope. Do **not** run Step 6.2 work in this task.

---

# 1. Source of Truth and Precedence

Primary Step specification:

```text
Phase6/Step-6.1-Embedding-Pipeline.md
```

Also consult only the direct dependency/control files needed for this Step:

```text
PM-Control/00-README-Implementation-Gate.md
PM-Control/04-Decision-Log-and-Open-Gates.md
PM-Control/05-Codex-Execution-Protocol.md
Phase5/Step-5.5-Chunking.md
Phase5/Step-5.6-Pipeline-Orchestration.md
Phase5/Step-5.7-Incremental-and-Reprocessing-Strategy.md
```

The actual accepted repository state and the PM decisions frozen in this task override stale implementation assumptions from older logical specs.

If the repository materially contradicts this frozen task in a way that changes public API, persistent data semantics beyond the authorized migration, Phase-5 lifecycle, retry semantics, provider/model identity, concurrency, the Step-6.1/6.2 boundary, or dependency architecture:

```text
STOP
→ report BLOCKED
→ do not invent a resolution
```

---

# 2. Accepted Repository State

Current Alembic head:

```text
0010_incremental_reprocessing_contract
```

Current accepted persistence already contains:

```text
Embedding
EmbeddingProfile
KnowledgeSource
KnowledgeVersion
Chunk
```

Current physical vector storage already exists:

```text
embeddings.vector
→ pgvector.sqlalchemy.Vector
→ NOT NULL
```

Current exact Embedding uniqueness:

```text
uq_embeddings_chunk_id_embedding_profile_id
UNIQUE(chunk_id, embedding_profile_id)
```

Current `EmbeddingProfile` fields:

```text
id
provider              NOT NULL
model_name            NOT NULL
model_version         NULLABLE
dimensions            NOT NULL
status                NOT NULL
created_at
```

Current profile statuses:

```text
ACTIVE
INACTIVE
```

Current `KnowledgeVersion` statuses:

```text
PROCESSING
ACTIVE
SUPERSEDED
FAILED
```

Current Phase-5 lineage available for reuse includes:

```text
KnowledgeVersion.transformation_run_id
KnowledgeVersion.chunking_strategy
KnowledgeVersion.chunking_version
KnowledgeVersion.chunk_size
KnowledgeVersion.chunk_max_chars
KnowledgeVersion.chunk_overlap

Chunk.chunk_index
Chunk.content
Chunk.content_type
Chunk.content_hash
Chunk.section
Chunk.lesson_id
Chunk.metadata
```

Current concurrency already enforces:

```text
at most one PROCESSING KnowledgeVersion per KnowledgeSource
```

through:

```text
KnowledgeSource row lock
+
uq_knowledge_versions_one_processing_per_source
```

Do not create another source-level lock system.

---

# 3. PM-Frozen Decisions

## 3.1 6.1-D1 — Durable EmbeddingProfile Identity

Implement Option B.

Extend `EmbeddingProfile` with durable semantic identity fields equivalent to:

```text
provider
provider_version
model_name
model_version
dimensions
embedding_input_version
normalize_embeddings
status
```

For the V0 baseline, the complete semantic identity is exactly:

```text
provider                = LOCAL
provider_version        = sentence-transformers/6.1.0
model_name              = BAAI/bge-m3
model_version           = 5617a9f61b028005a4858fdac845db406aefb181
dimensions              = 1024
embedding_input_version = v1
normalize_embeddings    = true
```

New profiles start:

```text
status = INACTIVE
```

`status` is lifecycle state, not semantic identity.

Do not overload `model_version` with unrelated values.

Do not add an `EmbeddingBuild`, profile-config, generic fingerprint, or dependency-graph table.

## 3.2 6.1-D2 — Zero-Chunk KnowledgeVersion

Freeze:

```text
required_chunk_count == 0
→ embedding build failure
→ KnowledgeVersion = FAILED
```

Do not treat:

```text
0 required == 0 embeddings
```

as successful completeness.

Do not reopen Step 5.5 and do not create placeholder Chunks/Embeddings.

---

# 4. Objective

Implement the Step-6.1 pipeline:

```text
persisted canonical Chunk[]
→ EmbeddingInputFormatter/v1
→ SentenceTransformerEmbeddingProvider
→ BAAI/bge-m3 dense normalized vectors
→ validated Embedding rows
```

The normal input is:

```text
KnowledgeVersion(status = PROCESSING)
└── Chunk[]
```

Successful Step-6.1 output is:

```text
KnowledgeVersion(status = PROCESSING)
├── complete Chunk[]
└── exactly one Embedding per required Chunk for the target EmbeddingProfile
```

Step 6.1 does not activate the KnowledgeVersion or a newly created profile.

Mental model:

```text
canonical persisted Chunk
→ deterministic semantic-only model input
→ model-specific length validation
→ dense inference
→ vector validation
→ short durable persistence

embedding complete
≠
retrieval active
```

---

# 5. Step 6.1 / Step 6.2 Boundary

Step 6.1 owns:

```text
EmbeddingProfile semantic identity
EmbeddingProfile exact get-or-create
deterministic embedding input formatting
local dense model inference
length validation
L2-normalized vector generation
vector output validation
Embedding persistence
idempotent batch retry
FAILED embedding retry compatibility
embedding completeness validation
```

Step 6.2 owns later:

```text
vector readiness
technical pgvector query probe
similarity/search primitives
KnowledgeVersion activation
EmbeddingProfile activation/switching
```

Do not implement Step 6.2 in this task.

---

# 6. Authorized Migration Freeze

Create exactly one forward migration:

```text
backend/migrations/versions/0011_embedding_profile_identity.py
```

Freeze:

```text
revision      = "0011_embedding_profile_identity"
down_revision = "0010_incremental_reprocessing_contract"
```

Do not modify migrations `0001`–`0010`.

## 6.1 New columns

Add to `embedding_profiles`:

```text
provider_version        TEXT NULL
embedding_input_version TEXT NULL
normalize_embeddings    BOOLEAN NULL
```

Do not change the existing nullability of:

```text
provider
model_name
model_version
dimensions
status
```

In particular:

```text
model_version remains nullable at DB level
```

because legacy rows may not have provable immutable model revision identity.

Do not backfill guessed historical values.

## 6.2 Semantic identity uniqueness

Add exactly one logical uniqueness constraint:

```text
name:
uq_embedding_profiles_semantic_identity
```

Columns, in this exact order:

```text
provider
provider_version
model_name
model_version
dimensions
embedding_input_version
normalize_embeddings
```

Do not include:

```text
status
created_at
id
```

Legacy rows with NULL semantic fields may remain outside full identity matching.

All new Step-6.1 target profiles must have every semantic identity field populated.

## 6.3 Downgrade

Downgrade must:

```text
drop uq_embedding_profiles_semantic_identity
drop normalize_embeddings
drop embedding_input_version
drop provider_version
```

Do not change vector storage, Chunk schema, KnowledgeVersion status schema, or pgvector installation.

---

# 7. ORM Model Freeze

Update:

```text
backend/app/database/models/knowledge.py
```

`EmbeddingProfile` must expose:

```text
provider                Text NOT NULL
provider_version        Text NULL
model_name              Text NOT NULL
model_version           Text NULL
dimensions              Integer NOT NULL
embedding_input_version Text NULL
normalize_embeddings    Boolean NULL
status                  String NOT NULL
```

Add ORM `UniqueConstraint` matching:

```text
uq_embedding_profiles_semantic_identity
```

Do not modify:

```text
Embedding.vector
Embedding Chunk/Profile uniqueness
Chunk schema
KnowledgeVersion schema/status values
```

---

# 8. Target Profile Semantic Identity

Create a small immutable internal value object equivalent to:

```python
@dataclass(frozen=True)
class EmbeddingProfileIdentity:
    provider: str
    provider_version: str
    model_name: str
    model_version: str
    dimensions: int
    embedding_input_version: str
    normalize_embeddings: bool
```

`status` is deliberately not part of this object.

For this Step the desired identity must resolve exactly to:

```text
LOCAL
sentence-transformers/6.1.0
BAAI/bge-m3
5617a9f61b028005a4858fdac845db406aefb181
1024
v1
true
```

A profile is valid for new Step-6.1 embedding work only when:

```text
all semantic identity fields are non-null
AND
all fields exactly equal the desired identity
AND
status is a valid existing lifecycle value
```

Do not silently treat incomplete legacy profiles as equivalent.

---

# 9. Exact Profile Get-or-Create Behavior

Implement repository functions equivalent to:

```text
get_embedding_profile_by_identity(...)
get_or_create_embedding_profile(...)
```

Repository functions do not commit; transaction ownership stays with the service/application boundary.

Freeze behavior:

```text
exact semantic identity exists
→ return that row unchanged

no exact identity exists
→ insert one row
→ status = INACTIVE

concurrent equivalent insert
→ DB uniqueness is final guard
→ rollback only the failed savepoint/insert attempt
→ re-query the exact semantic identity
→ return the committed row
```

Recommended SQLAlchemy shape:

```text
outer short transaction owned by caller
→ SELECT exact identity
→ if missing, INSERT/flush inside begin_nested() SAVEPOINT
→ on IntegrityError, rollback savepoint automatically
→ SELECT exact identity again
→ if exact row exists, reuse
→ otherwise re-raise the unexpected integrity failure
```

Do not use process-local locks to implement profile uniqueness.

Do not use `status` in the identity query.

Step 6.1 never activates or deactivates a reused profile.

For the initial baseline, a newly created target profile remains:

```text
INACTIVE
```

---

# 10. Dependency Freeze

Add exactly this direct runtime dependency:

```text
sentence-transformers==6.1.0
```

Update:

```text
backend/pyproject.toml
backend/uv.lock
```

Do not add:

```text
LangChain
LlamaIndex
```

Do not add `torch` as a direct dependency unless Step-6.1 production code directly imports `torch`.

If no production import is needed, keep PyTorch transitive through Sentence Transformers.

---

# 11. Configuration Freeze

Update:

```text
backend/app/core/config.py
backend/.env.example
```

Add Settings fields using current pydantic-settings naming/style equivalent to:

```text
embedding_provider       = "local"
embedding_model_name     = "BAAI/bge-m3"
embedding_model_revision = "5617a9f61b028005a4858fdac845db406aefb181"
embedding_device         = "auto"
embedding_batch_size     = 32
embedding_input_version  = "v1"
embedding_normalize      = true
```

Environment variable names must be exactly:

```text
EMBEDDING_PROVIDER
EMBEDDING_MODEL_NAME
EMBEDDING_MODEL_REVISION
EMBEDDING_DEVICE
EMBEDDING_BATCH_SIZE
EMBEDDING_INPUT_VERSION
EMBEDDING_NORMALIZE
```

Validation freeze:

```text
EMBEDDING_PROVIDER
→ supported V0 value: local

EMBEDDING_DEVICE
→ auto | cpu | cuda | mps

EMBEDDING_BATCH_SIZE
→ integer > 0

EMBEDDING_INPUT_VERSION
→ v1 for this implementation

EMBEDDING_NORMALIZE
→ must be true for V0

EMBEDDING_MODEL_NAME
→ BAAI/bge-m3 for V0

EMBEDDING_MODEL_REVISION
→ exact frozen immutable revision for V0
```

Operational values belong in Settings, not scattered service/provider constants.

The provider package version is not an env setting; derive/verify it from the installed `sentence-transformers` package and freeze the persisted value as:

```text
sentence-transformers/6.1.0
```

---

# 12. Provider Boundary Freeze

Create package/module boundaries equivalent to:

```text
backend/app/ai/
backend/app/ai/embeddings/
```

Use an interface equivalent to:

```python
class EmbeddingProvider(Protocol):
    @property
    def identity(self) -> EmbeddingProviderIdentity:
        ...

    @property
    def device(self) -> str:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...
```

Keep `embed_documents` and `embed_query` separate.

Do not expose the SentenceTransformer object outside the concrete provider.

---

# 13. SentenceTransformer Provider Freeze

Implement:

```text
SentenceTransformerEmbeddingProvider
```

Target model:

```text
BAAI/bge-m3
```

Immutable model revision:

```text
5617a9f61b028005a4858fdac845db406aefb181
```

Dense only:

```text
1024 dimensions
normalize_embeddings = true
```

Do not request/store:

```text
sparse vectors
multi-vector output
hybrid output
```

Provider semantic version must be obtained/validated against the installed package and exposed as exactly:

```text
sentence-transformers/6.1.0
```

A dependency/runtime version mismatch must fail safely; do not silently persist a false provider version.

---

# 14. Device Freeze

Supported configuration:

```text
auto
cpu
cuda
mps
```

For:

```text
auto
```

construct SentenceTransformer with library auto-device resolution equivalent to:

```text
device=None
```

The library may select an available accelerator and otherwise CPU.

For an explicitly requested device:

```text
cpu | cuda | mps
```

pass that explicit device.

Do not silently change an explicitly requested device after provider initialization/inference fails.

No CUDA requirement is introduced for the project.

---

# 15. Model Lifecycle Freeze

Provider/model lifecycle:

```text
one cached provider instance per application process
→ model lazy-loads on first actual embedding/tokenizer need
→ same model instance reused for later batches
```

Use a cached factory equivalent to:

```python
@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    ...
```

The concrete provider may keep:

```text
self._model = None
```

until first model access.

Do not load/unload the model per:

```text
Chunk
batch
service iteration
HTTP request
```

There is no public Step-6.1 embedding HTTP route.

Tests must be able to clear/replace the provider cache without downloading the real model.

---

# 16. Model Input Length Validation Freeze

The provider owns model-specific token-length validation.

Before every model encode call:

```text
formatted text
→ tokenizer belonging to the loaded BGE-M3 SentenceTransformer
→ truncation=False
→ add/count model special tokens
→ measure actual tokenized length
→ compare to model.max_seq_length
```

Expected BGE-M3 maximum:

```text
8192
```

If any input is too long:

```text
EMBEDDING_INPUT_TOO_LONG
```

No inference for that batch.

No silent truncation.

Do not use:

```text
Chunk.token_count
```

as BGE-M3 tokenizer truth.

It is acceptable in V0 to tokenize once for explicit validation and then allow SentenceTransformer to tokenize again during `encode()`.

Do not reproduce SentenceTransformer pooling/forward logic manually solely to avoid the second tokenization.

---

# 17. Encode Call Freeze

For document batches, concrete provider behavior must be equivalent to:

```text
model.encode(
    texts,
    batch_size=<current service batch size or equivalent>,
    normalize_embeddings=True,
    show_progress_bar=False,
    ...
)
```

Return plain Python:

```text
list[list[float]]
```

`embed_query(text)` must use the same model/revision/normalization identity and return:

```text
list[float]
```

Do not add query rewriting/instruction logic in Step 6.1.

---

# 18. EmbeddingInputFormatter/v1 Freeze

Implement deterministic formatter version:

```text
v1
```

`Chunk.content` remains canonical persisted source-derived content and must never be mutated.

Use a small typed/internal context equivalent to:

```text
chunk_id
chunk_index
content
content_type
section optional
document_title optional
lesson_id optional
lesson_title optional
hsk_level_number optional
```

## 18.1 DOCUMENT_TEXT

Exact format when section exists:

```text
Title: <document title>
Section: <chunk section>

<Chunk.content>
```

When section is absent:

```text
Title: <document title>

<Chunk.content>
```

## 18.2 VOCABULARY

```text
HSK: <HSKLevel.level_number>
Lesson: <Lesson.title>
Type: VOCABULARY

<Chunk.content>
```

## 18.3 GRAMMAR

```text
HSK: <HSKLevel.level_number>
Lesson: <Lesson.title>
Type: GRAMMAR

<Chunk.content>
```

## 18.4 LESSON_GENERAL

```text
HSK: <HSKLevel.level_number>
Lesson: <Lesson.title>
Type: LESSON_GENERAL

<Chunk.content>
```

## 18.5 Serialization rules

Freeze:

```text
line ending = "\n"
header order = exactly as above
optional Section absent → omit whole Section line
header/content separator = exactly one blank line
metadata label values → strip outer whitespace only
Chunk.content → copy exactly, no strip/rewrite
no forced trailing newline
```

Do not include:

```text
UUIDs
timestamps
storage references
page number
upload metadata
usage-right metadata
database identifiers
arbitrary provenance noise
```

If required semantic context is unavailable or inconsistent, fail the embedding build safely; do not invent a fallback title/HSK/lesson value.

---

# 19. Exact Formatter Repository Joins

Load embedding Chunk context from persisted relationships, not from text matching.

For every target version:

```text
Chunk
→ KnowledgeVersion
→ KnowledgeSource
```

For `DOCUMENT_TEXT`:

```text
KnowledgeSource.document_id
→ Document.id
→ Document.title

Chunk.section
→ optional Section label
```

Required validation:

```text
KnowledgeSource.source_type = DOCUMENT
Document exists
Document.title is non-null/non-blank
Chunk.content_type = DOCUMENT_TEXT
```

For Lesson-derived content:

```text
KnowledgeSource.lesson_id
→ Lesson.id
→ Lesson.title
→ HSKLevel.id
→ HSKLevel.level_number
```

and:

```text
Chunk.lesson_id must match KnowledgeSource.lesson_id
```

Required Lesson types are exactly:

```text
VOCABULARY
GRAMMAR
LESSON_GENERAL
```

Do not query Vocabulary/Grammar entities for formatter prefixes; the canonical structured source content is already in `Chunk.content`.

Repository queries must preserve:

```text
ORDER BY Chunk.chunk_index ASC
```

---

# 20. Embedding Repository Boundary

Create:

```text
backend/app/ai/embeddings/repository.py
```

Keep pgvector/SQLAlchemy persistence queries here.

Required internal primitives equivalent to:

```text
get_embedding_profile_by_identity
get_or_create_embedding_profile

get_version_and_source
lock_version
lock_source
find_processing_version

count_required_chunks
list_chunk_contexts_for_version
list_missing_chunk_contexts_for_profile
list_existing_embedding_profile_ids_for_version
list_existing_embedding_chunk_ids

insert_embeddings_conflict_safe
count_embeddings_for_version_profile
mark_version_failed
```

`insert_embeddings_conflict_safe` must use the PostgreSQL/SQLAlchemy equivalent of:

```sql
INSERT INTO embeddings (...)
VALUES (...)
ON CONFLICT ON CONSTRAINT uq_embeddings_chunk_id_embedding_profile_id
DO NOTHING
```

Freeze the implementation around `sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_nothing(constraint="uq_embeddings_chunk_id_embedding_profile_id")` or the exact repository-equivalent spelling.

Required semantics:

```text
exact Chunk/Profile uniqueness conflict
→ row was already persisted by another caller
→ treat as idempotently persisted/skipped
→ continue

unexpected integrity/database error
→ propagate
→ normal embedding failure handling applies
```

Do not overwrite an existing Embedding. Do not catch-and-ignore arbitrary `IntegrityError`/database errors. The conflict-safe statement handles only the named exact uniqueness conflict.

Exact helper decomposition may differ if it remains small and coherent, but service code must not contain scattered raw persistence SQL.

Do not create a generic multi-backend `VectorStore` abstraction.

---

# 21. Normal Embedding Service Flow

Create:

```text
EmbeddingService
```

with public internal method equivalent to:

```python
async def embed_processing_version(
    self,
    knowledge_version_id: UUID,
) -> EmbeddingBuildResult:
    ...
```

Normal flow:

```text
1. short DB read
   → validate KnowledgeVersion exists and status = PROCESSING
   → validate source relation
   → count required Chunks

2. required == 0
   → D2 zero-chunk failure flow

3. derive desired complete EmbeddingProfile identity
   from Settings + concrete provider identity

4. short DB transaction
   → exact profile get-or-create
   → validate complete semantic identity
   → do NOT activate/deactivate profile

5. repeat until no target-profile Chunk is missing:

   short DB read
   → select next missing Chunk contexts
   → ORDER BY chunk_index ASC
   → LIMIT EMBEDDING_BATCH_SIZE
   → end transaction

   format inputs
   → provider length validation
   → model inference
   → output validation

   short DB transaction
   → lock/re-check KnowledgeVersion still PROCESSING
   → re-check target profile identity
   → re-check which batch Chunk/Profile rows are still missing
   → conflict-safe insert only rows still missing using
     ON CONFLICT ON CONSTRAINT uq_embeddings_chunk_id_embedding_profile_id DO NOTHING
   → exact duplicate conflict counts as idempotent skip, not build failure
   → unexpected DB/integrity errors still fail normally
   → commit

6. short DB read
   → run final completeness query

7. if complete
   → return success result
   → KnowledgeVersion remains PROCESSING
   → profile state unchanged
```

Do not hold the full corpus vectors in memory.

Do not keep a DB transaction open during formatter/model inference.

---

# 22. EmbeddingBuildResult Freeze

Use a small internal result equivalent to:

```text
knowledge_version_id
embedding_profile_id
required_count
embedded_count
embedded_this_run
skipped_count
knowledge_version_status
```

Successful status must report:

```text
knowledge_version_status = PROCESSING
```

No HTTP response schema is required.

---

# 23. Batching Freeze

Config default:

```text
EMBEDDING_BATCH_SIZE=32
```

Load/process chunks:

```text
chunk_index ASC
```

Sequential batches only:

```text
batch 0
→ persist
→ batch 1
→ persist
→ ...
```

Do not add:

```text
parallel model batches
worker pool
Celery
Redis queue
background worker architecture
```

One provider call may vectorize all texts in the current service batch.

---

# 24. Transaction Boundary Freeze

Follow current accepted explicit async SQLAlchemy transaction ownership.

Never hold a DB transaction during:

```text
formatting that does not require DB
model tokenization
model inference
vector numerical validation
```

Per-batch flow:

```text
short DB read
→ transaction ends

format
→ tokenize/length-check
→ infer
→ validate output

short DB write transaction
→ lock/re-check required state
→ re-check existing Chunk/Profile rows
→ persist only still-missing rows
→ commit
```

The pre-insert re-check is an optimization, not the final race-control mechanism. Two callers may both re-check the same Chunk/Profile as missing before either insert commits.

Freeze the final persistence race as:

```text
caller A re-checks → missing
caller B re-checks → missing
caller A inserts
caller B attempts the exact same Chunk/Profile insert
→ PostgreSQL ON CONFLICT ON CONSTRAINT
   uq_embeddings_chunk_id_embedding_profile_id DO NOTHING
→ caller B treats the row as already persisted/skipped
→ neither caller overwrites the row
→ uniqueness race alone must NOT mark KnowledgeVersion FAILED
```

It is acceptable in V0 for both callers to perform duplicate expensive inference before persistence converges. Do not serialize model inference under a DB/process lock merely to avoid duplicate compute.

Unexpected integrity/database errors unrelated to that exact uniqueness conflict must propagate into normal embedding failure handling.

The existing DB unique constraint remains the final integrity authority.

---

# 25. Persistence and Idempotency Freeze

For the exact target profile:

```text
Embedding exists for Chunk/Profile
→ skip

Embedding missing
→ generate
→ attempt conflict-safe persist

exact same Chunk/Profile inserted concurrently
→ ON CONFLICT ON CONSTRAINT
   uq_embeddings_chunk_id_embedding_profile_id
   DO NOTHING
→ treat as already persisted/skipped
→ continue idempotently
```

The repository must not use a generic `except IntegrityError: pass` pattern. Only the named exact Chunk/Profile uniqueness conflict is idempotent; unexpected integrity/database errors remain failures.

Do not overwrite historical Embedding rows.

Do not deduplicate/copy by:

```text
Chunk.content_hash
```

Do not add:

```text
global embedding cache
content-hash vector table
cross-version vector-copy optimization
```

---

# 26. Output Validation Freeze

Before any Embedding row is persisted, validate the complete provider result.

Required checks:

```text
output vector count == input count

for every vector:
    len(vector) == EmbeddingProfile.dimensions == 1024
    every component is finite
    no NaN
    no Inf
```

Because V0 requires normalized output, also check:

```text
abs(L2_norm(vector) - 1.0) <= 1e-3
```

Invalid provider output:

```text
INVALID_EMBEDDING_OUTPUT
```

Do not persist any malformed vector from the failed batch.

Use standard-library numerical checks where sufficient; do not add a new dependency solely for validation.

---

# 27. Partial Failure Freeze

If a later batch fails:

```text
previous successful committed batches
→ keep

failed current batch
→ persist none of its malformed/failed output

remaining batches
→ stop

KnowledgeVersion PROCESSING
→ FAILED
```

Mark failure in a separate short transaction.

Do not delete Embeddings from earlier successful batches.

Do not delete the failed KnowledgeVersion.

Do not activate anything.

---

# 28. Zero-Chunk Failure Freeze

Before profile creation/model inference, compute:

```text
required_chunk_count
```

If:

```text
required_chunk_count == 0
```

then:

```text
KnowledgeVersion PROCESSING → FAILED
```

and raise/use:

```text
EMBEDDING_BUILD_FAILED
```

with safe internal detail equivalent to:

```text
reason = ZERO_REQUIRED_CHUNKS
```

Recommended application status code if surfaced internally through the shared contract:

```text
409
```

No new public HTTP error/endpoint is introduced.

---

# 29. Completeness Freeze

Final completeness is database-derived.

Required count:

```sql
COUNT(chunks)
WHERE chunks.knowledge_version_id = :target_version
```

Embedded count:

```sql
COUNT(embeddings)
JOIN chunks ON chunks.id = embeddings.chunk_id
WHERE chunks.knowledge_version_id = :target_version
  AND embeddings.embedding_profile_id = :target_profile
```

Success requires both:

```text
required_count > 0
AND
required_count == embedded_count
```

Do not count unrelated historical profiles.

Do not infer completeness from:

```text
last batch succeeded
```

or from provider-call counts.

---

# 30. FAILED Retry Public Internal Boundary

Provide explicit retry method equivalent to:

```python
async def retry_failed_version(
    self,
    knowledge_version_id: UUID,
    *,
    reprocessing_planner: ReprocessingPlanner,
) -> EmbeddingBuildResult:
    ...
```

Do not make FAILED retry an implicit side effect of `embed_processing_version()`.

The planner is injected for mismatch handoff; do not duplicate Step-5.7 invalidation policy inside the embedding module.

---

# 31. FAILED Retry Claim Freeze

Retry claim must use the accepted source-level serialization boundary.

Equivalent transaction:

```text
BEGIN

load FAILED KnowledgeVersion
→ resolve exact KnowledgeSource
→ SELECT KnowledgeSource ... FOR UPDATE
→ SELECT/lock exact KnowledgeVersion

ensure no PROCESSING KnowledgeVersion currently exists for the same source

validate retry compatibility

if compatible:
    FAILED → PROCESSING
    flush

COMMIT
```

Then run inference outside the transaction.

If another build is already PROCESSING:

```text
PROCESSING_ALREADY_IN_PROGRESS
```

Do not add:

```text
advisory lock system
new lock table
long-lived transaction
```

The existing partial unique PROCESSING constraint remains defense-in-depth.

---

# 32. FAILED Retry Compatibility Freeze

In-place retry is permitted only when all of the following can be proven from current durable state.

## 32.1 Source identity

For DOCUMENT:

```text
KnowledgeSource.document_id
→ Document.content_hash

KnowledgeVersion.transformation_run_id
→ TransformationRun
→ ParsingRun.raw_content_hash

current Document.content_hash
==
ParsingRun.raw_content_hash
```

Also require the Document's current approved transformed lineage to still point to the exact failed candidate transformation run where applicable:

```text
Document.approved_transformation_run_id
==
KnowledgeVersion.transformation_run_id
```

For LESSON:

```text
current canonical lesson snapshot
→ SHA-256
==
ParsingRun.raw_content_hash for the candidate lineage
```

Lesson must still be `PUBLISHED`.

## 32.2 Transformation lineage

Require:

```text
KnowledgeVersion.transformation_run_id is non-null
TransformationRun exists
TransformationRun.status = SUCCEEDED
TransformationRun.error_code is null
TransformationRun source matches KnowledgeSource
TransformationRun.parsing_run_id resolves to a valid ParsingRun
```

Persisted parser/cleaning/transformation identities must still match the current accepted processor identities used by Step 5.7.

Do not invent a second processor-version scheme.

## 32.3 Chunking config

Candidate KnowledgeVersion must exactly match current:

```text
DEFAULT_CHUNKING_CONFIG.strategy
DEFAULT_CHUNKING_CONFIG.version
DEFAULT_CHUNKING_CONFIG.target_chars
DEFAULT_CHUNKING_CONFIG.max_chars
DEFAULT_CHUNKING_CONFIG.overlap_chars
```

through the accepted fields:

```text
chunking_strategy
chunking_version
chunk_size
chunk_max_chars
chunk_overlap
```

No NULL required field is compatible for in-place retry.

## 32.4 Ordered Chunk set/content

Load candidate Chunks:

```text
ORDER BY chunk_index ASC
```

Require:

```text
at least one Chunk
contiguous indexes 0..N-1
content_hash non-null for every Chunk
recomputed accepted Step-5.5 content hash == persisted content_hash
metadata/provenance validates using accepted ChunkMetadata where required
```

Do not use text matching for provenance.

## 32.5 Exact previous target EmbeddingProfile proof

The candidate must have durable evidence that its failed embedding attempt targeted the same semantic profile now requested.

Conservative V0 proof:

```text
there is at least one persisted Embedding row
for a Chunk belonging to this failed KnowledgeVersion
```

and:

```text
all persisted Embedding rows for this candidate's Chunk set
reference exactly one EmbeddingProfile
```

and that profile's complete semantic identity exactly equals the current desired profile identity.

Why this rule exists:

```text
if a previous embedding failure happened before any Embedding row was committed,
the current schema has no durable KnowledgeVersion → EmbeddingProfile attempt pointer.
Do not guess which profile that failed attempt used.
```

Therefore:

```text
zero persisted Embedding rows on a FAILED candidate
→ profile identity of the previous failed attempt cannot be proven
→ do NOT retry that candidate in place
→ conservatively classify profile compatibility as unproven
→ use ReprocessingPlanner handoff with:
   embedding_profile_changed = true
   embedding_input_changed = false
```

This is a conservative compatibility failure at the embedding-profile boundary. It does **not** claim that a particular persisted profile field was observed to change.

This intentionally avoids adding a forbidden build table or changing KnowledgeVersion schema.

Do not infer old profile identity from current runtime configuration alone.

---

# 33. Compatible FAILED Retry Execution

When compatibility is fully proven:

```text
FAILED
→ claim under KnowledgeSource lock
→ PROCESSING
→ commit

then
→ run normal missing-embedding loop
→ skip already persisted target Chunk/Profile rows
→ embed only missing rows
```

If retry succeeds:

```text
KnowledgeVersion remains PROCESSING
```

If retry fails again:

```text
KnowledgeVersion → FAILED
```

Existing successful rows remain.

---

# 34. ReprocessingPlanner Handoff on Retry Mismatch

Do not transition the FAILED version when compatibility fails.

Exit/rollback the retry-claim transaction with the candidate still:

```text
FAILED
```

Then call the existing injected:

```text
ReprocessingPlanner.plan_source(...)
```

outside the source-lock transaction.

Map embedding identity mismatch flags to existing policy only:

```text
only embedding_input_version differs
→ embedding_profile_changed = false
→ embedding_input_changed = true

known provider / provider_version / model_name / model_version /
dimensions / normalize_embeddings mismatch
→ embedding_profile_changed = true
→ embedding_input_changed = false

previous embedding target identity is unprovable because the FAILED
candidate has zero persisted Embedding rows
→ embedding_profile_changed = true   # conservative compatibility failure
→ embedding_input_changed = false
→ reuse existing embedding-profile-change reason

source / parser / cleaning / transformation / chunk lineage differs
→ embedding_profile_changed = false
→ embedding_input_changed = false
→ let existing Step-5.7 lineage policy determine earliest stale stage
```

For the zero-persisted-row case, `ReprocessingPlanner.plan_source(...)` must therefore use the existing embedding-profile-change policy path and return/use:

```text
ReprocessingAction.FROM_EMBED
ReprocessingReason.EMBEDDING_PROFILE_CHANGED
```

according to the current planner contract. Do not invent a new reason solely for "unknown previous profile".

Do not execute the returned reprocessing plan in Step 6.1.

Return/raise the existing Step-6.1 mismatch error:

```text
EMBEDDING_FINGERPRINT_MISMATCH
```

with safe details equivalent to:

```text
reprocessing_action
reprocessing_reason
```

The authoritative action/reason comes from `ReprocessingPlanner`.

Do not create another invalidation enum/engine.

---

# 35. Error Freeze

Use the existing shared:

```text
ApplicationError
```

No new public endpoint is added.

Required Step-6.1 codes are exactly/equivalent to:

```text
EMBEDDING_PROFILE_INVALID
KNOWLEDGE_VERSION_NOT_PROCESSING
EMBEDDING_INPUT_TOO_LONG
EMBEDDING_PROVIDER_FAILED
INVALID_EMBEDDING_OUTPUT
EMBEDDING_BUILD_FAILED
EMBEDDING_FINGERPRINT_MISMATCH
PROCESSING_ALREADY_IN_PROGRESS   # existing project error
```

Recommended status semantics:

```text
EMBEDDING_PROFILE_INVALID          409
KNOWLEDGE_VERSION_NOT_PROCESSING   409
EMBEDDING_INPUT_TOO_LONG           422
EMBEDDING_PROVIDER_FAILED          500
INVALID_EMBEDDING_OUTPUT           500
EMBEDDING_BUILD_FAILED             500 normally; zero-Chunk state may use 409
EMBEDDING_FINGERPRINT_MISMATCH     409
PROCESSING_ALREADY_IN_PROGRESS     409
```

Do not expose raw model/library/database exception strings as API-safe messages/details.

Do not add error classes merely for visual symmetry; stable `ApplicationError` codes are sufficient.

---

# 36. Failure-State Ownership

`EmbeddingService` owns marking a confirmed PROCESSING embedding build `FAILED` when the embedding stage fails after eligibility has been established.

Use a separate short transaction equivalent to the accepted Phase-5 failure helper pattern.

Do not mark an arbitrary non-PROCESSING version FAILED merely because a caller supplied a bad ID/status.

Eligibility failure:

```text
version missing / not PROCESSING
→ KNOWLEDGE_VERSION_NOT_PROCESSING
→ do not mutate state
```

Zero Chunk is different:

```text
version is PROCESSING
but required Chunk set is empty
→ embedding build failure
→ mark FAILED
```

---

# 37. Structured Logging Freeze

Use current Python `logging` with structured `extra` fields.

Log Step-6.1 events with fields equivalent to:

```text
knowledge_version_id
embedding_profile_id
model_name
model_version
batch_index
batch_size
duration_ms
embedded_count
skipped_count
device
status
error_code optional
```

Retry mismatch logs may additionally include safe:

```text
reprocessing_action
reprocessing_reason
```

Do not log:

```text
full Chunk.content
full formatted embedding input
full vector values
raw provider exception body if sensitive/unbounded
```

---

# 38. Default Test Strategy

All normal/default tests must use fake/mock provider behavior.

Normal tests must not:

```text
download BAAI/bge-m3
require network access
require CUDA/MPS
load the real multi-GB model
```

A real-model smoke test is optional and is **not required** by this task.

If one is added, it must be explicitly opt-in/slow and excluded from normal CI/default `pytest` execution.

---

# 39. Migration Tests

Add focused tests for `0011_embedding_profile_identity` covering:

```text
0010 → 0011 forward upgrade
legacy existing EmbeddingProfile row survives
new semantic columns on legacy row remain NULL
no fake historical identity backfill
full baseline profile can be inserted
duplicate complete semantic identity is rejected by DB uniqueness
status difference does not permit duplicate semantic identity
different embedding_input_version is a different semantic identity
different normalize_embeddings is a different semantic identity
0011 downgrade removes only the Step-6.1 identity columns/constraint
```

Do not rewrite old migration tests to hide regressions.

---

# 40. Config Tests

Extend current Settings tests for:

```text
embedding defaults
provider allowed values
device auto/cpu/cuda/mps
invalid device rejected
batch size > 0
model name/revision V0 validation
input version v1 validation
normalization true requirement
.env.example contains names only and no secrets
```

Add new env names to test-environment cleanup where needed so host env cannot contaminate tests.

---

# 41. Profile Repository Tests

Cover:

```text
complete profile identity is required for target work
legacy nullable row is readable
legacy nullable row is never exact-match for V0 target
exact identity lookup/reuse returns same row
new exact identity creates INACTIVE row
status excluded from identity
concurrent equivalent get-or-create produces one semantic profile row
unexpected IntegrityError is not swallowed
```

---

# 42. Formatter Tests

Assert exact byte/string-equivalent formatting for:

```text
DOCUMENT_TEXT with Section
DOCUMENT_TEXT without Section
VOCABULARY
GRAMMAR
LESSON_GENERAL
```

Also test:

```text
fixed metadata line order
metadata outer whitespace stripped
Chunk.content leading/trailing whitespace remains unchanged
no forced trailing newline
missing required Document title fails
missing/mismatched Lesson relation fails
Chunk.lesson_id mismatch fails for Lesson-derived type
no UUID/page/storage/provenance noise is added
```

---

# 43. Provider Tests

Use a fake/monkeypatched SentenceTransformer object.

Cover:

```text
provider exposes frozen semantic identity
provider package version is sentence-transformers/6.1.0
model name/revision passed exactly
model is lazy-loaded
model loaded only once per provider
cached provider factory reuses provider
cache can be reset in tests

auto device passes library auto-resolution equivalent to device=None
explicit cpu/cuda/mps is passed through

actual model tokenizer is used for length validation
truncation=False
special tokens counted
exact max length accepted
max + 1 rejected with EMBEDDING_INPUT_TOO_LONG
encode not called after length failure

normalize_embeddings=True
1024 output shape accepted by service validation
embed_documents and embed_query remain distinct methods
provider exceptions map to EMBEDDING_PROVIDER_FAILED safely
```

No real model/network in default tests.

---

# 44. Embedding Service Tests

Use fake provider + dedicated test DB.

Cover at minimum:

## Eligibility / zero Chunk

```text
missing/non-PROCESSING version rejected without mutation
PROCESSING version with zero Chunks
→ EMBEDDING_BUILD_FAILED
→ FAILED
```

## Ordering / batching

```text
Chunks are consumed chunk_index ASC
batch default 32
configured batch size honored
batches run sequentially
```

## Transaction boundary

Use a fake provider callback/assertion proving:

```text
session.in_transaction() is false
```

while model inference executes.

## Persistence/idempotency

```text
existing exact Chunk/Profile row skipped
missing row inserted
writer re-check avoids unnecessary duplicate writes when visible
named ON CONFLICT DO NOTHING closes the remaining concurrent insert race
exact duplicate conflict is treated as already persisted/skipped
unique constraint remains final integrity authority
unrelated historical profile rows do not satisfy target completeness
```

Add an explicit normal-build concurrency test using two DB sessions/callers for the same already-PROCESSING KnowledgeVersion, same target profile, and same missing Chunk. Arrange the callers so both can reach the persistence race after inference.

Assert:

```text
both callers may infer
exactly one Embedding row exists afterward
duplicate exact insert is idempotent
KnowledgeVersion is NOT marked FAILED because of the uniqueness race
DB-derived final completeness can still succeed
```

Also test that an unexpected `IntegrityError`/database error not representing `uq_embeddings_chunk_id_embedding_profile_id` is not swallowed and follows normal embedding failure handling.

## Partial failure

With more than one batch:

```text
batch 1 succeeds + commits
batch 2 fails
batch 1 rows remain
batch 2 malformed rows absent
version becomes FAILED
```

## Output validation

Reject:

```text
wrong output count
wrong dimension
NaN
Inf
L2 norm outside 1e-3 tolerance
```

## Completeness

```text
required > 0 is mandatory
required == target-profile embedded count is mandatory
last-batch success alone is insufficient
```

## Final state

Successful normal build:

```text
KnowledgeVersion remains PROCESSING
new profile remains INACTIVE
```

No activation code is called.

---

# 45. FAILED Retry Tests

Create tests for compatible and incompatible retry.

## 45.1 Compatible partial retry

Seed:

```text
FAILED KnowledgeVersion
valid unchanged source/transformation/chunk lineage
non-empty valid ordered Chunk set
complete target EmbeddingProfile identity
at least one already persisted target-profile Embedding
some target-profile Embeddings missing
```

Assert:

```text
KnowledgeSource is used as concurrency claim boundary
FAILED → PROCESSING
existing target rows skipped
missing rows embedded
completion succeeds
version remains PROCESSING
```

## 45.2 Source identity changed

Assert:

```text
no FAILED → PROCESSING transition
ReprocessingPlanner called
EMBEDDING_FINGERPRINT_MISMATCH returned
planner action/reason reported safely
```

## 45.3 Transformation/chunk identity changed

Cover at least:

```text
transformation lineage mismatch
chunking config mismatch
chunk set/order mismatch
chunk content_hash mismatch
```

Each must refuse in-place reuse and hand off to planner.

## 45.4 Embedding identity changed

Cover:

```text
provider changed
provider_version changed
model_name/model_version changed
dimensions changed
embedding_input_version changed
normalize_embeddings changed
```

Only input-version-only mismatch sets:

```text
embedding_input_changed = true
```

Other semantic profile mismatches set:

```text
embedding_profile_changed = true
```

## 45.5 No persisted embedding proof

Seed:

```text
FAILED KnowledgeVersion
valid unchanged source lineage
valid unchanged transformation lineage
valid unchanged chunking config
valid non-empty ordered Chunk set/content
zero persisted Embedding rows for the candidate
```

Assert exactly:

```text
previous target profile cannot be proven
FAILED version is NOT transitioned to PROCESSING
candidate remains FAILED

ReprocessingPlanner.plan_source(...) is called with the equivalent of:
embedding_profile_changed = true
embedding_input_changed = false

planner returns/uses:
ReprocessingAction.FROM_EMBED
ReprocessingReason.EMBEDDING_PROFILE_CHANGED

EmbeddingService does NOT execute FROM_EMBED
EMBEDDING_FINGERPRINT_MISMATCH is returned/reported
with safe planner action/reason detail
```

Do not infer previous profile from current Settings and do not invent a separate "unknown profile" reason.

Retain distinct assertions for:

```text
input-version-only mismatch
→ embedding_profile_changed = false
→ embedding_input_changed = true

known profile mismatch
→ embedding_profile_changed = true
→ embedding_input_changed = false

upstream source/parser/cleaning/transform/chunk mismatch
→ embedding_profile_changed = false
→ embedding_input_changed = false
→ existing upstream lineage policy chooses earliest stale stage
```

## 45.6 Concurrent retry

Two sessions retry the same FAILED source.

Freeze result:

```text
one claimant may transition FAILED → PROCESSING
other claimant sees existing PROCESSING state
→ PROCESSING_ALREADY_IN_PROGRESS
```

No duplicate replacement version/profile is created.

---

# 46. FROM_EMBED Integration Freeze

Reuse existing:

```text
ReprocessingAction.FROM_EMBED
ReprocessingReason.EMBEDDING_PROFILE_CHANGED
ReprocessingReason.EMBEDDING_INPUT_CHANGED
```

Do not modify the dependency graph or invent a new action.

Step 6.1 may call `ReprocessingPlanner.plan_source()` only as the authoritative mismatch handoff described above.

For a FAILED candidate with otherwise valid upstream/chunk lineage but zero persisted Embedding rows, freeze the planner inputs as:

```text
embedding_profile_changed = true
embedding_input_changed = false
```

and use the existing `FROM_EMBED` / `EMBEDDING_PROFILE_CHANGED` path. This is conservative compatibility handling, not evidence that a specific persisted profile field changed.

Step 6.1 must not execute:

```text
FROM_PARSE
FROM_TRANSFORM
FROM_CHUNK
FROM_EMBED
```

plans itself.

Execution remains with accepted ingestion/reprocessing boundaries.

---

# 47. No Public API Work

Do not create:

```text
POST /embeddings
POST /embed
GET /embeddings
```

or any equivalent public/admin embedding endpoint.

Step 6.1 is an internal application/data pipeline capability.

Do not expose provider internals or vectors through existing APIs.

---

# 48. Expected Files

Create/update only files required by this Step, expected equivalent to:

```text
backend/pyproject.toml
backend/uv.lock
backend/.env.example

backend/app/core/config.py
backend/app/database/models/knowledge.py
backend/migrations/versions/0011_embedding_profile_identity.py

backend/app/ai/__init__.py
backend/app/ai/embeddings/__init__.py
backend/app/ai/embeddings/provider.py
backend/app/ai/embeddings/sentence_transformer_provider.py
backend/app/ai/embeddings/formatter.py
backend/app/ai/embeddings/repository.py
backend/app/ai/embeddings/service.py

backend/tests/test_config.py
backend/tests/test_step61_embedding_profile_migration.py
backend/tests/test_step61_embedding_formatter.py
backend/tests/test_step61_embedding_provider.py
backend/tests/test_step61_embedding_service.py

docs/ai/step-6.1-embedding-pipeline.md
```

Use the project-level `docs/ai/` path frozen by the Step specification.

Do not create empty `schemas.py`, `errors.py`, or abstraction files solely for symmetry if the existing `ApplicationError` and small internal dataclass/value objects are sufficient.

Do not modify ingestion/orchestration production files unless the frozen behavior cannot be implemented through the existing public/internal boundaries; report any such need explicitly in the completion report.

---

# 49. Scope Guardrails

Do not implement:

```text
Step 6.2
vector readiness
similarity search
semantic retrieval
metadata filtering
reranking
prompt construction
LLM generation
RAG orchestration
conversation memory
citations
sparse BGE-M3
multi-vector BGE-M3
global embedding cache
cross-version vector copying
parallel model workers
Celery
Redis queue
new microservice
KnowledgeVersion activation
EmbeddingProfile activation
new public embedding endpoint
Phase-5 redesign
```

Do not change:

```text
Embedding.vector type
Chunk schema
KnowledgeVersion status enum/check
Phase-5 source/version lifecycle schema
pgvector installation
```

except the explicitly authorized `EmbeddingProfile` identity migration.

---

# 50. Acceptance Criteria

Implementation is acceptable only when all are true:

- [ ] Current Alembic `0010` state was inspected before edits.
- [ ] Migration `0011_embedding_profile_identity` is forward-only from `0010_incremental_reprocessing_contract`.
- [ ] Only `EmbeddingProfile` semantic identity columns/constraint are added by `0011`.
- [ ] Legacy profile rows are not given guessed identity values.
- [ ] Target new embedding profiles require complete semantic identity.
- [ ] `uq_embedding_profiles_semantic_identity` excludes status.
- [ ] Concurrent equivalent profile creation resolves to one logical row.
- [ ] `sentence-transformers==6.1.0` is direct/pinned.
- [ ] No direct torch dependency exists unless production code directly imports torch.
- [ ] BAAI/bge-m3 exact immutable revision is used.
- [ ] Dense output only, 1024 dimensions.
- [ ] Normalization is true and part of profile identity.
- [ ] `EmbeddingInputFormatter/v1` exact deterministic formats are implemented.
- [ ] `Chunk.content` is never mutated/re-written.
- [ ] Formatter context comes from exact persisted source relationships.
- [ ] Provider document/query methods remain separate.
- [ ] Model is lazy-loaded once and reused per process/provider lifecycle.
- [ ] `auto` device uses library auto-resolution; CPU remains safe fallback.
- [ ] Provider validates actual tokenizer length with no silent truncation.
- [ ] `Chunk.token_count` is not used as model-length truth.
- [ ] Batches are configurable, baseline 32, ordered by `chunk_index`, sequential only.
- [ ] No DB transaction spans model inference.
- [ ] Existing exact Chunk/Profile Embeddings are skipped.
- [ ] Batch writer re-checks existence before insert.
- [ ] Normal Embedding persistence uses `ON CONFLICT ON CONSTRAINT uq_embeddings_chunk_id_embedding_profile_id DO NOTHING` or the frozen repository-equivalent SQLAlchemy statement.
- [ ] A concurrent exact Chunk/Profile duplicate insert is treated as idempotently already persisted and does not by itself mark KnowledgeVersion FAILED.
- [ ] Unexpected integrity/database errors are not swallowed by the duplicate-conflict path.
- [ ] A normal two-caller persistence-race test proves convergence to exactly one Chunk/Profile row and DB-derived completeness.
- [ ] Partial successful batches survive later failure.
- [ ] Embedding-stage failure marks eligible PROCESSING version FAILED.
- [ ] Zero Chunk version fails and becomes FAILED.
- [ ] Vector count/dimension/finite/norm validation runs before persistence.
- [ ] Completeness requires `required > 0` and exact target-profile row coverage.
- [ ] Safe FAILED in-place retry proves source/transformation/chunk/profile identity.
- [ ] FAILED retry with no persisted target-profile evidence is conservatively rejected and handed to planner with `embedding_profile_changed=true` and `embedding_input_changed=false`.
- [ ] Zero-persisted-row FAILED retry uses the existing `FROM_EMBED` / `EMBEDDING_PROFILE_CHANGED` policy path, leaves the candidate FAILED, and reports `EMBEDDING_FINGERPRINT_MISMATCH` without executing reprocessing.
- [ ] Input-version-only, known profile mismatch, unknown zero-row profile compatibility, and upstream-lineage mismatch planner flags are tested as distinct cases.
- [ ] Compatible FAILED retry transitions under existing source lock to PROCESSING and embeds only missing rows.
- [ ] Concurrent FAILED retry returns existing `PROCESSING_ALREADY_IN_PROGRESS` behavior.
- [ ] Retry mismatch delegates stale-stage decision to existing ReprocessingPlanner.
- [ ] No second invalidation engine/action enum is created.
- [ ] Successful Step 6.1 leaves KnowledgeVersion PROCESSING.
- [ ] Step 6.1 never activates an EmbeddingProfile.
- [ ] No retrieval/search/reranking/LLM/activation work is implemented.
- [ ] Normal tests do not download/load the real model.
- [ ] Step Note and actually-used Concepts/Tools are updated after implementation.

---

# 51. Verification Commands

Run from:

```text
backend/
```

Dependency/lock validation:

```bash
uv lock --check
```

Migration validation against the dedicated test database/environment used by the repository:

```bash
uv run alembic upgrade head
```

Focused Step-6.1 tests:

```bash
uv run pytest \
  tests/test_step61_embedding_profile_migration.py \
  tests/test_step61_embedding_formatter.py \
  tests/test_step61_embedding_provider.py \
  tests/test_step61_embedding_service.py
```

Relevant Phase-5 regression tests:

```bash
uv run pytest \
  tests/test_step55_chunking.py \
  tests/test_step55_chunking_service.py \
  tests/test_step56_document_pipeline.py \
  tests/test_step56_lesson_pipeline.py \
  tests/test_step56_orchestration_concurrency.py \
  tests/test_step57_reprocessing_planner.py \
  tests/test_step57_reprocessing_execution.py \
  tests/test_step57_reprocessing_concurrency.py
```

Full backend regression suite:

```bash
uv run pytest
```

Import/bytecode sanity:

```bash
uv run python -m compileall app
```

Do not claim checks passed unless actually executed and successful.

Do not run a real-model/network smoke test as part of default verification.

---

# 52. Step Note Deliverable

After implementation, create/update the actual project Step Note at the established docs path with at least:

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

with:

```text
profile identity
=
provider
+ provider version
+ model name/revision
+ dimensions
+ input format version
+ normalization behavior
```

## Core Knowledge

Capture only concepts actually implemented, especially:

```text
dense embeddings
model/profile identity
embedding input versioning
model revision pinning
L2 normalization
idempotency
partial failure
short transaction boundary
processing lineage
safe retry proof
```

## Data Flow

Document/Lesson persisted source relationships:

```text
KnowledgeVersion
→ Chunk[]
→ formatter context
→ BGE-M3
→ Embedding[]
```

## Key Design Decisions

Include:

```text
local BGE-M3 baseline
exact sentence-transformers pin
immutable HF revision
explicit EmbeddingProfile semantic identity
no silent truncation
batch persistence
no global vector cache
no activation in Step 6.1
```

## Reusable Approach

Explain that expensive derived ML artifacts should always carry enough durable semantic identity to prove whether reuse is safe after model/input/config changes.

## Common Mistakes

Include:

```text
using model name without immutable revision
mixing formatter versions under one profile
holding DB transaction during inference
silently truncating model input
using Chunk.token_count across models
overwriting old embeddings
assuming final batch success means corpus completeness
retrying FAILED work without durable compatibility proof
```

## Definition of Done

Reflect actual implementation/test evidence, not only this task text.

---

# 53. Concepts Discovered — Expected Classification

Add only if actually used in implementation.

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

Do not add concepts that were only discussed but not implemented.

---

# 54. Tools Used — Expected Classification

Add only if actually present in implementation.

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| BAAI/bge-m3 | AI | 6.1 | V0 multilingual dense embedding model |
| sentence-transformers | AI | 6.1 | Local model/tokenizer inference library |
| PostgreSQL + pgvector | BOTH | 6.1 | Durable vector persistence already used by the project |
| SQLAlchemy async | DE | 6.1 | Async persistence, transactions, locks, and completeness queries |
| Alembic | DE | 6.1 | Forward migration for durable EmbeddingProfile semantic identity |

Add PyTorch as a direct Tool entry only if project code directly imports/uses it rather than merely receiving it transitively through Sentence Transformers.

---

# 55. Before Editing

First return a concise implementation plan containing:

```text
files to inspect/change
migration/schema change
provider/profile interfaces
retry/concurrency approach
test plan
any blocker found
```

If a material blocker exists, stop and report it.

If no blocker exists, proceed in the same Codex task.

---

# 56. Completion Report Required from Codex

Return exactly enough evidence for specialist review:

```text
Status: DONE | PARTIAL | BLOCKED

What changed
Files changed
Migration/schema changes
Dependency/lock changes
Provider/model identity implemented
Formatter behavior implemented
Retry/concurrency behavior implemented
Tests/checks run + exact results
Acceptance criteria checklist
Deviations from frozen task
Risks/follow-up
```

Explicitly report whether:

```text
0011 is current migration head
sentence-transformers is exactly 6.1.0
no direct torch dependency was added (or why it was required)
normal tests avoided real model/network
KnowledgeVersion remains PROCESSING on success
new target profile remains INACTIVE
no Step-6.2 work was implemented
```

---

# 57. Final Non-Goals

Do not use this task to optimize beyond measured V0 needs.

Specifically do not add:

```text
ANN index
HNSW
IVFFlat
hybrid sparse+dense BGE-M3
multi-vector retrieval
cross-version embedding reuse
background workers
model server
hosted embedding provider
multi-provider routing
GPU-specific project architecture
```

Production hosting/runtime profiling remains a later evidence gate.

---

# 58. Final Task Boundary

This Codex task ends when:

```text
0011 profile identity is implemented
+
BAAI/bge-m3 local provider boundary exists
+
formatter v1 exists
+
PROCESSING KnowledgeVersion can produce complete validated target-profile Embeddings
+
partial failure/retry semantics are tested
+
zero Chunk fails safely
+
all required tests/regressions pass
+
Step documentation reflects actual implementation
```

It does **not** end with retrieval readiness or activation.

Next Step is decided only by PM after specialist review and Step-6.1 acceptance.
