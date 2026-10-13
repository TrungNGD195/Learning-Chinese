# Codex Task — Step 7.3 Retrieval Evaluation & Rerank Threshold Calibration

## 0. Status / ownership

Implement **Step 7.3 only**.

Canonical prerequisite:

```text
Step 7.2 = DONE
dataset_version = v0.8.0
60 / 60 APPROVED
48 DEVELOPMENT / 12 HOLDOUT
OFFICIAL_GATE = PASS
```

Frozen dependency:

```text
Step 6.8-A implementation = accepted
calibration gate = OPEN

RAG_MIN_RERANK_SCORE
→ MUST be derived from Step 7.3 calibration evidence
→ MUST NOT be guessed
→ MUST NOT be written into runtime configuration in this task
```

This task is owned by DevOps & QA with AI Engineering interfaces reused as already accepted.

Do not start Step 6.8-B.

---

# 1. Objective

Build and run the retrieval-isolated evaluation for Lesson Chat RAG and produce a reproducible **threshold recommendation** for PM approval.

The task must:

1. evaluate semantic candidate retrieval at `Top 20`;
2. evaluate reranked output at `Top 5`;
3. calculate:
   - Recall@20
   - Recall@5
   - Precision@5
   - nDCG@5
   - Scope Violation Rate
   - Cases With Scope Violation
   - before/after reranker deltas;
4. support REQUIRED evidence equivalence groups;
5. collect raw `rerank_score` distributions from internal retrieval attempts;
6. sweep candidate thresholds on DEVELOPMENT only;
7. recommend one `RAG_MIN_RERANK_SCORE` candidate from DEVELOPMENT evidence;
8. verify the frozen recommendation on HOLDOUT without retuning;
9. write reproducible run artifacts;
10. leave the actual runtime threshold unchanged pending PM approval.

This is **retrieval evaluation**, not generation/E2E evaluation.

---

# 2. Required preflight against the current repository

Before changing code, inspect and reuse the actual accepted runtime interfaces from Steps 6.3–6.5 and 6.8-A.

At minimum locate the existing equivalents of:

```text
SemanticRetrievalService
RetrievalFilter / RetrievalScope
RetrievalCandidate

RerankingService
RerankedCandidate

RAG_EVIDENCE_CALIBRATION_MODE
RAG_MIN_RERANK_SCORE
```

Also inspect the current fixture/test-data strategy for resolving Step 7.2 stable evidence locators to runtime Chunks.

The Step 7.2 handoff artifact may contain only the evaluation subtree. Therefore exact backend filenames must be taken from the **current repository**, not invented from this task packet.

Hard rules:

```text
reuse current retrieval service
reuse current filtering/scope logic
reuse current reranker/provider/model
do not implement a parallel retriever
do not implement a fake reranker
do not bypass actual vector retrieval with gold evidence
do not modify database schema
```

## PM-approved fixture runtime bootstrap

The previous preflight found a real gap:

```text
Step 7.2 stable fixture locator
→ no production-shaped runtime Chunk mapping
```

PM has now approved **Option A**:

```text
accepted Step 7.2 internal fixture source
→ evaluation-only bootstrap
→ existing source/version/chunk path
→ real Chunk records
→ existing embedding path
→ ACTIVE evaluation knowledge
→ deterministic stable_locator → runtime Chunk mapping
→ existing SemanticRetrievalService
→ existing RerankingService
→ Step 7.3 evaluation
```

This bootstrap is part of the Step 7.3 evaluation harness only. It is **not** a new application architecture.

Hard constraints:

```text
no DB schema change
no RAG architecture change
no Step 7.2 ground-truth change
no physical DB UUIDs written into dataset
no text/fuzzy matching for evidence identity
no fake/in-memory retriever
no parallel retrieval implementation

stable fixture locator must be preserved through existing provenance/metadata
physical runtime IDs are run-local/generated only
reuse existing embedding/retrieval/reranking services
```

If an exact repository filename/class differs from this task, use the existing accepted equivalent.

---

# 2A. Exact accepted fixture pack to bootstrap

Input fixture pack:

```text
evaluation/fixtures/lesson_chat_rag/v0.1.0/
├── manifest.json
└── sources/
    ├── lesson-01-greetings.json
    ├── lesson-02-numbers-age.json
    ├── lesson-03-family.json
    └── internal-kb-beginner-notes.json
```

The bootstrap must validate the current accepted logical identity before mutating the evaluation database:

```text
fixture_pack = lesson_chat_rag
fixture_pack_version = 0.1.0
status = ACCEPTED_FOR_EVALUATION_FIXTURE

source_count = 4
lesson_source_count = 3
internal_kb_source_count = 1
educational_block_count = 26
trusted_external_source_count = 0
```

Exact source identities:

```text
1. fixture.lesson.hsk1.01.greetings
   kind = LESSON
   lesson_locator = fixture:hsk1:lesson:01:greetings
   blocks = 7
   intended_scope = CURRENT_LESSON

2. fixture.lesson.hsk1.02.numbers-age
   kind = LESSON
   lesson_locator = fixture:hsk1:lesson:02:numbers-age
   blocks = 7
   intended_scope = CURRENT_LESSON

3. fixture.lesson.hsk1.03.family
   kind = LESSON
   lesson_locator = fixture:hsk1:lesson:03:family
   blocks = 7
   intended_scope = CURRENT_LESSON

4. fixture.internal-kb.hsk1.beginner-notes
   kind = INTERNAL_KB
   source_locator = fixture:internal-kb:hsk1:beginner-notes
   blocks = 5
   intended_scope = INTERNAL_KB
```

Every fixture block has:

```text
source_id
block_id
stable_locator
source_locator
content_type
content
```

All 26 `stable_locator` values must be unique before bootstrap proceeds.

Do not bootstrap the trusted-external registry in Step 7.3.

## Fixture content fingerprint

The bootstrap must compute and record a deterministic fixture identity from the actual checked-in files.

Minimum:

```text
fixture_manifest_sha256
per-source SHA-256
aggregate fixture content SHA-256
```

The aggregate calculation must be deterministic: use stable relative path ordering plus exact file bytes, or an equivalently documented canonical algorithm.

For the currently reviewed fixture pack, the checked-in source bundle inspected by the specialist had:

