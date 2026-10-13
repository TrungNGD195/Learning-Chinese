# Codex Task — Step 5.7 Incremental / Reprocessing Strategy

## Task Identity

**Project:** LLM + RAG Web App học tiếng Trung cho người mới bắt đầu  
**Phase:** 5 — Data Engineering  
**Step:** 5.7 — Incremental / Reprocessing Strategy  
**Owner:** Data Engineering Specialist  
**Status:** FROZEN / READY FOR CODEX AFTER PM REVIEW

Use the current accepted repository after Step 5.6.

Authoritative accepted state:

```text
Step 5.1 — CLOSED
Step 5.2 — CLOSED
Step 5.3 — CLOSED
Step 5.4 — CLOSED
Step 5.5 — CLOSED
Step 5.6 — CLOSED

Current Alembic head:
0009_pipeline_orchestration_contract
```

Preserve all accepted decisions through D-064 and frozen Step-5.7 decisions:

```text
D-065 — Document Re-review Lifecycle and Approved Artifact Identity
D-066 — Step 5.7 Exact Build Lineage / Migration 0010
D-067 — Published Lesson Reprocessing Trigger / Maintenance Boundary
```

Do not redesign architecture.

Do not implement Step 5.8 or Phase 6.

Do not run a new architecture discovery exercise unless the actual accepted repository materially contradicts this task.

---

# 1. Objective

Implement deterministic **stage-level incremental/reprocessing** for V0.

Mental model:

```text
desired processing identity
→ compare against exact persisted causal lineage
→ find first stale stage
→ reuse only valid upstream artifacts
→ rebuild every dependent downstream stage
→ preserve old ACTIVE knowledge
→ NO_OP when already satisfied
```

Supported planner actions:

```text
NO_OP
FROM_PARSE
FROM_TRANSFORM
FROM_CHUNK
FROM_EMBED
```

`FROM_EMBED` is policy-only in Step 5.7.

Do not implement embedding generation or Phase-6 behavior.

---

# 2. V0 Granularity Freeze

Step 5.7 is **stage-level incremental processing**.

Do not introduce:

```text
paragraph-level invalidation
single-block reprocessing graph
per-chunk dependency DAG
cross-version partial Chunk remapping
partial embedding reuse
vector copying
artifact-edge tables
generic dependency graph persistence
```

The corpus is intentionally small enough that stage-level reuse is the correct V0 trade-off.

---

# 3. Dependency Model

Ordered dependency graph:

```text
SOURCE
↓
PARSE / CLEAN
↓
TRANSFORM
↓
CHUNK
↓
EMBED
```

Earliest stale stage invalidates itself and all downstream stages.

Examples:

```text
source changed
→ FROM_PARSE

parser changed
→ FROM_PARSE

cleaning changed
→ FROM_PARSE

transformation changed
→ FROM_TRANSFORM

chunking strategy/version/config changed
→ FROM_CHUNK

future embedding profile/input identity changed
→ FROM_EMBED

nothing relevant changed and required artifacts validate
→ NO_OP
```

---

# 4. Reprocessing Planner Boundary

Create equivalent:

```text
backend/app/ingestion/reprocessing.py
```

with:

```text
ReprocessingPlanner
ReprocessingService
```

Separation:

```text
ReprocessingPlanner
→ decides what is stale
→ returns typed plan
→ MUST NOT execute pipeline stages

ReprocessingService
→ plans/revalidates current state
→ executes through accepted orchestration/stage boundaries
```

The service may share the module with the planner if consistent with repository style.

Do not create:

```text
ReprocessingPlan database table
dependency_graph table
artifact_edges table
generic orchestration-state model
```

---

# 5. Plan Enum Freeze

Use a typed enum equivalent to:

```text
NO_OP
FROM_PARSE
FROM_TRANSFORM
FROM_CHUNK
FROM_EMBED
```

No extra plan level is needed for V0.

`FROM_EMBED` remains a future-policy result only.

---

# 6. Reason Code Freeze

Use typed reason codes equivalent to:

```text
SOURCE_CHANGED
PARSER_CHANGED
CLEANING_CHANGED
TRANSFORMATION_CHANGED
CHUNKING_CHANGED

ARTIFACT_MISSING
ARTIFACT_INVALID

REVIEW_PENDING

EMBEDDING_PROFILE_CHANGED
EMBEDDING_INPUT_CHANGED
```

Reason codes explain the first stale dependency.

Do not use raw exception text as a planner reason.

---

# 7. ReprocessingPlan Contract

Use a typed result equivalent to:

```text
ReprocessingPlan

source_type
source_id

action
reason

source_fingerprint

requires_document_review

reusable_parsed_ref optional
reusable_transformed_ref optional

baseline_knowledge_version_id optional
```

Planner may return exact reusable artifact refs.

The execution path must **re-plan/revalidate current state before work**.

Do not blindly execute a stale plan object created earlier.

---

# 8. Document Source Fingerprint Freeze

Document source identity is:

```text
Document.content_hash
```

This is the accepted SHA-256 of immutable uploaded raw bytes.

Do not include:

```text
original_filename
storage path
upload timestamp
Document row timestamp
```

as content identity.

A genuinely different Document body remains:

```text
new Document upload
```

not mutation of the existing raw bytes.

Step 5.7 must not overwrite immutable Document raw storage.

---

# 9. Lesson Source Fingerprint Freeze

Lesson source identity is:

```text
SHA-256(canonical existing raw_lesson_snapshot/v1 bytes)
```

Reuse the accepted Step-5.2 deterministic snapshot contract.

Do not change:

```text
raw_lesson_snapshot/v1
```

Do not add a new Lesson source-hash column.

Do not bump snapshot schema version.

Use the same canonical serialization contract already used by Lesson raw snapshot creation.

Current knowledge-facing snapshot includes the accepted deterministic Lesson/Hsk/Vocabulary/Grammar fields and ordering.

---

# 10. Lesson Fingerprint Planning

For maintenance planning:

```text
current PUBLISHED Lesson state
→ build canonical raw_lesson_snapshot/v1 bytes in memory
→ SHA-256
→ compare to exact baseline ParsingRun.raw_content_hash
```

Do not persist a new raw artifact merely to inspect whether the Lesson is stale.

Persist a new Raw Lesson Snapshot only when execution actually needs `FROM_PARSE`.

No automatic rebuild from edit operations.

---

# 11. Parser Identity Freeze

Reuse persisted identities from `ParsingRun`.

Equivalent parser identities already accepted:

```text
PDF:
parser_name / parser_version from accepted PDF parser

DOCX:
parser_name / parser_version from accepted DOCX parser

TXT:
txt_utf8 / v1

Markdown:
markdown_blocks / v1

Lesson:
raw_lesson_snapshot / v1
```

Use the actual current accepted constants/functions from repository.

Do not introduce Git commit SHA as processor identity.

---

# 12. Cleaning Identity Freeze

Reuse:

```text
ParsingRun.cleaning_strategy
ParsingRun.cleaning_version
```

Current accepted desired identity:

```text
basic_text_cleaning / v1
```

Parse/Clean is one rerun boundary in V0.

A parser or cleaning change produces:

```text
FROM_PARSE
```

---

# 13. Transformation Identity Freeze

Reuse:

```text
TransformationRun.transformation_strategy
TransformationRun.transformation_version
```

Current accepted desired identity:

```text
canonical_document / v1
```

A transformation-only identity change produces:

```text
FROM_TRANSFORM
```

when exact reusable ParsedArtifactRef remains valid.

---

# 14. Chunking Identity Freeze

Reuse persisted KnowledgeVersion fields:

```text
chunking_strategy
chunking_version
chunk_size
chunk_max_chars
chunk_overlap
```

Current accepted values for new builds:

```text
structure_aware
v1
1200
1800
150
```

Do not duplicate these values into another fingerprint table.

---

# 15. Derived Fingerprints Freeze

Do **not** add persisted:

```text
parse_fingerprint
transform_fingerprint
chunk_fingerprint
```

Derive deterministic fingerprints from existing persisted data and exact artifact bytes.

Canonical serialization for derived fingerprints must be deterministic:

```text
UTF-8
sorted keys
compact separators
ensure_ascii=False where JSON is used
```

Do not hash unordered runtime dictionaries directly.

---

# 16. Parse / Clean Derived Fingerprint

Equivalent identity:

```text
hash(
  source_fingerprint,
  parser_name,
  parser_version,
  cleaning_strategy,
  cleaning_version
)
```

All fields already exist or are deterministically derived.

No schema column is required.

---

# 17. Transformation Derived Fingerprint

Equivalent identity:

```text
hash(
  exact parsed artifact identity/content,
  transformation_strategy,
  transformation_version
)
```

Use exact persisted Parsed artifact bytes/validated content reachable through the baseline `ParsingRun`.

No latest-run lookup.

No transform fingerprint column.

---

# 18. Chunk Desired-Build Fingerprint

Equivalent identity:

```text
hash(
  exact transformed artifact identity/content,
  chunking_strategy,
  chunking_version,
  target_chars,
  max_chars,
  overlap_chars
)
```

Use deterministic canonical config serialization.

Do not include:

```text
KnowledgeVersion UUID
timestamps
Chunk UUIDs
```

as desired-build identity.

---

# 19. Frozen D-065 — Approved vs Review Candidate Identity

Add:

```text
Document.approved_transformation_run_id
```

FK:

```text
→ transformation_runs.id
```

Nullable for legacy rows.

The two Document pointers have distinct meanings:

```text
review_transformation_run_id
→ current transformed candidate under human review

approved_transformation_run_id
→ last human-approved transformed artifact
```

Never infer approved artifact from:

```text
latest TransformationRun
current TransformationRun
ACTIVE KnowledgeVersion
timestamps
recency
```

---

# 20. Initial Document Approval

For first approval:

```text
approved_transformation_run_id
=
review_transformation_run_id
```

Set approved identity as part of the approval state transition.

Then preserve Step-5.6 contract:

```text
human approval COMMIT
→ downstream knowledge build
```

Downstream initial approved build must use exactly:

```text
approved_transformation_run_id
```

and persist that exact transform lineage on the new KnowledgeVersion.

---

# 21. Processor-Driven Document Re-review

If an already-approved Document becomes stale because of:

```text
parser identity/version
cleaning identity/version
transformation identity/version
```

Step 5.7 intentionally permits the controlled transition:

```text
APPROVED
→ PENDING + PROCESSING
```

Only explicit reprocessing logic may perform this transition.

Do not expose a generic client status mutation.

At re-review start:

KEEP:

```text
approved_transformation_run_id
approved_by
approved_at
old ACTIVE KnowledgeVersion
```

CLEAR:

```text
review_transformation_run_id
```

Set:

```text
review_status = PENDING
processing_status = PROCESSING
```

Claim must use the accepted Document row-lock / short-transaction pattern.

Commit before slow Parse/Transform work.

---

# 22. Document Re-review Successful Candidate

On successful required Parse/Transform work:

```text
review_status = PENDING
processing_status = PREVIEW_READY

review_transformation_run_id
→ new candidate B

approved_transformation_run_id
→ previous approved artifact A
```

Old ACTIVE knowledge remains untouched while B waits for Admin review.

Do not Chunk candidate B before re-approval.

---

# 23. Document Re-approval

When Admin approves candidate B:

```text
approved_transformation_run_id
→ B

approved_by
approved_at
→ new approval identity/time

review_status
→ APPROVED
```

Human approval commits first.

Replacement knowledge build then uses **exact B**:

```text
approved_transformation_run_id
→ exact TransformationRun
→ NEW KnowledgeVersion(PROCESSING)
→ KnowledgeVersion.transformation_run_id = B
→ Chunk
```

Do not build from prior A after B is re-approved.

---

# 24. Document Candidate Rejection With Previous Approval

If candidate B is rejected and:

```text
approved_transformation_run_id != NULL
```

this means:

```text
reject new candidate
≠
erase prior human approval
```

Restore:

```text
review_transformation_run_id
=
approved_transformation_run_id

review_status
=
APPROVED

processing_status
=
PREVIEW_READY
```

Keep:

```text
approved_transformation_run_id
approved_by
approved_at
old ACTIVE KnowledgeVersion
```

No replacement knowledge build occurs.

Candidate artifact/run history remains retained; only candidate selection is discarded.

---

# 25. Initial Review Rejection

If:

```text
approved_transformation_run_id = NULL
```

preserve Step-5.6 first-review semantics:

```text
PENDING + PREVIEW_READY
→ REJECTED
```

Do not convert first-review rejection into the re-review restore behavior.

---

# 26. Chunking-Only Document Reprocessing

If only chunking strategy/version/config is stale:

```text
do NOT reopen human review
```

Use:

```text
approved_transformation_run_id
→ exact approved TransformedArtifactRef
→ NEW KnowledgeVersion(PROCESSING)
→ persist transformation_run_id
→ Chunk
```

Do not:

```text
Parse
Transform
clear approval
change review candidate
```

---

# 27. Frozen D-066 — Migration 0010

Create exactly one Step-5.7 migration:

```text
0010_incremental_reprocessing_contract
```

with:

```text
down_revision = 0009_pipeline_orchestration_contract
```

Do not modify migrations `0001–0009`.

D-064 already widened Alembic revision storage; do not add another Alembic-width migration.

---

# 28. Migration 0010 Schema Delta

Add only:

```text
documents.approved_transformation_run_id
    nullable
    FK → transformation_runs.id
    ON DELETE SET NULL

knowledge_versions.transformation_run_id
    nullable
    FK → transformation_runs.id
    ON DELETE RESTRICT
```

Both columns remain nullable for legacy compatibility.

No other Step-5.7 schema change is authorized.

The exact FK delete semantics are frozen from accepted repository conventions:

```text
Document.review_transformation_run_id
→ transformation_runs.id
→ ON DELETE SET NULL
```

Therefore the sibling:

```text
Document.approved_transformation_run_id
```

must also use:

```text
ON DELETE SET NULL
```

This prevents deleting a Document when historical TransformationRun data is removed, while making missing approved lineage explicit as NULL.

For causal build lineage, the accepted repository already uses:

```text
TransformationRun.parsing_run_id
→ parsing_runs.id
→ ON DELETE RESTRICT
```

Therefore:

```text
KnowledgeVersion.transformation_run_id
→ transformation_runs.id
→ ON DELETE RESTRICT
```

must protect exact build lineage from silent deletion.

Do not use CASCADE for either new FK.

---

# 28A. Safe Deterministic Existing-Approved-Document Bridge

Migration 0010 MUST distinguish:

```text
safe deterministic migration of already-authoritative Step-5.6 identity
≠
guessed legacy lineage
```

Under accepted Step 5.6 / D-060, an existing approved Document may already have:

```text
review_status = APPROVED
review_transformation_run_id = A
```

where A is the exact human-reviewed artifact preserved after approval.

Migration 0010 MUST backfill:

```text
documents.approved_transformation_run_id
=
documents.review_transformation_run_id
```

ONLY when all deterministic conditions hold:

```text
Document.review_status = APPROVED

Document.review_transformation_run_id IS NOT NULL

referenced TransformationRun exists

TransformationRun.source_type = DOCUMENT

TransformationRun.document_id = Document.id

TransformationRun.status = SUCCEEDED

TransformationRun.transformed_storage_reference IS NOT NULL

TransformationRun.error_code IS NULL
```

This is not inferred from recency.

It is migration of an already-authoritative D-060 approved identity into the dedicated D-065 column.

Do NOT backfill for:

```text
PENDING Documents

REJECTED Documents

APPROVED Documents with NULL review pointer

APPROVED Documents whose referenced run is missing

run source_type mismatch

run document_id mismatch

run not SUCCEEDED

run missing transformed_storage_reference

run with non-NULL error_code
```

When deterministic approved identity cannot be proven:

```text
approved_transformation_run_id
→ remains NULL
```

Application behavior must replan/fail conservatively rather than guess.

---

# 28B. KnowledgeVersion Legacy Lineage Remains Conservative

Do NOT broadly backfill:

```text
KnowledgeVersion.transformation_run_id
```

from:

```text
latest TransformationRun

newest successful TransformationRun

Document approved pointer merely because it exists

ACTIVE status alone

timestamps

creation order
```

unless exact historical build→transform causal lineage can genuinely be proven from already-accepted persisted data.

Default legacy behavior remains:

```text
KnowledgeVersion.transformation_run_id = NULL
→ unsafe exact reuse rejected
→ conservative earlier-stage plan
```

Do not weaken D-066.

---

# 29. Forbidden Step-5.7 Persistence

Do not add:

```text
parse_fingerprint
transform_fingerprint
chunk_fingerprint

ReprocessingPlan table
dependency_graph table
artifact_edges table
generic lineage JSON replacing relational FK identity

new Lesson source_hash column
new raw_lesson_snapshot version
embedding schema
vector schema
```

Exact causal lineage is relational.

Fingerprints remain derived.

---

# 30. KnowledgeVersion Transformation Lineage

`KnowledgeVersion.transformation_run_id` means:

```text
the exact TransformationRun
whose TransformedDocument
was used to build this KnowledgeVersion's Chunk set
```

Durable lineage:

```text
KnowledgeVersion
→ exact TransformationRun
→ exact ParsingRun
→ exact raw/source fingerprint
```

No latest/current transformation selection.

---

# 31. Document KnowledgeVersion Lineage

For:

```text
initial approved build
re-approved replacement build
chunk-only rebuild
```

use:

```text
Document.approved_transformation_run_id
→ exact TransformationRun
→ create NEW KnowledgeVersion(PROCESSING)
→ KnowledgeVersion.transformation_run_id = exact run
→ Chunk
```

Successful Chunk build must not leave ambiguous transform lineage.

---

