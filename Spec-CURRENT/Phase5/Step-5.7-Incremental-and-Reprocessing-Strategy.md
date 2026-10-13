# Step 5.7 — Incremental / Reprocessing Strategy

## Goal

Implement a deterministic V0 strategy for detecting stale ingestion artifacts and deciding the earliest stage that must be rerun when source content or processing configuration changes.

The strategy must support:

- new Document ingestion;
- Published Lesson content changes;
- parser/cleaning/transformation/chunking changes;
- future embedding-model / embedding-input changes;
- safe reuse of valid upstream artifacts;
- safe creation of replacement KnowledgeVersions when Chunk output may change;
- no-op behavior when nothing relevant changed;
- protection of the currently ACTIVE knowledge version during rebuilds;
- explicit maintenance/admin-driven reprocessing instead of surprise mass rebuilds.

V0 incremental processing is stage-level, not per-paragraph/per-chunk optimization.

---

# Core Principle

Use:

```text
first stale stage
→ rerun that stage
→ invalidate/rebuild all dependent downstream stages
```

Reuse valid upstream outputs whose fingerprints still match.

Example:

```text
Transformation version changed

Raw Artifact        → reuse
Parsed Artifact     → reuse
Transformed Artifact→ rebuild
Chunk[]             → rebuild
Embedding           → later rebuild
```

Do not rerun the entire pipeline when an earlier stage remains valid.

---

# V0 Incremental Granularity

V0 uses:

```text
stage-level incremental processing
```

Do not implement:

```text
paragraph-level invalidation
single-block reprocessing
cross-version partial chunk remapping
partial embedding graph updates
artifact DAG database
```

The corpus is small enough that stage-level reuse is the correct complexity level.

---

# Source Immutability — Document

Raw uploaded Document bytes remain immutable.

Do not replace:

```text
documents/<id>/raw.<ext>
```

in-place with a different file body.

If a user/admin has a genuinely new file version, V0 treats it as a new uploaded Document/source input through the normal upload workflow.

This preserves provenance and avoids one Document identity representing multiple byte sequences over time.

---

# New Document

A new Document uses the full normal flow:

```text
new file
→ Raw
→ Parse/Clean
→ Transform
→ Preview
→ Admin Review
→ Approve
→ KnowledgeSource
→ KnowledgeVersion PROCESSING
→ Chunk
```

No special incremental optimization is needed for a source that has never been processed.

---

# Source Fingerprint — Document

Reuse the SHA-256 raw content hash already produced during Raw Data Ingestion.

Logical field:

```text
raw_content_hash
```

Do not use:

```text
filename
storage path
upload timestamp
```

as the source-content fingerprint.

Renaming a file does not mean its content changed.

---

# Source Fingerprint — Lesson

Published Lesson data is mutable application data.

For every Raw Lesson Snapshot, compute a deterministic source hash:

```text
source_hash = SHA-256(canonical_snapshot_json)
```

The canonical snapshot must use stable ordering and include knowledge-facing fields already approved for the Lesson snapshot, such as:

```text
lesson identity
title/relevant lesson content
Vocabulary
Grammar
ordering
source version/update marker when appropriate
```

Exclude unstable/non-semantic fields from the hash where practical.

Same logical Lesson content should produce the same source hash.

---

# Processor / Stage Versions

Track explicit stage processing identities.

Logical values include:

```text
parser_name
parser_version

cleaning_strategy
cleaning_version

transformation_strategy
transformation_version

chunking_strategy
chunking_version
chunking_config
```

Future Phase 6 adds:

```text
EmbeddingProfile
embedding_input_version
```

Do not use only Git commit SHA as the persisted business/data processing version.

Git revision may be logged separately but does not replace explicit processor versions.

---

# Stage Fingerprints

Persist or derive deterministic fingerprints for stage outputs.

Equivalent design:

## Parse/Clean fingerprint

```text
hash(
  source_hash
  + parser identity/version
  + cleaning strategy/version
)
```

## Transformation fingerprint

```text
hash(
  parsed_artifact_hash
  + transformation strategy/version
)
```

## Chunk fingerprint / desired build identity

```text
hash(
  transformed_artifact_hash
  + chunking strategy/version
  + chunking configuration
)
```

Future embedding dependency:

```text
hash(
  chunk content / identity
  + EmbeddingProfile
  + embedding_input_version
)
```

