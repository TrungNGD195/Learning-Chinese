# Step 6.5 — Reranking / Evidence Score — JIT Codex Task

**Status:** FROZEN / READY_FOR_PM_TASK_REVIEW  
**Owner:** AI Engineering Specialist / Codex after PM freeze  
**Prerequisite:** Step 6.4 PM-accepted DONE / CLOSED  
**Accepted Alembic head:** `0012_vector_storage_readiness`  
**PM decisions 6.5-D1..D3 are frozen. Do not run Codex until PM issues the separate execution authorization.**

---

## 1. Repository reconciliation

Accepted repository state after Step 6.4:

- `SemanticRetrievalService.retrieve(query_text, *, retrieval_filter=None)` returns already-scoped `RetrievalCandidate[]`.
- Step 6.4 pushes eligibility predicates into the pgvector SQL before cosine ordering / LIMIT.
- ACTIVE `EmbeddingProfile` and ACTIVE `KnowledgeVersion` gates remain owned by Step 6.2.
- `RetrievalCandidate` currently carries semantic rank, `distance`, `retrieval_score`, full Chunk content and normalized provenance needed by reranking.
- Step 6.3 query normalization is implemented by `QueryPreprocessor`: trim → Unicode NFC → collapse whitespace.
- `RAG_RETRIEVAL_CANDIDATE_K` is accepted as default `20`, range `1..100`, backend-owned.
- No reranking package/module exists yet.
- Current direct ML dependency is `sentence-transformers==6.1.0`; `transformers` and PyTorch are already present in the accepted lock through that runtime. `FlagEmbedding` is not currently present.
- No schema or Alembic change is required for Step 6.5.
- Existing `MessageRetrieval` semantics already reserve semantic `rank`, `retrieval_score`, and nullable `rerank_score`; persistence remains owned by later RAG/application orchestration, not Step 6.5.

### Reconciled dependency implementation direction

Latest PM instruction says not to introduce another framework when the accepted runtime can support the model directly. The official BAAI model supports direct Hugging Face Transformers sequence-classification inference. Therefore the JIT design uses a small provider around existing `transformers` + PyTorch rather than adding LangChain/LlamaIndex or requiring a new reranker framework.

If implementation imports `transformers`/`torch` directly, promote them to explicit direct project dependencies at the versions already accepted by the lock unless dependency resolution proves a compatible focused change is necessary. Do not casually upgrade the existing ML stack.

---

## 2. Problem

Dense semantic retrieval is a candidate-generation stage. A bi-encoder can place broadly related chunks in the candidate pool but does not jointly reason over `(query, passage)`.

Step 6.5 must take only the already-eligible semantic candidates and use a local cross-encoder reranker to produce a stronger relevance ordering without widening scope, changing ACTIVE safety, or inventing an evidence threshold.

---

## 3. Objective

Implement a local multilingual reranking boundary using:

```text
BAAI/bge-reranker-v2-m3
revision = 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
```

that:

1. accepts the learner query and already-filtered `RetrievalCandidate[]`;
2. builds deterministic reranker passage text;
3. scores query/passage pairs in bounded sequential batches;
4. preserves raw reranker scores;
5. preserves original semantic retrieval diagnostics/provenance;
6. sorts deterministically by reranker relevance;
7. returns configured final Top-K `RerankedCandidate[]`;
8. never applies `RAG_MIN_RERANK_SCORE` in Step 6.5.

---

## 4. Why this Step exists

Mental separation:

```text
Step 6.3/6.4
eligible semantic candidates
        ↓
Step 6.5
pairwise relevance refinement
        ↓
Step 6.6
context/prompt construction
```

Without Step 6.5, final evidence ordering depends only on embedding similarity. With Step 6.5, the model sees query and passage jointly before context construction.

---

## 5. Prerequisites

- Step 6.1 embedding provider boundary accepted.
- Step 6.2 ACTIVE vector-storage safety accepted.
- Step 6.3 semantic retrieval accepted.
- Step 6.4 scope/filter-before-Top-K accepted.
- Existing `RetrievalCandidate` contract accepted.
- PM decisions 6.5-D1 through 6.5-D3 are frozen in this task; execution still requires separate PM authorization.