```text
manifest.json
sha256 = 6a02b5c6d43063dcaa381586628cf9b7b3e68945025872039947f02c848b3276

sources/internal-kb-beginner-notes.json
sha256 = cef9b36e2f4a426ee49146eccae1f1df503f7494ae791144b5c01e7b1c610c0f

sources/lesson-01-greetings.json
sha256 = 64bc5a7252d14b28e72ea34934df0411f48584ab2c65b3b2c5eaf049aad6bf3f

sources/lesson-02-numbers-age.json
sha256 = 765d0ab8c7a05b010fc917538bb690add88622800e58f0aad6b437f052b31a6d

sources/lesson-03-family.json
sha256 = 797a912041b0f36417eb6c140d5869b1029205e9b3e6987825ca7808dfab94c0
```

If the current repository bytes differ, do **not** silently force these historical hashes. Record the actual checked-in hashes and verify that the logical manifest/status/source counts still match the accepted v0.1.0 fixture pack. If the semantic fixture content changed rather than formatting/packaging only:

```text
STOP
→ BLOCKED — FIXTURE DRIFT REQUIRES REVIEW
```

Do not recalibrate against silently changed fixture ground truth.

---

# 2B. Evaluation database isolation

The production retrieval path only knows `ACTIVE` knowledge. Therefore evaluation fixture knowledge must become genuinely `ACTIVE`, but it must never contaminate normal Development/Production data.

Use a **dedicated evaluation/test PostgreSQL database** with the existing project database schema and pgvector support.

Required safety contract:

```text
Step 7.3 bootstrap DB
≠ normal Development DB
≠ Production DB
```

Reuse the repository's existing Test/Evaluation database configuration and migration/bootstrap conventions where available.

Before any destructive reset/bootstrap:

1. resolve the target database identity;
2. verify the environment is explicitly Test/Evaluation;
3. verify it is not the configured normal Development/Production target;
4. fail closed if safety cannot be established.

Never implement source isolation by changing production retrieval filters to know about an evaluation-only flag.

Never add a database column such as:

```text
is_evaluation_fixture
fixture_pack_id
evaluation_run_id
```

solely for Step 7.3.

Isolation comes from the dedicated evaluation database, not a production schema change.

If the repository has no safe way to target a separate evaluation/test database without a new architecture-level persistence decision:

```text
STOP
→ BLOCKED — EVALUATION DB ISOLATION GAP
```

---

# 2C. Bootstrap lifecycle

Implement one evaluation-only bootstrap boundary following repository conventions, for example:

```text
Step73FixtureBootstrap
```

The exact class/module name may differ.

It orchestrates existing services; it must not duplicate their internals.

Canonical lifecycle:

```text
1. validate evaluation DB safety
2. validate fixture pack identity/status/counts
3. inspect/reset prior fixture-owned evaluation state as requested
4. materialize required business/source identities
5. create canonical fixture-backed source artifacts with stable provenance
6. use existing KnowledgeSource / KnowledgeVersion / Chunk path
7. run existing embedding path
8. run existing vector-readiness checks
9. activate evaluation KnowledgeVersions through existing activation service
10. verify exactly one accepted ACTIVE EmbeddingProfile
11. build deterministic stable_locator → runtime Chunk mapping
12. verify all required Step 7.2 internal evidence locators resolve
13. freeze bootstrap identity
14. run Step 7.3 retrieval evaluation through existing services
```

No LLM call is allowed anywhere in this bootstrap.

---

# 2D. Materialize the three Lesson fixture sources

The three Lesson fixtures must participate in strict `CURRENT_LESSON` retrieval through real `lesson_id` relationships.

For each accepted Lesson fixture:

```text
fixture Lesson source
→ create/reuse evaluation-only real Lesson business identity
→ produce fixture-backed canonical Lesson source artifact
→ existing LESSON KnowledgeSource
→ PROCESSING KnowledgeVersion
→ existing ChunkingService/path
→ real Chunk rows with lesson_id
```

Required Lesson mappings:

```text
fixture:hsk1:lesson:01:greetings
→ run-local Lesson.id for fixture.lesson.hsk1.01.greetings

fixture:hsk1:lesson:02:numbers-age
→ run-local Lesson.id for fixture.lesson.hsk1.02.numbers-age

fixture:hsk1:lesson:03:family
→ run-local Lesson.id for fixture.lesson.hsk1.03.family
```

Use existing curriculum/HSK prerequisites already required by the current Lesson model. Create/reuse only the minimum evaluation records necessary in the dedicated evaluation database.

The synthetic `hsk_level_number = 1` remains an evaluation fixture identity and must not be presented as official HSK certification.

## Lesson source artifact

Do not create chunks directly.

Convert the fixture Lesson source into the repository's existing canonical parsed/transformed Lesson artifact boundary, or the nearest accepted internal artifact consumed by the existing chunker.

Each fixture block must preserve:

```text
fixture_pack = lesson_chat_rag
fixture_pack_version = 0.1.0
fixture_source_id
fixture_block_id
fixture_stable_locator
fixture_source_locator
lesson_locator
content_type
```

inside existing source/provenance/metadata fields.

Do not add a schema field solely for these values.

The canonical text/structured representation must be deterministic and source-derived. Do not paraphrase with an LLM.

Then invoke the **existing** source/version/chunk services so the resulting chunks have real:

```text
Chunk.id
Chunk.knowledge_version_id
Chunk.chunk_index
Chunk.content_type
Chunk.lesson_id
source/provenance metadata
```

If current chunking combines multiple fixture blocks, preserve/aggregate all member stable locators in existing provenance/metadata.

If current chunking splits one fixture block, every derived chunk must retain that block's stable locator.

Do not force one fixture block = one runtime Chunk if the existing chunking policy says otherwise.

---

# 2E. Materialize the broader Internal-KB fixture source

Source:

```text
fixture.internal-kb.hsk1.beginner-notes
source_locator = fixture:internal-kb:hsk1:beginner-notes
blocks = 5
content_type = DOCUMENT_TEXT
```

This source must be visible to the existing `INTERNAL_KB` retrieval scope as approved internal authored knowledge, not as a Lesson and not as external data.

Use the existing internal-document/source lifecycle.

Preferred production-shaped evaluation flow:

```text
fixture internal-kb source
→ create/reuse evaluation-only internal Document/source owner
→ source_category = existing INTERNAL_AUTHORED equivalent
→ deterministic canonical TransformedDocument/artifact
→ evaluation document reaches existing approval-ready state
→ invoke existing approval/knowledge-build use case
→ KnowledgeSource(DOCUMENT)
→ KnowledgeVersion(PROCESSING)
→ existing ChunkingService/path
→ real DOCUMENT_TEXT Chunk rows
```

The fixture JSON is already specialist-reviewed structured evaluation content. The evaluation adapter may create the existing canonical transformed artifact directly; it must not invent a new parser or convert the source through a fake retrieval path.

Every canonical block must preserve:

```text
fixture_pack
fixture_pack_version
fixture_source_id
fixture_block_id
fixture_stable_locator
fixture_source_locator
content_type
```

through existing provenance/metadata.

The existing internal source category/filter semantics must make this source eligible in `INTERNAL_KB`.

Do not weaken normal approval/ACTIVE gates in runtime retrieval.

---

# 2F. Existing embedding and activation path

After all four fixture sources have complete real Chunks:

```text
KnowledgeVersion = PROCESSING
```

Use the accepted existing embedding path:

```text
Chunk[]
→ existing EmbeddingInputFormatter
→ existing EmbeddingProvider
→ real Embedding rows
```

Use the currently selected accepted `EmbeddingProfile`.

Do not:

```text
generate vectors in the evaluation code manually
store hard-coded vectors
use random vectors
mock embeddings for the actual calibration run
change embedding model/profile
```

Required readiness:

```text
all required Chunks exist
exactly one Embedding per required Chunk/profile
vector dimensions match profile
vectors are valid/non-null
pgvector query probe succeeds
```

Then use the existing activation service:

```text
PROCESSING KnowledgeVersion
→ vector readiness PASS
→ ACTIVE
```

If the evaluation database has no ACTIVE profile yet, use the existing controlled profile bootstrap/activation behavior for the already accepted baseline profile. Do not create a second simultaneous production-style ACTIVE profile.

Before evaluation starts, assert:

```text
all 4 fixture KnowledgeSources have one intended ACTIVE evaluation KnowledgeVersion
all expected fixture-derived Chunks are retrievable
the accepted embedding profile is ACTIVE
no non-fixture normal application corpus is present in the evaluation DB
```

Any embedding/readiness/activation failure blocks the benchmark. Do not downgrade it to "no evidence."

---

# 2G. Deterministic stable_locator → runtime Chunk resolver

Implement an evaluation-only resolver, following repository conventions, equivalent to:

```text
FixtureEvidenceResolver
```

Input:

```text
fixture stable_locator
+
frozen bootstrap identity
```

Output:

```text
one or more runtime Chunk IDs
```

Resolution source:

```text
ACTIVE Chunk
→ existing persisted source/provenance/metadata
→ fixture_stable_locator / aggregated fixture stable locators
```

Never use:

```text
Chunk.content == fixture text
substring search
fuzzy text match
embedding similarity
title-only matching
chunk_index guesses without provenance
```

## Mapping cardinality

Support both:

```text
one fixture stable_locator
→ one runtime Chunk
```

and:

```text
one fixture stable_locator
→ multiple runtime Chunks
```

when existing chunking splits a source block.

Also support:

```text
multiple fixture stable_locators
→ one runtime Chunk
```

when existing chunking legitimately merges adjacent blocks and preserves aggregated provenance.

## Resolver validation

Before evaluation:

```text
all 26 fixture block stable locators
→ resolve to >= 1 ACTIVE runtime Chunk
```

and every `INTERNAL_CHUNK` stable locator referenced by an APPROVED `v0.8.0` EvaluationCase must resolve.

Hard failures:

```text
referenced locator resolves to zero ACTIVE Chunks
locator provenance missing after chunking
locator maps only to FAILED/SUPERSEDED/non-active knowledge
fixture source identity conflicts
mapping uses non-fixture source unexpectedly
```

Duplicate physical Chunk IDs across several stable locators are valid only when the Chunk provenance explicitly records all those locators.

Persist the generated mapping in the evaluation run artifact, never in the dataset.

---

# 2H. Bootstrap reset, cleanup, and idempotency

The bootstrap must be safely repeatable.

Provide repository-native behavior equivalent to:

```text
bootstrap --ensure
bootstrap --reset
```

Exact CLI spelling may follow current conventions.

## `--ensure`

If the dedicated evaluation DB already contains a fixture bootstrap whose reproducibility identity matches:

```text
fixture pack/version/content hash
processor/chunking identity
embedding profile/model identity
embedding input identity
```

and integrity checks pass:

```text
reuse existing ACTIVE evaluation knowledge
→ NO_OP bootstrap
```

Do not create duplicate KnowledgeSources, KnowledgeVersions, Chunks, or Embeddings.

If identity differs or integrity fails, do not partially reuse stale downstream state.

Either:

```text
require explicit --reset
```

or use the repository's existing safe reprocessing planner if it can deterministically rebuild the correct stages.

## `--reset`

Allowed only against the verified dedicated evaluation/test database.

Reset only evaluation fixture-owned records/artifacts or recreate the dedicated evaluation DB using the existing safe test/evaluation database reset path.

Never run destructive fixture cleanup against normal Development/Production data.

After reset:

```text
bootstrap same fixture + same config
→ semantically identical source/chunk provenance
→ physical UUIDs may differ
→ stable locator mapping remains logically equivalent
```

## Cleanup after a run

Automatic cleanup is optional.

If implemented:

```text
run artifacts remain on disk/repository output
evaluation DB fixture state may be retained for debugging
```

A cleanup command must obey the same evaluation-database safety checks.

Do not make benchmark correctness depend on cleanup succeeding after artifacts have been safely written.

---

# 2I. Bootstrap reproducibility identity

Compute a deterministic logical `fixture_bootstrap_id` from at least:

```text
fixture_pack
fixture_pack_version
fixture aggregate content SHA-256

transformation/adapter identity
chunking strategy/version/config

embedding profile provider
embedding model name/version/revision if available
embedding dimensions
embedding input formatter/version

database schema migration head or equivalent schema identity
```

Do **not** include physical runtime UUIDs in the logical bootstrap ID.