Exact serialization must be canonical and deterministic.

Do not hash unordered runtime dictionaries without stable serialization.

---

# Artifact Reuse Rule

A stage output may be reused only when all are true:

```text
stage previously SUCCEEDED
AND expected input fingerprint matches
AND processor/config fingerprint matches
AND persisted artifact still exists
AND artifact passes required integrity/validation checks
```

Otherwise the stage is stale.

---

# No-op Rule

If:

```text
source fingerprint unchanged
AND all required processor/config fingerprints unchanged
AND successful artifacts already exist
```

then:

```text
ReprocessingPlan = NO_OP
```

Do not create:

```text
new Parsed Artifact
new Transformed Artifact
new KnowledgeVersion
duplicate Chunk rows
```

solely because a retry/reprocess command was called.

---

# Invalidation Dependency Graph

Use a simple ordered dependency model:

```text
SOURCE
↓
PARSE/CLEAN
↓
TRANSFORM
↓
CHUNK
↓
EMBED
```

A change invalidates itself and every downstream stage.

Examples:

```text
SOURCE changed
→ PARSE/CLEAN stale
→ TRANSFORM stale
→ CHUNK stale
→ EMBED stale
```

```text
TRANSFORM changed
→ TRANSFORM stale
→ CHUNK stale
→ EMBED stale
```

```text
CHUNK changed
→ CHUNK stale
→ EMBED stale
```

```text
EMBEDDING PROFILE changed
→ EMBED stale only
```

---

# Reprocessing Planner

Implement a small deterministic application/domain service equivalent to:

```text
ReprocessingPlanner
```

Input conceptually:

```text
current source/artifact fingerprints
+
desired processor/config versions
```

Output a plan equivalent to:

```text
NO_OP
FROM_PARSE
FROM_TRANSFORM
FROM_CHUNK
FROM_EMBED
```

Include a reason code where useful:

```text
SOURCE_CHANGED
PARSER_CHANGED
CLEANING_CHANGED
TRANSFORMATION_CHANGED
CHUNKING_CHANGED
EMBEDDING_PROFILE_CHANGED
EMBEDDING_INPUT_CHANGED
ARTIFACT_MISSING
```

The planner must not itself execute the pipeline.

Execution remains with the existing orchestration/stage services.

---

# No ReprocessingPlan Table in V0

Do not create a persistent:

```text
reprocessing_plans
dependency_graph
artifact_edges
```

table.

The plan can be derived deterministically from persisted fingerprints/state.

Log the selected plan/reason.

Persist only data that is needed for durable artifact/version state.

---

# Source Change Rule

## Published Lesson

If Lesson source hash changes:

```text
new Raw Lesson Snapshot
→ Parse/Clean
→ Transform
→ new KnowledgeVersion PROCESSING
→ Chunk
```

Do not reuse Parsed/Transformed outputs derived from the previous content.

## Document

Because raw Document bytes are immutable in V0, a changed file body is a new Document upload and follows the full source workflow.

---

# Parser Change Rule

If parser identity/version changes:

```text
reuse immutable Raw
→ Parse/Clean again
→ Transform again
→ Chunk again
```

Do not re-upload Raw.

Any downstream artifact produced from the old parser is considered stale.

---

# Cleaning Change Rule

If cleaning strategy/version changes:

```text
reuse Raw
→ Parse/Clean again
→ Transform again
→ Chunk again
```

Parsing and Cleaning are treated as one logical rerun boundary in V0.

Do not patch the previously cleaned text incrementally.

---

# Transformation Change Rule

If only transformation strategy/version changes:

```text
reuse Parsed/Cleaned Artifact
→ Transform again
→ Chunk again
```

Do not parse Raw again.

---

# Chunking Change Rule

If only chunking strategy/version/config changes:

```text
reuse approved TransformedDocument
→ create new KnowledgeVersion PROCESSING
→ rechunk
```

Do not:

```text
reparse
retransform
force Admin content review again
```

because the approved normalized knowledge content is unchanged.

Examples that trigger this rule:

```text
target_chars changed
max_chars changed
overlap changed
structure_aware/v1 → structure_aware/v2
```

---

# Embedding Model/Profile Change Rule

When a future embedding model changes:

```text
new EmbeddingProfile
→ reuse existing Chunk[]
→ generate embeddings for the new profile
→ switch configured active profile only after success
```

