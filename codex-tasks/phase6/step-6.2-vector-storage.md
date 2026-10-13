# Codex Task — Step 6.2 Vector Storage

## Task Identity

**Project:** LLM + RAG Web App học tiếng Trung cho người mới bắt đầu  
**Phase:** 6 — AI / RAG Engineering  
**Step:** 6.2 — Vector Storage  
**Owner:** AI Engineering Specialist  
**Status:** FROZEN / READY_FOR_PM_TASK_REVIEW  
**Execution gate:** Do not run Codex until PM explicitly approves this task  
**Implementation mode:** One Codex task = this Step only

Use the current accepted repository after Step 6.1 and the PM-frozen Step-6.2 decision below.

Do **not** redesign architecture. Do **not** expand scope. Do **not** run Step 6.3 work in this task.

---

# 1. Source of Truth and Precedence

Primary Step specification:

```text
Phase6/Step-6.2-Vector-Storage.md
```

Also consult only the direct dependency/control files needed for this Step:

```text
PM-Control/00-README-Implementation-Gate.md
PM-Control/04-Decision-Log-and-Open-Gates.md
PM-Control/05-Codex-Execution-Protocol.md
Phase5/Step-5.6-Pipeline-Orchestration.md
Phase5/Step-5.7-Incremental-and-Reprocessing-Strategy.md
Phase6/Step-6.1-Embedding-Pipeline.md
```

The actual accepted repository state and the PM decision frozen in this task override stale implementation assumptions from older logical specs.

If the repository materially contradicts this frozen task in a way that changes global embedding-space semantics, bootstrap cohort semantics, Step-6.3 retrieval assumptions, persistent schema beyond the authorized `0012` migration, activation concurrency, or profile/version coherence:

```text
STOP
→ report BLOCKED
→ do not invent a resolution
```

---

# 2. Accepted Repository State

Current Alembic head:

```text
0011_embedding_profile_identity
```

Step 6.1 is DONE / CLOSED.

Current accepted persistence includes:

```text
KnowledgeSource
KnowledgeVersion
Chunk
EmbeddingProfile
Embedding
```

Current vector storage:

```text
Embedding.vector
→ pgvector.sqlalchemy.Vector()
→ NOT NULL
→ variable dimension
```

The pgvector extension is already migration-managed from `0001_initial_schema`.

Current Embedding uniqueness:

```text
uq_embeddings_chunk_id_embedding_profile_id
UNIQUE(chunk_id, embedding_profile_id)
```

Current Embedding schema does **not** have a profile-first index.

Current `EmbeddingProfile` semantic identity:

```text
provider
provider_version
model_name
model_version
dimensions
embedding_input_version
normalize_embeddings
```

Profile lifecycle statuses:

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

Current database already enforces:

```text
max one ACTIVE KnowledgeVersion per KnowledgeSource
max one PROCESSING KnowledgeVersion per KnowledgeSource
```

Current Phase-5 / Step-6.1 concurrency primitives include source/version row locking. Reuse them. Do not introduce another lock system.

Step 6.1 guarantees on successful build:

```text
KnowledgeVersion = PROCESSING
required Chunk count > 0
exactly one validated Embedding per required Chunk
for the target EmbeddingProfile
new target profile remains INACTIVE
```

Do not regenerate embeddings in this Step.

---

# 3. PM-Frozen Decision — 6.2-D1

Use Option A.

V0 production has:

```text
0 or 1 ACTIVE EmbeddingProfile globally
```

After initial bootstrap, normal retrieval operation expects:

```text
exactly 1 ACTIVE EmbeddingProfile
```

Core invariant:

```text
ACTIVE KnowledgeVersion
+
ACTIVE EmbeddingProfile
+
complete technically-ready Embeddings for that exact pair
```

must hold for production knowledge after bootstrap.

Do **not** add:

```text
KnowledgeVersion.embedding_profile_id
```

Do **not** support mixed active embedding spaces or profile fan-out in V0.

## 3.1 Initial bootstrap

Bootstrap cohort is:

```text
every KnowledgeSource existing at the bootstrap activation snapshot
```

For each source, the intended candidate is the source's **single current PROCESSING KnowledgeVersion**.

Do not choose:

```text
latest FAILED
latest SUPERSEDED
arbitrary highest version_number regardless of status
```

The existing one-PROCESSING-per-source DB invariant makes the intended candidate unambiguous.

Bootstrap requires:

```text
cohort is non-empty
no ACTIVE EmbeddingProfile exists
no ACTIVE KnowledgeVersion exists
exactly one PROCESSING candidate exists for every source in the cohort
every candidate is vector-ready under the target INACTIVE profile
```

If a source has no PROCESSING candidate, including a source whose only current candidate is FAILED/unready, bootstrap does not proceed.

When complete, one transaction atomically performs:

```text
target EmbeddingProfile INACTIVE → ACTIVE
all bootstrap candidates PROCESSING → ACTIVE
all candidate activated_at values = the same transaction timestamp
```

No partial bootstrap activation is allowed.

## 3.2 Normal post-bootstrap source activation

Normal activation API does **not** accept an arbitrary target profile.

It resolves the current globally ACTIVE profile internally.

A candidate may activate only when:

```text
candidate.status = PROCESSING
AND
candidate is vector-ready under the current globally ACTIVE profile
```

Replacement:

```text
new PROCESSING → ACTIVE
old ACTIVE     → SUPERSEDED
```

in one transaction.

For a new source with no prior ACTIVE version:

```text
candidate PROCESSING → ACTIVE
```

under the same active-profile readiness rule.

Do not activate a version that only has complete vectors under another INACTIVE profile.

## 3.3 Profile migration

To switch:

```text
P1 ACTIVE
→
P2 INACTIVE
```

require every currently ACTIVE KnowledgeVersion to be technically ready under P2.

Then one transaction performs only:

```text
P1 ACTIVE   → INACTIVE
P2 INACTIVE → ACTIVE
```

KnowledgeVersion statuses do not change solely because of profile migration.

Do not rebuild, supersede, or recreate KnowledgeVersions for profile migration.

---

# 4. Objective

Implement Step 6.2:

```text
persisted Embedding rows
→ storage/readiness validation
→ exact cosine storage primitive
→ safe global profile/version activation primitives
```