# 32. Lesson KnowledgeVersion Lineage

Lesson claim still occurs first:

```text
create PROCESSING KnowledgeVersion
→ transformation_run_id may initially be NULL
→ COMMIT durable claim
```

Then:

```text
Raw Snapshot
→ Parse
→ Transform
```

After Transform succeeds and before Chunk completes:

```text
KnowledgeVersion.transformation_run_id
=
exact successful TransformationRun.id
```

Then:

```text
Chunk exact transformed artifact into that version
```

If failure occurs before Transform succeeds:

```text
transformation_run_id may remain NULL
version → FAILED
```

A successful Chunk build must not leave `transformation_run_id` ambiguous.

---

# 33. Legacy NULL Lineage

For legacy KnowledgeVersion rows:

```text
transformation_run_id = NULL
```

do not guess using:

```text
newest TransformationRun
latest successful TransformationRun
timestamps
creation order
```

Planner must reject unsafe exact reuse and select the earliest stage whose upstream identity can still be proven.

Prefer a conservative rebuild over guessed reuse.

---

# 34. Exact ParsedArtifactRef Reuse

Once an exact baseline `TransformationRun` is known:

```text
TransformationRun.parsing_run_id
→ exact ParsingRun
→ parsed_storage_reference
→ exact ParsedArtifactRef
```

Validate:

```text
ParsingRun.status = SUCCEEDED
artifact exists
artifact validates
source identity matches
raw_content_hash matches
parser identity matches desired identity
cleaning identity matches desired identity
```

No separate Parsed pointer is required.

Do not select latest ParsingRun.

---

# 35. Exact TransformedArtifactRef Reuse

Construct exact reusable transformed refs only from exact lineage.

Document:

```text
approved_transformation_run_id
→ exact successful TransformationRun
→ exact TransformedArtifactRef
```

Lesson:

```text
baseline KnowledgeVersion.transformation_run_id
→ exact successful TransformationRun
→ exact TransformedArtifactRef
```

Never use latest/current TransformationRun lookup.

---

# 36. Baseline KnowledgeVersion Selection

For reuse of an existing knowledge build, use the source's stable current knowledge baseline only when its identity is deterministic.

Rules:

```text
existing PROCESSING version
→ maintenance execution is blocked
→ PROCESSING_ALREADY_IN_PROGRESS
```

When an ACTIVE KnowledgeVersion exists:

```text
use the unique ACTIVE version as baseline_knowledge_version_id
```

Do not select a historical version by recency.

For Document exact approved artifact identity remains `approved_transformation_run_id`; it is not inferred from ACTIVE.

For Lesson exact transformed input of the ACTIVE baseline must come from:

```text
ACTIVE KnowledgeVersion.transformation_run_id
```

If no exact safe baseline exists, choose the earliest safe rebuild rather than guessing.

---

# 37. Artifact Reuse Rule

An existing stage output is reusable only if all are true:

```text
previous stage run = SUCCEEDED

AND
input/source fingerprint matches

AND
processor/config identity matches

AND
persisted artifact exists

AND
artifact validates

AND
source/lineage identity matches
```

Otherwise the stage is stale.

Reuse existing artifact loaders/validators.

Do not duplicate parser/transformation validation logic.

---

# 38. Raw Artifact Integrity

Document:

```text
immutable raw file
→ verify availability
→ SHA-256 bytes
→ compare Document.content_hash
```

If raw file is missing/corrupt:

```text
ARTIFACT_MISSING / ARTIFACT_INVALID
```

Do not mutate source fingerprint to hide corruption.

Lesson historical raw reuse:

```text
ParsingRun.raw_storage_reference
ParsingRun.raw_content_hash
```

must validate when used as historical lineage.

---

# 39. Parsed Artifact Integrity

Use accepted `parsed_cleaned_artifact/v1` loader/schema validation.

Verify exact source and raw hash lineage.

Missing:

```text
ARTIFACT_MISSING
```

Malformed/inconsistent:

```text
ARTIFACT_INVALID
```

Do not invoke parser only to test whether a persisted parsed artifact is valid.

---

# 40. Transformed Artifact Integrity

Use accepted:

```text
load_transformed_artifact(...)
```

and exact `TransformedArtifactRef`.

Missing:

```text
ARTIFACT_MISSING
```

Invalid canonical artifact:

```text
ARTIFACT_INVALID
```

Do not retransform merely to validate a reusable artifact.

---

# 41. Chunk Set Integrity

Planner may validate a baseline Chunk set using persisted rows and existing contracts.

Equivalent checks:

```text
KnowledgeVersion build config is complete
chunk_index is deterministic/consecutive as required
required Chunk rows exist
each content_hash satisfies accepted D-057 contract
Chunk metadata validates according to accepted schema
```

Do not rerun chunking merely to validate existing chunks.

A missing/corrupt Chunk set with valid transformed input yields:

```text
FROM_CHUNK / ARTIFACT_MISSING|ARTIFACT_INVALID
```

---

# 42. Planner Precedence Freeze

Earliest stale stage wins.

Equivalent precedence:

```text
source mismatch
→ FROM_PARSE / SOURCE_CHANGED

parser mismatch
→ FROM_PARSE / PARSER_CHANGED

cleaning mismatch
→ FROM_PARSE / CLEANING_CHANGED

parsed artifact missing
→ FROM_PARSE / ARTIFACT_MISSING

parsed artifact invalid
→ FROM_PARSE / ARTIFACT_INVALID

transformation mismatch
→ FROM_TRANSFORM / TRANSFORMATION_CHANGED

transformed artifact missing
→ FROM_TRANSFORM / ARTIFACT_MISSING

transformed artifact invalid
→ FROM_TRANSFORM / ARTIFACT_INVALID

chunking mismatch
→ FROM_CHUNK / CHUNKING_CHANGED

Chunk set missing
→ FROM_CHUNK / ARTIFACT_MISSING

Chunk set invalid
→ FROM_CHUNK / ARTIFACT_INVALID

embedding-only desired identity difference
→ FROM_EMBED

everything valid
→ NO_OP
```

When exact lineage is absent, the planner must fall back to the earliest safe stage that can be proven.

---

# 43. NO_OP Freeze

NO_OP creates:

```text
NO ParsingRun
NO TransformationRun
NO KnowledgeVersion
NO Chunk replacement
```

Repeated unchanged maintenance calls converge to NO_OP.

Do not create another version merely because a reprocess command was invoked.

---

# 44. Document REVIEW_PENDING NO_OP

Special case:

```text
Document has a matching re-review candidate
candidate is PREVIEW_READY
review_status = PENDING
candidate satisfies desired Parse/Transform identity
```

Planner returns equivalent:

```text
NO_OP / REVIEW_PENDING
```

Do not create another candidate while one matching candidate is awaiting human review.

Do not Chunk it before approval.

---

# 45. FROM_PARSE Freeze

`FROM_PARSE` means:

```text
reuse valid Raw when appropriate
→ Parse/Clean
→ Transform
→ downstream behavior by source type
```

Triggers include:

```text
SOURCE_CHANGED
PARSER_CHANGED
CLEANING_CHANGED
parsed artifact missing/invalid
unsafe exact lineage requiring parse-level recovery
```

---

# 46. Document FROM_PARSE Execution

For existing Document:

```text
reuse immutable raw bytes
→ Parse/Clean
→ Transform
→ candidate PREVIEW_READY
→ wait for Admin re-review
```

Do not create new KnowledgeVersion before re-approval.

Do not Chunk candidate automatically.

Use D-065 controlled re-review transition.

---

# 47. Lesson FROM_PARSE Execution

For PUBLISHED Lesson:

```text
create/reuse KnowledgeSource
→ allocate NEW PROCESSING KnowledgeVersion claim
→ COMMIT claim

create current canonical Raw Lesson Snapshot
→ Parse/Clean
→ Transform
→ persist exact transformation_run_id on version
→ Chunk
```

If any stage fails:

```text
new version → FAILED
old ACTIVE unchanged
```

---

# 48. FROM_TRANSFORM Freeze

`FROM_TRANSFORM` means:

```text
reuse exact valid ParsedArtifactRef
→ Transform
→ downstream behavior by source type
```

No raw parse rerun.

Trigger:

```text
transformation identity/version change
transformed artifact missing/invalid
```

when exact parsed input remains valid.

---

# 49. Document FROM_TRANSFORM Execution

Use exact ParsedArtifactRef from exact baseline lineage.

Then:

```text
Transform
→ new candidate PREVIEW_READY
→ human re-review
```

Do not Parse.

Do not Chunk before re-approval.

Preserve old approved pointer and old ACTIVE knowledge while candidate waits.

---

# 50. Lesson FROM_TRANSFORM Execution

Allocate a NEW PROCESSING KnowledgeVersion under existing concurrency protections.

Reuse exact ParsedArtifactRef.

Then:

```text
Transform
→ persist exact transformation_run_id on new version
→ Chunk
```

Do not Parse.

Failure:

```text
new version → FAILED
old ACTIVE unchanged
```

---

# 51. FROM_CHUNK Freeze

`FROM_CHUNK` means:

```text
reuse exact accepted/baseline TransformedArtifactRef
→ NEW PROCESSING KnowledgeVersion
→ persist exact transformation_run_id
→ build_chunks()
```

No Parse.

No Transform.

---

# 52. Document FROM_CHUNK

Use:

```text
Document.approved_transformation_run_id
```

not:

```text
review_transformation_run_id
```

when a different candidate is pending review.

Chunk-only changes do not reopen review.

Do not mutate:

```text
approved_by
approved_at
review_status
review candidate
```

---

# 53. Lesson FROM_CHUNK

Use:

```text
baseline KnowledgeVersion.transformation_run_id
→ exact TransformationRun
→ exact TransformedArtifactRef
```

Then:

```text
NEW PROCESSING KnowledgeVersion
→ same exact transformation_run_id
→ build_chunks()
```

Never select latest TransformationRun.

---

# 54. FROM_EMBED Freeze

Policy-only.

Planner may return:

```text
FROM_EMBED
```

for future:

```text
EmbeddingProfile change
embedding_input_version change
```

Step 5.7 must NOT:

```text
generate embeddings
write vectors
create vector index
activate KnowledgeVersion
run retrieval
```

If only embedding identity changes:

```text
no Parse
no Transform
no Chunk
no new KnowledgeVersion solely for embedding-only change
```

Pure planner tests may supply desired future embedding identity inputs.

Do not add Phase-6 persistence solely for these tests.

---

# 55. Frozen D-067 — Lesson Maintenance Trigger

PUBLISHED Lesson may mutate through accepted curriculum editing operations.

Repeated publish is **not** the reprocessing trigger.

Use explicit internal maintenance boundaries equivalent to:

```text
ReprocessingService.plan_source(...)
ReprocessingService.reprocess_source(...)
```

No automatic Lesson-edit hook.

No second publish transition.

---

# 56. No Automatic Rebuild on Lesson Edit

Do not automatically call reprocessing from:

```text
PATCH Lesson
attach Vocabulary
attach Grammar
patch Lesson-Vocabulary association
patch Lesson-Grammar association
edit shared Vocabulary
edit shared Grammar
application startup
deployment
```

An edit may make one or more Lessons stale.

It does not itself execute a rebuild.

---

# 57. Shared Vocabulary / Grammar Behavior

Canonical Vocabulary/Grammar may be shared across Lessons.

Do not assume:

```text
edit one item
→ rebuild only currently edited Lesson
```

Each requested Lesson's canonical `raw_lesson_snapshot/v1` hash determines its own stale state.

No automatic fan-out rebuild.

A future operations wrapper may inspect many Lessons by repeatedly using the same planner/service.

Do not implement a scheduler/mass rebuild engine now.

---

# 58. Lesson Explicit Maintenance Source Change

On:

```text
plan_source(LESSON, id)
```

or revalidation inside:

```text
reprocess_source(LESSON, id)
```

compute current snapshot SHA-256.

Compare against exact baseline:

```text
KnowledgeVersion.transformation_run_id
→ TransformationRun.parsing_run_id
→ ParsingRun.raw_content_hash
```

If changed:

```text
FROM_PARSE / SOURCE_CHANGED
```

Execution creates a new Raw Lesson Snapshot and full downstream build from Parse.

---

# 59. Maintenance Interface Freeze

Step 5.7 requires only internal/testable application service APIs equivalent to:

```text
ReprocessingService.plan_source(...)
ReprocessingService.reprocess_source(...)
```

No public HTTP route is required.

No CLI dependency required.

No scheduler.

No worker.

No startup scan.

No automatic deployment rebuild.

Future Admin UI/ops may wrap the same service without duplicating logic.

---

# 60. ReprocessingService Execution Rule

`reprocess_source(...)` must:

```text
re-plan/revalidate current state
→ acquire required claim/lock
→ re-check relevant state
→ execute exact plan
```

Do not trust a plan created by an earlier request without revalidation.

No generic long-lived persisted plan object.

---

# 61. Document Reprocessing Concurrency

Reuse Step-5.6 Document processing claim:

```text
Document FOR UPDATE
→ validate explicit reprocessing transition
→ set PROCESSING
→ short COMMIT
```

For processor-driven re-review:

```text
APPROVED
→ PENDING + PROCESSING
```

with D-065 pointer semantics.

If already processing:

```text
PROCESSING_ALREADY_IN_PROGRESS
```

Do not hold Document row lock across Parse/Transform.

---

# 62. Knowledge Build Concurrency

Reuse Step-5.6:

```text
KnowledgeSource FOR UPDATE
+
partial unique:
one PROCESSING KnowledgeVersion/source
```

Maintenance must not race an existing processing/build attempt.

If a PROCESSING version already exists:

```text
PROCESSING_ALREADY_IN_PROGRESS
```

Do not create a parallel replacement version.

---

# 63. New KnowledgeVersion Rule

Whenever effective Chunk output may change because of:

```text
source content
parser/cleaning
transformation
chunking
```

use a:

```text
NEW KnowledgeVersion(PROCESSING)
```

Exception:

```text
Document FROM_PARSE/FROM_TRANSFORM
→ first produce human-review candidate
→ wait
→ create replacement version only after approval
```

Never overwrite current ACTIVE Chunk rows.

---

# 64. ACTIVE Protection

Old ACTIVE remains available throughout replacement processing and Document re-review.

Failure:

```text
new PROCESSING
→ FAILED

old ACTIVE
→ unchanged
```

Do not activate in Step 5.7.

Do not mark old ACTIVE FAILED.

Do not rebuild ACTIVE Chunk rows in place.

---

# 65. Retention Freeze

Retain:

```text
Raw artifacts
Parsed artifacts
Transformed artifacts
FAILED KnowledgeVersions
SUPERSEDED KnowledgeVersions
TransformationRun history
ParsingRun history
rejected re-review candidate artifacts
```

No automatic GC.

No cleanup scheduler.

---

# 66. Provenance / Metadata Freeze

Document filename is not source identity.

Current Lesson fields included by accepted canonical snapshot, including:

```text
title
description
Vocabulary
Grammar
ordering
```

are part of source identity.

Do not introduce a separate provenance-only fingerprint schema.

If a future field genuinely needs different semantics, that is a later decision.

---

# 67. Failure Semantics

Planner errors due to absent/invalid artifact should be typed/safe.

Execution stage failures preserve accepted stage error handling and Step-5.6 failure propagation.

For a new knowledge version:

```text
failure
→ new version FAILED
→ old ACTIVE unchanged
```

For Document re-review Parse/Transform failure:

```text
processing_status = FAILED
review_status remains PENDING
approved_transformation_run_id remains old A
approved_by / approved_at remain old approval identity
old ACTIVE remains
```

Do not erase previous approval artifact merely because candidate generation failed.

The failed reprocessing attempt may later be explicitly retried through the same maintenance service.

## Failed Re-review Retry Freeze

A processor-driven re-review failure is explicitly retryable when the Document is exactly:

```text
review_status = PENDING
processing_status = FAILED
approved_transformation_run_id != NULL
```

This state means:

```text
a candidate-generation attempt failed
while a previous human-approved artifact still exists
```

On explicit:

```text
ReprocessingService.reprocess_source(...)
```

the service must re-plan/revalidate current desired state and then:

```text
BEGIN
→ lock Document
→ verify:
     review_status = PENDING
     processing_status = FAILED
     approved_transformation_run_id != NULL

→ preserve approved_transformation_run_id
→ preserve approved_by
→ preserve approved_at
→ preserve old ACTIVE KnowledgeVersion
→ ensure review_transformation_run_id is NULL
→ set processing_status = PROCESSING
→ COMMIT
```

Then execute the **newly planned earliest stale stage**.

Do NOT require:

```text
review_status = APPROVED
```

for this retry.

Do NOT route this through ordinary Step-5.6 first-processing retry semantics in a way that loses prior approval identity.

If desired processor/source identities changed again while FAILED:

```text
re-plan
→ new earliest stale stage wins
```

Do not resume an old plan blindly.

On successful retry:

```text
review_status = PENDING
processing_status = PREVIEW_READY
review_transformation_run_id = new candidate B

approved_transformation_run_id = old A
approved_by / approved_at preserved
old ACTIVE preserved
```

On repeated failure:

```text
review_status = PENDING
processing_status = FAILED
review_transformation_run_id = NULL

approved_transformation_run_id = old A
approved_by / approved_at preserved
old ACTIVE preserved
```

Existing concurrency remains:

```text
PROCESSING
→ PROCESSING_ALREADY_IN_PROGRESS
```

No new orchestration-state model.

---

# 68. Document Review APIs After D-065

Reuse existing preview/approve/reject routes/services.

Preview:

```text
review_transformation_run_id
→ current candidate
```

Approval:

```text
candidate pointer
→ approved pointer
→ commit
→ replacement build
```

Reject:

```text
if approved pointer exists:
    reject candidate
    restore previous approved state

else:
    preserve initial-review REJECTED semantics
```

Do not create a new review-history endpoint/table.

---

# 69. Initial Approval Regression

Step 5.7 must not break first-time Step-5.6 flow.

Initial ready Document:

```text
approved_transformation_run_id = NULL
review_transformation_run_id = A
PENDING + PREVIEW_READY
```

Approve:

```text
approved_transformation_run_id = A
review_status = APPROVED
approval COMMIT
→ knowledge build
→ new version.transformation_run_id = A
```

---

# 70. Step-5.6 Knowledge Retry Regression

Approved Document knowledge retry must continue to use:

```text
approved_transformation_run_id
```

After D-065 it must not rely on `review_transformation_run_id` as the authoritative approved artifact.

This matters when:

```text
review pointer = candidate B
approved pointer = old A
```

or after restoration.

Knowledge retry must not accidentally build unapproved B.

Legacy bridge regression is mandatory:

```text
pre-0010 Step-5.6 Document:
review_status = APPROVED
review_transformation_run_id = A
approved_transformation_run_id does not yet exist

A = valid successful DOCUMENT TransformationRun
    for that exact Document
```

After migration 0010:

```text
approved_transformation_run_id = A
```

Then accepted Document knowledge retry must remain usable:

```text
retry
→ approved_transformation_run_id A
→ exact transformed artifact A
→ NEW PROCESSING KnowledgeVersion
→ KnowledgeVersion.transformation_run_id = A
→ Chunk
```

Migration 0010 must not make an already-valid Step-5.6 approved Document unusable merely because the dedicated approved pointer did not exist before 0010.

---

# 71. Lesson Publish Regression

Existing Lesson publish still:

```text
DRAFT → PUBLISHED COMMIT
→ initial ingestion orchestration
```

Step 5.7 does not change this initial publish flow.

Repeated publish remains invalid and is not a reprocessing trigger.

Maintenance reprocessing is explicit and separate.

---

# 72. Migration 0010 Upgrade Tests

Verify:

```text
0009_pipeline_orchestration_contract
→ 0010_incremental_reprocessing_contract
```

Legacy application data survives.

New columns exist:

```text
documents.approved_transformation_run_id
knowledge_versions.transformation_run_id
```

Both remain nullable.

Exact FK semantics:

```text
documents.approved_transformation_run_id
→ transformation_runs.id
→ ON DELETE SET NULL

knowledge_versions.transformation_run_id
→ transformation_runs.id
→ ON DELETE RESTRICT
```

Migrations `0001–0009` remain unchanged.

## Case A — Deterministic Existing Approved Document

Before 0010:

```text
Document.review_status = APPROVED
Document.review_transformation_run_id = A

A:
source_type = DOCUMENT
document_id = exact Document.id
status = SUCCEEDED
transformed_storage_reference IS NOT NULL
error_code IS NULL
```

After upgrade:

```text
Document.approved_transformation_run_id = A
```

Verify the row remains valid and existing approved knowledge operations have exact approved identity.

## Case B — Pending Document

Before:

```text
review_status = PENDING
review_transformation_run_id = B
```

After:

```text
approved_transformation_run_id = NULL
```

Do not promote a pending candidate.

## Case C — Rejected Document

Before:

```text
review_status = REJECTED
review_transformation_run_id = B or NULL
```

After:

```text
approved_transformation_run_id = NULL
```

Do not promote a rejected candidate.

## Case D — Ambiguous / Invalid Approved Row

Cover approved rows where one deterministic requirement is false, for example:

```text
review pointer NULL
missing referenced run
run belongs to another Document
run source_type mismatch
run status != SUCCEEDED
transformed_storage_reference NULL
error_code non-NULL
```

After:

```text
approved_transformation_run_id = NULL
```

No guessed lineage.

## Case E — Legacy KnowledgeVersion

Legacy:

```text
KnowledgeVersion.transformation_run_id = NULL
```

must remain NULL unless the exact causal build→transform relationship is independently provable.

Do not perform broad KnowledgeVersion backfill from:

```text
approved Document pointer
ACTIVE status
latest/newest run
timestamps
```

## FK Delete Behavior

Test:

```text
Document.approved_transformation_run_id = A
DELETE TransformationRun A
```

according to retained-history test setup / isolated FK test.

Expected FK behavior:

```text
Document remains
approved_transformation_run_id → NULL
```

for `ON DELETE SET NULL`.

Test:

```text
KnowledgeVersion.transformation_run_id = T
DELETE TransformationRun T
```

Expected:

```text
delete is rejected by FK
KnowledgeVersion remains
transformation_run_id remains T
```

for `ON DELETE RESTRICT`.

Do not use destructive CASCADE.

---

# 73. Migration 0010 Downgrade

Downgrade:

```text
0010
→ 0009
```

must remove only Step-5.7 schema delta.

Preserve legacy/application data unrelated to the removed columns.

D-064 Alembic control-column width remains compatible.

Final migration verification:

```text
alembic current
alembic check
```

must pass at head.

---

# 74. Fingerprint Tests

Add focused tests:

```text
identical Document raw bytes
→ identical source fingerprint

filename change
→ Document source fingerprint unchanged

same Lesson canonical snapshot
→ same source hash

Lesson knowledge-content change
→ source hash changes

deterministic processor/config serialization
→ same derived fingerprint
```

Do not test Git SHA.

---

# 75. NO_OP Tests

Prove:

```text
same source
same desired processor/config
exact lineage exists
required artifacts valid
Chunk set valid
→ NO_OP
```

NO_OP creates no:

```text
ParsingRun
TransformationRun
KnowledgeVersion
Chunk replacement
```

Repeated unchanged maintenance call remains NO_OP.

---

# 76. REVIEW_PENDING Test

Given:

```text
approved artifact A
matching candidate B waiting PENDING + PREVIEW_READY
desired parse/transform identities already satisfied by B
```

planner:

```text
NO_OP / REVIEW_PENDING
```

No second candidate created.

No knowledge build started.

---

# 77. FROM_PARSE Planner Tests

Cover:

```text
source hash change
→ FROM_PARSE / SOURCE_CHANGED

parser identity change
→ FROM_PARSE / PARSER_CHANGED

cleaning identity change
→ FROM_PARSE / CLEANING_CHANGED

parsed artifact missing
→ FROM_PARSE / ARTIFACT_MISSING

parsed artifact invalid
→ FROM_PARSE / ARTIFACT_INVALID
```

Earliest stale stage must win over downstream differences.

---

# 78. FROM_PARSE Execution Tests — Document

Approved Document A:

```text
explicit reprocess
→ APPROVED → PENDING + PROCESSING
→ approved pointer stays A
→ review pointer cleared
→ Raw reused
→ Parse
→ Transform B
→ PENDING + PREVIEW_READY
→ review pointer B
→ approved pointer A
```

Verify:

```text
no Chunk
no new KnowledgeVersion before approval
old ACTIVE unchanged
```

---

# 79. FROM_PARSE Execution Tests — Lesson

Changed PUBLISHED Lesson:

```text
explicit maintenance
→ NEW PROCESSING version claim
→ current Raw Snapshot
→ Parse
→ Transform
→ persist exact transformation_run_id
→ Chunk
```

Old ACTIVE unchanged.

No repeated publish call.

---

# 80. FROM_TRANSFORM Planner Tests

Transformation identity mismatch with valid exact Parsed artifact:

```text
→ FROM_TRANSFORM / TRANSFORMATION_CHANGED
```

Transformed artifact missing/invalid:

```text
→ FROM_TRANSFORM / ARTIFACT_MISSING|ARTIFACT_INVALID
```

when parsed artifact remains valid.

---

# 81. FROM_TRANSFORM Execution — Document

Verify:

```text
exact ParsedArtifactRef reused
parse not called
Transform creates candidate B
approved A retained
candidate waits for review
no Chunk/version before reapproval
```

---

# 82. FROM_TRANSFORM Execution — Lesson

Verify:

```text
exact ParsedArtifactRef reused
parse not called
NEW PROCESSING version
Transform
version.transformation_run_id = new exact run
Chunk
```

Old ACTIVE untouched.

---

# 83. FROM_CHUNK Planner Tests

Cover:

```text
chunking strategy change
chunking version change
target_chars change
max_chars change
overlap change
Chunk set missing
Chunk set invalid
```

Expected:

```text
FROM_CHUNK
```

when exact transformed input remains valid.

---

# 84. FROM_CHUNK Execution — Document

Verify:

```text
uses approved_transformation_run_id
does not use candidate review pointer
does not parse
does not transform
does not reopen review

NEW PROCESSING version
version.transformation_run_id = approved run
Chunk
```

---

# 85. FROM_CHUNK Execution — Lesson

Verify:

```text
baseline ACTIVE KnowledgeVersion.transformation_run_id
→ exact transformed artifact

NEW PROCESSING version
→ same transform lineage
→ Chunk
```

