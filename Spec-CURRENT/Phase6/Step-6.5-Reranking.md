# Step 6.5 — Reranking

## Goal

Implement a local multilingual reranking layer that refines the relevance ordering of already-filtered semantic retrieval candidates.

Input:

```text
Filtered RetrievalCandidate[<=20]
```

Output:

```text
Top-K RerankedCandidate[]
```

Core flow:

```text
Filtered RetrievalCandidate[]
↓
RerankPassageFormatter/v1
↓
RerankerProvider
↓
query-passage scoring
↓
rerank_score DESC
↓
Top 5 RerankedCandidate[]
```

V0 model:

```text
BAAI/bge-reranker-v2-m3
```

Do not broaden retrieval scope, fetch new candidates, perform prompt construction, call an LLM, or implement tier fallback in this step.

---

# Core Principle

Reranking is a relevance-refinement stage.

Correct pipeline order:

```text
Filter
→ Semantic Retrieve
→ Rerank
```

Do not:

```text
global retrieval
→ rerank
→ filter
```

Scope correctness comes before relevance refinement.

The reranker only scores candidates already admitted by the Step 6.4 retrieval scope/filter rules.

---

# Why Reranking Exists

Dense embedding retrieval is a bi-encoder stage:

```text
query embedding
↔
passage embedding
```

It is efficient for candidate generation.

The reranker performs deeper pairwise relevance scoring:

```text
(query, passage)
→ relevance score
```

Use it to reorder the Top semantic candidates before context construction.

---

# V0 Reranker Model

Use:

```text
BAAI/bge-reranker-v2-m3
```

Reasons:

```text
multilingual
Chinese/Vietnamese/English capable
local inference
compatible with current BGE-oriented retrieval stack
no per-request external API dependency
```

The reranker does not generate embeddings.

It only scores query-passage pairs.

---

# RerankerProvider

Create an abstraction equivalent to:

```python
class RerankerProvider:
    def score(
        self,
        query: str,
        passages: list[str],
    ) -> list[float]:
        ...
```

V0 implementation:

```text
BgeRerankerProvider
→ BAAI/bge-reranker-v2-m3
```

Keep provider/model-specific behavior isolated from application/service logic.

Do not let `SemanticRetrievalService` know BGE implementation details.

---

# Suggested Module Structure

Equivalent:

```text
ai/
├── embeddings/
├── retrieval/
└── reranking/
    ├── provider.py
    ├── bge_provider.py
    ├── formatter.py
    ├── service.py
    ├── schemas.py
    └── errors.py
```

Exact filenames may follow the existing codebase convention.

Do not put cross-encoder inference into:

```text
Router
ConversationService
SemanticRetrievalService
repository
```

---

# RerankingService

Create an application/service boundary equivalent to:

```text
RerankingService
```

Responsibilities:

- accept a preprocessed query;
- accept already-filtered `RetrievalCandidate[]`;
- format passage text deterministically;
- validate reranker input lengths;
- run local reranker inference;
- validate returned score count/values;
- preserve original semantic retrieval metadata;
- produce deterministic rerank ordering;
- select configured Top-K;
- fail explicitly on technical reranker failure;
- emit structured logs.

The service must not:

- search the database for new candidates;
- widen retrieval scope;
- change ACTIVE safety gates;
- call external retrieval;
- build LLM prompts.

---

# Input Candidate Set

The reranker consumes only candidates that already passed:

```text
ACTIVE EmbeddingProfile
ACTIVE KnowledgeVersion
RetrievalScope
RetrievalFilter
Semantic Retrieval
```

It must not create or discover new candidates.

Candidate identity/provenance remains unchanged.

---

# Query Input

Reuse the deterministic query text already normalized by Step 6.3:

```text
trim
Unicode NFC
light whitespace normalization
```

Do not:

```text
LLM rewrite
translate
query expand
keyword expand
```

inside reranking.

The reranker receives the actual text query.

---