Step 6.2 answers:

```text
Are these persisted vectors technically queryable,
and is this version/profile state safe to expose to production retrieval?
```

It does **not** answer:

```text
Which chunks are relevant to a learner query?
```

That belongs to Step 6.3.

Mental model:

```text
vector persisted
≠
vector complete
≠
vector technically queryable
≠
vector active for production retrieval
```

---

# 5. Step 6.2 / Step 6.3 Boundary

Step 6.2 owns:

```text
pgvector schema reconciliation
cosine-distance storage semantics
exact vector nearest-neighbor storage primitive
vector readiness validation
technical query probe
single ACTIVE profile enforcement
initial bootstrap activation
normal per-source KnowledgeVersion activation
profile migration/switching
activation locking/idempotency/failure behavior
```

Step 6.3 later owns:

```text
query embedding orchestration
retrieval candidate counts
retrieval score mapping
semantic thresholding
metadata filtering
retrieval policy
```

Do not implement Step 6.3 behavior here.

---

# 6. Authorized Migration Freeze

Create exactly one forward migration:

```text
backend/migrations/versions/0012_vector_storage_readiness.py
```

Freeze:

```text
revision      = "0012_vector_storage_readiness"
down_revision = "0011_embedding_profile_identity"
```

Do not modify migrations `0001`–`0011`.

## 6.1 Profile-first Embedding index

Create exactly:

```text
ix_embeddings_embedding_profile_id
```

on:

```text
embeddings.embedding_profile_id
```

This is a normal B-tree relational index.

Do not create an ANN/vector index.

## 6.2 Exactly one globally ACTIVE EmbeddingProfile

Create exactly this logical partial unique index:

```text
uq_embedding_profiles_one_active
```

Equivalent SQLAlchemy model definition:

```python
Index(
    "uq_embedding_profiles_one_active",
    "status",
    unique=True,
    postgresql_where=text("status = 'ACTIVE'"),
)
```

Equivalent PostgreSQL intent:

```sql
CREATE UNIQUE INDEX uq_embedding_profiles_one_active
ON embedding_profiles (status)
WHERE status = 'ACTIVE';
```

This allows:

```text
0 ACTIVE profiles
or
1 ACTIVE profile
```

and rejects 2+ ACTIVE profiles.

Do not include profile semantic-identity columns in this lifecycle index.

Do not silently rewrite legacy profile statuses before creating the index. If existing persisted data violates the invariant, migration failure is preferable to guessing which profile should remain ACTIVE.

## 6.3 Embedding.chunk_id ON DELETE CASCADE

Actual accepted migration/schema evidence from the clean repository rebuilt through `0011_embedding_profile_identity` confirms that migration `0001_initial_schema` created the existing PostgreSQL FK with the exact name:

```text
fk_embeddings_chunk_id_chunks
```

This is the only accepted baseline for Step 6.2. Do not probe for or guess alternate legacy constraint names at runtime. Preserve the existing repository FK name across the migration.

Migration upgrade:

```text
drop fk_embeddings_chunk_id_chunks
recreate fk_embeddings_chunk_id_chunks
embeddings.chunk_id → chunks.id
ON DELETE CASCADE
```

Migration downgrade:

```text
drop fk_embeddings_chunk_id_chunks  # Step-6.2 CASCADE form
recreate fk_embeddings_chunk_id_chunks
embeddings.chunk_id → chunks.id
without ON DELETE CASCADE
```

Update the ORM `Embedding.chunk_id` ForeignKey to use:

```text
ondelete="CASCADE"
```

Do not change the EmbeddingProfile FK delete behavior.

## 6.4 Explicitly unchanged schema

Do not change:

```text
Embedding.vector type
Embedding.vector nullability
EmbeddingProfile semantic identity
KnowledgeVersion columns/statuses
Chunk columns
pgvector extension
vector dimension storage
KnowledgeVersion→Profile relationship
```

Do not add:

```text
HNSW
IVFFlat
READY status
new vector table
new activation table
new lock table
```

---

# 7. ORM Freeze

Update only the existing relevant model definitions.

`EmbeddingProfile` adds model metadata equivalent to:

```python
Index(
    "uq_embedding_profiles_one_active",
    "status",
    unique=True,
    postgresql_where=text("status = 'ACTIVE'"),
)
```

`Embedding` adds:

```text
Index("ix_embeddings_embedding_profile_id", "embedding_profile_id")
```

and changes only the Chunk FK delete rule to:

```text
chunk_id → chunks.id ON DELETE CASCADE
```

Preserve:

```text
uq_embedding_profiles_semantic_identity
uq_embeddings_chunk_id_embedding_profile_id
```

---

# 8. Distance / pgvector Query Freeze

V0 metric:

```text
cosine distance
```

pgvector operator:

```text
<=>
```

Use the pgvector SQLAlchemy comparator equivalent to:

```python
Embedding.vector.cosine_distance(query_vector)
```

Do not manually implement cosine math in Python for persisted-neighbor queries.

Mental model:

```text
smaller distance
→ more similar
```

The storage layer returns:

```text
chunk_id
distance
```

Do not convert distance into a product-level relevance score.

Do not apply a semantic distance threshold.

Do not support caller-selected metrics.

---

# 9. Exact Search Freeze

Use exact scan only:

```text
ORDER BY Embedding.vector <=> :query_vector
LIMIT :limit
```

No HNSW / IVFFlat / ANN setup.

For deterministic test behavior, use a stable secondary order when distances tie, equivalent to:

```text
ORDER BY distance ASC, Chunk.id ASC
```

The secondary order is deterministic storage behavior only; it is not a semantic ranking policy.

---

# 10. Internal Result Schemas

Use focused internal schemas equivalent to the following.

## 10.1 Nearest vector result

```text
NearestVectorResult
- chunk_id: UUID
- distance: float
```

No content, citation metadata, score mapping, or rerank fields in this primitive.

## 10.2 Vector readiness result

```text
VectorReadinessResult
- knowledge_version_id: UUID
- embedding_profile_id: UUID
- ready: bool
- required_chunk_count: int
- embedding_count: int
- expected_dimensions: int
- invalid_dimension_count: int
- probe_distance: float | None
- failure_code: str | None
```

`ready=True` requires:

```text
failure_code = None
invalid_dimension_count = 0
probe_distance is finite
```

This schema is internal, not a public API response.

---

# 11. Complete EmbeddingProfile Identity Validation

A Step-6.2 target profile is complete only when all are provably present:

```text
provider                 non-empty
provider_version         non-empty
model_name               non-empty
model_version            non-empty
dimensions               > 0
embedding_input_version  non-empty
normalize_embeddings     is not NULL
status                   ACTIVE or INACTIVE
```

Legacy nullable profile rows remain readable but are not readiness-eligible.

Do not infer missing profile identity from current application Settings.

---

# 12. Vector Pair Readiness Invariant

Implement one internal, lifecycle-status-agnostic storage validation equivalent to:

```text
check_vector_pair_readiness(
    knowledge_version_id,
    embedding_profile_id,
)
→ VectorReadinessResult
```

This primitive answers only:

```text
Does this exact KnowledgeVersion + EmbeddingProfile pair have
complete, dimension-consistent, technically queryable vectors?
```

It does **not** answer whether the pair is eligible for bootstrap, normal version activation, profile migration, or production search. Those lifecycle rules are owned by the calling service operation.

Pair readiness is `ready=True` only when all are true:

```text
KnowledgeVersion exists
EmbeddingProfile exists
profile semantic identity is complete
profile.status is a valid lifecycle value in {ACTIVE, INACTIVE}
required_chunk_count > 0
embedding_count == required_chunk_count
invalid_dimension_count == 0
technical pgvector query probe succeeds
```

It MUST NOT require any specific `KnowledgeVersion.status`. In particular, both a `PROCESSING` version and an `ACTIVE` version may be pair-ready when their persisted vector pair is complete and queryable.

`required_chunk_count`:

```text
COUNT(chunks WHERE knowledge_version_id = target)
```

`embedding_count`:

```text
COUNT(
  embeddings
  JOIN chunks ON chunks.id = embeddings.chunk_id
  WHERE chunks.knowledge_version_id = target
    AND embeddings.embedding_profile_id = profile
)
```

Because `UNIQUE(chunk_id, embedding_profile_id)` already exists, count equality plus the join proves exactly one target-profile Embedding per required Chunk.

Dimension validation must execute in PostgreSQL using pgvector dimension introspection equivalent to:

```text
vector_dims(Embedding.vector)
```

Count invalid rows where:

```text
vector_dims(vector) != EmbeddingProfile.dimensions
```

Do not deserialize every vector solely to count dimensions in Python.

`Embedding.vector NOT NULL` remains schema-enforced.

Pair readiness performs no state mutation, is not persisted, and does not add a READY lifecycle state.

Lifecycle wrappers separately enforce:

```text
bootstrap                → version PROCESSING + target profile INACTIVE
normal version activation → version PROCESSING + current global profile ACTIVE
profile migration        → version ACTIVE + target profile INACTIVE
production nearest search → version ACTIVE + requested/global profile ACTIVE
```

---

# 13. Pair Readiness Reason / Error Mapping

`check_vector_pair_readiness()` may return `ready=False` for expected persisted-storage validation failures.

Freeze `failure_code` mapping:

```text
version missing or required chunks/embeddings incomplete
→ KNOWLEDGE_VERSION_NOT_VECTOR_READY

profile missing, incomplete identity, or invalid lifecycle value
→ EMBEDDING_PROFILE_NOT_READY

stored vector dimension mismatch
→ VECTOR_DIMENSION_MISMATCH

probe executes but result is missing/non-finite/not near self-distance zero
→ KNOWLEDGE_VERSION_NOT_VECTOR_READY

pgvector/operator/database execution failure during probe
→ VECTOR_QUERY_FAILED
```

`KNOWLEDGE_VERSION_NOT_PROCESSING` is a lifecycle-eligibility error used by normal/bootstrap activation logic, not by pair readiness.

Do not mutate KnowledgeVersion or EmbeddingProfile lifecycle state while computing pair readiness.

Do not expose raw SQL/database error strings.

---

# 14. Technical Query Probe

Readiness must run one storage-only probe for the exact candidate/profile pair.

## 14.1 Probe source

Select one deterministic persisted target-profile Embedding from the candidate, ordered by:

```text
Chunk.chunk_index ASC
then Embedding.id ASC
```

Use that stored vector as the probe vector.

Do not call the embedding provider/model.

## 14.2 Probe query

Equivalent relational query:

```text
Embedding
JOIN Chunk
WHERE Chunk.knowledge_version_id = candidate_id
  AND Embedding.embedding_profile_id = profile_id
ORDER BY Embedding.vector <=> :probe_vector ASC,
         Chunk.id ASC
LIMIT 1
```

Use the SQLAlchemy pgvector expression:

```python
Embedding.vector.cosine_distance(probe_vector)
```

Validate:

```text
query executes
one row returns
returned row belongs to exact candidate/profile
distance is finite
vector dimension is correct
abs(distance) <= 1e-6
```

`1e-6` is the frozen self-distance tolerance.

A different Chunk may be returned when two persisted vectors are identical; that is acceptable as long as the returned row belongs to the exact candidate/profile and the nearest distance is within the self-distance tolerance.

This probe validates storage/queryability only. It does not judge semantic relevance.

---

# 15. Low-Level ACTIVE Search Primitive

Expose an internal storage primitive equivalent to:

```python
nearest_vectors(
    session,
    query_vector,
    embedding_profile_id,
    limit,
) -> list[NearestVectorResult]
```

Repository query must itself enforce all safety gates:

```text
Embedding.embedding_profile_id = requested profile
EmbeddingProfile.id = requested profile
EmbeddingProfile.status = ACTIVE
KnowledgeVersion.status = ACTIVE
```

Equivalent joins:

```text
Embedding
JOIN Chunk
JOIN KnowledgeVersion
JOIN EmbeddingProfile
```

Then:

```text
ORDER BY cosine distance ASC, Chunk.id ASC
LIMIT :limit
```

Do not rely on Step 6.3 callers to add ACTIVE filters.

A service-level wrapper should additionally:

```text
require limit > 0
resolve/validate the requested profile is the globally ACTIVE profile
validate len(query_vector) == active_profile.dimensions
normalize unexpected pgvector/database exceptions to VECTOR_QUERY_FAILED
```