No Parse.

No Transform.

No latest-run query.

---

# 86. FROM_EMBED Tests

Planner-only tests:

```text
embedding profile identity change
→ FROM_EMBED / EMBEDDING_PROFILE_CHANGED

embedding input identity change
→ FROM_EMBED / EMBEDDING_INPUT_CHANGED
```

Verify no:

```text
Parse
Transform
Chunk
new KnowledgeVersion
embedding generation
vector write
```

Do not add Phase-6 schema.

---

# 87. Exact Lineage Tests

Prove:

```text
KnowledgeVersion
→ exact TransformationRun
→ exact ParsingRun
→ exact raw_content_hash
```

Create multiple newer historical runs and prove they are ignored if not referenced.

No latest/newest/timestamp selection.

---

# 88. Legacy NULL Lineage Tests

Given legacy:

```text
KnowledgeVersion.transformation_run_id = NULL
```

planner must not guess.

Verify the planner chooses a conservative earlier safe stage according to what can still be proven.

Do not fabricate backfill during migration.

---

# 89. Document Initial Approval Pointer Test

First approval:

```text
review pointer = A
approved pointer = NULL
```

After approval:

```text
approved pointer = A
review pointer remains current reviewed artifact
APPROVED
```

Replacement build uses A.

---

# 90. Document Re-review Candidate Test

Given:

```text
approved pointer = A
old ACTIVE built from A
```

reprocess to B:

```text
approved pointer remains A
review pointer becomes B
review_status = PENDING
processing_status = PREVIEW_READY
old ACTIVE remains
```

---

# 91. Document Re-approval Test

Approve B:

```text
approved pointer → B
approved_by / approved_at updated
review_status → APPROVED
approval commits
→ new build uses B
→ new KnowledgeVersion.transformation_run_id = B
```

Old ACTIVE unchanged until future Phase-6 activation.

---

# 92. Document Candidate Rejection Test

Candidate B with approved A:

```text
reject
→ review pointer restored to A
→ approved pointer remains A
→ review_status = APPROVED
→ processing_status = PREVIEW_READY
→ old ACTIVE unchanged
```

No knowledge build.

Candidate run/artifact history retained.

---

# 93. First-Review Rejection Regression

When:

```text
approved pointer = NULL
```

reject initial candidate:

```text
→ REJECTED
```

Preserve Step-5.6 initial rejection semantics.

---

# 94. Document Candidate Generation Failure and Retry Test

Approved A, reprocessing starts, then Parse/Transform fails.

Verify:

```text
processing_status = FAILED
review_status = PENDING
review pointer = NULL
approved pointer = A
approved_by / approved_at preserved
old ACTIVE unchanged
```

No replacement knowledge build.

## Explicit Failed Re-review Retry

Fixture:

```text
approved artifact A

review_status = PENDING
processing_status = FAILED

approved_transformation_run_id = A
review_transformation_run_id = NULL

approved_by / approved_at populated
old ACTIVE KnowledgeVersion present
```

Call:

```text
ReprocessingService.reprocess_source(...)
```

Verify durable claim:

```text
lock Document
→ exact retryable re-review state validated
→ processing_status = PROCESSING
→ COMMIT before slow work
```

Preserve:

```text
approved_transformation_run_id = A
approved_by
approved_at
old ACTIVE
```

Execution must re-plan first.

Do not blindly resume the plan from the previous failed attempt.

Success:

```text
review_status = PENDING
processing_status = PREVIEW_READY
review_transformation_run_id = B
approved_transformation_run_id = A
old ACTIVE unchanged
```

Repeated failure:

```text
review_status = PENDING
processing_status = FAILED
review_transformation_run_id = NULL
approved_transformation_run_id = A
approved_by / approved_at preserved
old ACTIVE unchanged
```

Also prove that if desired identities changed again while FAILED:

```text
retry planner
→ new earliest stale stage wins
```

---

# 95. Lesson Explicit Maintenance Tests

Editing PUBLISHED Lesson:

```text
does NOT automatically create
Raw artifact
ParsingRun
TransformationRun
KnowledgeVersion
Chunks
```

Explicit `plan_source` detects hash difference.

Explicit `reprocess_source` performs required rebuild.

Repeated `/publish` remains invalid and is not used.

---

# 96. Shared Vocabulary / Grammar Tests

Use shared canonical item affecting two PUBLISHED Lessons.

After edit:

```text
no automatic rebuild
```

Planning each Lesson independently:

```text
affected Lesson snapshot hash differs
→ stale

unaffected Lesson
→ unchanged / NO_OP
```

Do not automatically fan out builds.

---

# 97. Safe KnowledgeVersion Tests

Any Chunk-changing rebuild:

```text
NEW PROCESSING version
```

Failure:

```text
new → FAILED
old ACTIVE unchanged
old ACTIVE Chunks unchanged
```

No activation.

No in-place ACTIVE Chunk replacement.

---

# 98. Concurrency Tests

Document processor-driven re-review:

```text
row-lock claim
→ one processing attempt
```

Second concurrent trigger:

```text
PROCESSING_ALREADY_IN_PROGRESS
```

Lesson/Chunk rebuild:

```text
KnowledgeSource FOR UPDATE
+
PROCESSING partial unique index
```

Second concurrent build rejected.

No parallel replacement versions.

---

# 99. Operations Tests

Verify no automatic:

```text
startup rebuild
deployment rebuild
edit-trigger rebuild
scheduler
worker
GC
```

`ReprocessingService.reprocess_source()` must internally re-plan/revalidate.

---

# 100. Artifact Integrity Tests

For each stage, test at least missing and malformed/inconsistent persisted artifact behavior.

Verify planner chooses the earliest safe required stage.

Examples:

```text
valid Raw + missing Parsed
→ FROM_PARSE

valid Parsed + missing Transformed
→ FROM_TRANSFORM

valid Transformed + missing Chunk set
→ FROM_CHUNK
```

Do not silently reuse invalid artifacts.

---

# 101. No Latest Selection Tests

Add source-level tests with multiple historical:

```text
ParsingRun
TransformationRun
KnowledgeVersion
```

Verify exact FK/pointer lineage controls selection.

Forbidden queries/behaviors:

```text
ORDER BY created_at DESC LIMIT 1
MAX(created_at)
newest successful TransformationRun
latest ParsingRun
```

for artifact identity selection.

---

# 102. Step-5.6 Regression Tests

Update/fix focused Step-5.6 tests as necessary for new approved pointer semantics.

Must preserve:

```text
initial Document process
preview exact candidate
approval commit-before-build
duplicate approval
knowledge retry
Lesson publish durable claim
Lesson failure propagation
ACTIVE protection
D-064 migration behavior
```

No regression.

---

# 103. No New Runtime Dependency

Expected:

```text
NO new runtime dependency
```

Reuse:

```text
Python hashlib/json
Pydantic
SQLAlchemy
PostgreSQL
Alembic
FileStorage / LocalFileStorage
existing FastAPI application/service boundaries
pytest
uv
```

Do not add incremental-processing framework.

---

# 104. Likely Files — Create

Likely create:

```text
backend/app/ingestion/reprocessing.py

backend/migrations/versions/
    0010_incremental_reprocessing_contract.py

backend/tests/
    test_step57_reprocessing_planner.py
    test_step57_reprocessing_execution.py
    test_step57_reprocessing_concurrency.py

docs/data/
    step-5.7-incremental-reprocessing-strategy.md
```

Exact test splitting may follow repository conventions.

---

# 105. Likely Files — Modify

Likely modify:

```text
backend/app/database/models/document.py
backend/app/database/models/knowledge.py

backend/app/ingestion/repository.py
backend/app/ingestion/service.py
backend/app/ingestion/parsing_service.py
backend/app/ingestion/transformation/service.py
backend/app/ingestion/orchestrator.py

backend/app/admin/service.py
```

Potentially router schemas only if existing review behavior requires narrow response compatibility updates; do not add a public reprocessing API.

Tests:

```text
backend/tests/test_database.py
backend/tests/test_migration_preservation.py
backend/tests/test_step56_document_pipeline.py
backend/tests/test_step56_lesson_pipeline.py
```

Do not perform unrelated refactors.

---

# 106. Migration Tests

Run focused migration tests covering:

```text
0009 → 0010
legacy data preservation
nullable new FKs
valid FK enforcement
no guessed backfill
0010 → 0009 downgrade
0001–0009 unchanged
```

Final:

```text
alembic current
→ 0010_incremental_reprocessing_contract

alembic check
→ PASS / no pending upgrade operations
```

---

# 107. Full Backend Regression

Run:

```text
uv run pytest
```

All required backend tests must pass.

Do not claim implementation complete if required PostgreSQL/migration verification is blocked.

Report unrelated warnings separately.

---

# 108. Step Note

Create:

```text
docs/data/step-5.7-incremental-reprocessing-strategy.md
```

Required headings:

```text
Objective
Why
Mental Model
Core Knowledge
Data Flow
Key Design Decisions
Reusable Approach
Common Mistakes
Definition of Done
Concepts Discovered
Tools Used
```

---

# 109. Step Note — Mental Model

Use:

```text
desired processing identity
→ compare to exact persisted causal lineage
→ first stale stage
→ reuse only valid upstream artifacts
→ rebuild downstream
→ preserve old ACTIVE
→ NO_OP when already satisfied
```

Document re-review:

```text
approved artifact A
+
candidate B

B waits for human review
while A remains authoritative
```

Lesson:

```text
explicit maintenance
→ current canonical snapshot hash
→ exact baseline raw hash
→ plan
→ rebuild only from first stale stage
```

---

# 110. Step Note — Core Knowledge

Include only concepts actually used, explaining:

```text
stage-level incremental processing
causal lineage
derived fingerprints
artifact integrity
first-stale-stage planning
NO_OP/idempotency
Document re-review candidate vs approved artifact
new-version replacement
ACTIVE protection
explicit maintenance trigger
source-level concurrency
```

---

# 111. Step Note — Common Mistakes

Include:

```text
selecting latest TransformationRun
selecting latest ParsingRun
using timestamps as lineage
using filename as Document source identity
changing raw_lesson_snapshot/v1 unnecessarily
persisting redundant fingerprint columns
building a Document candidate before re-approval
using review candidate for chunk-only approved rebuild
erasing old approval when candidate is rejected
treating failed re-review retry as first-time processing and losing prior approval
guessing legacy KnowledgeVersion lineage from approved pointer or ACTIVE status
automatically rebuilding on Lesson edit
using repeated publish as Lesson rebuild trigger
overwriting ACTIVE Chunk rows
creating a new KnowledgeVersion for NO_OP
creating a new KnowledgeVersion solely for FROM_EMBED
adding dependency graph / plan table
adding scheduler/worker/GC
```

---

# 112. Concepts Discovered Format

Use:

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|

Likely concepts if actually used:

```text
Incremental Reprocessing — DE
First-Stale-Stage Planning — DE
Derived Fingerprint — DE
Causal Data Lineage — DE
Artifact Reuse — DE
Artifact Integrity — DE
NO_OP / Idempotency — DE
Document Re-review Candidate — DE
Approved Artifact Identity — DE
Replacement KnowledgeVersion — DE
ACTIVE-Version Protection — DE
Explicit Maintenance Boundary — DE
Source-Level Concurrency — DE
Partial Rebuild — DE
Row Locking — SYSTEM
Typed Planner Contract — SYSTEM
```

Only record concepts actually used.

---

# 113. Tools Used Format

Use:

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|

Likely tools:

```text
Python hashlib/json — SYSTEM
Pydantic — SYSTEM
SQLAlchemy — DE
PostgreSQL — DE
Alembic — DE
FileStorage / LocalFileStorage — DE
pytest — SYSTEM
uv — SYSTEM
```

Do not list unused/future tools.

---

# 114. Scope Guardrails

Do not implement:

```text
Embedding generation
Embedding model integration
Vector storage
Vector indexing
Retrieval
Filtering
Reranking
Prompt construction
LLM generation

KnowledgeVersion activation

paragraph-level invalidation
block-level dependency graph
partial Chunk remapping
partial embedding reuse
cross-version vector copying

automatic production scheduler
automatic startup rebuild
automatic deployment rebuild
automatic edit-trigger reprocessing
automatic fan-out Lesson rebuild

Airflow
Prefect
Dagster
Celery
Kafka
Redis queue

automatic GC

public reprocessing HTTP API
new CLI dependency
new frontend UI

Step 5.8
Phase 6 implementation
```

---

# 115. Acceptance Criteria

Step 5.7 is acceptable only when all are true:

- [ ] Accepted Steps 5.1–5.6 remain compatible.
- [ ] D-065 is preserved exactly.
- [ ] D-066 is preserved exactly.
- [ ] D-067 is preserved exactly.
- [ ] `ReprocessingPlanner` exists as a decision-only boundary.
- [ ] `ReprocessingService` exists as explicit internal plan/execute boundary.
- [ ] Planner action enum is NO_OP/FROM_PARSE/FROM_TRANSFORM/FROM_CHUNK/FROM_EMBED.
- [ ] Frozen reason codes are implemented.
- [ ] Plan result is typed.
- [ ] Execution re-plans/revalidates current state.
- [ ] Document source fingerprint is `Document.content_hash`.
- [ ] Filename/path/timestamp are not Document content identity.
- [ ] Lesson source fingerprint reuses canonical `raw_lesson_snapshot/v1`.
- [ ] No Lesson snapshot version bump is introduced.
- [ ] No Lesson source-hash column is introduced.
- [ ] Parser identity comes from accepted parser name/version.
- [ ] Cleaning identity comes from accepted strategy/version.
- [ ] Transformation identity comes from accepted strategy/version.
- [ ] Chunking identity/config comes from KnowledgeVersion fields.
- [ ] Derived fingerprints use deterministic canonical serialization.
- [ ] No parse/transform/chunk fingerprint columns exist.
- [ ] Migration `0010_incremental_reprocessing_contract` follows 0009.
- [ ] Migrations 0001–0009 are unchanged.
- [ ] `documents.approved_transformation_run_id` exists and is nullable for legacy.
- [ ] `documents.approved_transformation_run_id` FK uses `ON DELETE SET NULL`.
- [ ] `knowledge_versions.transformation_run_id` exists and is nullable for legacy.
- [ ] `knowledge_versions.transformation_run_id` FK uses `ON DELETE RESTRICT`.
- [ ] Existing Step-5.6 APPROVED Documents with deterministic valid D-060 review identity are backfilled to `approved_transformation_run_id`.
- [ ] PENDING/REJECTED/ambiguous approved Document rows are not promoted to approved lineage.
- [ ] Legacy KnowledgeVersion lineage is not broadly guessed/backfilled.
- [ ] Initial Document approval sets approved pointer from review pointer.
- [ ] Processor-driven re-review preserves old approved pointer.
- [ ] Failed processor-driven re-review ends at PENDING + FAILED while preserving prior approved pointer and approval metadata.
- [ ] PENDING + FAILED + approved pointer is an explicit retryable re-review state.
- [ ] Failed re-review retry re-plans/revalidates before claiming PROCESSING.
- [ ] Failed re-review retry preserves approved identity/old ACTIVE on success and repeated failure.
- [ ] Re-review preserves approved_by/approved_at until new approval.
- [ ] Re-review preserves old ACTIVE.
- [ ] New candidate uses review pointer only.
- [ ] Re-approval moves approved pointer to candidate.
- [ ] Re-approval refreshes approved_by/approved_at.
- [ ] Candidate rejection with previous approval restores prior approved state.
- [ ] Initial rejection without prior approval preserves Step-5.6 REJECTED semantics.
- [ ] Chunk-only Document rebuild uses approved pointer.
- [ ] Chunk-only Document rebuild does not reopen review.
- [ ] KnowledgeVersion stores exact TransformationRun used for Chunk build.
- [ ] Lesson version may be NULL-lineage before transform but not after successful Chunk completion.
- [ ] Legacy NULL lineage is never guessed.
- [ ] Exact Parsed reuse follows TransformationRun → ParsingRun.
- [ ] Exact transformed reuse follows approved pointer or KnowledgeVersion transformation lineage.
- [ ] No latest/current run selection is used.
- [ ] Reuse requires SUCCEEDED run + matching input identity + processor identity + artifact existence + validation + lineage match.
- [ ] Earliest stale stage wins.
- [ ] NO_OP creates no runs/version/chunks.
- [ ] Matching pending review candidate produces NO_OP/REVIEW_PENDING.
- [ ] FROM_PARSE reuses valid Raw and rebuilds downstream.
- [ ] Document FROM_PARSE routes to re-review and does not Chunk before approval.
- [ ] Lesson FROM_PARSE creates new PROCESSING version and rebuilds downstream.
- [ ] FROM_TRANSFORM reuses exact ParsedArtifactRef.
- [ ] Document FROM_TRANSFORM routes to re-review.
- [ ] Lesson FROM_TRANSFORM persists new exact transformation lineage then Chunks.
- [ ] FROM_CHUNK reuses exact approved/baseline transformed artifact.
- [ ] FROM_CHUNK creates NEW PROCESSING KnowledgeVersion.
- [ ] FROM_CHUNK does not Parse/Transform.
- [ ] FROM_EMBED is policy-only.
- [ ] FROM_EMBED creates no new KnowledgeVersion solely for embedding-only change.
- [ ] No Phase-6 embedding/vector/retrieval implementation exists.
- [ ] PUBLISHED Lesson edits do not auto-rebuild.
- [ ] Repeated publish is not a reprocessing trigger.
- [ ] Explicit maintenance computes current Lesson snapshot hash.
- [ ] Shared Vocabulary/Grammar edits are independently detectable per Lesson.
- [ ] No automatic fan-out rebuild exists.
- [ ] Existing Document and KnowledgeSource concurrency protections are reused.
- [ ] Existing PROCESSING build blocks maintenance execution.
- [ ] No parallel replacement KnowledgeVersions are created.
- [ ] Chunk-changing rebuilds use NEW PROCESSING versions.
- [ ] Old ACTIVE versions and Chunks remain untouched.
- [ ] Failed replacement version becomes FAILED.
- [ ] No KnowledgeVersion activation is implemented.
- [ ] Raw/Parsed/Transformed/failed historical artifacts remain retained.
- [ ] No automatic GC exists.
- [ ] Focused fingerprint tests pass.
- [ ] Planner NO_OP tests pass.
- [ ] FROM_PARSE tests pass.
- [ ] FROM_TRANSFORM tests pass.
- [ ] FROM_CHUNK tests pass.
- [ ] FROM_EMBED policy tests pass.
- [ ] Exact-lineage tests pass.
- [ ] Legacy NULL-lineage tests pass.
- [ ] Document re-review/reapproval/rejection tests pass.
- [ ] Lesson maintenance tests pass.
- [ ] Concurrency tests pass.
- [ ] Migration tests cover deterministic approved-Document backfill cases A–D.
- [ ] Migration tests prove legacy KnowledgeVersion NULL lineage remains conservative.
- [ ] Migration tests prove approved-pointer `ON DELETE SET NULL`.
- [ ] Migration tests prove KnowledgeVersion-lineage `ON DELETE RESTRICT`.
- [ ] Migration upgrade/downgrade tests pass.
- [ ] Full backend regression passes.
- [ ] Alembic current/check pass.
- [ ] Step Note is complete.
- [ ] Concepts/Tools tables use project format.
- [ ] No new runtime dependency is added.
- [ ] No scope creep.