Record physical generated IDs separately for diagnostics.

Two runs with the same logical bootstrap identity may have different UUIDs but must have equivalent:

```text
source identities
stable locator coverage
chunk provenance
embedding configuration
retrieval corpus semantics
```

---

# 2J. Bootstrap run artifacts

Extend the Step 7.3 run artifact to include:

```text
evaluation/runs/<run_id>/
├── manifest.json
├── fixture-bootstrap.json
├── fixture-runtime-map.json
├── cases.jsonl
├── summary.json
└── threshold-calibration.json
```

## `fixture-bootstrap.json`

Minimum:

```text
fixture_bootstrap_id
fixture_pack
fixture_pack_version
fixture content hashes
bootstrap timestamp
evaluation DB isolation marker / safe environment identity
source_count = 4
block_count = 26

per source:
  fixture source_id
  fixture source locator / lesson locator
  runtime source type
  runtime source/category identity
  run-local business owner ID when applicable
  run-local KnowledgeSource ID
  run-local ACTIVE KnowledgeVersion ID
  produced Chunk count

chunking identity
embedding profile/model identity
vector readiness result
activation result
bootstrap action = CREATED | REUSED | RESET_REBUILT
```

Do not record secrets or full DB URLs.

## `fixture-runtime-map.json`

Minimum:

```text
fixture_bootstrap_id
mapping_version

stable_locator:
  fixture_source_id
  fixture_block_id
  runtime_chunk_ids[]
  runtime_knowledge_version_id
  runtime_content_type
  runtime_lesson_id?  # run-local, when Lesson
  provenance_check = PASS
```

Physical IDs are allowed here because this is a run-local diagnostic artifact.

They must never be copied back into `development.jsonl` or `holdout.jsonl`.

---

# 2K. Bootstrap failure policy

The PM approval resolves the architecture decision, but technical integrity failures must still stop the benchmark.

Return:

```text
BLOCKED — FIXTURE BOOTSTRAP FAILED
```

for failures such as:

```text
fixture semantic drift from accepted pack
unsafe/non-isolated database target
cannot create required real Lesson/internal source identities
existing canonical source/version/chunk path cannot consume fixture-backed artifact
stable locator cannot survive existing provenance/metadata
chunking drops required locator provenance
not all 26 locators resolve
Step 7.2 referenced locator cannot resolve
embedding generation fails
vector readiness fails
activation fails
retrieval cannot see ACTIVE fixture knowledge
unexpected normal application corpus contaminates evaluation DB
```

Return:

```text
BLOCKED — EVALUATION RUNTIME UNAVAILABLE
```

for missing runtime infrastructure such as unavailable PostgreSQL/pgvector or unavailable accepted local embedding/reranker model dependencies.

Do not respond to any of these failures by:

```text
injecting gold candidates
text matching
hard-coding chunk UUIDs
mocking the actual calibration run
skipping ACTIVE gates
creating a fake vector store
creating a second retriever
```

Unit tests may still use mocks/fakes around evaluator math and orchestration seams; the actual calibration run may not.


---

# 3. Frozen evaluation checkpoints

Use the production-shaped internal retrieval pipeline:

```text
query
→ backend-owned RetrievalScope / RetrievalFilter
→ semantic retrieval Top 20
→ rerank the same candidate pool
→ reranked Top 5
```

Evaluate:

```text
Checkpoint A = semantic Top 20
Checkpoint B = reranked Top 5
```

For reranker before/after comparison:

```text
before rerank
→ first 5 from semantic Top 20 order

after rerank
→ first 5 from reranked order
```

Report:

```text
Δ Recall@5
Δ Precision@5
Δ nDCG@5
```

Do not add an unfiltered/global benchmark path that production does not use.

---

# 4. Exact dataset subset and tier-attempt plan

Use only `review_status = APPROVED` cases from dataset `v0.8.0`.

Do not mutate dataset files.

## 4.1 Excluded from Step 7.3 internal retrieval benchmark

```text
OUT_OF_DOMAIN_REFUSAL
```

Reason:

```text
domain policy may stop the request before retrieval
→ refusal correctness belongs to Step 7.5
```

Do not retrieve these 7 cases.

Do not call external retrieval for any case.

## 4.2 MULTI_TURN_CONTEXT retrieval rule

For every multi-turn case:

```text
retrieval query = current question only
```

Do not pass `conversation_context` into retrieval/reranking.

History is generation/context information, not retrieval evidence in V0.

## 4.3 Tier-attempt semantics

A single EvaluationCase may produce more than one **internal tier attempt**.

### Case expected tier = CURRENT_LESSON

Run:

```text
CURRENT_LESSON
→ POSITIVE_USABLE attempt
```

Do not also benchmark INTERNAL_KB for that case.

### Case expected tier = INTERNAL_KB

Run:

```text
CURRENT_LESSON
→ NEGATIVE_INSUFFICIENT attempt

INTERNAL_KB
→ POSITIVE_USABLE attempt
```

### Case expected tier = TRUSTED_EXTERNAL

Step 6.8-B is not implemented.

Use the case only to verify that both internal tiers are insufficient:

```text
CURRENT_LESSON
→ NEGATIVE_INSUFFICIENT attempt

INTERNAL_KB
→ NEGATIVE_INSUFFICIENT attempt
```

Do not call the external URL/provider.

### Case bucket = NO_EVIDENCE_REFUSAL

These cases have no bound current Lesson in V0.

Run only:

```text
INTERNAL_KB
→ NEGATIVE_INSUFFICIENT diagnostic attempt
```

Do not fabricate a CURRENT_LESSON binding.

## 4.4 Expected attempt counts — DEVELOPMENT

From the canonical `v0.8.0` dataset:

```text
CURRENT_LESSON positive attempts = 20
  16 CURRENT_LESSON_ANSWERABLE
  4 MULTI_TURN_CONTEXT expected CURRENT_LESSON

CURRENT_LESSON negative attempts = 16
  8 INTERNAL_KB_FALLBACK
  4 MULTI_TURN_CONTEXT expected INTERNAL_KB
  4 TRUSTED_EXTERNAL_FALLBACK

INTERNAL_KB positive attempts = 12
  8 INTERNAL_KB_FALLBACK
  4 MULTI_TURN_CONTEXT expected INTERNAL_KB

INTERNAL_KB negative attempts = 10
  6 NO_EVIDENCE_REFUSAL
  4 TRUSTED_EXTERNAL_FALLBACK

TOTAL DEVELOPMENT INTERNAL TIER ATTEMPTS = 58
```