If the requested profile is not the globally ACTIVE profile:

```text
EMBEDDING_PROFILE_NOT_READY
```

If query-vector dimensions do not match:

```text
VECTOR_DIMENSION_MISMATCH
```

Do not add a product default for `limit` here.

---

# 16. ACTIVE Profile Resolver

Implement one authoritative active-profile resolver.

Read-only resolver behavior:

```text
0 ACTIVE profiles
→ ACTIVE_EMBEDDING_PROFILE_NOT_FOUND

1 ACTIVE profile
→ return it

>1 ACTIVE profiles
→ MULTIPLE_ACTIVE_EMBEDDING_PROFILES
```

The partial unique index should make `>1` impossible after migration, but keep defense-in-depth behavior for corrupt/legacy states.

For any lifecycle-changing activation transaction, use a locking resolver that locks **all EmbeddingProfile rows in deterministic ID order first**, then derives the active profile from the locked rows.

Reason:

```text
all activation operations share the same first lock domain
→ bootstrap/profile migration/per-source activation serialize safely
→ no transient profile-switch race requires a second lock technology
```

V0 corpus/profile counts are small; this coarse profile-row serialization is intentional and acceptable.

---

# 17. Global Lock Order

All lifecycle-changing activation operations must follow:

```text
1. EmbeddingProfile rows
   ORDER BY id
   FOR UPDATE

2. KnowledgeSource rows
   ORDER BY id
   FOR UPDATE

3. KnowledgeVersion rows
   ORDER BY id
   FOR UPDATE
```

Never lock a source/version first and then attempt to acquire profile locks.

Do not add:

```text
Redis locks
advisory locks
lock table
queue
process-local mutex
```

Repository methods must not commit.

Service owns commit/rollback.

---

# 18. Initial Bootstrap — Exact Snapshot and Candidate Selection

Expose a service operation equivalent to:

```text
bootstrap_profile(target_profile_id)
```

It takes no caller-supplied KnowledgeVersion list.

The service derives the complete cohort itself.

## 18.1 Bootstrap transaction

One transaction performs the full final revalidation and mutation.

Exact order:

```text
BEGIN

1. lock all EmbeddingProfile rows ORDER BY id
2. verify target profile exists, complete, and INACTIVE
3. verify zero ACTIVE profiles
4. lock every KnowledgeSource currently existing ORDER BY id
5. define those locked source IDs as the bootstrap snapshot/cohort
6. require cohort size > 0
7. lock KnowledgeVersion rows for those sources with status in {PROCESSING, ACTIVE}
   ORDER BY id
8. verify zero ACTIVE KnowledgeVersions
9. verify exactly one PROCESSING KnowledgeVersion per cohort source
10. for every PROCESSING candidate, run check_vector_pair_readiness(candidate, target_profile)
11. if every candidate ready:
       target profile → ACTIVE
       every candidate → ACTIVE
       every candidate.activated_at = same transaction timestamp
12. flush
COMMIT
```

Existing source-lock conventions mean a normal build cannot concurrently create another PROCESSING version for a locked source.

A `KnowledgeSource` inserted after the source-lock snapshot statement is not part of this bootstrap cohort. It may later complete and activate through the normal post-bootstrap path under the now-ACTIVE profile.

Bootstrap is not allowed with an empty source cohort.

## 18.2 Bootstrap failure

Any of these refuse activation without partial mutation:

```text
target profile missing/incomplete/not INACTIVE
an ACTIVE profile already exists
an ACTIVE KnowledgeVersion already exists
empty cohort
source with no PROCESSING candidate
source with unready/FAILED candidate state
readiness failure for any candidate
```

Use one transaction. Any mutation-time failure rolls back all profile/version changes.

Do not mark unready candidates FAILED solely because bootstrap readiness failed.

---

# 19. Normal Post-Bootstrap Version Activation

Expose a service operation equivalent to:

```text
activate_version(version_id)
```

Do not accept `embedding_profile_id` from the caller.

The globally ACTIVE profile is authoritative.

## 19.1 Transaction order

```text
BEGIN

1. lock all EmbeddingProfile rows ORDER BY id
2. resolve exactly one ACTIVE profile
3. read candidate enough to identify source_id
4. lock that KnowledgeSource
5. lock all KnowledgeVersion rows for that source with status in {PROCESSING, ACTIVE}
   ORDER BY id
6. resolve the target candidate and current previous ACTIVE version from locked rows
```

If the target candidate is PROCESSING:

```text
7. separately require candidate.status = PROCESSING
8. run check_vector_pair_readiness(candidate, current ACTIVE profile) and require ready
9. candidate PROCESSING → ACTIVE
10. candidate.activated_at = transaction timestamp
11. if a different previous ACTIVE exists:
       previous ACTIVE → SUPERSEDED
12. flush
COMMIT
```

Never supersede the previous ACTIVE before the candidate readiness recheck passes.

## 19.2 Already ACTIVE target

If the requested target version is already ACTIVE:

```text
verify it is the source's sole ACTIVE version
run check_vector_pair_readiness(target, current ACTIVE profile) and require ready
→ return idempotent NO_OP success
```

For this coherence check, call the same status-agnostic `check_vector_pair_readiness(target, current_active_profile)` primitive. The surrounding idempotency path separately requires the target to already be `ACTIVE`.

If an already ACTIVE target is not coherent with the active profile:

```text
ACTIVATION_CONFLICT
```

Do not silently report success for a corrupt active state.

## 19.3 Ineligible states

```text
FAILED      → reject
SUPERSEDED  → reject
missing     → reject
PROCESSING but not ready → reject, remain PROCESSING
```

Use `KNOWLEDGE_VERSION_NOT_VECTOR_READY` or `ACTIVATION_CONFLICT` according to the exact condition below.

---

# 20. Profile Migration — Exact Transaction

Expose a service operation equivalent to:

```text
migrate_active_profile(target_profile_id)
```

This operation is post-bootstrap profile switching, not initial bootstrap.

## 20.1 Transaction order

```text
BEGIN

1. lock all EmbeddingProfile rows ORDER BY id
2. require exactly one current ACTIVE profile P1
3. require target profile P2 exists and has complete semantic identity
```

If:

```text
P2.id == P1.id
```