# RerankPassageFormatter

Create:

```text
RerankPassageFormatter/v1
```

This is separate from `EmbeddingInputFormatter`.

The two may share helper functions, but they are separate logical contracts.

Reason:

```text
embedding input evolution
≠
reranking input evolution
```

A future change to one must not automatically force the other to change.

---

# Document Passage Format

For Document candidates:

```text
Title: <document title>
Section: <section path when available>

<Chunk.content>
```

Do not inject:

```text
retrieval score
semantic rank
database UUID
storage path
page number unless semantically necessary
```

into the reranker passage text.

---

# Lesson Passage Format

For Lesson candidates:

```text
HSK: <level>
Lesson: <lesson title>
Type: <VOCABULARY | GRAMMAR | LESSON_GENERAL>

<Chunk.content>
```

Keep formatting deterministic.

Do not mutate `Chunk.content`.

---

# No Retrieval Metadata in Model Input

Do not include:

```text
retrieval_score
semantic rank
source priority weight
```

inside reranker model text.

The reranker should estimate relevance from:

```text
query
+
semantic passage content
```

Existing retrieval metadata remains available for tracing and tie-breaking.

---

# Candidate Count

The reranker scores at most the candidate set returned by semantic retrieval.

V0 baseline:

```text
candidate_k = 20
```

Do not fetch additional candidates.

---

# Rerank Top-K

Default:

```text
rerank_top_k = 5
```

Configuration:

```text
RERANKER_TOP_K=5
```

If:

```text
candidate_count < rerank_top_k
```

return:

```text
min(candidate_count, rerank_top_k)
```

Do not fabricate/pad results.

---

# Empty Candidate List

If input is:

```text
[]
```

return:

```text
[]
```

without loading/calling the reranker model.

This is a valid no-candidate result.

---

# Rerank Score Semantics

Preserve the raw model relevance score.

Contract:

```text
higher = better
```

Do not normalize to 0..1 automatically.

Do not call the score a probability unless the chosen provider/model explicitly defines it that way.

Score scale is provider/model/version dependent.

---

# No Rerank Threshold Yet

Do not apply:

```text
rerank_score < threshold
→ discard
```

in Step 6.5.

V0 behavior:

```text
score all candidates
→ sort
→ take top K
```

Relevance thresholding requires evaluation and belongs to later RAG/evaluation policy.

---

# Final Ordering

Baseline final ordering is:

```text
rerank_score DESC
```

Do not use weighted score fusion such as:

```text
0.7 * rerank_score
+
0.3 * retrieval_score
```

because the score spaces are not calibrated/comparable and no evaluation has selected weights.

Keep original retrieval score for trace/debug only.

---

# Tie-breaking

Use deterministic tie-breaking:

```text
rerank_score DESC
→ original semantic rank ASC
→ stable candidate identity/order
```

Do not allow nondeterministic output ordering for equal scores.

---

# RerankedCandidate

Use a runtime DTO equivalent to:

```text
RerankedCandidate
├── all RetrievalCandidate fields
├── rerank_score
└── rerank_rank
```

Do not discard:

```text
semantic rank
retrieval_score
provenance
scope metadata
```

The original retrieval trace must remain inspectable.

---

# MessageRetrieval Semantics

Existing `MessageRetrieval` fields:

```text
rank
retrieval_score
rerank_score
```

V0 rule:

```text
rank
= original semantic retrieval rank
```

```text
retrieval_score
= semantic retrieval score
```

```text
rerank_score
= cross-encoder relevance score
```

Do not repurpose `rank` into rerank rank.

Runtime `rerank_rank` does not require a schema migration.

Final ordering can be reconstructed from `rerank_score`.

---

# Persist Rerank Scores for All Candidates

When a later RAG/application orchestration layer persists `MessageRetrieval`, store `rerank_score` for all candidates that were scored, not only the final Top 5.

Typical:

```text
20 semantic candidates
→ rerank all 20
→ persist trace for all 20
→ Step 6.6 consumes top 5
```

This supports:

```text
evaluation
debugging
retrieval-vs-reranking comparison
```

Storage overhead is small.

---

# Batch Reranking

Run query-passage pairs in batches.

Baseline:

```text
RERANKER_BATCH_SIZE=8
```

Example:

```text
(query, passage 1)
...
(query, passage 8)
→ batch 1
```

Cross-encoder inference is heavier than dense embedding inference, so use a smaller baseline than Step 6.1.

Batch size is configurable.

---

# Sequential Batches

V0 processes:

```text
batch 1
→ batch 2
→ batch 3
```

Do not parallelize multiple reranker batches.

Reasons:

```text
OOM risk
GPU contention
small candidate count
simpler online failure semantics
```

---

# Model Lifecycle

Use lazy model loading:

```text
first reranking request
→ load model
→ retain one provider/model instance per process
```

Do not reload the model for every request.

Lazy load avoids unnecessary startup cost when reranking is not used immediately.

---

# Device Configuration

Use a dedicated setting:

```text
RERANKER_DEVICE=auto
```

Do not assume it must equal `EMBEDDING_DEVICE`.

This allows deployment choices such as:

```text
Embedding model → GPU
Reranker       → CPU
```

or the reverse.

`auto` should select an available supported accelerator with CPU fallback.

---

# Precision Configuration

Do not hard-code:

```text
FP16 everywhere
```

Use provider/device-appropriate automatic/default precision.

Reduced precision may be used where supported, but it must not be a universal assumption in application code.

---

# Input Length Validation

Validate:

```text
query + formatted passage
```

against the reranker tokenizer/model limit.

If too long:

```text
RERANK_INPUT_TOO_LONG
```

Do not silently truncate.

Phase 5 chunk sizing should normally keep passages within safe bounds, but validation remains required.

---

# Invalid Candidate / Input Behavior

Do not partially rerank a mixed-validity candidate set.

If one candidate causes an invalid reranker input/contract failure, treat the entire reranking operation as a technical failure. Do not emit a mixed result and do not silently replace the required rerank signal with semantic ordering.

Do not return:

```text
candidate A → reranked
candidate B → no rerank
candidate C → reranked
```

in one result set.

---

# Reranker Technical Failure

The end-to-end RAG evidence policy uses calibrated `rerank_score` to decide whether evidence is usable. Therefore a technical reranker failure cannot be treated as semantic no-evidence and cannot safely masquerade as a normal semantic Top-5 result.

Required behavior:

```text
reranker success
→ return reranked candidates with rerank_score

reranker technical failure / invalid output
→ raise typed technical error
→ caller marks AI run/message FAILED
```

Log the technical error with stage/model metadata but no sensitive content/secrets.

Do not trigger another retrieval tier solely because reranking failed technically.

---

# No Automatic Retry in Same Request

Do not automatically retry reranker inference in V0.

For local model failure/OOM:

```text
attempt once
→ technical failure
→ propagate typed error
```

Immediate retry often increases latency and repeats the same failure. A user-level retry may start a new request through the normal message retry path.

---

# Invalid Reranker Output

Validate:

```text
number of scores == number of passages
all scores finite
no NaN
no Inf
```

If invalid:

```text
INVALID_RERANKER_OUTPUT
```

Then:

```text
discard rerank output
→ raise INVALID_RERANKER_OUTPUT
```

Do not persist malformed scores and do not convert invalid reranker output into a successful semantic-only result.

---

# Partial Batch Failure

If:

```text
batch 1 succeeds
batch 2 fails
```

do not use batch-1 rerank scores.

For online runtime:

```text
discard partial rerank scores
→ fallback entire candidate set to semantic order
```

This avoids mixed ranking semantics.

---

# Scope Independence

The reranker does not know or enforce:

```text
CURRENT_LESSON > INTERNAL_KB
```

It receives one already-scoped candidate set and reranks within that set.