These attempts come from 42 DEVELOPMENT cases; 6 DEVELOPMENT OOD cases are excluded.

## 4.5 Expected attempt counts — HOLDOUT

```text
CURRENT_LESSON positive attempts = 5
  4 CURRENT_LESSON_ANSWERABLE
  1 MULTI_TURN_CONTEXT expected CURRENT_LESSON

CURRENT_LESSON negative attempts = 4
  2 INTERNAL_KB_FALLBACK
  1 MULTI_TURN_CONTEXT expected INTERNAL_KB
  1 TRUSTED_EXTERNAL_FALLBACK

INTERNAL_KB positive attempts = 3
  2 INTERNAL_KB_FALLBACK
  1 MULTI_TURN_CONTEXT expected INTERNAL_KB

INTERNAL_KB negative attempts = 3
  2 NO_EVIDENCE_REFUSAL
  1 TRUSTED_EXTERNAL_FALLBACK

TOTAL HOLDOUT INTERNAL TIER ATTEMPTS = 15
```

These attempts come from 11 HOLDOUT cases; 1 HOLDOUT OOD case is excluded.

The runner must assert these counts for `dataset_version = v0.8.0` so accidental selection drift fails fast.

---

# 5. Scope derivation for each attempt

Do not use final expected tier alone as a filter.

Build the same internal scope each runtime tier would use.

## CURRENT_LESSON attempt

Require a valid `lesson_context.lesson_locator`.

Resolve that stable Lesson locator to the current repository Lesson identity.

Use strict Lesson-only retrieval scope equivalent to:

```text
source_type = LESSON
lesson_id = bound current Lesson
```

plus any already-frozen backend-owned constraints.

If a case scheduled for a CURRENT_LESSON attempt has no resolvable lesson context:

```text
fail evaluation preflight
```

## INTERNAL_KB attempt

Use the existing broader internal scope:

```text
ACTIVE internal knowledge only
published Lesson knowledge
approved CURRICULUM_MATERIAL
approved INTERNAL_AUTHORED
no external source
```

Do not exclude the current Lesson manually unless existing runtime policy does so.

## Scope violation

Scope correctness is evaluated against the **attempt scope**.

Examples:

```text
CURRENT_LESSON attempt
→ candidate from another Lesson
→ scope violation

INTERNAL_KB attempt
→ external/non-ACTIVE/unapproved candidate
→ scope violation
```

Expected:

```text
Scope Violation = zero-tolerance
```

Any scope violation must be clearly surfaced in the run summary and must prevent a clean Step 7.3 PASS.

---

# 6. Evidence identity and relevance grading

## 6.1 Evidence matching

Internal EvaluationCase evidence uses:

```text
source_kind = INTERNAL_CHUNK
stable_locator
```

Resolve stable locators to runtime Chunk identities through deterministic provenance mapping.

One stable locator may map to multiple physical chunks after materialization/chunking.

Treat every resolved physical chunk as a valid member of that evidence reference.

Do not write runtime UUIDs back to the dataset.

## 6.2 REQUIRED equivalence groups

Group `required_evidence[]` by:

```text
requirement_id
```

All REQUIRED refs sharing one `requirement_id` are equivalent members of one information requirement.

For Recall:

```text
group hit
→ at least one candidate matching any member is retrieved inside K
```

If a case has N required groups:

```text
Recall@K
=
required groups hit within K
/
N required groups
```

Singleton REQUIRED evidence remains one group.

## 6.3 Relevance grades

Per retrieved physical candidate:

```text
matches REQUIRED evidence   → 2
matches ACCEPTABLE evidence → 1
otherwise                   → 0
```

If a candidate matches both, REQUIRED wins.

Do not infer relevance from embedding score or textual similarity.

Current v0.8.0 has no approved ACCEPTABLE evidence rows, but the evaluator must support them.

## 6.4 Metrics

Compute retrieval metrics only for `POSITIVE_USABLE` attempts that have required ground truth.

### Recall@20

Group-aware REQUIRED coverage in semantic Top 20.

### Recall@5

Group-aware REQUIRED coverage in Top 5.

Calculate both:

```text
semantic_top5 Recall@5
reranked_top5 Recall@5
```

### Precision@5

```text
count(grade > 0 in Top 5) / 5
```

Missing positions count as non-relevant.

Calculate before and after rerank.

### nDCG@5

Use relevance grades `2 / 1 / 0`.

Use standard:

```text
gain(rel) = 2^rel - 1

DCG@5
= Σ gain(rel_i) / log2(i + 1)
  for ranks i = 1..5

nDCG@5
= DCG@5 / IDCG@5
```

IDCG is built from the annotated relevant evidence grades available for that attempt, truncated to 5.

For Recall, equivalence groups are explicitly group-aware as above.

For Precision/nDCG, grade retrieved candidates by their matched evidence refs; do not alter Step 7.2 ground truth.

Negative attempts do not receive Recall/nDCG as if they were answerable. Store these metric fields as `null` / not-applicable and use them for score/gate diagnostics.

---

# 7. Per-case / per-attempt result model

Keep one line per EvaluationCase in `cases.jsonl`.

A case may contain multiple `tier_attempts[]`.

Minimum logical shape:

```text
RetrievalEvaluationCaseResult
├── case_id
├── split
├── bucket
├── question
├── expected_tier
├── tier_attempts[]
│   ├── tier = CURRENT_LESSON | INTERNAL_KB
│   ├── attempt_label = POSITIVE_USABLE | NEGATIVE_INSUFFICIENT
│   ├── applied_scope
│   ├── required_evidence_groups
│   ├── semantic_candidates[]
│   │   ├── semantic_rank
│   │   ├── chunk_id
│   │   ├── stable_locator(s)
│   │   ├── retrieval_score
│   │   ├── relevance_grade
│   │   ├── matched_evidence_id?
│   │   └── scope_pass
│   ├── semantic_top20_recall
│   ├── semantic_top5_metrics
│   ├── reranked_candidates[]
│   │   ├── semantic_rank
│   │   ├── rerank_rank
│   │   ├── rerank_score
│   │   ├── relevance_grade
│   │   ├── matched_evidence_id?
│   │   └── scope_pass
│   ├── reranked_top5_metrics
│   ├── max_rerank_score
│   ├── max_relevant_rerank_score?
│   └── scope_violation
└── case_scope_violation
```