---

## 6. Mental Model

```text
Retrieval says:
"Which chunks are plausible semantic neighbors?"

Filtering says:
"Which chunks are eligible for this scope?"

Reranking says:
"Among those eligible candidates, which query/passage pairs are most relevant?"
```

Reranking is not:

- another retrieval query;
- source-policy filtering;
- evidence acceptance;
- fallback orchestration;
- prompt packing;
- LLM generation.

---

## 7. Exact Data Flow

```text
query_text
↓
QueryPreprocessor.preprocess()  # reuse exact Step-6.3 normalization
↓
normalized_query
+
already-filtered RetrievalCandidate[]
↓
validate candidate-set integrity
↓
select reranker candidate pool = first semantic Top 20 (`candidates[:20]`)
↓
RerankPassageFormatter/v1
↓
passages[] aligned 1:1 with candidates[]
↓
validate every query+passage pair length without truncation
↓
sequential batches
↓
RerankerProvider.score(normalized_query, passages_batch)
↓
raw rerank scores
↓
validate score count + finite values
↓
attach rerank_score to every scored candidate
↓
sort:
rerank_score DESC
→ semantic rank ASC
→ stable chunk identity ASC
↓
assign runtime rerank_rank = 1..N
↓
select configured RERANKER_TOP_K
↓
RerankedCandidate[]
```

No database access is required in this flow.

---

## 8. Reranker provider / model contract

Create a provider abstraction equivalent to:

```python
class RerankerProvider(Protocol):
    @property
    def identity(self) -> RerankerProviderIdentity: ...

    @property
    def device(self) -> str: ...

    def validate_pair_lengths(self, query: str, passages: list[str]) -> None: ...

    def score(self, query: str, passages: list[str]) -> list[float]: ...
```

### Required identity fields

Runtime identity must be immutable and observable:

```text
provider
provider_version
model_name
model_revision
reranker_input_version
```

V0 logical values:

```text
provider = LOCAL
model_name = BAAI/bge-reranker-v2-m3
model_revision = 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
reranker_input_version = v1
```

The exact model revision is part of reranker/calibration identity. The same exact revision must be passed to both tokenizer and model loading. Do not use floating `main`. If model/revision changes after threshold calibration, recalibration is required before release.

`provider_version` must identify the concrete inference library/version actually imported by the provider.

### Implementation library

Use the already accepted Hugging Face Transformers + PyTorch runtime directly unless PM later overrides this task.

Equivalent implementation shape:

```text
AutoTokenizer.from_pretrained(model_name, revision=model_revision)
AutoModelForSequenceClassification.from_pretrained(
    model_name,
    revision=model_revision,
)
```

Do not enable implicit truncation.

### Raw score contract

Use raw sequence-classification logits as `rerank_score`.

```text
higher = better
```

Do not sigmoid-normalize, clamp, convert to probability, or otherwise transform the raw model relevance score.

### Model lifecycle

```text
first rerank request
→ lazy-load tokenizer/model
→ retain one provider/model instance per process
```

Do not reload model per request/batch.

### Device

Add:

```text
RERANKER_DEVICE=auto
```

Supported logical behavior:

```text
auto
→ supported accelerator when safely available
→ CPU fallback
```

Do not require it to equal `EMBEDDING_DEVICE`.

Do not hard-code FP16 globally. Use provider/device-appropriate default precision.

---

## 9. Query / candidate input construction

### Query

`RerankingService` receives `query_text: str` and internally reuses:

```text
QueryPreprocessor.preprocess(query_text)
```

The helper is deterministic/idempotent, so this does not require a Step-6.3 API change.

Do not:

- translate;
- LLM rewrite;
- expand keywords;
- add Lesson/HSK metadata to the query.

### RerankPassageFormatter/v1

Create a separate formatter contract from `EmbeddingInputFormatter`.

#### Document candidate

```text
Title: <document title>
Section: <section>          # only when present

<Chunk.content>
```

Do not add page number unless a later PM change explicitly requires it as semantic input.

#### Lesson candidate