Do not automatically:

```text
reparse
retransform
rechunk
create new KnowledgeVersion
```

if Chunk content is unchanged.

The EmbeddingProfile model is the correct representation for provider/model changes.

Actual embedding implementation belongs to Phase 6.

---

# Embedding Input Format Change

Future Phase 6 may define an embedding input such as:

```text
title + section + Chunk.content
```

rather than:

```text
Chunk.content
```

Track a logical:

```text
embedding_input_version
```

If only this version changes:

```text
re-embed only
```

Do not rechunk.

This rule must be reflected in the dependency model even though implementation is Phase 6.

---

# Document Re-review Rule

For an already-approved Document:

If any of these change:

```text
parser
cleaning
transformation
```

the human-visible normalized representation may change.

Required flow:

```text
Raw
→ new Parsed/Cleaned candidate
→ new TransformedDocument candidate
→ PREVIEW_READY
→ Admin re-review / re-approve
→ new KnowledgeVersion
```

Do not automatically promote changed normalized content into internal knowledge without review.

During re-review:

```text
old ACTIVE KnowledgeVersion
→ remains available
```

---

# Chunking-only Review Rule

If only Chunking changes:

```text
same approved TransformedDocument
→ new chunk boundaries
```

No Admin content re-review is required.

Chunking is a retrieval-engineering concern, not a change to the approved source representation.

---

# Provenance-only Metadata Changes

For metadata changes that do not alter normalized knowledge text/structure, such as:

```text
author
publisher
original reference
usage_rights_note
description
```

V0 behavior:

```text
update provenance metadata
→ no parse
→ no transform
→ no rechunk
```

If a future retrieval/embedding stage explicitly depends on a metadata field, that dependency must be represented in that stage's fingerprint.

Do not rebuild by default for metadata-only edits.

---

# Stage Reuse and Downstream Invalidation

Use the first mismatch rule.

Example:

```text
Parsed fingerprint matches
Transformation fingerprint mismatches

→ reuse Parsed Artifact
→ rebuild Transformed Artifact
→ rebuild Chunk set
```

Example:

```text
Chunking fingerprint matches
but persisted transformed artifact is missing

→ upstream artifact integrity check fails
→ choose appropriate safe rerun stage
```

Do not claim an artifact is reusable if its backing file is missing/corrupt.

---

# Cross-version Per-chunk Reuse

Do not implement cross-version per-chunk embedding reuse in V0.

Although Chunk `content_hash` may identify unchanged content, skip logic such as:

```text
new Chunk hash == old Chunk hash
→ copy old vector
```

for now.

Reasons:

- cross-version provenance mapping complexity;
- profile compatibility complexity;
- small corpus;
- low immediate value.

Keep `content_hash` because it may enable this optimization later.

V0 optimization stops at stage-level artifact reuse.

---

# Automatic Trigger Policy

Automatic rebuild is allowed only for clear product events where appropriate.

Recommended V0:

```text
Published Lesson knowledge content changes
→ trigger/recommend new knowledge build
```

Document:

```text
new upload
→ normal Admin process/review workflow
```

Processing-code/config changes:

```text
parser version changed
cleaning version changed
transformation version changed
chunking version/config changed
→ explicit maintenance/admin reprocessing command
```

Do not automatically scan and rebuild all knowledge at application startup/deployment.

---

# No Mass Rebuild on Deployment

Do not implement:

```text
application starts
→ detects code version change
→ rebuild entire corpus automatically
```

This creates unexpected workload and risky production behavior.

Reprocessing due to processor/config changes must be explicit.

---

# Maintenance Reprocessing Interface

Provide a simple maintenance/service/CLI boundary that reuses:

```text
ReprocessingPlanner
+
IngestionOrchestrator
```

Equivalent use cases:

```text
reprocess one source
reprocess all stale sources
reprocess due to chunking config change
inspect planned rerun reason
```

Example conceptual commands:

```text
reprocess --source <id>
reprocess --all-stale
reprocess --reason chunking_changed
```

Exact CLI framework is optional.

Do not duplicate ingestion logic inside a script.

Do not build a scheduler UI solely for V0.

---

# KnowledgeVersion Rule

Whenever the effective Chunk set may change because of:

```text
source content
parser/cleaning representation
transformation
chunking
```

build a:

```text
new KnowledgeVersion
status = PROCESSING
```

Do not overwrite Chunk records belonging to the current ACTIVE KnowledgeVersion.

---

# Safe Rebuild

Required lifecycle:

```text
old ACTIVE
↓ remains untouched

new PROCESSING
→ rebuild required stages
→ Chunk
→ later Embed
```

If the new build succeeds through all required Phase 6 stages:

```text
new → ACTIVE
old → SUPERSEDED
```

If it fails:

```text
new → FAILED
old remains ACTIVE
```

A partially rebuilt version must never become production retrieval knowledge.

---

# Activation Transaction

When Phase 6 has successfully produced all required embeddings, activate using a short transaction:

```text
validate new version fully ready
↓
new PROCESSING → ACTIVE
old ACTIVE → SUPERSEDED
↓
commit
```

Enforce only one ACTIVE KnowledgeVersion per KnowledgeSource.

Step 5.7 defines the policy; actual Phase 6 completion wiring may finalize this transition.

---

# Failed Reprocessing Retention

When a candidate rebuild fails:

```text
new KnowledgeVersion → FAILED
```

Preserve:

```text
failed version
failed/intermediate artifacts
safe error metadata/logs
```

for debugging.

Do not automatically delete them immediately.

---

# No Automatic Garbage Collection in V0

Do not implement automatic retention/GC for:

```text
Raw Artifacts
Parsed Artifacts
Transformed Artifacts
FAILED KnowledgeVersions
SUPERSEDED KnowledgeVersions
```

The V0 corpus is small.

Retaining them improves:

```text
debugging
auditability
comparison
rollback analysis
```

Add cleanup policy only when storage becomes an actual operational concern.

---

# Suggested Fingerprint Persistence

Inspect the existing ingestion/document/artifact models first.

Persist only the minimum identifiers needed to answer:

```text
what source content produced this?
which processor version produced this?
which config produced this?
```

Equivalent fields may include:

```text
input_fingerprint
output_content_hash
processor_name
processor_version
strategy/config version
```

Do not create a new relational table for every stage if artifact metadata can cleanly store these values.

Use explicit fields for stable/high-value properties rather than hiding everything in one opaque JSON object.

---

# Concurrency

Reuse Step 5.6 concurrency rules.

For the same source:

```text
max one active processing/reprocessing operation in V0
```

A maintenance reprocess request must not race an already-running build.

Do not silently create two replacement KnowledgeVersions for the same trigger.

---

# Idempotency

Running the planner/maintenance command twice with unchanged desired configuration should result in:

```text
first run
→ build if stale

second run
→ NO_OP
```

Do not generate duplicate versions when the latest successful/candidate state already satisfies the desired fingerprint set.

---

# Tests

Add focused tests covering at least:

## Fingerprints

- same Document bytes produce same source fingerprint;
- renamed file with same bytes retains same content hash behavior;
- stable Lesson snapshot produces stable source hash;
- Lesson content change changes source hash;
- deterministic config serialization produces stable stage fingerprints.

## Planner — no-op

- identical source + parser + cleaning + transform + chunk config returns `NO_OP`;
- no new KnowledgeVersion is created for NO_OP;
- missing required artifact prevents unsafe reuse.

## Planner — source change

- Lesson source change selects `FROM_PARSE`;
- changed source invalidates transform/chunk downstream;
- old artifacts are not reused as current outputs.

## Planner — parser/cleaning

- parser version change selects `FROM_PARSE`;
- cleaning version change selects `FROM_PARSE`;
- Raw artifact is reused;
- downstream transformation/chunks are rebuilt.

## Planner — transformation

- transformation version change selects `FROM_TRANSFORM`;
- Parsed artifact is reused;
- Chunk output is rebuilt.

## Planner — chunking

- chunking strategy change selects `FROM_CHUNK`;
- target/max/overlap config change selects `FROM_CHUNK`;
- approved TransformedDocument is reused;
- no parsing/transformation occurs;
- new KnowledgeVersion is created;
- no Admin content re-review is required.

## Planner — embedding

- EmbeddingProfile change selects `FROM_EMBED`;
- embedding input version change selects `FROM_EMBED`;
- no new KnowledgeVersion is required solely for embedding-profile change when Chunk content is unchanged;
- no Parse/Transform/Chunk stage runs.

## Document review