Preserve raw reranker scores exactly as returned.

Do not normalize them to 0..1 and do not call them probabilities.

---

# 8. Reranker before/after evaluation

For each positive attempt, compare the same semantic Top 20 pool:

```text
semantic first 5
vs
reranked first 5
```

Aggregate by:

```text
overall positive internal attempts
CURRENT_LESSON positive attempts
INTERNAL_KB positive attempts
dataset bucket
split
```

Report:

```text
Recall@20

semantic Recall@5
semantic Precision@5
semantic nDCG@5

reranked Recall@5
reranked Precision@5
reranked nDCG@5

Δ Recall@5
Δ Precision@5
Δ nDCG@5
```

Do not set quality/regression pass thresholds here.

---

# 9. Threshold calibration dataset

Calibration uses **DEVELOPMENT only**.

Holdout must never influence the candidate selection/recommendation.

Use all 58 DEVELOPMENT internal tier attempts.

## 9.1 Positive calibration samples

Positive attempts:

```text
20 CURRENT_LESSON positives
12 INTERNAL_KB positives
32 total
```

At candidate threshold `t`:

```text
true_evidence_accepted(attempt, t)
=
at least one grade > 0 candidate
in reranked Top 5
with rerank_score >= t
```

Report:

```text
true-evidence acceptance rate overall
true-evidence acceptance rate CURRENT_LESSON
true-evidence acceptance rate INTERNAL_KB
```

## 9.2 Negative calibration samples

Negative attempts:

```text
16 CURRENT_LESSON negatives
10 INTERNAL_KB negatives
26 total
```

For these attempts, ground truth says the tier is insufficient.

At threshold `t`:

```text
false_evidence_accepted(attempt, t)
=
at least one candidate
in reranked Top 5
with rerank_score >= t
```

Because reranked Top 5 is score-descending, this is equivalent to:

```text
max_rerank_score >= t
```

Report:

```text
false-evidence acceptance rate overall
false-evidence acceptance rate CURRENT_LESSON
false-evidence acceptance rate INTERNAL_KB
```

Also report negative score distributions separately for:

```text
fallback negatives
TRUSTED_EXTERNAL internal-tier negatives
NO_EVIDENCE diagnostics
```

---

# 10. Threshold sweep

The reranker score is model/version dependent and must remain raw.

Create threshold candidates only from DEVELOPMENT observed rerank scores.

The candidate set must be deterministic and cover every gate-decision boundary:

```text
all unique finite rerank_score values observed in DEVELOPMENT reranked Top 5
+
math.nextafter(max_observed_score, +inf)
```

Sort ascending.

Do not round candidate thresholds before evaluating them.

Human-readable reports may show a rounded display value, but the raw candidate must be preserved.

For every threshold candidate, store at least:

```text
threshold
true_evidence_acceptance_rate_overall
false_evidence_acceptance_rate_overall

true_evidence_acceptance_rate_current_lesson
false_evidence_acceptance_rate_current_lesson

true_evidence_acceptance_rate_internal_kb
false_evidence_acceptance_rate_internal_kb

positive_attempts_accepted
negative_attempts_falsely_accepted
```

Also output the Pareto frontier where:

```text
higher true-evidence acceptance is better
lower false-evidence acceptance is better
```

---

# 11. Mechanical threshold recommendation policy

This task must produce a **recommendation**, not runtime approval.

Do not invent a numeric target such as:

```text
FEAR <= 5%
TEAR >= 95%
```

Those would be new quality gates not frozen by the spec.

Use the following transparent recommendation heuristic only to select a PM-review candidate from the measured DEVELOPMENT sweep:

1. Find the minimum observed overall `false_evidence_acceptance_rate`.
2. Among thresholds with that minimum false-evidence rate, choose the one with the highest overall `true_evidence_acceptance_rate`.
3. Tie-break by the higher of:
   - minimum tier-specific true-evidence acceptance across CURRENT_LESSON and INTERNAL_KB;
4. Final tie-break:
   - choose the higher threshold.

This encodes:

```text
avoid false evidence first
→ retain as much true evidence as possible
```

without inventing a numeric pass gate.

If any of the following holds:

```text
no finite rerank scores
no positive DEVELOPMENT samples
no negative DEVELOPMENT samples
one internal tier has no positive or no negative calibration samples
recommended threshold accepts zero true evidence overall
recommended threshold accepts zero true evidence for either internal tier
```

then:

```text
recommended_threshold = null
recommendation_status = REVIEW_REQUIRED
```

and return to PM rather than guessing.

Otherwise:

```text
recommendation_status = RECOMMENDATION_READY_FOR_PM
recommended_threshold = measured raw score
```

This does **not** modify environment/runtime settings.

---

# 12. HOLDOUT verification

After DEVELOPMENT produces one recommendation:

```text
freeze recommended threshold
→ evaluate on HOLDOUT
→ do not retune
```

Use all 15 HOLDOUT internal tier attempts.

Report the same:

```text
true-evidence acceptance rate overall/by tier
false-evidence acceptance rate overall/by tier
retrieval/rerank metrics
scope violations
```

The holdout result is verification evidence for PM.

Do not search holdout thresholds and do not choose a different per-holdout value.

No numeric holdout quality gate is added in Step 7.3.

Scope violation remains zero-tolerance independently.

---

# 13. Run artifact format

Implement reproducible artifacts under:

```text
evaluation/runs/<run_id>/
├── manifest.json
├── cases.jsonl
├── summary.json
└── threshold-calibration.json
```

Do not create a database table for evaluation runs.

## manifest.json

Minimum:

```text
run_id
timestamp
evaluation_step = "7.3"
dataset_version = "v0.8.0"
dataset_schema_version
dataset_splits = ["DEVELOPMENT", "HOLDOUT"]
code_commit
embedding_profile
embedding_model
embedding_model_version/revision if available
chunking/version identity
candidate_k = 20
reranker_model
reranker_model_version/revision if available
reranker_top_k = 5
reranker config
retrieval/filter config
RAG_EVIDENCE_CALIBRATION_MODE = true
runtime RAG_MIN_RERANK_SCORE observed before run
fixture/source resolution identity
fixture_bootstrap_id
fixture pack/version/content hash
evaluation DB isolation marker
fixture source/block counts
```