```text
HSK: <hsk_level_number>
Lesson: <lesson title>
Type: <content_type>

<Chunk.content>
```

Required candidate provenance already exists in `RetrievalCandidate`.

Do not inject:

```text
retrieval_score
semantic rank
rerank rank
source priority
UUIDs
storage path
```

Do not mutate `Chunk.content` / candidate content.

### Candidate integrity

Before inference:

- input must be a sequence of `RetrievalCandidate` instances;
- candidate IDs must be unique within one rerank operation;
- content must be non-empty text after basic contract validation;
- duplicate *text* with different candidate IDs remains valid and distinct;
- provenance fields are never rewritten by reranking.

Malformed internal candidate input fails the entire operation with a normalized technical error equivalent to:

```text
INVALID_RERANK_INPUT
```

Do not silently drop malformed candidates.

---

## 10. Candidate-count / rerank-top-K semantics

### Retrieval candidate input

Accepted upstream configuration remains:

```text
RAG_RETRIEVAL_CANDIDATE_K
DEFAULT = 20
RANGE = 1..100
```

Step 6.5 must not fetch any new candidate.

Freeze the V0 reranker input pool as:

```text
candidates[:20]
```

Therefore:

- fewer than 20 upstream candidates → rerank all;
- exactly 20 → rerank all 20;
- more than 20 → rerank only original semantic ranks 1..20;
- semantic ranks 21+ are not scored or returned by Step 6.5;
- preserve each selected candidate's original semantic `rank` and `retrieval_score`;
- do not add `RERANKER_CANDIDATE_K`;
- do not change `RAG_RETRIEVAL_CANDIDATE_K` (default 20, range 1..100).

### Rerank Top-K

Accepted semantic default:

```text
RERANKER_TOP_K=5
```

Output count:

```text
min(scored_candidate_count, rerank_top_k)
```

No padding.

Frozen bounds:

```text
RERANKER_TOP_K
default = 5
range = 1..5
```

### Batch size

Accepted default:

```text
RERANKER_BATCH_SIZE=8
```

Batches execute sequentially.

Frozen bounds:

```text
RERANKER_BATCH_SIZE
default = 8
range = 1..20
```

Do not add frontend overrides for rerank candidate count, batch size or Top-K.

---

## 11. Score semantics

Keep three concepts separate:

```text
retrieval_score
= Step 6.3 cosine similarity
= preserved diagnostic

rerank_score
= raw BGE reranker relevance logit
= higher is better

final evidence acceptance
= NOT owned by Step 6.5
```

Do not overwrite `retrieval_score`.

Do not normalize or clamp `rerank_score`.

Do not combine scores:

```text
NO 0.7 * rerank_score + 0.3 * retrieval_score
```

Final Step-6.5 ordering uses rerank score only, with deterministic tie-breaks.

---

## 12. Rank / result schemas

Create immutable runtime DTO equivalent to:

```text
RerankedCandidate
├── all RetrievalCandidate fields unchanged
├── rerank_score: float
└── rerank_rank: int
```

Existing `RetrievalCandidate.rank` remains the original semantic retrieval rank.

Tie-breaking:

```text
rerank_score DESC
→ RetrievalCandidate.rank ASC
→ chunk_id ASC
```

Do not repurpose semantic `rank` into rerank rank.

No schema migration is required for runtime `rerank_rank`.

Later persistence rule:

```text
MessageRetrieval.rank = original semantic rank
MessageRetrieval.retrieval_score = semantic score
MessageRetrieval.rerank_score = raw reranker score
```

Step 6.5 itself does not persist MessageRetrieval.

---

## 13. Threshold boundary

Step 6.5 MUST NOT introduce:

```text
RAG_MIN_RERANK_SCORE
```

Step 6.5:

```text
score
→ order
→ Top-K
```

Step 7.3 later:

```text
DEVELOPMENT rerank-score distributions
→ calibrate threshold
→ verify on HOLDOUT
→ PM freezes RAG_MIN_RERANK_SCORE
```

Any reranker model/revision change after calibration requires recalibration before release.

---

## 14. Service / provider responsibilities