---

# 116. Suggested Verification Commands

Focused Step-5.7:

```text
uv run pytest \
  tests/test_step57_reprocessing_planner.py \
  tests/test_step57_reprocessing_execution.py \
  tests/test_step57_reprocessing_concurrency.py \
  -vv
```

Database/migration:

```text
uv run pytest \
  tests/test_database.py \
  tests/test_migration_preservation.py \
  -vv
```

Step-5.6 regressions if separated:

```text
uv run pytest \
  tests/test_step56_document_pipeline.py \
  tests/test_step56_lesson_pipeline.py \
  tests/test_step56_orchestration_concurrency.py \
  -vv
```

Full backend:

```text
uv run pytest
```

Alembic:

```text
uv run alembic current
uv run alembic check
```

Use the dedicated test PostgreSQL database.

---

# 117. Codex Constraints

Codex must:

```text
inspect current accepted Step-5.6 repository before editing
preserve accepted Step-5.6 orchestration/failure/concurrency contracts
preserve D-065 / D-066 / D-067
reuse accepted parsing/transformation/chunking services
reuse accepted artifact schemas/loaders
reuse existing source/version row-lock protections
derive fingerprints deterministically
use exact persisted causal lineage
use new migration 0010 only
perform only the frozen deterministic approved-Document bridge in migration 0010
use approved pointer ON DELETE SET NULL
use KnowledgeVersion transformation lineage ON DELETE RESTRICT
support explicit failed re-review retry state without losing prior approval
retain historical artifacts
```

Codex must NOT:

```text
change D-065
change D-066
change D-067

modify migrations 0001–0009
invent latest/current run semantics
backfill guessed legacy lineage
skip the required deterministic Step-5.6 approved-Document bridge
broadly backfill KnowledgeVersion.transform lineage from approved pointer/ACTIVE/latest/timestamps
choose different FK delete semantics
require review_status=APPROVED for failed re-review retry

add parse/transform/chunk fingerprint columns
add Lesson source_hash column
change raw_lesson_snapshot/v1
add plan/dependency/artifact-edge tables

add public reprocessing HTTP API
add scheduler
add worker/queue
add automatic edit trigger
add startup/deployment mass rebuild
add automatic GC

add embedding generation
add vectors
add retrieval
activate KnowledgeVersion
implement Step 5.8
implement Phase 6

perform unrelated refactors
add runtime dependency without reporting a blocker
```

If the actual accepted repository materially contradicts this task:

```text
STOP
→ report the exact contradiction
```

Do not silently choose a new architecture.

---

# 118. Required Codex Completion Handoff

Return:

```text
Step:
Status:

What was done:
- ...

D-065 preserved:
- ...

D-066 preserved:
- ...

D-067 preserved:
- ...

Files/components changed:
- ...

Planner boundary:
- ...

Maintenance service boundary:
- ...

Plan enum:
- ...

Reason codes:
- ...

Plan result contract:
- ...

Document source fingerprint:
- ...

Lesson source fingerprint:
- ...

Parser identity:
- ...

Cleaning identity:
- ...

Transformation identity:
- ...

Chunking identity/config:
- ...

Derived fingerprint implementation:
- ...

Migration 0010:
- revision
- down_revision
- schema delta
- deterministic existing-approved-Document bridge
- ambiguous Document behavior
- KnowledgeVersion legacy NULL-lineage behavior
- approved pointer FK ondelete
- KnowledgeVersion lineage FK ondelete

approved_transformation_run_id:
- ...

KnowledgeVersion.transformation_run_id:
- ...

Legacy approved-Document bridge:
- deterministic backfill conditions
- pending/rejected behavior
- invalid/ambiguous approved behavior

KnowledgeVersion legacy NULL-lineage behavior:
- ...

FK delete semantics:
- approved_transformation_run_id = ON DELETE SET NULL
- KnowledgeVersion.transformation_run_id = ON DELETE RESTRICT
- repository convention/evidence

Failed re-review retry:
- exact retryable state
- claim transition
- preserved approved identity
- success behavior
- repeated failure behavior
- re-planning behavior

Exact ParsedArtifactRef reuse:
- ...

Exact TransformedArtifactRef reuse:
- ...

Artifact integrity validation:
- ...

Planner precedence:
- ...

NO_OP:
- ...

FROM_PARSE:
- ...

FROM_TRANSFORM:
- ...

FROM_CHUNK:
- ...

FROM_EMBED policy:
- ...

Document initial approval:
- ...

Document re-review:
- ...

Document re-approval:
- ...

Document candidate rejection:
- ...

Document chunk-only rebuild:
- ...

Lesson maintenance trigger:
- ...

Lesson source-change detection:
- ...

Shared Vocabulary/Grammar behavior:
- ...

KnowledgeVersion lifecycle:
- ...

ACTIVE protection:
- ...

Concurrency:
- ...

Retention:
- ...

Dependencies:
- ...

Concepts added:
- ...

Tools added:
- ...

Tests / verification:
- fingerprints
- planner
- execution
- exact lineage
- Document re-review
- Lesson maintenance
- concurrency
- DB/schema
- migration deterministic backfill
- migration FK delete semantics
- failed re-review retry
- Step-5.6 regression
- full backend
- Alembic current/check

Problems / risks:
- ...

Decisions needed:
- ...

Recommended next action:
- ...
```

Do not claim COMPLETE if required tests are blocked or failing.

---

# 119. Definition of Done

Ready for Data Engineering specialist actual-code review only when:

```text
requirements satisfied

D-065 preserved
D-066 preserved
D-067 preserved

ReprocessingPlanner implemented
ReprocessingService implemented

derived fingerprints deterministic
exact causal lineage implemented
no latest/current run selection

migration 0010 verified
deterministic Step-5.6 approved-Document bridge verified
ambiguous approved Document remains NULL verified
approved pointer ON DELETE SET NULL verified
KnowledgeVersion lineage ON DELETE RESTRICT verified
approved transformation pointer verified
KnowledgeVersion transform lineage verified
legacy KnowledgeVersion NULL lineage safe

NO_OP verified
FROM_PARSE verified
FROM_TRANSFORM verified
FROM_CHUNK verified
FROM_EMBED policy-only verified

Document re-review verified
failed re-review PENDING+FAILED state verified
failed re-review retry claim/re-plan verified
failed re-review retry preserves approved identity verified
repeated retry failure preserves approved identity verified
re-approval verified
candidate rejection verified
chunk-only no-review verified

Lesson explicit maintenance verified
no edit-trigger rebuild verified
shared-content stale detection verified

new-version safety verified
ACTIVE protection verified
concurrency protection verified

artifact validation/reuse verified
retention/no-GC verified

no new runtime dependency
no public reprocessing API
no scheduler/worker
no automatic mass rebuild
no embedding/vector/retrieval
no activation
no Step 5.8

focused tests pass
DB/migration tests pass
Step-5.6 regressions pass
full backend regression passes
Alembic current/check pass

Step Note complete
Concepts/Tools correct
no scope creep
```

After Codex completes:

```text
Data Engineering Specialist
→ independent actual-code review
→ PM acceptance
```

Do not begin Step 5.8 automatically.