Tier fallback and retrieval orchestration belong to Step 6.8.

---

# No Source Priority Boost

Do not add handcrafted source/category bonuses to reranker output.

Do not:

```text
Lesson + 0.2
CURRICULUM_MATERIAL + 0.1
INTERNAL_AUTHORED + 0
```

Reranker score represents query-passage relevance only.

Source priority is a separate policy concern.

---

# Duplicate Content with Different Provenance

Keep distinct candidates even when:

```text
Chunk A.content == Chunk B.content
```

if they represent different Chunk/source identities.

Do not deduplicate purely on text equality/content hash.

Provenance and citation may differ.

Context diversity/deduplication may be considered later in context construction/evaluation.

---

# Dependencies

Use:

```text
FlagEmbedding
transformers
PyTorch
```

for the V0 BGE reranker implementation.

Encapsulate external library usage behind `RerankerProvider`.

Do not introduce:

```text
LangChain
LlamaIndex
```

solely for reranking.

---

# External Reranker Providers

The provider abstraction may support future implementations such as managed reranking APIs.

Do not implement speculative providers in V0.

Only implement the local BGE provider required now.

---

# Configuration

Add/reuse settings equivalent to:

```text
RERANKER_PROVIDER=local
RERANKER_MODEL_NAME=BAAI/bge-reranker-v2-m3
RERANKER_DEVICE=auto
RERANKER_BATCH_SIZE=8
RERANKER_TOP_K=5
RERANKER_INPUT_VERSION=v1
```

Validate positive/bounded batch/top-K values.

Do not hard-code operational settings inside service/provider code.

---

# Structured Logging

Log fields equivalent to:

```text
model_name
candidate_count
rerank_top_k
batch_count
device
rerank_duration_ms
top_retrieval_score optional
top_rerank_score optional
rerank_status
fallback_used
status
error_code optional
```

Do not log full query/passage text by default in infrastructure logs.

Do not log internal model tensors.

---

# Suggested Errors

Use the normalized backend error contract.

Stable errors may include equivalents of:

```text
RERANKER_NOT_AVAILABLE
RERANK_INPUT_TOO_LONG
RERANKER_INFERENCE_FAILED
INVALID_RERANKER_OUTPUT
RERANKING_FAILED
```

These errors are technical failures. The higher RAG orchestration layer must fail the current AI run/message rather than treat them as semantic insufficiency or trigger another evidence tier.

---

# Tests

Add focused tests covering at least:

## Provider / formatter

- local BGE provider is encapsulated;
- passage formatter is deterministic;
- Document format includes title/section/content;
- Lesson format includes HSK/lesson/type/content;
- `Chunk.content` is not mutated;
- retrieval rank/score are not injected into model text.

## Candidate integrity

- reranker receives only provided candidates;
- no DB search for additional candidates occurs;
- scope/provenance stays unchanged;
- no inactive/out-of-scope candidate appears.

## Batch behavior

- baseline batch size is configurable and defaults to 8;
- batches run sequentially;
- score order aligns with input order.

## Scoring/ranking

- higher rerank score ranks first;
- raw score is not normalized to 0..1;
- no threshold is applied;
- no weighted fusion with semantic score occurs;
- semantic rank is used as tie-break;
- ordering is deterministic.

## Result contract

- RerankedCandidate preserves RetrievalCandidate fields;
- rerank_score is added;
- runtime rerank_rank is assigned;
- original semantic rank/retrieval_score remain unchanged.

## Persistence semantics

- `MessageRetrieval.rank` remains semantic rank;
- rerank_score is available for all scored candidates;
- no rerank-rank schema migration is required.

## Empty / small candidate sets

- [] returns [] without model call;
- candidate count < top-K returns all candidates;
- no fake padding.

## Input length

- overlong query-passage pair fails reranking;
- no silent truncation occurs.

## Failure semantics