### `RerankPassageFormatter`

Owns only deterministic candidate → passage text formatting.

### `RerankerProvider`

Owns:

- concrete model/tokenizer loading;
- exact model revision;
- device;
- provider/model tokenization;
- pair-length validation support;
- batched model inference;
- raw logit extraction;
- model/provider exception normalization at provider boundary.

### `RerankingService`

Owns:

- query preprocessing reuse;
- candidate-set contract validation;
- passage formatting;
- candidate-pool policy after PM D2;
- sequential batch orchestration;
- provider output validation;
- partial-failure discard;
- deterministic sort/rank;
- Top-K selection;
- structured logging/timing.

Must NOT:

- query the database;
- perform retrieval;
- alter scope/filter;
- call an LLM;
- build prompts;
- perform evidence thresholding/fallback.

---

## 15. Transaction / inference boundary

Reranking operates entirely on already-hydrated runtime DTOs.

```text
DB transaction required: NO
DB query required: NO
DB write required: NO
```

The caller must not wrap reranking inference inside a database transaction.

Add a test/fake session guard only if the final service accidentally receives database dependencies; preferred design is no session dependency at all.

---

## 16. Error / failure behavior

### Empty input

```text
candidates = []
→ return []
→ do not load/call model
```

### Malformed candidate / duplicate candidate ID

```text
→ INVALID_RERANK_INPUT
→ no partial output
```

Duplicate passage text with distinct candidate IDs remains valid.

### Pair too long

Validate actual `(query, formatted passage)` tokenizer length against the pinned model/tokenizer limit **without truncation**.

```text
→ RERANK_INPUT_TOO_LONG
```

Do not silently truncate.

### Provider/model initialization unavailable

```text
→ RERANKER_NOT_AVAILABLE
```

### Inference failure / OOM

```text
→ RERANKER_INFERENCE_FAILED
```

No automatic same-request retry.

### Output count mismatch / NaN / Inf

```text
→ INVALID_RERANKER_OUTPUT
```

Discard all output for the operation.

### Partial batch failure

Freeze according to the later and more specific technical-failure contracts:

```text
batch 1 succeeds
batch 2 fails
→ discard every partial rerank score
→ raise typed technical failure
→ NO semantic-order successful fallback
```

The earlier prose sentence suggesting semantic-order fallback is stale relative to:

- the Step-6.5 technical-failure section;
- Step-6.5 tests/acceptance criteria;
- later Step-6.8 orchestration requirement that reranker technical failure fails the AI run and must not trigger semantic-success substitution or another tier.

Technical failure is never `[]` / “no evidence”.

---

## 17. Logging

Structured fields may include:

```text
provider
provider_version
model_name
model_revision
reranker_input_version
candidate_count
scored_count
rerank_top_k
batch_size
batch_count
device
rerank_duration_ms
top_retrieval_score optional
top_rerank_score optional
status
error_code optional
```

Do NOT log:

- raw query text;
- full passage/Chunk content;
- query-passage pairs;
- tokenizer input IDs/tensors;
- large score arrays;
- raw provider exception text/tracebacks containing model inputs;
- secrets.

Log only normalized technical error codes on failure.

---

## 18. Expected files

Equivalent focused change set:

```text
backend/app/ai/reranking/
├── __init__.py
├── provider.py
├── transformers_provider.py
├── formatter.py
├── schemas.py
├── service.py
└── errors.py

backend/app/core/config.py
backend/.env.example
backend/pyproject.toml          # only if direct dependency ownership needs promotion
backend/uv.lock                 # only if dependency metadata/resolution changes

backend/tests/
├── test_step65_rerank_formatter.py
├── test_step65_reranker_provider.py
├── test_step65_reranking_service.py
└── optional focused support helper

docs/ai/step-6.5-reranking.md
```

No migration file.

Do not edit Step 6.1–6.4 production behavior except imports/interfaces strictly necessary for Step 6.5 integration tests.

---

## 19. Testing matrix

### Query reuse

- exact Step-6.3 trim/NFC/whitespace normalization reused;
- no translation/rewrite/query expansion;
- original caller query object/content is not mutated.