then verify all current ACTIVE KnowledgeVersions remain coherent under P1 and return idempotent NO_OP success.

Otherwise require:

```text
P2.status = INACTIVE
```

Then:

```text
4. read source IDs owning current ACTIVE KnowledgeVersions
5. lock those KnowledgeSource rows ORDER BY id
6. lock all current ACTIVE KnowledgeVersion rows ORDER BY id
7. snapshot/cohort = those locked ACTIVE KnowledgeVersions
8. require cohort is non-empty
9. separately require every cohort KnowledgeVersion remains ACTIVE
10. for every ACTIVE KnowledgeVersion, run check_vector_pair_readiness(version, P2) and require ready
11. if every pair is ready:
       P1 ACTIVE   → INACTIVE
       P2 INACTIVE → ACTIVE
12. flush
COMMIT
```

KnowledgeVersion statuses and `activated_at` values do not change during profile migration.

Because ordinary version activation locks profile rows first, it cannot add/change an ACTIVE KnowledgeVersion while the migration cohort is being validated under the locked profile set.

## 20.2 Migration failure

If any ACTIVE version lacks complete/valid/queryable P2 embeddings:

```text
refuse profile switch
P1 remains ACTIVE
P2 remains INACTIVE
KnowledgeVersion statuses unchanged
```

Do not mark versions FAILED.

If transaction mutation fails:

```text
ROLLBACK
```

Do not use a compensating second transaction.

---

# 21. Pair Readiness Reuse and Lifecycle Eligibility

Do not implement separate storage/queryability rules for:

```text
PROCESSING candidate validation
already-ACTIVE idempotency
profile-migration ACTIVE-version validation
```

Use the single status-agnostic primitive:

```text
check_vector_pair_readiness(knowledge_version_id, embedding_profile_id)
```

It owns only the shared pair checks:

```text
version/profile existence
complete profile semantic identity
required chunks > 0
exact target-profile embedding completeness
dimension coherence
technical pgvector probe
```

Lifecycle eligibility remains separate and must be checked by each service operation:

```text
bootstrap:
  version.status == PROCESSING
  target_profile.status == INACTIVE
  AND pair readiness ready

normal activation:
  version.status == PROCESSING
  global_profile.status == ACTIVE
  AND pair readiness ready

already-ACTIVE NO_OP validation:
  version.status == ACTIVE
  global_profile.status == ACTIVE
  AND pair readiness ready

profile migration:
  version.status == ACTIVE
  target_profile.status == INACTIVE
  AND pair readiness ready
```

Do not pass an `allowed_status` into the pair-readiness helper. Do not duplicate vector completeness/dimension/probe logic in lifecycle services.

---

# 22. Idempotency Freeze

## Readiness

Repeated readiness:

```text
no mutation
same persisted state
→ same result
```

## Bootstrap

If a global ACTIVE profile already exists:

```text
bootstrap_profile(...)
→ reject / ACTIVATION_CONFLICT
```

Do not treat bootstrap as a second profile-migration API.

## Normal activation

Already ACTIVE coherent target:

```text
NO_OP success
```

FAILED/SUPERSEDED target:

```text
not eligible
```

## Profile migration

Target already globally ACTIVE and all ACTIVE versions coherent:

```text
NO_OP success
```

Target INACTIVE and cohort ready:

```text
atomic switch
```

No status oscillation or duplicate rows are created.

---

# 23. Failure Behavior Freeze

Readiness/probe validation is not itself a destructive lifecycle transition.

These conditions refuse activation but do **not** automatically mark a candidate FAILED:

```text
missing target-profile Embedding
wrong profile
incomplete profile identity
vector dimension mismatch
technical query probe failure
```

Old ACTIVE knowledge/profile remains unchanged until a replacement transaction successfully commits.

Technical pgvector/database failure must not be converted into semantic "no evidence".

Do not delete historical Embeddings, SUPERSEDED versions, or inactive profiles in Step 6.2.

---

# 24. Error Freeze

Use existing `ApplicationError` conventions.

No public Step-6.2 router is required.

Freeze only these Step-6.2 codes unless repository reconciliation proves an existing equivalent should be reused verbatim:

```text
KNOWLEDGE_VERSION_NOT_PROCESSING
KNOWLEDGE_VERSION_NOT_VECTOR_READY
EMBEDDING_PROFILE_NOT_READY
ACTIVE_EMBEDDING_PROFILE_NOT_FOUND
MULTIPLE_ACTIVE_EMBEDDING_PROFILES
VECTOR_DIMENSION_MISMATCH
VECTOR_QUERY_FAILED
ACTIVATION_CONFLICT
```

Recommended internal HTTP-style status mapping for `ApplicationError` consistency:

```text
KNOWLEDGE_VERSION_NOT_PROCESSING       → 409
KNOWLEDGE_VERSION_NOT_VECTOR_READY     → 409
EMBEDDING_PROFILE_NOT_READY            → 409
ACTIVE_EMBEDDING_PROFILE_NOT_FOUND     → 409
MULTIPLE_ACTIVE_EMBEDDING_PROFILES     → 500
VECTOR_DIMENSION_MISMATCH              → 500
VECTOR_QUERY_FAILED                    → 500
ACTIVATION_CONFLICT                    → 409
```

These are internal/application errors; do not create a new public vector API solely to expose them.

Do not expose raw DB exception strings in `details`.

---

# 25. Repository Boundary

Create a focused module equivalent to:

```text
app/ai/vector_storage/repository.py
```

Repository owns SQL/ORM only and never commits.

Required responsibilities equivalent to:

```text
count_required_chunks
count_embeddings_for_version_profile
count_invalid_vector_dimensions
select_probe_embedding
run_candidate_probe
nearest_vectors
list/lock all profiles ordered by id
resolve active profiles from locked/read rows
list/lock all KnowledgeSources ordered by id
list/lock relevant KnowledgeVersions ordered by id
load version/source identity
```

You may reuse already-correct Step-6.1 read helpers where doing so keeps one source of truth and does not create circular imports. Do not refactor Step 6.1 broadly just to share trivial queries.

Do not put activation business rules into the repository.

---

# 26. Service Boundary

Create a focused service equivalent to:

```text
VectorStorageService
```

Responsibilities:

```text
pair-readiness orchestration
lifecycle eligibility validation
profile completeness validation
technical probe normalization
ACTIVE profile resolution
initial bootstrap
normal KnowledgeVersion activation
profile migration
pair-coherence validation
idempotency
transaction boundaries
structured logging
stable ApplicationError mapping
```

Repository never commits.

Service owns:

```text
commit
rollback
```

No model/provider call is allowed anywhere in this module.

---

# 27. Logging Freeze

Use current Python logging conventions and structured `extra` fields equivalent to:

```text
embedding_profile_id
knowledge_version_id
vector_count
dimensions
distance_metric = cosine
readiness_status
query_probe_duration_ms
activation_action
status
error_code optional
```

For global operations also include safe counts when useful:

```text
source_count
version_count
```

Do not log:

```text
full vectors
raw SQL
full Chunk.content
embedding inputs
```

---

# 28. No Configuration / Dependency Expansion

Step 6.2 requires no new application environment variable.

Use fixed V0 storage contract:

```text
distance_metric = cosine
```

Do not make metric caller/config selectable in this Step.

Do not add a new runtime dependency.

Keep existing:

```text
PostgreSQL
pgvector
SQLAlchemy async
Alembic
```

No vector-database SDK.

---

# 29. Expected Files

Expected new files:

```text
backend/migrations/versions/0012_vector_storage_readiness.py

backend/app/ai/vector_storage/__init__.py
backend/app/ai/vector_storage/schemas.py
backend/app/ai/vector_storage/repository.py
backend/app/ai/vector_storage/service.py
backend/app/ai/vector_storage/errors.py

docs/ai/step-6.2-vector-storage.md

backend/tests/test_step62_vector_storage_migration.py
backend/tests/test_step62_vector_repository.py
backend/tests/test_step62_vector_readiness.py
backend/tests/test_step62_activation.py
```

Expected modification:

```text
backend/app/database/models/knowledge.py
```

Modify `backend/app/database/models/__init__.py` only if the current export convention actually requires it.

Do not modify Step-6.1 provider/formatter/model configuration unless a test-only import path mechanically requires a non-semantic fix. Any material Step-6.1 behavior change is out of scope.

---

# 30. Migration Tests

Use the real PostgreSQL/pgvector test database.

Cover at minimum:

```text
0011 → 0012 upgrade succeeds
0012 is Alembic head
alembic check has no pending schema operations
```

Inspect the `0011` baseline before upgrade and prove:

```text
existing Embedding.chunk_id FK name = fk_embeddings_chunk_id_chunks
existing FK targets chunks.id
existing FK has no ON DELETE CASCADE
```

Then upgrade to `0012` and inspect schema to prove:

```text
pgvector extension still exists
Embedding.vector is VECTOR / variable dimension
Embedding.vector is NOT NULL
uq_embeddings_chunk_id_embedding_profile_id preserved
ix_embeddings_embedding_profile_id exists
uq_embedding_profiles_one_active exists and is partial on status='ACTIVE'
0 ACTIVE profiles allowed
1 ACTIVE profile allowed
2 ACTIVE profiles rejected
fk_embeddings_chunk_id_chunks still targets chunks.id
fk_embeddings_chunk_id_chunks has ON DELETE CASCADE
EmbeddingProfile FK delete semantics unchanged
no HNSW index
no IVFFlat index
```

Test deletion:

```text
Chunk deleted
→ dependent Embedding deleted
```

Do not rely only on ORM cascade behavior; prove DB FK behavior.

Also verify the downgrade/re-upgrade path explicitly:

```text
0012 downgrade
→ drops the Step-6.2 CASCADE form of fk_embeddings_chunk_id_chunks
→ recreates fk_embeddings_chunk_id_chunks against chunks.id without ON DELETE CASCADE

0012 re-upgrade
→ restores ON DELETE CASCADE under the same exact FK name
```

Do not accept a downgrade that gratuitously renames the FK.

---

# 31. Repository / Distance Tests

Real PostgreSQL/pgvector tests must prove:

```text
cosine comparator / <=> semantics
smaller cosine distance sorts first
storage returns chunk_id + distance
no invented relevance score
exact scan works without HNSW/IVFFlat
stable tie order
```

ACTIVE safety query must prove repository itself excludes:

```text
PROCESSING KnowledgeVersion
FAILED KnowledgeVersion
SUPERSEDED KnowledgeVersion
INACTIVE EmbeddingProfile
```

and returns only rows where both:

```text
KnowledgeVersion.status = ACTIVE
EmbeddingProfile.status = ACTIVE
```

Historical Embeddings under inactive profiles may remain stored. A PROCESSING KnowledgeVersion must remain excluded from `nearest_vectors` even when its version/profile pair is pair-ready.

Validate wrong query-vector dimension through the service wrapper.

No threshold test should exist because no threshold belongs in this layer.

---

# 32. Pair Readiness Tests

Cover at minimum:

```text
PROCESSING version + complete target-profile vectors → pair ready
ACTIVE version + complete target-profile vectors → pair ready
required_chunk_count > 0
missing target-profile Embedding → not ready
wrong-profile Embeddings do not count
legacy/incomplete profile identity → not ready
dimension mismatch → not ready
technical query failure → not ready/error normalized
probe missing result → not ready
probe non-finite distance → not ready
probe self-distance > 1e-6 → not ready
no KnowledgeVersion status mutation
no profile lifecycle mutation
no READY status introduced
no embedding provider/model call
```

Explicitly prove pair readiness itself does not reject an `ACTIVE` KnowledgeVersion merely for being ACTIVE.

Also prove dimension validation uses stored pgvector dimensions and expected profile dimensions.

---

# 33. Bootstrap Tests

Use real DB transactions/concurrency where locking matters.

Cover:

```text
empty source cohort refuses bootstrap
zero ACTIVE profile precondition
existing ACTIVE profile refuses bootstrap
existing ACTIVE KnowledgeVersion refuses bootstrap even if pair-ready
source with no PROCESSING candidate blocks bootstrap
FAILED/unready source blocks bootstrap
wrong-profile/incomplete embeddings block bootstrap
complete multi-source cohort activates target profile + every candidate atomically
all activated_at timestamps for bootstrap candidates use same transaction timestamp
transaction failure rolls back profile + every candidate status
no partial activation observable
source inserted after bootstrap cohort snapshot is not part of that snapshot
```