`manifest.json` must point to:

```text
fixture-bootstrap.json
fixture-runtime-map.json
```

If exact model revision is not exposed by current code, record the best reproducible identity already available and do not invent one.

## cases.jsonl

One line per evaluated dataset case with `tier_attempts[]` as defined above.

Do not include OOD cases.

## summary.json

Minimum:

```text
case counts by split/bucket
tier attempt counts by split/tier/label

Recall@20
semantic Recall@5
semantic Precision@5
semantic nDCG@5
reranked Recall@5
reranked Precision@5
reranked nDCG@5

reranker metric deltas

Scope Violation Rate
Cases With Scope Violation

metrics overall
metrics by CURRENT_LESSON / INTERNAL_KB
metrics by dataset bucket

threshold recommendation status
recommended threshold
development calibration headline metrics
holdout verification headline metrics
```

## threshold-calibration.json

Minimum:

```text
calibration_artifact_version
dataset_version
reranker identity
selection_split = DEVELOPMENT
verification_split = HOLDOUT
positive/negative attempt definitions
development sample counts
threshold candidate sweep[]
pareto_frontier[]
recommendation_policy
recommendation_status
recommended_threshold
development trade-off at recommendation
holdout verification at frozen recommendation
```

The threshold recommendation is reproducible only with the same reranker identity/config.

---

# 14. CLI / execution boundary

Add a simple repository-native command/entry point following current project conventions.

Equivalent capability:

```text
run Step 7.3 retrieval evaluation
→ select dataset v0.8.0
→ run DEVELOPMENT calibration
→ freeze recommendation
→ run HOLDOUT verification
→ write artifact
```

Do not add a new framework.

Do not require an HTTP endpoint.

Do not route through LLM generation or citation code.

If the repository uses `uv`, invoke through the existing backend/project environment.

---

# 15. Configuration rules

Calibration execution may use:

```text
RAG_EVIDENCE_CALIBRATION_MODE=true
RAG_MIN_RERANK_SCORE=null/unset
```

only for this explicit evaluation/bootstrap path.

Do not change the accepted normal-runtime rule:

```text
outside calibration mode
missing/null RAG_MIN_RERANK_SCORE
→ configuration failure
```

Do not commit a guessed numeric default.

Do not update `.env`, production config, deployment config, PM decision log, or runtime threshold in this task.

PM approval happens after the calibration artifact is reviewed.

---

# 16. Tests

Add focused deterministic unit tests for at least:

## Fixture bootstrap / resolver

- fixture manifest validates exactly 4 accepted internal sources and 26 unique stable locators;
- three Lesson fixture sources create/reuse real evaluation Lesson identities;
- one broader fixture source becomes eligible approved `INTERNAL_AUTHORED` internal knowledge through existing source/version/chunk semantics;
- fixture source/block/stable locators survive into existing Chunk provenance/metadata;
- chunk merge preserves all contributing stable locators;
- chunk split preserves the originating stable locator on every derived chunk;
- all 26 stable locators resolve to one or more ACTIVE runtime Chunks;
- resolver supports one-to-many and many-to-one locator/chunk mappings;
- resolver never uses text equality/fuzzy matching;
- runtime UUIDs are never written into Step 7.2 dataset files;
- existing embedding pipeline creates real embeddings for fixture chunks;
- vector readiness must pass before activation;
- only ACTIVE evaluation knowledge is exposed to retrieval;
- bootstrap `--ensure` is idempotent / NO_OP when identity and integrity match;
- reset/rebuild produces logically equivalent locator coverage even if UUIDs change;
- destructive reset fails closed outside a verified evaluation/test database;
- fixture drift, missing provenance, missing locator, incomplete embeddings, readiness failure, activation failure, or evaluation-corpus contamination blocks the run;
- `fixture-bootstrap.json` and `fixture-runtime-map.json` contain required reproducibility fields.


## Dataset selection / attempt planning

- OOD cases excluded.
- multi-turn retrieval uses current question only.
- expected CURRENT_LESSON creates one positive Lesson attempt.
- expected INTERNAL_KB creates negative Lesson + positive Internal attempt.
- expected TRUSTED_EXTERNAL creates two negative internal attempts and no external call.
- NO_EVIDENCE creates Internal-KB negative attempt only.
- v0.8.0 attempt counts are exactly:
  - DEVELOPMENT = 58
  - HOLDOUT = 15.

## Evidence groups

- two REQUIRED evidence refs with same `requirement_id`;
- retrieving either member counts the group as hit;
- retrieving neither misses the group;
- singleton group works.

## Relevance grades

- REQUIRED = 2.
- ACCEPTABLE = 1.
- unrelated = 0.
- REQUIRED wins if identities overlap.

## Metrics

- Recall@20 group coverage.
- before/after Recall@5.
- Precision@5.
- nDCG@5 standard gain/discount.
- reranker delta calculation.
- negative attempt metrics are N/A rather than fake recall values.

## Scope

- candidate outside CURRENT_LESSON scope is violation.
- invalid INTERNAL_KB provenance is violation.
- any scope violation appears in summary.

## Threshold calibration

- sweep uses DEVELOPMENT only.
- holdout scores never influence recommended threshold.
- false acceptance uses max Top-5 rerank score.
- true acceptance requires an actually relevant candidate above threshold.
- recommendation heuristic follows the exact tie-break policy.
- pathological/no-sample conditions return REVIEW_REQUIRED.
- raw scores are not normalized.
- holdout verification uses the frozen DEVELOPMENT threshold.

## Artifact reproducibility

- required manifest fields exist.
- cases output is deterministic for deterministic mocked candidates.
- summary counts match case/attempt records.
- threshold artifact records dataset/reranker identity.

Use mocks/fakes only for unit tests around evaluator math/planning.

At least one integration-level test must wire the evaluator to the existing retrieval/reranking service boundaries without invoking an LLM.

Do not mock away the entire production retrieval interface in the integration test.

---

# 17. Documentation