### Formatter

Document:

- title + optional section + content;
- absent section omitted deterministically;
- no page/rank/score/UUID/storage path in model passage.

Lesson:

- HSK + lesson title + content type + content;
- deterministic formatting;
- candidate content unchanged.

### Candidate integrity

- only provided candidate IDs are scored/returned;
- no retrieval/DB search occurs;
- duplicate IDs fail;
- duplicate text with different IDs remains distinct;
- malformed/empty content fails whole operation;
- scope/provenance fields unchanged.

### Model identity/provider

- configured model name exactly `BAAI/bge-reranker-v2-m3`;
- exact revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` is passed to `AutoTokenizer.from_pretrained(...)`;
- the same exact revision is passed to `AutoModelForSequenceClassification.from_pretrained(...)`;
- provider identity reports the exact model revision plus provider/library version and input version;
- wrong/unexpected model configuration fails closed;
- model lazy-loads once and is reused;
- device config independent from embedding device;
- no global FP16 assumption.

### Input length

- tokenizer called without truncation for validation;
- exactly-at-limit pair accepted;
- over-limit pair → RERANK_INPUT_TOO_LONG;
- no silent truncation before inference.

### Candidate-count semantics

- fewer than 20 candidates → all are reranked;
- exactly 20 candidates → all 20 are reranked;
- more than 20 candidates → only `candidates[:20]` / semantic ranks 1..20 enter the reranker;
- semantic ranks 21+ are never scored or returned by Step 6.5;
- every selected candidate is scored before Top-K selection;
- original semantic rank and `retrieval_score` remain unchanged;
- reranker never fetches additional candidates.

### Config bounds

Test exactly:

`RERANKER_BATCH_SIZE`:

- 1 accepted;
- 8 accepted;
- 20 accepted;
- 0 rejected;
- negative rejected;
- 21 rejected.

`RERANKER_TOP_K`:

- 1 accepted;
- 5 accepted;
- 0 rejected;
- negative rejected;
- 6 rejected.

Normal frontend/caller cannot supply runtime batch/top-K overrides.

### Batch behavior

- sequential batches only;
- input/output score alignment preserved across batch boundaries;
- candidate count not divisible by batch size handled;
- model called expected number of times.

### Score validation

- raw negative score preserved;
- raw positive score preserved;
- no sigmoid/clamp/normalization;
- higher score sorts first;
- score count mismatch fails;
- NaN fails;
- +Inf/-Inf fail.

### Ordering

- rerank_score DESC primary;
- semantic rank ASC first tie-break;
- stable chunk ID final tie-break;
- deterministic repeated runs with deterministic provider output.

### Result contract

- all RetrievalCandidate fields preserved exactly;
- original semantic `rank` unchanged;
- original `retrieval_score` unchanged;
- `rerank_score` added;
- runtime `rerank_rank` assigned;
- raw vectors absent.

### Top-K

- configured Top-K in frozen range 1..5 is returned;
- candidate_count < top-K returns all;
- no padding;
- candidate_count = 0 returns [] without provider/model load.

### Failures

- provider init failure → RERANKER_NOT_AVAILABLE;
- inference failure → RERANKER_INFERENCE_FAILED;
- no automatic retry;
- partial later-batch failure discards prior scores and raises failure;
- technical failure never returns semantic-order success;
- technical failure never becomes `[]`/no-evidence.

### Boundaries

Prove no:

- retrieval scope widening;
- CURRENT_LESSON → INTERNAL_KB fallback;
- RAG_MIN_RERANK_SCORE;
- threshold filtering;
- weighted score fusion;
- context construction;
- LLM call;
- external retrieval;
- MessageRetrieval persistence;
- schema migration.

### Real-model smoke

If the pinned model is available locally / can be downloaded in the execution environment:

- run one small real-model query/passage smoke;
- assert finite raw logits;
- assert a clearly related passage can outrank an unrelated passage.

If model download is unavailable, record this as an environment limitation; focused fake/provider contract tests remain mandatory.

---

## 20. Verification commands

Run from `backend/` using the project's accepted environment workflow.

Minimum:

```text
uv lock --check
uv sync                       # required if pyproject/lock dependency ownership changes
python -m compileall app
alembic current
alembic check
```

Focused:

```text
pytest -q tests/test_step65_*.py
```

Regressions:

```text
Step 6.4 focused suite
Step 6.3 suite
Step 6.2 suite
Step 6.1 suite
Phase 5.5–5.7 suite
full backend suite
```

Expected Alembic head remains:

```text
0012_vector_storage_readiness
```

No migration/schema drift.

---

## 21. Scope / non-goals

Do NOT implement:

- `RAG_MIN_RERANK_SCORE`;
- evidence acceptance decision;
- CURRENT_LESSON → INTERNAL_KB fallback;
- external retrieval;
- source/category boosts;
- retrieval/reranker weighted fusion;
- context dedup/diversity policy;
- context token budgeting;
- prompt construction;
- LLM generation;
- citations;
- conversation memory;
- DB persistence of rerank results;
- generic managed reranker provider;
- remote reranker API;
- Celery/queue/Redis/distributed inference;
- parallel reranker batches;
- GPU orchestration;
- LangChain/LlamaIndex;
- schema migration.

---

## 22. Step Note (draft contract; finalize after implementation)

### Objective

Refine already-filtered semantic candidates with a local multilingual query-passage reranker and produce deterministic Top-K evidence ordering.

### Why

Dense retrieval generates plausible candidates efficiently; cross-encoder reranking gives stronger pairwise relevance ordering before prompt construction.

### Mental Model

```text
Eligibility first
→ candidate generation
→ relevance refinement
→ context construction later
```

### Core Knowledge

- bi-encoder retrieval vs cross-encoder reranking;
- raw model score semantics;
- deterministic ranking/tie-breaks;
- model version identity and calibration dependency;
- batching and no-silent-truncation;
- technical failure vs semantic insufficiency.

### Data Flow

Use the exact flow from Section 7.

### Key Design Decisions

- BAAI/bge-reranker-v2-m3 local baseline;
- direct provider abstraction;
- deterministic passage formatter v1;
- raw logits, no normalization;
- semantic rank preserved;
- no threshold in Step 6.5;
- no DB transaction/access during reranking;
- technical reranker failure fails the operation;
- 6.5-D1 = A: exact reranker revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`;
- 6.5-D2 = A: only semantic ranks 1..20 (`candidates[:20]`) enter reranking;
- 6.5-D3 = A: batch size range 1..20, Top-K range 1..5.