The post-snapshot source case must remain safe for later normal activation; Step 6.2 need not automatically activate it.

---

# 34. Normal Version Activation Tests

Cover:

```text
requires exactly one global ACTIVE profile
candidate must be PROCESSING and ready under that active profile
candidate with vectors only under another INACTIVE profile is rejected
new source with no previous ACTIVE activates safely
replacement activates new and supersedes old in same transaction
activated_at set only on newly activated candidate
transaction failure leaves old ACTIVE and candidate PROCESSING
already ACTIVE coherent target → NO_OP
already ACTIVE incoherent target → ACTIVATION_CONFLICT
ACTIVE/SUPERSEDED/FAILED targets are not eligible for a new PROCESSING→ACTIVE transition even if pair-ready
FAILED target rejected
SUPERSEDED target rejected
missing target rejected
```

Concurrency:

```text
two activation attempts for same source
→ row locks + DB constraints converge to one ACTIVE version
→ no availability gap
```

Also test ordinary activation racing with profile migration. Final state must satisfy the global coherence invariant; it is acceptable for one caller to receive `ACTIVATION_CONFLICT` and retry rather than both succeeding.

---

# 35. Profile Migration Tests

Cover:

```text
requires one current ACTIVE profile
missing ACTIVE profile rejected
incomplete target profile rejected
ACTIVE version + complete P2 vectors → pair readiness succeeds and version may participate in migration
P2 cannot replace P1 until every ACTIVE KnowledgeVersion is pair-ready under P2
ACTIVE version missing P2 vectors → pair readiness false and global switch refused
one unready ACTIVE version blocks global switch
successful switch P1 ACTIVE→INACTIVE + P2 INACTIVE→ACTIVE is atomic
KnowledgeVersion statuses unchanged by profile migration
activated_at values unchanged by profile migration
target already ACTIVE + all ACTIVE versions coherent → NO_OP
transaction failure preserves P1 ACTIVE / P2 INACTIVE
```

Concurrency:

```text
P1→P2 vs P1→P3 concurrent migration
→ deterministic profile locks serialize
→ exactly one ACTIVE profile after completion

profile migration vs ordinary source activation
→ profile locks serialize before source locks
→ no ACTIVE version is left without ready Embeddings under the resulting ACTIVE profile
```

---

# 36. Boundary Tests

Explicitly prove Step 6.2 does **not**:

```text
call EmbeddingProvider
call BGE-M3
regenerate vectors
rewrite EmbeddingInputFormatter
perform query rewriting
choose product retrieval candidate count
apply semantic threshold
apply metadata filtering
rerank
call an LLM
activate a second simultaneous profile
use mixed-profile search
implement Step 6.3 orchestration
```

---

# 37. Verification Commands

Run from `backend/` using the project's real PostgreSQL/pgvector test environment.

At minimum:

```bash
uv lock --check
uv run alembic upgrade head
uv run alembic current
uv run alembic check

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

If the exact accepted repository test filenames differ mechanically, use the actual current names while preserving the frozen coverage.

Do not claim a command passed unless it was actually run.

No external model/network is needed for Step 6.2 tests.

---

# 38. Step Note Deliverable

Create/update:

```text
docs/ai/step-6.2-vector-storage.md
```

Include:

## Objective

Make persisted embeddings technically queryable and safely activatable without implementing retrieval policy.

## Why

Persisted vectors are not automatically production-safe. The system must prove completeness, physical queryability, dimension coherence, and lifecycle coherence before retrieval can see them.

## Mental Model

```text
Embedding exists
→ storage integrity
→ vector pair readiness
→ lifecycle eligibility
→ atomic profile/version activation
→ production-searchable
```

## Core Knowledge

```text
pgvector variable-dimension VECTOR
cosine distance
exact nearest-neighbor scan
readiness vs lifecycle state
single global embedding space
atomic state swap
partial unique index
row-lock ordering
```

## Data Flow

```text
Step-6.1 Embedding[]
→ status-agnostic pair readiness
→ technical cosine probe
→ lifecycle-specific activation gate
→ ACTIVE profile/version state
→ Step 6.3 storage primitive
```

## Key Design Decisions

Document at least:

```text
one global ACTIVE profile
no KnowledgeVersion→Profile FK
exact cosine search only
no ANN index
bootstrap cohort = all sources existing at snapshot
normal activation uses current ACTIVE profile
profile switch requires all ACTIVE versions ready under target
profile→source→version lock order
pair-readiness failures are non-destructive
```

## Reusable Approach

Explain the distinction:

```text
data exists
vs
data complete
vs
data technically usable
vs
data active for production
```

## Common Mistakes

Include:

```text
activating after count check only
searching PROCESSING/SUPERSEDED rows
mixing profiles
switching profile before all active versions are ready
superseding old version before new readiness succeeds
adding ANN indexes prematurely
holding inconsistent lock order
turning DB/query failure into semantic no-results
```

## Definition of Done

Mirror the frozen acceptance criteria below.

---

# 39. Concepts Discovered

After successful implementation, update Step documentation / PM handoff with only concepts actually used.

| Concept | Category | Role / Why it matters |
|---|---|---|
| Vector Readiness | BOTH | Proves persisted AI data is complete and technically queryable before activation |
| Cosine Distance | AI | Fixed V0 semantic vector distance contract |
| Exact Vector Search | BOTH | Simple deterministic pgvector baseline for the small corpus |
| Global Embedding Space | AI | Prevents production retrieval from mixing incompatible profiles |
| Production Activation Gate | SYSTEM | Prevents incomplete/non-ready data exposure |
| Atomic Version Swap | SYSTEM | Replaces active source knowledge without an availability gap |
| Atomic Profile Switch | SYSTEM | Changes the global embedding space without mixed production state |
| Partial Unique Index | DE | DB-level enforcement of at most one ACTIVE profile |
| Lock Ordering | SYSTEM | Prevents activation/profile-switch deadlocks and races |
| Defense-in-depth Validation | BOTH | Revalidates vector integrity/queryability after generation |

Do not add concepts merely mentioned but not used.

---

# 40. Tools Used

After successful implementation, record only actually used tools.

| Tool | Category | Role / Why used |
|---|---|---|
| PostgreSQL | DE | Transactional storage, row locking, partial indexes, lifecycle atomicity |
| pgvector | BOTH | VECTOR type, `vector_dims`, cosine distance/operator |
| SQLAlchemy async | DE | Repository queries and `FOR UPDATE` locking |
| Alembic | DE | `0012` forward schema reconciliation |

Do not add a standalone vector database or ANN tooling.

---

# 41. Acceptance Criteria

Implementation is complete only when all are true:

## Schema / migration

- [ ] `0012_vector_storage_readiness` exists with correct down_revision.
- [ ] `ix_embeddings_embedding_profile_id` exists.
- [ ] `uq_embedding_profiles_one_active` enforces 0-or-1 ACTIVE profile globally.
- [ ] `0011` baseline exposes `fk_embeddings_chunk_id_chunks` without `ON DELETE CASCADE`.
- [ ] `0012` preserves the exact FK name `fk_embeddings_chunk_id_chunks` and adds `ON DELETE CASCADE`.
- [ ] `0012` downgrade restores `fk_embeddings_chunk_id_chunks` without `ON DELETE CASCADE`.
- [ ] ORM matches migration semantics.
- [ ] `Embedding.vector` remains variable-dimension `Vector()` and NOT NULL.
- [ ] Existing Chunk/Profile uniqueness remains unchanged.
- [ ] No HNSW/IVFFlat/ANN index exists.
- [ ] No `KnowledgeVersion.embedding_profile_id` is added.

## Storage / query

- [ ] Cosine `<=>` / `.cosine_distance()` is the only V0 metric.
- [ ] Exact scan is used.
- [ ] Storage result is `chunk_id + distance`.
- [ ] No threshold or product relevance-score mapping is added.
- [ ] Repository search itself filters ACTIVE KnowledgeVersion + ACTIVE profile, even when excluded PROCESSING pairs are pair-ready.

## Pair readiness / lifecycle eligibility

- [ ] `check_vector_pair_readiness(version_id, profile_id)` is lifecycle-status-agnostic for KnowledgeVersion.
- [ ] Pair readiness is derived, read-only, and not persisted.
- [ ] Both PROCESSING and ACTIVE versions can be pair-ready when vectors are complete/queryable.
- [ ] Required Chunk count is > 0.
- [ ] Exact target-profile completeness is checked.
- [ ] Complete semantic profile identity is required.
- [ ] Stored pgvector dimensions are checked against profile dimensions.
- [ ] Technical cosine probe runs.
- [ ] Probe self-distance tolerance is `1e-6`.
- [ ] No embedding model/provider call occurs.
- [ ] Lifecycle wrappers separately enforce PROCESSING/ACTIVE version status and INACTIVE/ACTIVE profile status for their operation.
- [ ] No READY status is added or persisted.

## Bootstrap

- [ ] Bootstrap cohort is all KnowledgeSources existing at the locked snapshot.
- [ ] Exactly one PROCESSING candidate per cohort source is required separately from pair readiness.
- [ ] An ACTIVE version is not accepted as a bootstrap candidate merely because it is pair-ready.
- [ ] Empty cohort is not activated.
- [ ] Any unready/missing candidate blocks the whole bootstrap.
- [ ] First profile + all candidates activate atomically.
- [ ] No partial bootstrap state is visible.

## Normal activation

- [ ] Global ACTIVE profile is resolved internally.
- [ ] Candidate must separately be PROCESSING and pair-ready under that profile.
- [ ] Previous ACTIVE is superseded in the same transaction.
- [ ] Old ACTIVE survives failed replacement activation.
- [ ] Already ACTIVE coherent target is an idempotent NO_OP.
- [ ] FAILED/SUPERSEDED targets are not reactivated.

## Profile migration

- [ ] Every current ACTIVE KnowledgeVersion is allowed through status-agnostic pair readiness and must be pair-ready under target P2.
- [ ] P1→P2 status switch is atomic.
- [ ] KnowledgeVersion statuses do not change solely for profile migration.
- [ ] Exactly one profile remains ACTIVE.
- [ ] Normal version activation cannot race profile migration into incoherent state.

## Concurrency / transactions

- [ ] Lifecycle operations lock profile rows first, then source rows, then version rows.
- [ ] Lock sets are ordered by UUID/id.
- [ ] Repository never commits.
- [ ] Service owns transactions.
- [ ] No Redis/advisory/process-local lock is introduced.

## Boundaries

- [ ] Step 6.1 behavior remains closed.
- [ ] Step 6.3 is not implemented.
- [ ] No public vector-search endpoint is added.
- [ ] No query embedding/filter/rerank/LLM behavior is added.

## Verification / documentation

- [ ] Focused Step-6.2 tests pass.
- [ ] Step-6.1 regressions pass.
- [ ] Phase-5.5–5.7 regressions pass.
- [ ] Full backend suite passes.
- [ ] Alembic upgrade/current/check pass.
- [ ] `compileall app` passes.
- [ ] Step Note reflects actual implementation.

---

# 42. Scope Guardrails

Do **not** implement:

```text
Step 6.3 semantic retrieval
query embedding orchestration
metadata filtering
reranking
RAG evidence threshold
prompt construction
LLM generation
conversation memory
citations
external retrieval/fallback
HNSW
IVFFlat
ANN optimization
separate vector database
embedding regeneration
mixed-profile production retrieval
per-profile retrieval fan-out
KnowledgeVersion→EmbeddingProfile FK
new lock service/table
queue/Celery
public vector API
```

Do not broaden migration `0012` beyond the three authorized schema changes.

---

# 43. Completion Report Required From Codex

Return exactly enough evidence for specialist review:

```text
Step
Status

Files changed
Migration changed
Schema changed
Dependency changed

0012 migration details
Vector/index/FK details
Distance/operator implementation
Readiness implementation
Technical probe
Low-level nearest_vectors
Bootstrap flow
Normal activation flow
Profile migration flow
Lock order/concurrency
Idempotency
Failure behavior
Errors/logging
Tests added/changed

Verification commands actually run + exact results
Warnings
Problems/risks
Deviations from frozen task
Decisions needed

Production source changed: YES/NO
Step 6.3 started: NO
```

If any frozen requirement cannot be implemented without an architecture decision, stop and report the blocker instead of silently changing the contract.