- provider failure raises a typed technical error;
- technical failure is explicitly observable;
- no automatic retry occurs;
- wrong score count raises `INVALID_RERANKER_OUTPUT`;
- NaN/Inf raises `INVALID_RERANKER_OUTPUT`;
- partial batch success followed by failure discards partial scores and fails the reranking operation.

## Scope/policy boundaries

- reranker does not implement CURRENT_LESSON → INTERNAL_KB fallback;
- no source/category boost is applied;
- duplicate text with different provenance remains distinct;
- no prompt/LLM/external retrieval occurs.

---

# Verification Flow

Required smoke demo:

```text
Filtered RetrievalCandidate[<=20]
↓
RerankPassageFormatter/v1
↓
BGE reranker
↓
score each query-passage pair
↓
rerank_score DESC
↓
Top 5 RerankedCandidate[]
```

Verify:

```text
relevant candidate
→ can move above its original semantic rank
```

and:

```text
scope unchanged
candidate set not broadened
retrieval_score retained
semantic rank retained
rerank_score added
```

Failure verification:

```text
reranker unavailable/fails
→ typed technical error
→ no successful reranked result
→ higher RAG layer may mark the assistant run FAILED
```

No context packing, LLM call, scope fallback, or external retrieval is allowed in the Step 6.5 verification path.

---

# Out of Scope

Do not implement in Step 6.5:

```text
context token budgeting
prompt construction
LLM generation
CURRENT_LESSON → INTERNAL_KB fallback
external retrieval
conversation memory
citation rendering
source-priority boosts
weighted score fusion
rerank threshold tuning
dedup/diversity policy
parallel reranker workers
managed reranker APIs
LangChain/LlamaIndex
```

These belong to later Phase 6/7 work.

---

# Acceptance Criteria

- [ ] BAAI/bge-reranker-v2-m3 is the V0 local multilingual reranker.
- [ ] `RerankerProvider` abstraction exists.
- [ ] Local BGE implementation is isolated.
- [ ] `RerankingService` operates only on already-filtered retrieval candidates.
- [ ] Filter → Retrieve → Rerank order is preserved.
- [ ] Reranker does not broaden scope or search for new candidates.
- [ ] Query text reuses deterministic Step 6.3 preprocessing.
- [ ] `RerankPassageFormatter/v1` exists separately from embedding formatter.
- [ ] Retrieval rank/score are not included in model input.
- [ ] Up to 20 semantic candidates may be reranked.
- [ ] Default rerank_top_k is 5 and configurable.
- [ ] Empty candidate list returns [] without model inference.
- [ ] Raw reranker score is preserved with higher=better semantics.
- [ ] No arbitrary rerank threshold is applied.
- [ ] Final ordering uses rerank_score only.
- [ ] No embedding/reranker weighted score fusion is used.
- [ ] Deterministic tie-breaking exists.
- [ ] `RerankedCandidate` preserves original retrieval metadata.
- [ ] MessageRetrieval.rank remains semantic rank.
- [ ] rerank_score can be persisted for all scored candidates.
- [ ] Default batch size is 8 and configurable.
- [ ] Batches run sequentially in V0.
- [ ] Reranker model lazy-loads and is retained per process.
- [ ] Reranker device is configurable independently from embedding device.
- [ ] FP16 is not hard-coded globally.
- [ ] Reranker input length is validated without silent truncation.
- [ ] Technical reranker failure propagates as a typed technical failure; no semantic-only success result is produced.
- [ ] Technical reranker failure is explicit/observable.
- [ ] No automatic retry occurs in the same request.
- [ ] Invalid/partial reranker output is discarded and surfaced as a typed technical failure.
- [ ] No tier fallback/source boost/external retrieval occurs.
- [ ] Step 6.6 can directly consume the Top 5 reranked candidates.

# Expected Deliverable

Reranking foundation plus documentation:

```text
docs/ai/
└── step-6.5-reranking.md
```

Next Step:

**Step 6.6 — Prompt / Context Construction**