### Reusable approach

For future rerankers:

```text
freeze model identity
→ define deterministic model input contract
→ validate lengths
→ score bounded candidates
→ validate outputs
→ preserve upstream diagnostics
→ separate scoring from threshold policy
```

### Common Mistakes

- reranking before scope filtering;
- normalizing raw scores without evidence;
- overwriting semantic rank;
- silently truncating query/passage;
- treating technical reranker failure as no evidence;
- thresholding before calibration;
- losing candidate provenance;
- introducing source boosts into reranker score.

### Definition of Done

All frozen acceptance criteria pass, regressions pass, no migration exists, Step Note is reconciled to actual implementation, and specialist handoff is accepted by PM.

---

## 23. Concepts Discovered (record on completion if actually implemented)

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Cross-encoder reranking | AI | 6.5 | Jointly scores query/passage pairs to refine semantic candidate ordering. |
| Reranker model identity/versioning | AI | 6.5 | Keeps rerank scores reproducible and makes threshold calibration version-specific. |
| Raw relevance logit | AI | 6.5 | Preserves provider-native score semantics without unjustified normalization. |
| Deterministic rerank tie-breaking | BOTH | 6.5 | Makes runtime/evaluation outputs reproducible. |
| Bounded sequential inference batching | AI | 6.5 | Controls local inference memory/latency without queue complexity. |
| Technical failure vs semantic no-evidence | BOTH | 6.5 | Prevents infrastructure/model failure from corrupting fallback/evidence policy. |

---

## 24. Tools Used

At JIT pre-review time: **none newly used by production code yet**.