Create/update:

```text
docs/evaluation/step-7.3-retrieval-evaluation.md
```

It must reflect the actual implementation and include:

## Step Note

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- Reusable approach
- Common Mistakes
- Definition of Done

## Concepts Discovered

Only concepts actually used.

Expected likely categories:

```text
Retrieval evaluation       AI
Evidence equivalence group AI
Graded relevance           AI
Rerank threshold calibration AI
Holdout verification       AI
Evaluation run artifact    SYSTEM
Reproducible evaluation    BOTH or SYSTEM only if actually used that way
```

Use only allowed categories:

```text
DE / AI / BOTH / SYSTEM
```

Do not use `QA` as a category.

## Tools Used

Only tools actually used.

## Step Specification

Update the implementation-facing Step 7.3 spec/documentation so it matches actual code and run contract.

Do not change Step 7.2 ground truth.

---

# 18. Acceptance criteria

Implementation is ready for specialist review only when:

- approved dataset `v0.8.0` is consumed without modification;
- the 4 accepted internal fixture sources are bootstrapped into a dedicated evaluation/test database;
- all 26 stable locators are preserved through existing provenance/metadata and resolve deterministically to ACTIVE runtime Chunks;
- real embeddings are generated through the accepted existing embedding path;
- vector readiness and activation use existing services;
- bootstrap is idempotent/resettable and fails closed against non-evaluation databases;
- run artifact records fixture/bootstrap identity plus run-local locator-to-Chunk mapping;
- actual production retrieval/filter/reranker boundaries are reused;
- no external retrieval is called;
- no LLM is called;
- no Step 6.8-B code is added;
- semantic Top 20 is evaluated;
- semantic pre-rerank Top 5 is evaluated;
- reranked Top 5 is evaluated;
- Recall@20, Recall@5, Precision@5, nDCG@5 are implemented;
- equivalent REQUIRED evidence groups are supported;
- reranker before/after deltas are reported;
- scope violation detection is implemented with zero-tolerance reporting;
- NO_EVIDENCE is diagnostic, not forced to return `[]`;
- OOD is excluded;
- DEVELOPMENT calibration uses exactly 58 internal tier attempts;
- HOLDOUT verification uses exactly 15 internal tier attempts;
- raw rerank scores are preserved;
- threshold sweep is DEVELOPMENT-only;
- holdout does not affect threshold selection;
- a numeric recommendation is produced only from measured results;
- no numeric threshold is written to runtime config;
- run artifacts are reproducible;
- focused tests pass;
- current project test suite relevant to touched components passes;
- docs reflect implementation;
- Step 6.8-B remains NOT STARTED;
- Step 7.3 implementation does not claim PM threshold approval.

---

# 19. Required execution result

After implementation, actually run the retrieval evaluation in the correct project environment if the required DB/models/fixture corpus are available.

Return one of:

## Success path

```text
READY_FOR_SPECIALIST_REVIEW
```

with:

```text
run_id
artifact path
dataset version
code commit
embedding identity
reranker identity

DEVELOPMENT:
  attempt counts
  retrieval metrics
  scope violations
  threshold sweep summary
  recommendation status
  recommended raw RAG_MIN_RERANK_SCORE candidate
  TEAR / FEAR overall and by tier at recommendation

HOLDOUT:
  attempt counts
  retrieval metrics
  scope violations
  TEAR / FEAR overall and by tier at frozen recommendation

tests / commands / results
files changed
docs changed
problems / risks
decisions needed
```

Explicitly state:

```text
runtime RAG_MIN_RERANK_SCORE was NOT modified
```

## Blocked execution path

If implementation is complete but a real run cannot be performed because the accepted fixture corpus cannot be resolved/materialized into the production retrieval stack:

```text
BLOCKED — FIXTURE RESOLUTION GAP
```

Return exact evidence of the missing boundary.

If required model/runtime dependencies are unavailable:

```text
BLOCKED — EVALUATION RUNTIME UNAVAILABLE
```

Return the exact missing dependency/environment issue.

Do not fabricate benchmark scores.

If calibration data exists but the recommendation policy returns no defensible threshold:

```text
REVIEW_REQUIRED — NO DEFENSIBLE THRESHOLD
```

Do not guess a value.

---

# 20. Explicit non-goals

Do NOT:

- modify `RAG_MIN_RERANK_SCORE`;
- commit a numeric threshold default;
- close the 6.8-A gate;
- start Step 6.8-B;
- call trusted external runtime retrieval;
- select an external provider/domain allowlist;
- modify Step 7.2 dataset ground truth;
- add/rewrite EvaluationCases;
- change RAG tier order;
- change embedding model;
- change reranker model;
- normalize raw reranker scores;
- alter retrieval/reranking architecture;
- add weighted retrieval/rerank fusion;
- add generation evaluation;
- call an LLM;
- add citation evaluation;
- add end-to-end fallback/refusal evaluation;
- set Recall/nDCG regression gates;
- add CI quality gates;
- add a new framework/service.

---

# 21. Codex completion handoff

Return:

```text
Step:
7.3 — Retrieval Evaluation & Rerank Threshold Calibration

Status:

What was implemented:
Files created:
Files modified:
Dependencies added/removed:

Dataset subset / attempt counts:
Runtime interfaces reused:
Evaluation DB isolation:
Fixture bootstrap lifecycle:
Fixture bootstrap ID:
Fixture source materialization:
Embedding/readiness/activation:
Fixture/stable-locator resolution:
Fixture runtime mapping artifact:
Bootstrap idempotency/reset result:
Metric implementation:
Equivalent evidence group behavior:
Scope evaluation:
Threshold sweep:
Recommendation policy:
Holdout verification:
Run artifact:

Actual calibration result:
- recommended threshold candidate:
- recommendation status:
- DEVELOPMENT TEAR/FEAR:
- HOLDOUT TEAR/FEAR:

Verification commands/results:
Tests:

Runtime config changed:
- MUST be NO

RAG_MIN_RERANK_SCORE modified:
- MUST be NO

Step 6.8-B started:
- MUST be NO

Step 7.2 ground truth changed:
- MUST be NO

Documentation:
Concepts added:
Tools added:

Problems / risks:
Decisions needed:
Recommended next action:
```

Do not claim PM approval of the threshold.