- parser/cleaning/transformation changes on approved Document require a new PREVIEW_READY candidate and re-review;
- old ACTIVE version remains available while candidate waits for approval;
- chunking-only change does not require content re-review.

## Metadata edits

- provenance-only metadata update does not trigger reprocessing;
- source/content artifacts remain unchanged.

## Safe versioning

- new build never mutates ACTIVE version;
- failed replacement becomes FAILED;
- old ACTIVE remains ACTIVE;
- successful full future build can atomically switch ACTIVE/SUPERSEDED state.

## Operational behavior

- deployment/startup does not automatically mass-reprocess corpus;
- explicit maintenance command uses the shared planner/orchestrator;
- duplicate unchanged maintenance calls converge to NO_OP;
- concurrent source rebuild requests are rejected/serialized safely.

## Retention

- failed version/artifacts remain available for inspection;
- no automatic GC removes old artifacts in V0.

---

# Reprocessing Matrix

Canonical V0 matrix:

| Change | Reuse | Rerun From | Admin Re-review |
| --- | --- | --- | --- |
| New Document | none | Full pipeline | Yes, normal review |
| Published Lesson content | immutable raw history only | Raw Snapshot / Parse | No extra doc-style review |
| Parser version | Raw | Parse/Clean | Yes for Document |
| Cleaning version | Raw | Parse/Clean | Yes for Document |
| Transformation version | Parsed/Cleaned | Transform | Yes for Document |
| Chunking strategy/config | Approved TransformedDocument | Chunk | No |
| Embedding model/profile | Chunk[] | Embed | No |
| Embedding input format | Chunk[] | Embed | No |
| Provenance-only metadata | Existing artifacts | No rebuild | No |

---

# Out of Scope

Do not implement in Step 5.7:

```text
per-paragraph incremental parsing
per-block invalidation graph
cross-version vector copying
partial chunk embedding reuse
automatic production scheduler
mass rebuild on application startup
Airflow/Prefect/Dagster
Celery/Kafka/Redis queue
automatic GC/retention cleanup
embedding generation itself
vector indexing
retrieval
reranking
prompting
LLM generation
evaluation of whether a new chunking/model version is better
```

Those belong to later phases or future optimization.

---

# Acceptance Criteria

- [ ] V0 incremental processing is stage-level.
- [ ] Raw Document bytes remain immutable.
- [ ] New Document uses normal full ingestion workflow.
- [ ] Document source fingerprint uses raw SHA-256.
- [ ] Lesson source fingerprint uses deterministic canonical snapshot hashing.
- [ ] Parser/Cleaning/Transformation/Chunking have explicit versions/config identities.
- [ ] Stage fingerprints are deterministic.
- [ ] Valid upstream artifacts can be safely reused.
- [ ] First stale stage determines rerun start.
- [ ] Same source/config/artifacts result in NO_OP.
- [ ] Source/parser/cleaning changes rerun from Parse/Clean.
- [ ] Transformation changes rerun from Transform.
- [ ] Chunking changes rerun from Chunk.
- [ ] Embedding model/input changes require Embed only.
- [ ] Document parser/cleaning/transformation changes require re-review.
- [ ] Chunking-only changes do not require re-review.
- [ ] Provenance-only metadata changes do not rebuild knowledge.
- [ ] `ReprocessingPlanner` or equivalent centralizes invalidation logic.
- [ ] No ReprocessingPlan table is required in V0.
- [ ] Cross-version per-chunk embedding reuse is deferred.
- [ ] Code/config changes do not trigger automatic mass rebuild at startup.
- [ ] Explicit maintenance reprocessing reuses planner/orchestrator logic.
- [ ] Any Chunk-changing rebuild creates a new KnowledgeVersion.
- [ ] ACTIVE versions are never overwritten during rebuild.
- [ ] Failed replacement builds leave old ACTIVE knowledge untouched.
- [ ] Failed/SUPERSEDED artifacts are retained in V0.
- [ ] No automatic GC is introduced.
- [ ] Phase 6 can continue with safe Embedding/activation behavior.

# Expected Deliverable

Incremental/reprocessing strategy plus documentation:

```text
docs/data/
└── step-5.7-incremental-reprocessing-strategy.md
```

Next Phase:

**Phase 6 — RAG & LLM**

Next Step:

**Step 6.1 — Embedding Pipeline**