Authorized implementation runtime if PM freezes this task:

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| Hugging Face Transformers | AI | 6.5 | Load/tokenize/run the pinned BGE sequence-classification reranker using existing ML runtime. |
| PyTorch | AI | 6.5 | Local inference tensor runtime. |

Do not add these to the PM Tools Master List until implementation actually uses them.

---

## 25. Acceptance Criteria

### Model/provider

- [ ] BAAI/bge-reranker-v2-m3 is the only V0 reranker model.
- [ ] PM-frozen exact model revision is used for tokenizer + model loading.
- [ ] Provider/model identity is observable and immutable for the process.
- [ ] Local provider is isolated behind `RerankerProvider`.
- [ ] Existing Transformers/PyTorch runtime is used; no new generic RAG framework.
- [ ] Model lazy-loads once and is reused.
- [ ] Device is independently configurable with CPU fallback.
- [ ] FP16 is not globally hard-coded.

### Input

- [ ] Step-6.3 query normalization is reused exactly.
- [ ] `RerankPassageFormatter/v1` is deterministic and separate from embedding formatter.
- [ ] Document format uses title/optional section/content.
- [ ] Lesson format uses HSK/lesson/content-type/content.
- [ ] Retrieval scores/ranks/UUIDs are not included in model text.
- [ ] Candidate content/provenance is not mutated.
- [ ] Duplicate IDs fail; duplicate text with distinct provenance remains distinct.
- [ ] Pair length is validated without silent truncation.

### Candidate count / configuration

- [ ] Reranker input pool is exactly the first semantic Top 20 (`candidates[:20]`); ranks 21+ are never scored/returned by Step 6.5.
- [ ] Every selected candidate is scored before Top-K selection; no new candidates are fetched.
- [ ] `RERANKER_BATCH_SIZE` default = 8 and range = 1..20.
- [ ] `RERANKER_TOP_K` default = 5 and range = 1..5.
- [ ] No frontend/runtime request override is exposed.
- [ ] Batches are sequential.

### Scores / rank

- [ ] Raw model logit is preserved as `rerank_score`.
- [ ] `higher = better`.
- [ ] No sigmoid/0..1 normalization/clamping is applied.
- [ ] No score threshold is applied.
- [ ] No weighted fusion with retrieval score exists.
- [ ] Original semantic rank and retrieval_score remain unchanged.
- [ ] Deterministic order is rerank_score DESC → semantic rank ASC → chunk_id ASC.
- [ ] `rerank_rank` is runtime-only.

### Failure semantics

- [ ] Empty input returns [] without model load/call.
- [ ] Model init failure is typed technical failure.
- [ ] Inference failure is typed technical failure.
- [ ] Overlong input fails explicitly.
- [ ] Wrong score count/NaN/Inf fails explicitly.
- [ ] Partial-batch failure discards all partial scores and fails the whole operation.
- [ ] No technical failure becomes semantic-order success, `[]`, no-evidence, or tier fallback.
- [ ] No same-request automatic retry.

### Boundary

- [ ] Step-6.4 filter/scope contract is unchanged.
- [ ] Reranking never broadens candidate scope.
- [ ] No DB access/transaction is required during reranking.
- [ ] No MessageRetrieval persistence occurs here.
- [ ] `RAG_MIN_RERANK_SCORE` is absent.
- [ ] No context/prompt/LLM/external fallback/citation/memory work exists.
- [ ] Step 6.6 can consume the final ordered Top-K directly.
- [ ] No Alembic migration/schema change exists.

---

## 26. Codex completion-report format

Return exactly enough evidence for specialist review:

```text
Step:
6.5 — Reranking / Evidence Score

Status:
READY_FOR_SPECIALIST_REVIEW | BLOCKED

Files changed:
<list>

Production code changed:
YES/NO

Migration changed:
NO expected

Schema changed:
NO expected

Dependencies changed:
YES/NO + exact package/version changes

Accepted Alembic head:
0012_vector_storage_readiness

Reranker provider:
<exact provider implementation/library>

Reranker model:
BAAI/bge-reranker-v2-m3

Reranker model revision:
953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e

RERANKER_INPUT_VERSION:
v1

RERANKER_BATCH_SIZE:
default = 8
min = 1
max = 20

RERANKER_TOP_K:
default = 5
min = 1
max = 5

Reranked candidate-pool policy:
semantic ranks 1..20 only (`candidates[:20]`); ranks 21+ are not scored/returned

Score semantics:
raw model logit; higher = better; no normalization/clamp

RAG_MIN_RERANK_SCORE introduced:
NO

Partial batch failure:
all partial scores discarded; typed technical failure; no semantic fallback

DB transaction during inference:
NO

Step 6.4 scope/filter contract preserved:
YES/NO

Step 6.6 started:
NO

Verification commands + exact results:
- uv lock --check
- uv sync if dependency metadata changed
- Alembic current/check
- Step 6.5 focused tests
- Step 6.4 regressions
- Step 6.3 regressions
- Step 6.2 regressions
- Step 6.1 regressions
- Phase 5.5–5.7 regressions
- full backend suite
- compileall app

Warnings:
<list>

Problems/risks:
<list>

Decisions needed:
NONE

6.5-D1:
A — revision 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e

6.5-D2:
A — reranker pool = semantic ranks 1..20 (`candidates[:20]`)

6.5-D3:
A — batch 1..20 default 8; Top-K 1..5 default 5
```

---

# FROZEN PM DECISIONS

## 6.5-D1 = A — Exact reranker model revision

Freeze:

```text
model_name = BAAI/bge-reranker-v2-m3
model_revision = 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
```

Use this exact revision for both:

```python
AutoTokenizer.from_pretrained(model_name, revision=model_revision)
AutoModelForSequenceClassification.from_pretrained(model_name, revision=model_revision)
```

Do not use floating `main`. The exact revision is part of reranker/calibration identity. If the model/revision changes after threshold calibration, `RAG_MIN_RERANK_SCORE` must be recalibrated before release.

---

## 6.5-D2 = A — Reranker candidate pool

Upstream retrieval remains:

```text
RAG_RETRIEVAL_CANDIDATE_K
default = 20
range = 1..100
```

Step 6.5 reranker pool is:

```text
candidates[:20]
```

Rules:

- preserve original semantic rank and `retrieval_score`;
- every selected candidate is scored before Top-K selection;
- ranks 21+ are not scored or returned by Step 6.5;
- do not add `RERANKER_CANDIDATE_K`;
- do not fetch new candidates.

Production/evaluation checkpoint remains:

```text
semantic Top 20
→ rerank all selected 20
→ Top 5
```

---

## 6.5-D3 = A — Reranker config bounds

Freeze:

```text
RERANKER_BATCH_SIZE
default = 8
min = 1
max = 20

RERANKER_TOP_K
default = 5
min = 1
max = 5
```

Equivalent:

```python
reranker_batch_size: int = Field(default=8, ge=1, le=20)
reranker_top_k: int = Field(default=5, ge=1, le=5)
```

No frontend/per-request override. Output count remains:

```text
min(scored_candidate_count, reranker_top_k)
```

No padding.

---

## Resolved specification drift — no PM decision requested

The Step-6.5 prose contains one stale sentence under “Partial Batch Failure” suggesting:

```text
fallback entire candidate set to semantic order
```

This conflicts with more specific/later contracts in the same Step and later RAG orchestration:

```text
technical reranker failure
→ typed technical failure
→ no semantic-success substitution
→ no broader-tier fallback
```

The executable task therefore freezes **typed technical failure** and treats semantic-order fallback as stale prose. This is necessary for the later calibrated rerank-score evidence gate to remain meaningful.

---

# JIT pre-review status

```text
Repository state reconciled: YES
Architecture changes proposed: NO
Schema changes proposed: NO
Step-6.4 filter contract preserved: YES
RAG_MIN_RERANK_SCORE introduced: NO
Step-6.6 boundary preserved: YES

6.5-D1: A — frozen
6.5-D2: A — frozen
6.5-D3: A — frozen

Remaining blockers: NONE
Decisions needed: NONE

Production code changed: NO
Codex run: NO
Step 6.6 started: NO
```
