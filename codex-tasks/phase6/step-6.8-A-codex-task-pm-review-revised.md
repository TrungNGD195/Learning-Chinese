# Step 6.8-A — Internal End-to-End RAG Bootstrap / Score Collection
## Final JIT Task / Specification for PM Review

**Status:** READY_FOR_PM_TASK_REVIEW  
**Owner:** AI Engineering Specialist  
**Repository state reconciled:** YES — accepted Step 3.6, 6.3, 6.4, 6.5, 6.6, 6.9, 6.10 implementation evidence inspected  
**Inherited CLOSED contracts:** D-084, D-085, D-086 FROZEN  
**Step-specific decisions:** D-087 through D-092 FROZEN  
**Implementation authorization:** NOT YET  
**PM approval required before Codex:** YES  
**Production code changed during JIT review:** NO  
**Codex run:** NO  
**Step 6.8-B:** DO NOT START  
**Phase 7 implementation:** DO NOT START  
**Decisions needed:** NONE  
**Remaining JIT blocker:** NONE  

---

# 0. Execution Boundary

Implement **Step 6.8-A only**.

Current PM order remains:

```text
6.1 CLOSED
→ 6.2 CLOSED
→ 6.3 CLOSED
→ 6.4 CLOSED
→ 6.5 CLOSED
→ 6.6 CLOSED
→ 6.7 CLOSED
→ 6.9 CLOSED
→ 6.10 CLOSED
→ 6.8-A Internal End-to-End RAG bootstrap / score collection
→ 7.1
→ 7.2
→ 7.3 calibrate RAG_MIN_RERANK_SCORE
→ PM records calibrated threshold
→ close 6.8-A normal-runtime evidence gate
→ 6.8-B
```

This task must make the internal RAG path structurally complete while preserving the calibration release gate.

Do NOT implement external retrieval, Step 6.8-B, or Phase 7 in this task.

---

# 1. Objective

Integrate the already-accepted internal AI components into one production-shaped Lesson Chat RAG flow while also exposing the score-only calibration seam required by Step 7.3.

The task must support two distinct operating paths.

## A. Internal calibration/evaluation

```text
trusted evaluation query + trusted lesson scope
↓
CURRENT_LESSON retrieve → rerank → trace
AND
INTERNAL_KB retrieve → rerank → trace
↓
CalibrationScoreTrace
↓
STOP
```

No prompt, memory, LLM, citations, Assistant finalization, or production retrieval persistence.

## B. Normal learner RAG after threshold calibration

```text
ConversationService Transaction A
↓
Assistant PENDING committed
↓
D-090 processing guard
↓
AIChatService
↓
RagOrchestrator
↓
CURRENT_LESSON retrieve/rerank/evidence gate
↓ insufficient only
INTERNAL_KB retrieve/rerank/evidence gate
↓
first usable internal tier OR semantic NO_EVIDENCE
↓
if grounded:
Prompt → Memory → LLM → Citation Validation
↓
RagRunResult
↓
ConversationService Transaction B
↓
atomic retrieval/citation/content/status persistence
```

---

# 2. Non-Negotiable Frozen Decisions

Preserve the relevant already-CLOSED Step-6.9/6.10 contracts **D-084, D-085, D-086** and the Step-6.8-A-specific decisions **D-087 through D-092** exactly.

## D-084 — Memory-specific exact-preflight fail-soft fallback

Conversation memory is optional continuity context.

Frozen priority:

```text
current mandatory request
+ current retrieved evidence
> conversation memory
```

For **each logical generation attempt** when memory is eligible:

```text
current evidence PromptPackage
→ derive residual memory budget
→ ConversationMemoryBuilder.build(...) once for THIS logical attempt
→ whole-turn packing
→ attach selected memory
→ serialize generation request
→ provider-exact preflight
```

If the first exact preflight fits:

```text
→ responses.create(...)
```

If the first exact preflight overflows **and non-empty memory is present**:

```text
same logical attempt
→ remove ALL conversation memory only
→ preserve system / LearningContext / current evidence / source_map / current query / generation config
→ do NOT perform another DB memory selection merely to create empty memory
→ perform exactly one final provider-exact preflight
→ generate if valid
```

This zero-memory fallback:

```text
is NOT a new logical generation attempt
is NOT an application transient retry
does NOT consume LLM_MAX_TRANSIENT_RETRIES
```

Per logical attempt:

```text
normal memory/no-memory case → 1 exact preflight
memory exact-overflow case   → max 2 exact preflights
responses.create(...)        → max 1 for that logical attempt
```

If the zero-memory request still exceeds the context limit, fail with the accepted context-limit technical error. Do not remove/repack evidence, reduce output reserve, truncate, switch models, or continue generation.

## D-085 — Memory turn cap / disable policy

Preserve:

```text
RAG_MEMORY_MAX_TURNS
integer
range = 0..3
default = 3
```

Memory selection remains:

```text
same Conversation only
completed eligible turns only
most recent eligible window
whole turns only
chronological serialization
residual-budget aware
```

`RAG_MEMORY_MAX_TURNS=0` disables selected memory without changing retrieval/evidence behavior.

A **new logical generation attempt** created by the accepted application transient retry budget makes memory eligible again and must rebuild memory fresh for that attempt. Do not reuse a zero-memory fallback decision from a previous logical attempt.

## D-086 — External citation trust policy ownership

Step 6.10 already owns provider-independent validation of supplied external citation provenance, but production external provider/domain allowlist selection remains Step 6.8-B under D-003.

Step 6.8-A must not choose an external provider, configure production trusted domains, or run external retrieval.

## D-087 — Calibration is score-only

`calibration=true` is an internal evaluation mode.

It runs internal retrieval/reranking only and persists no production RAG output.

## D-088 — Calibration flag dominates threshold

```text
calibration=true + threshold=None
→ calibration

calibration=true + threshold=numeric
→ calibration

calibration=false + threshold=None
→ learner technical/configuration failure before retrieval

calibration=false + threshold=finite numeric
→ normal learner runtime
```

Learner APIs must not accept calibration flags or threshold overrides.

## D-089 — MessageRetrieval semantics

Grounded success persists **all reranker-scored candidates from exactly one selected internal tier**.

```text
rank            = original semantic retrieval rank
retrieval_score = semantic retrieval score
rerank_score    = cross-encoder score
```

Semantic NO_EVIDENCE persists zero `MessageRetrieval` rows.

Technical failure persists zero normal `MessageRetrieval` rows.

Calibration persists zero production `MessageRetrieval` rows.

## D-090 — One processor per Assistant attempt

Processing identity is:

```text
assistant_message_id
```

Use a PostgreSQL **session-level**, non-blocking advisory lock held on one dedicated physical connection for the full processing lifetime.

No PROCESSING/CLAIMED/LEASED schema state.

## D-091 — Exact semantic no-evidence response

The learner-visible V0 response is exactly:

```text
Hiện tại mình chưa có đủ nguồn đáng tin cậy để trả lời câu hỏi này.
```

Do not alter punctuation, spacing, accents, or wording.

## D-092 — Reranker dual-view contract

One logical reranker execution exposes:

```text
RerankResult
├── scored_candidates
└── top_candidates
```

`top_candidates` is derived from the same deterministic `scored_candidates` ordering.

No second rerank execution.

---

# 3. Accepted Repository Baseline

## 3.1 Database session convention

Existing database infrastructure exposes:

```python
SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

and request-scoped `get_db_session()`.

Step 6.8-A must reuse this infrastructure.

No new engine, pool, or DB framework.

## 3.2 Step 6.3 / 6.4 retrieval

Current service:

```python
SemanticRetrievalService(
    session: AsyncSession,
    *,
    provider: EmbeddingProvider | None = None,
    settings: Settings | None = None,
)
```

Current public retrieval method:

```python
await retrieve(
    query_text: str,
    *,
    retrieval_filter: RetrievalFilter | None = None,
) -> list[RetrievalCandidate]
```

Important accepted behavior:

- profile read is a short DB transaction;
- query embedding runs outside a DB transaction;
- vector search + metadata hydration run in a later short DB transaction;
- service explicitly rejects query embedding if a DB transaction is open;
- technical retrieval failures are not converted to `[]`;
- `candidate_k` remains backend-owned `RAG_RETRIEVAL_CANDIDATE_K`;
- `CURRENT_LESSON` filter is built with `build_scope_filter(...)` using trusted `Conversation.lesson_id`;
- `INTERNAL_KB` uses the accepted unrestricted ACTIVE internal scope (`None` filter).

Do not reimplement retrieval SQL inside RagOrchestrator.

## 3.3 Step 6.5 reranking — actual reconciliation required by D-092

Current accepted implementation:

```python
RerankingService.rerank(
    query_text: str,
    candidates: Sequence[RetrievalCandidate],
) -> list[RerankedCandidate]
```

Actual implementation already:

```text
validates candidate pool
→ scores all candidates
→ deterministic sort
→ creates full reranked list
→ currently returns reranked[:top_k]
```

This task must perform the approved **minimal runtime-interface reconciliation**.

Add an immutable runtime result equivalent to:

```python
@dataclass(frozen=True)
class RerankResult:
    scored_candidates: tuple[RerankedCandidate, ...]
    top_candidates: tuple[RerankedCandidate, ...]
```

Change only the return contract needed to expose both already-computed views.

Required:

```text
score once
→ deterministic full ordering
→ scored_candidates = full ordered tuple
→ top_candidates = first min(N, RERANKER_TOP_K)
```

Preserve existing batching, provider behavior, input validation, failure semantics, and ordering.

Empty input:

```text
RerankResult((), ())
```

with no model/provider inference.

Do not run a second logical `RerankingService.rerank()` call to obtain Top-K.

## 3.4 Step 6.6 PromptContextBuilder

Actual module/class:

```text
backend/app/ai/prompting/builder.py
PromptContextBuilder
```

Constructor:

```python
PromptContextBuilder(*, token_counter: TokenCounter)
```

Public method:

```python
build(
    *,
    user_query: str,
    candidates: Sequence[RerankedCandidate],
    prompt_budget: PromptBudget,
    learning_context: LearningContext | None = None,
) -> ContextBuildResult
```

For Step 6.8-A:

```text
RerankResult.top_candidates
→ candidates=
```

directly.

Do not introduce another internal evidence DTO merely for this connection.

Actual Step-6.6 builder requires at most 5 candidates and preserves rerank order.

Prompt budget for the accepted V0 generation configuration:

```text
model_input_limit          = GenerationConfig.model_input_limit
reserved_output_tokens     = GenerationConfig.max_output_tokens
serialization_overhead_tokens = 0
```

`serialization_overhead_tokens=0` is the frozen local-packing policy because provider-native exact preflight owns provider structural accounting.

Do not invent another guessed overhead.

Step 6.8-A does not add a new curriculum/learning-context query. Pass:

```python
learning_context=None
```

unless the current repository already contains an accepted trusted `LearningContext` builder that can be reused without new scope. Do not create one solely for this task.

## 3.5 Step 6.9 Conversation Memory

Actual builder:

```python
ConversationMemoryBuilder(
    session,
    *,
    token_counter: TokenCounter,
    repository=conversation_repository,
)
```

```python
await build(
    *,
    conversation_id: UUID,
    current_user_sequence_number: int,
    memory_token_budget: int,
    max_turns: int,
) -> ConversationMemory
```

Actual composition helpers:

```python
derive_memory_token_budget(package: PromptPackage) -> int
with_conversation_memory(package, memory) -> PromptPackage
```

Memory must remain separate from evidence and citations.

### D-090 transaction reconciliation for memory

Current Step-6.9 repository read uses the supplied `AsyncSession` but the builder does not explicitly end the read transaction before token counting.

D-090 now requires no DB transaction to span memory construction/token counting.

Apply the smallest compatible reconciliation **without changing the public build signature**:

```text
ConversationMemoryBuilder.build
→ open one explicit short read transaction only around
   list_recent_completed_turn_pairs_for_memory(...)
→ end that transaction
→ validate/sanitize/token-count/pack memory with no DB transaction open
```

Use a fresh Step-6.8-A internal session for memory building.

Do not move memory query logic into ConversationService.

## 3.6 Step 6.7 generation seam and retry ownership

Reuse the accepted Step-6.7/6.9 generation components already in the repository.

Current accepted downstream shapes include:

```text
PromptPackage
→ LLMRequestSerializer.serialize(package, GenerationConfig)
→ LLMGenerationRequest
→ existing LLMProvider / OpenAILLMProvider generation path
→ LLMGenerationResult
```

Step-6.9 has already extended serialization for role-preserving conversation memory and has already implemented the D-084 exact-preflight fallback behavior.

### Accepted retry owner

The accepted OpenAI adapter currently owns the **application-controlled transient retry loop**.

Preserve:

```text
OpenAI SDK automatic retries = 0
AsyncOpenAI(..., max_retries=0)

application transient retry budget = LLM_MAX_TRANSIENT_RETRIES
V0 max = 1

logical attempt 1
→ accepted transient failure
→ application-owned backoff/jitter
→ logical attempt 2
→ stop
```

Do **not** describe this as an SDK retry.

Do **not** add a second independent retry loop in RagOrchestrator/ConversationService on top of the accepted Step-6.7 retry owner.

### Step-6.8-A integration refinement

D-084/D-085 require the memory selection/composition part of generation to be **attempt-scoped**, not RAG-run-scoped:

```text
FOR EACH logical generation attempt:
    rebuild eligible conversation memory fresh
    → whole-turn pack under the same already-selected evidence PromptPackage
    → serialize request
    → run the accepted exact-preflight / zero-memory fallback
    → at most one responses.create(...) for that logical attempt
```

The accepted retry loop remains the retry-policy owner. Implement only the **smallest internal attempt-preparation seam** needed so that a new logical attempt can obtain freshly rebuilt memory/request input while preserving the existing retry loop, retry classification, backoff/jitter, exact-preflight behavior, and `max_retries=0` SDK configuration.

Do not create a new `GenerationRetryService`, generic retry framework, second provider adapter, or parallel retry policy.

If the current repository exposes an equivalent accepted attempt-preparation seam, reuse it directly. If satisfying fresh per-attempt memory would require a material architecture/public-interface redesign rather than a small internal reconciliation, STOP and report `BLOCKED — DECISION NEEDED`.

Do not bypass `LLMRequestSerializer`.

Do not call provider SDK methods from ConversationService or RagOrchestrator.

Reuse the existing model-aware/tiktoken `TokenCounter` implementation from the accepted Step-6.7 repository. Do not create a second tokenizer implementation.

## 3.7 Step 6.10 citation validation

Reuse:

```python
sources_from_prompt_package(package)
CitationValidator.validate(
    text=generated_text,
    sources=...,
    citation_required=True,
)
```

Grounded learner answers require citation validation.

The validator returns trusted `ValidatedCitation` snapshots.

Do not use model-authored URLs/titles/provenance.

Semantic NO_EVIDENCE does not invoke citation validation.

## 3.8 Conversation baseline

Current internal request is extended to:

```python
@dataclass(frozen=True)
class ChatRequest:
    user_id: UUID
    conversation_id: UUID
    lesson_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    content: str
```

No `AsyncSession`, ORM entity, DB connection, provider credential, or lock handle crosses this AI boundary.

---

# 4. Ownership

## ConversationService owns

```text
business/Conversation gates
Transaction A
retry state machine
D-090 lock lifecycle
authoritative Assistant state checks
call AIChatService
Transaction B
commit/rollback
failure finalization
HTTP/application mapping
```

ConversationService must NOT own:

```text
retrieval logic
reranking logic
evidence threshold logic
prompt building
memory selection
LLM serialization/provider call
citation parsing/validation
```

## AIChatService owns

```text
ChatRequest scalar/value adaptation
RagOrchestrator delegation
safe normalized AI/RAG technical error boundary
```

It owns no DB transaction and receives no ORM/session from ConversationService.

## RagOrchestrator owns

```text
internal tier sequencing
internal SessionFactory use for AI-owned reads
retrieval
reranking
evidence gate
PromptContextBuilder
ConversationMemoryBuilder integration
LLM serialization/generation
citation validation
RagRunResult construction
calibration score collection seam
```

It does NOT:

```text
commit/rollback learner Message state
set Assistant COMPLETED/FAILED
persist MessageRetrieval
persist MessageCitation
map HTTP status
run external retrieval
```

---

# 5. Runtime DTOs

Create a small provider-independent RAG runtime package following repository conventions, preferably:

```text
backend/app/ai/rag/
├── __init__.py
├── schemas.py
├── errors.py
└── orchestrator.py
```

Do not create a generic pipeline framework.

## 5.1 Enums

```text
RagRunStatus
├── GROUNDED_ANSWER
└── NO_EVIDENCE

RagInternalTier
├── CURRENT_LESSON
└── INTERNAL_KB

RagTierUsed
├── CURRENT_LESSON
├── INTERNAL_KB
└── NONE
```

## 5.2 RetrievalTraceEntry

```python
@dataclass(frozen=True)
class RetrievalTraceEntry:
    chunk_id: UUID
    rank: int
    retrieval_score: float
    rerank_score: float
```

`rank` is original semantic rank.

Do not add `rerank_rank` to the persistence DTO.

## 5.3 RagRunResult

Exact frozen logical contract:

```python
@dataclass(frozen=True)
class RagRunResult:
    assistant_message_id: UUID
    status: RagRunStatus
    assistant_content: str
    tiers_attempted: tuple[RagInternalTier, ...]
    tier_used: RagTierUsed
    current_lesson_candidate_count: int
    current_lesson_scored_count: int
    internal_kb_candidate_count: int
    internal_kb_scored_count: int
    selected_context_count: int
    memory_selected_turn_count: int
    retrieval_trace: tuple[RetrievalTraceEntry, ...]
    validated_citations: tuple[ValidatedCitation, ...]
```

Runtime-only.

`memory_selected_turn_count` is frozen as:

```text
number of conversation-memory turns attached to the FINAL successful provider request
that produced assistant_content
```

Therefore:

```text
final successful request uses normal selected memory
→ actual selected turn count

same logical attempt succeeds through D-084 zero-memory overflow fallback
→ 0

transient failure creates a new logical attempt
→ memory is rebuilt fresh
→ if that retry succeeds with memory, use the selected count from THAT successful attempt

memory disabled / no eligible memory
→ 0
```

This field is runtime metadata only. It must describe the final successful provider request, not the maximum memory selected earlier in the RAG run and not a failed logical attempt.

If the accepted Step-6.7 result does not currently expose enough final-request metadata to determine this value unambiguously, add only the smallest internal runtime metadata needed to the existing generation result/path. Do not persist that metadata and do not change the public API.

Do NOT persist `RagRunResult`.

Do NOT add a `rag_runs` table.

Do NOT add fields for:

```text
provider payload
PromptPackage
ConversationMemory full text
chunk content
LLMGenerationResult object
token usage
stage timing blobs
error_code/error_stage
```

Those remain component results/logging, not the orchestration persistence contract.

---

# 6. RagRunResult Invariants

## Grounded CURRENT_LESSON

```text
status = GROUNDED_ANSWER
tier_used = CURRENT_LESSON
tiers_attempted = (CURRENT_LESSON,)
internal_kb_candidate_count = 0
internal_kb_scored_count = 0
selected_context_count > 0
memory_selected_turn_count >= 0
retrieval_trace = ALL scored candidates from CURRENT_LESSON only
validated_citations = trusted Step-6.10 snapshots
assistant_content = exact generated text that passed citation validation
```

## Grounded INTERNAL_KB

```text
status = GROUNDED_ANSWER
tier_used = INTERNAL_KB
tiers_attempted = (CURRENT_LESSON, INTERNAL_KB)
retrieval_trace = ALL scored candidates from INTERNAL_KB only
```

Rejected CURRENT_LESSON candidates must not appear in:

```text
retrieval_trace
PromptPackage
source_map
validated_citations
```

for an INTERNAL_KB-selected grounded answer.

## Semantic NO_EVIDENCE

```text
status = NO_EVIDENCE
assistant_content = exact D-091 copy
tiers_attempted = (CURRENT_LESSON, INTERNAL_KB)
tier_used = NONE
selected_context_count = 0
memory_selected_turn_count = 0
retrieval_trace = ()
validated_citations = ()
```

Candidate/scored counts for both attempted tiers remain populated.

---

# 7. Configuration

Extend existing `Settings` only with:

```python
rag_evidence_calibration_mode: bool = False
rag_min_rerank_score: float | None = None
```

Environment names:

```text
RAG_EVIDENCE_CALIBRATION_MODE
RAG_MIN_RERANK_SCORE
```

Update `.env.example` safely.

## Validation

`RAG_MIN_RERANK_SCORE`:

- may be `None`;
- numeric strings from environment may parse normally;
- if numeric, value must be finite;
- reject `NaN`;
- reject `+Inf` / `-Inf`;
- reject Python bool-as-number input explicitly;
- invalid strings must fail Settings validation;
- no guessed numeric default.

Use the current Pydantic settings conventions.

## Internal runtime configuration error

Use one stable internal code:

```text
RAG_CONFIGURATION_INVALID
```

for learner-path mode/threshold configuration that prevents RAG execution.

It is not a new learner API contract; normal technical failure still maps through the existing Conversation AI failure response.

---

# 8. Operating Modes

## 8.1 Calibration mode

When:

```text
rag_evidence_calibration_mode = True
```

learner `AIChatService.generate_reply()` must fail with `RAG_CONFIGURATION_INVALID` before embedding/retrieval begins.

This is true whether the threshold is null or numeric.

## 8.2 Normal learner mode

Allowed only when:

```text
rag_evidence_calibration_mode = False
AND
rag_min_rerank_score is finite numeric
```

If threshold is null:

```text
RAG_CONFIGURATION_INVALID
→ zero retrieval
```

---

# 9. Evidence Gate

Normal learner evidence gate:

```python
usable = any(
    candidate.rerank_score >= settings.rag_min_rerank_score
    for candidate in rerank_result.scored_candidates
)
```

Equality passes.

Do not use `retrieval_score` for evidence acceptance.

Do not use candidate existence as evidence sufficiency.

Do not treat Top-K membership as evidence sufficiency.

The threshold selects/rejects the **tier**. It does not create a new per-candidate pruning stage.

When a tier is accepted, Step 6.6 receives the D-092 `top_candidates` unchanged.

---

# 10. Internal Tier Flow

Implement a small internal helper for one tier; exact private function name may follow repository style.

Conceptual flow:

```text
query
+ trusted lesson ID when CURRENT_LESSON
↓
open internal SessionFactory session
↓
SemanticRetrievalService.retrieve(...)
↓
close internal session
↓
RerankingService.rerank(...) ONCE
↓
RerankResult
```

### CURRENT_LESSON

Use:

```python
build_scope_filter(
    RetrievalScope.CURRENT_LESSON,
    trusted_lesson_id=request.lesson_id,
)
```

### INTERNAL_KB

Use accepted INTERNAL_KB filter behavior:

```python
build_scope_filter(RetrievalScope.INTERNAL_KB, ...)
# resolves to None
```

or direct equivalent current repository use.

Do not query external sources.

Do not merge candidate pools across tiers.

---

# 11. Normal RagOrchestrator Flow

Normal method name may follow repository convention; prefer one clear learner method such as:

```python
async def run(self, request: ChatRequest) -> RagRunResult
```

Do not expose HTTP concepts here.

Required order:

```text
validate normal runtime configuration
↓
CURRENT_LESSON retrieve
↓
CURRENT_LESSON rerank once
↓
evidence gate over scored_candidates
```

If usable:

```text
select CURRENT_LESSON
→ do not call INTERNAL_KB
```

Else:

```text
INTERNAL_KB retrieve
↓
INTERNAL_KB rerank once
↓
evidence gate
```

If neither usable:

```text
construct NO_EVIDENCE RagRunResult
→ STOP
```

No prompt, memory, LLM, or citation work in semantic NO_EVIDENCE.

---

# 12. Grounded Prompt / Memory / Generation / Citation Flow

For exactly one selected tier:

```text
selected RerankResult.top_candidates
↓
PromptContextBuilder.build(...) exactly once
↓
ContextBuildResult
```

If `CONTEXT_BUDGET_EXHAUSTED` occurs:

```text
technical failure
→ no fallback to another tier
```

Do not call PromptContextBuilder for rejected tiers.

## PromptBudget

Build from accepted generation config:

```python
PromptBudget(
    model_input_limit=generation_config.model_input_limit,
    reserved_output_tokens=generation_config.max_output_tokens,
    serialization_overhead_tokens=0,
)
```

## Memory sequence lookup

`ChatRequest` intentionally does not carry `current_user_sequence_number`.

Before memory build, use a fresh internal DB session and a short authoritative read of `request.user_message_id`.

Validate that the current message:

```text
exists
belongs to request.conversation_id
role = USER
status = COMPLETED
```

Read its `sequence_number` as a scalar/runtime value.

Do not pass the ORM object beyond the short read boundary.

## Memory and bounded logical generation attempts

The **selected evidence PromptPackage is built once** and remains unchanged across generation attempts.

First derive the residual memory budget from that already-selected evidence package.

For **each logical generation attempt when memory is eligible**:

```text
same evidence PromptPackage
→ derive/use the same evidence-first residual memory budget basis
→ ConversationMemoryBuilder.build(...) once for THIS logical attempt
→ with_conversation_memory(...)
→ LLMRequestSerializer.serialize(...)
→ accepted Step-6.7 exact-preflight/generation attempt flow
```

Correct rule:

```text
ConversationMemoryBuilder
= once per logical generation attempt when memory is eligible
NOT once per entire grounded RAG run
```

A D-084 zero-memory exact-preflight fallback belongs to the **same logical attempt**:

```text
memory-aware exact preflight overflows
→ remove all memory from the already-prepared request/package for THIS attempt
→ no second DB memory selection merely to construct empty memory
→ exact preflight once more
→ generation if valid
```

If that logical attempt later encounters an accepted transient provider failure, the application transient retry may create **one new logical generation attempt**. For that new attempt:

```text
memory becomes eligible again
→ rebuild memory fresh
→ do not inherit the prior attempt's zero-memory fallback decision
```

No memory work occurs for semantic NO_EVIDENCE or calibration.

## Generation

Reuse the accepted Step-6.7/6.9 application-owned retry path:

```text
GenerationConfig.from_settings(settings)
LLMRequestSerializer.serialize(...)
accepted application transient retry owner
OpenAI SDK max_retries = 0
```

Correct distinction:

```text
one RAG orchestration / one Assistant processing attempt
may contain the bounded logical generation-attempt behavior frozen by Step 6.7 + D-084/D-085
```

Generation retries must **not** cause another:

```text
retrieval
rerank
evidence gate
PromptContextBuilder execution
```

The selected tier, `scored_candidates`, `top_candidates`, evidence package, and source_map remain fixed for all bounded generation attempts in that RAG run.

## Citation validation

After the **final successful generated answer** only:

```python
sources = sources_from_prompt_package(package_with_memory)
validation = citation_validator.validate(
    text=generation_result.text,
    sources=sources,
    citation_required=True,
)
```

Validation failure is a technical failure.

Do not run a citation-repair LLM.

Construct `RagRunResult.validated_citations` from:

```python
validation.citations
```

Citation validation occurs only after the accepted bounded generation flow returns the final successful answer. Failed/transient logical attempts are never citation-validated.

Set `RagRunResult.memory_selected_turn_count` from the memory actually attached to that final successful provider request, using the frozen semantics in Section 5.3.

Do not carry full `CitationValidationResult` across the Conversation persistence boundary.

---

# 13. Calibration Score-Collection Contract

Create a separate runtime contract from `RagRunResult`.

Preferred module placement:

```text
backend/app/ai/rag/schemas.py
```

or a nearby focused `calibration.py` only if repository organization benefits.

Do not create a persistence model/table.

## Request

```python
@dataclass(frozen=True)
class CalibrationScoreRequest:
    query: str
    lesson_id: UUID
```

No learner/user/Assistant persistence identity is required.

## Candidate trace

```python
@dataclass(frozen=True)
class CalibrationCandidateTrace:
    chunk_id: UUID
    retrieval_rank: int
    retrieval_score: float
    rerank_rank: int
    rerank_score: float
    knowledge_source_id: UUID
    source_type: str
    source_lesson_id: UUID | None
    content_type: str
```

This contains enough identity/rank/score/scope information for Step 7.3 without exposing chunk text.

## Tier trace

```python
@dataclass(frozen=True)
class CalibrationTierTrace:
    tier: RagInternalTier
    status: str          # "SCORED" | "EMPTY"
    retrieval_candidate_count: int
    scored_count: int
    candidates: tuple[CalibrationCandidateTrace, ...]
```

Technical retrieval/reranker failure must raise the existing normalized technical error rather than return partial successful traces.

## Full trace

```python
@dataclass(frozen=True)
class CalibrationScoreTrace:
    current_lesson: CalibrationTierTrace
    internal_kb: CalibrationTierTrace
```

## Collection method

Expose one small internal method equivalent to:

```python
async def collect_calibration_scores(
    self,
    request: CalibrationScoreRequest,
) -> CalibrationScoreTrace
```

Required:

```text
calibration mode must be enabled
CURRENT_LESSON always measured
INTERNAL_KB always measured independently
no threshold-based tier winner
no PromptContextBuilder
no ConversationMemoryBuilder
no LLM
no CitationValidator
no Assistant lifecycle
no MessageRetrieval
no MessageCitation
no evaluation artifact writes
```

Phase 7 will own evaluation run files/artifacts.

---

# 14. AIChatService Integration

Update the internal Protocol to:

```python
class AIChatService(Protocol):
    async def generate_reply(self, request: ChatRequest) -> RagRunResult:
        ...
```

Add `assistant_message_id` to `ChatRequest`.

Replace the default production stub wiring with the real RAG-backed AIChatService while preserving test fakes as test utilities.

Do not keep a hidden production fallback that returns deterministic stub prose if RAG/provider configuration is missing.

The real service delegates to RagOrchestrator.

It must not accept a DB session from ConversationService.

Update old conversation test fakes to return valid `RagRunResult` objects rather than raw strings.

---

# 15. D-090 Processing Guard

Prefer a focused Conversation/application module:

```text
backend/app/conversation/processing_lock.py
```

Do not put PostgreSQL lock SQL inside RagOrchestrator.

## 15.1 Stable advisory key

Freeze one deterministic mapping:

```python
digest = hashlib.sha256(assistant_message_id.bytes).digest()
lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
```

Do not use Python `hash()`.

Document theoretical 64-bit collision as extremely low-probability false contention.

## 15.2 Acquire

Use the existing `AsyncEngine` and one dedicated `AsyncConnection`:

```text
engine.connect()
→ SELECT pg_try_advisory_lock(:key)
→ end/commit acquisition transaction
→ keep SAME connection checked out
→ no transaction open
```

Acquisition is non-blocking.

If false:

```text
DUPLICATE_RAG_GENERATION
HTTP boundary = 409
zero AI work
zero Assistant mutation
```

## 15.3 State check after lock acquisition

Use a short authoritative DB state check.

Required Assistant identity:

```text
id = request.assistant_message_id
conversation_id = request.conversation_id
role = ASSISTANT
reply_to_message_id = request.user_message_id
```

State:

```text
PENDING   → may process
COMPLETED → DUPLICATE_RAG_GENERATION
FAILED    → DUPLICATE_RAG_GENERATION
```

COMPLETED/FAILED same-attempt processing performs no AI call and no mutation.

## 15.4 Release

In `finally`, on the **same physical connection**:

```text
SELECT pg_advisory_unlock(:key)
→ end/commit unlock transaction
→ return connection to pool
```

If unlock safety cannot be guaranteed, invalidate/close the connection so a pooled connection cannot retain an unknown advisory lock.

No session-level advisory lock may leak back into the pool.

## 15.5 No long DB transaction

The dedicated lock connection may stay checked out, but no DB transaction intentionally spans:

```text
embedding
reranking
prompt building
memory token packing
LLM inference
citation validation
```

Do not use:

```text
SELECT ... FOR UPDATE held across AI work
pg_advisory_xact_lock for processing lifetime
```

---

# 16. ConversationService Flow

Preserve existing synchronous HTTP behavior.

No queue, worker, SSE, WebSocket, or background job.

## 16.1 Send — Transaction A

Existing business flow remains:

```text
lock/validate Conversation
validate test-state chat availability
create USER COMPLETED
create ASSISTANT PENDING
reply_to_message_id = USER.id
touch Conversation
construct ChatRequest including assistant_message_id
COMMIT
```

Then release Transaction A before AI work.

## 16.2 Retry — Transaction A

Preserve existing retry state machine:

```text
FAILED Assistant target
→ resolve original USER
→ Conversation row lock / latest-attempt rules
→ create NEW Assistant PENDING
→ new assistant_message_id
→ COMMIT
```

Do not reuse the old failed Assistant ID.

## 16.3 Processing

After Transaction A:

```text
acquire D-090 advisory lock
→ state check
→ AIChatService.generate_reply(request)
→ RagRunResult
→ Transaction B
→ release advisory lock in finally
```

---

# 17. Transaction B

ConversationService owns one short atomic success transaction.

Always re-load the target Assistant with a row lock before finalization.

Verify:

```text
correct assistant ID
correct conversation
role = ASSISTANT
status = PENDING
reply_to_message_id = expected user ID
```

## 17.1 Grounded success

```text
BEGIN
→ insert MessageRetrieval rows from RagRunResult.retrieval_trace
→ insert MessageCitation rows from RagRunResult.validated_citations
→ set Assistant.content = RagRunResult.assistant_content
→ PENDING → COMPLETED
→ flush
→ COMMIT
```

Reuse existing Step-6.10 `repository.add_message_citations(...)` directly.

Do not require/reconstruct a discarded full `CitationValidationResult` merely to use the historical helper `finalize_validated_assistant(...)`.

Add one small repository helper for `MessageRetrieval` insertion if the current repository does not already contain one.

Repository helper must flush only; it must not commit.

## 17.2 NO_EVIDENCE success

Validate `RagRunResult` no-evidence invariants, then:

```text
BEGIN
→ zero MessageRetrieval inserts
→ zero MessageCitation inserts
→ set exact D-091 content
→ PENDING → COMPLETED
→ COMMIT
```

Public response returns:

```text
citations=[]
```

## 17.3 Technical failure

For retrieval/rerank/prompt/memory/LLM/citation/config technical failure:

```text
short finalization transaction
→ target Assistant PENDING → FAILED
→ content = None
→ no normal MessageRetrieval
→ no MessageCitation
→ COMMIT
```

Return the existing learner-safe AI failure contract.

Never expose raw provider/model/DB exception text.

## 17.4 Duplicate processing exception

`DUPLICATE_RAG_GENERATION` is special:

```text
do NOT mark Assistant FAILED
```

because another processor may own or may already have completed that attempt.

---

# 18. MessageRetrieval Persistence

Use existing ORM/table only.

No migration.

For each `RetrievalTraceEntry`:

```text
message_id      = selected Assistant.id
chunk_id        = trace.chunk_id
rank            = trace.rank
retrieval_score = trace.retrieval_score
rerank_score    = trace.rerank_score
```

Do not persist rejected-tier traces on grounded success.

Do not persist any normal trace for NO_EVIDENCE, calibration, or failed runs.

---

# 19. Public API Behavior

No new public routes.

No calibration endpoint.

No threshold/calibration request fields.

Existing send/retry API shapes remain.

Step-6.10 citation-aware `MessageResponse.citations[]` remains authoritative.

## Send/retry grounded success

Returns the persisted Assistant message with validated citation snapshots projected through the existing citation API logic.

## Semantic NO_EVIDENCE

Returns normal successful Assistant `COMPLETED` message with:

```text
content = exact D-091 string
citations = []
```

## Duplicate processor

```text
DUPLICATE_RAG_GENERATION
→ HTTP 409
```

No second public error name.

## Other technical AI/RAG failures

Use existing safe learner AI failure response semantics (`AI_RESPONSE_FAILED`) with safe message IDs only.

---

# 20. Error Boundary

Do not convert technical failures into semantic no-evidence.

Examples that remain technical:

```text
embedding failure
vector DB failure
invalid retrieval filter
reranker failure
invalid reranker output
prompt budget failure
memory repository/token failure
LLM provider/config/auth/timeout failure
citation validation failure
RAG configuration invalid
Transaction B failure
```

No tier fallback occurs because of a technical failure.

Tier fallback is only:

```text
CURRENT_LESSON semantically insufficient
→ INTERNAL_KB
```

---

# 21. Structured Logging

Add safe Step-6.8-A orchestration logs.

Allowed fields include:

```text
conversation_id
assistant_message_id
calibration_mode
retrieval_tiers_attempted
tier_used
current_lesson_candidate_count
current_lesson_scored_count
internal_kb_candidate_count
internal_kb_scored_count
selected_context_count
memory_selected_turn_count
citation_count
retrieval_duration_ms
rerank_duration_ms
context_build_duration_ms
memory_build_duration_ms
llm_duration_ms
citation_validation_duration_ms
total_rag_duration_ms
status
error_stage
error_code
lock_acquired
duplicate_processing
lock_release_status
```

Calibration logs may include counts/timings/status only.

Do not log:

```text
learner question
chunk content
conversation-memory text
full prompt
generated answer
provider credentials
raw exception text
embedding vectors
```

Phase-7 score source is `CalibrationScoreTrace`, not logs.

---

# 22. Expected Files / Components

Inspect current repository before editing and follow existing exact names where newer accepted code differs.

Expected new files are equivalent to:

```text
backend/app/ai/rag/
├── __init__.py
├── schemas.py
├── errors.py
└── orchestrator.py

backend/app/conversation/processing_lock.py

docs/ai/step-6.8-end-to-end-rag.md
```

Expected modifications include:

```text
backend/app/ai/reranking/schemas.py
backend/app/ai/reranking/service.py
backend/app/ai/memory/builder.py
backend/app/ai/llm/openai_provider.py        # only as needed for the small D-084/D-085 attempt-preparation reconciliation
backend/app/ai/llm/schemas.py                # only if final successful request memory metadata cannot otherwise be derived
backend/app/conversation/ai_chat.py
backend/app/conversation/service.py
backend/app/conversation/repository.py
backend/app/core/config.py
backend/.env.example
```

and focused tests.

Modify additional existing dependency-wiring files only where required to replace the Phase-3 stub with the accepted real RAG-backed service.

Do not create speculative layers merely to match this suggested file list.

---

# 23. Schema / Migration / Dependency Impact

Expected:

```text
Schema change:     NO
Migration:         NO
New dependency:    NO
Public API schema: NO
Frontend change:   NO
```

Reuse:

```text
PostgreSQL
SQLAlchemy async engine/sessionmaker
pgvector retrieval
existing MessageRetrieval
existing MessageCitation
existing tiktoken/model-aware counter
existing OpenAI provider stack
```

Do not modify Alembic history for Step 6.8-A.

If implementation discovers that a schema/migration is actually required, STOP and report `BLOCKED — DECISION NEEDED` instead of adding one.

---

# 24. Focused Tests — Reranker D-092

Add/update tests proving:

1. full scored ordered set is retained;
2. Top-K is derived from the same set;
3. Top-K length is `min(scored_count, RERANKER_TOP_K)`;
4. deterministic ordering remains:

```text
rerank_score DESC
→ original semantic rank ASC
→ stable identity/order
```

5. `rerank_rank` is assigned consistently over the full deterministic scored order;
6. empty candidates returns two empty views with zero inference;
7. batched inference is executed only once for the logical rerank operation — deriving Top-K does not repeat batches;
8. partial/invalid reranker failure still fails closed with no partial successful result.

---

# 25. Focused Tests — Configuration / Modes

Cover:

```text
calibration=true + threshold=None
calibration=true + threshold=numeric
calibration=false + threshold=None
calibration=false + finite numeric
```

Assert:

- learner RAG never retrieves while calibration=true;
- normal learner RAG never retrieves with null threshold;
- numeric threshold is not applied to choose a calibration winner;
- equality to threshold passes;
- NaN/Inf/bool invalid;
- no guessed default exists.

---

# 26. Focused Tests — Calibration

Use fake embedding/reranker dependencies or the existing deterministic test seams.

No real model/network calls.

Verify:

```text
CURRENT_LESSON measured
AND
INTERNAL_KB measured independently
```

including empty candidate cases.

Assert:

```text
PromptContextBuilder calls = 0
ConversationMemoryBuilder calls = 0
LLM calls = 0
CitationValidator calls = 0
MessageRetrieval inserts = 0
MessageCitation inserts = 0
Assistant lifecycle writes = 0
```

Trace must expose retrieval/rerank rank+score and scope identity required by Step 7.3.

---

# 27. Focused Tests — Normal Tier Orchestration

## Current Lesson selected

```text
CURRENT_LESSON passes threshold
→ INTERNAL_KB not called
→ PromptContextBuilder once
→ bounded logical generation-attempt flow
   → memory once per logical attempt when eligible
   → accepted exact-preflight / zero-memory fallback semantics
→ citation validation once on final successful answer
```

Verify selected-tier retrieval trace contains **all CURRENT_LESSON scored candidates**, not Top-K only.

Generation retry behavior must not repeat retrieval, reranking, evidence gating, or PromptContextBuilder.

## Internal KB selected

```text
CURRENT_LESSON insufficient
→ INTERNAL_KB passes
→ prompt receives only INTERNAL_KB top_candidates
```

Rejected CURRENT_LESSON evidence must not leak into prompt/source_map/persistence/citations.

## Semantic no-evidence

Both tiers insufficient:

```text
exact D-091 content
Assistant COMPLETED
citations=[]
zero MessageRetrieval
zero MessageCitation
prompt=0
memory=0
LLM=0
citation validation=0
```

## Technical failures

At each major stage, verify:

```text
Assistant FAILED
content=None
zero normal retrieval rows
zero citation rows
no semantic fallback caused by the technical error
```

---

# 28. Focused Tests — Prompt / Memory / Generation Attempts / Citation

Verify the invariant foundation first:

- `top_candidates`, never full `scored_candidates`, enter PromptContextBuilder;
- PromptContextBuilder executes exactly once per grounded RAG run;
- prompt budget uses generation input limit + output reserve + zero local serialization overhead;
- `CONTEXT_BUDGET_EXHAUSTED` does not trigger another tier;
- memory runs only after prompt/evidence selection;
- memory cannot alter retrieval/rerank/evidence gate;
- memory empty is valid;
- each memory DB read transaction is ended before token counting/packing;
- current user message is not duplicated in memory;
- LLM serializer preserves historical roles;
- OpenAI SDK automatic retries remain `max_retries=0`;
- application transient retry remains bounded to max 1;
- citation validation uses `citation_required=True`;
- citation failure is technical;
- memory never becomes a citation source.

Add explicit D-084/D-085 generation-attempt coverage:

## A. First logical attempt succeeds

```text
logical attempt 1
→ memory eligible
→ ConversationMemoryBuilder called once
→ exact preflight fits
→ generation succeeds
→ no transient retry
```

Assert `RagRunResult.memory_selected_turn_count` equals the turns attached to the successful provider request.

## B. Exact preflight overflows with memory

```text
logical attempt 1
→ memory built once
→ memory-aware exact preflight overflows
→ SAME logical attempt removes all memory
→ second/final exact preflight
→ generation succeeds with zero memory
```

Assert:

```text
evidence unchanged
source_map unchanged
retrieval calls unchanged
rerank calls unchanged
evidence gate not repeated
PromptContextBuilder not repeated
no second ConversationMemoryBuilder/DB selection merely to create empty memory
memory_selected_turn_count = 0
```

## C. Transient failure creates a new logical attempt

```text
logical attempt 1
→ memory built fresh
→ accepted transient failure
→ application retry budget consumed
→ logical attempt 2
→ memory becomes eligible again
→ ConversationMemoryBuilder builds memory fresh again
→ attempt 2 succeeds
```

Assert the final `memory_selected_turn_count` is from attempt 2's successful provider request.

## D. Zero-memory fallback on attempt 1 does not disable memory on attempt 2

```text
attempt 1
→ memory built
→ exact overflow
→ zero-memory fallback
→ responses.create(...) encounters accepted transient failure

attempt 2
→ memory eligible again
→ fresh ConversationMemoryBuilder execution
→ memory-aware request may be used again
```

Do not carry attempt-1 zero-memory fallback state into attempt 2.

## E. Bounded preflight / retry counts

Preserve:

```text
logical generation attempts <= LLM_MAX_TRANSIENT_RETRIES + 1
V0 logical attempts <= 2
exact preflights per logical attempt <= 2
worst-case exact preflights with 2 attempts <= 4
responses.create(...) <= 1 per logical attempt
OpenAI SDK retries = 0
```

No unbounded loop.

## F. Citation validation only after final successful generation

Transient/failed logical attempts perform zero citation validation.

The final successful answer performs citation validation exactly once before RagRunResult success is returned.

## G. RAG stages remain one-shot despite generation retries

For a grounded RAG run with a transient generation retry, assert:

```text
selected tier retrieval = unchanged / not repeated
selected tier rerank = not repeated
evidence gate = not repeated
PromptContextBuilder = exactly 1
ConversationMemoryBuilder = once per logical generation attempt when eligible
```

---

# 29. PostgreSQL Integration Tests — D-090

These tests must use real PostgreSQL connections from the test database.

SQLite/mock-only proof is insufficient.

Cover at least:

1. two independent connections target same `assistant_message_id`:
   - first acquires;
   - second fails non-blocking;
   - second receives `DUPLICATE_RAG_GENERATION`;
   - second performs zero AI work;
2. different Assistant IDs can process concurrently;
3. session advisory lock survives acquisition transaction end;
4. lock connection has no intentionally open DB transaction during fake slow AI work;
5. success finalizes then releases lock;
6. technical failure finalizes FAILED then releases lock;
7. raised exception/cancellation executes the release path;
8. after release, the same key can be acquired again, but COMPLETED/FAILED state check prevents regeneration;
9. valid retry creates a new Assistant ID and new lock identity;
10. duplicate caller never marks shared Assistant FAILED;
11. unlock occurs on the same physical connection;
12. failed/unsafe unlock invalidates or closes the connection rather than returning an unknown held lock to the pool.

---

# 30. Transaction B Integration Tests

Use PostgreSQL test DB.

## Grounded atomicity

Given a valid `RagRunResult`:

```text
MessageRetrieval rows
+
MessageCitation rows
+
Assistant content
+
COMPLETED
```

must commit atomically.

Simulate a citation/retrieval insert/finalization failure and verify no partially successful `COMPLETED` state remains.

## No-evidence atomicity

Verify exact D-091 content and zero retrieval/citation rows.

## Failure finalization

Verify PENDING → FAILED with zero normal retrieval/citation rows.

---

# 31. Conversation API Regression Tests

Update existing send/retry tests for the new `RagRunResult` AI boundary.

Preserve:

```text
Conversation ownership/privacy
chat disabled during active periodic test
sequence allocation
USER persistence on AI failure
retry targets only latest valid FAILED attempt
retry creates new Assistant attempt
message history pagination/order
citation[] response contract
```

Add duplicate-processing HTTP 409 coverage.

No frontend contract regeneration should be required because public schema does not change.

---

# 32. Regression Commands

Run focused tests first, then broader regression.

Equivalent minimum verification:

```bash
cd backend

uv run pytest \
  tests/test_step65_reranking_service.py \
  tests/test_step63_retrieval_service.py \
  tests/test_step64_retrieval_service.py \
  tests/test_step610_citation_validator.py \
  tests/test_step610_citation_persistence.py \
  tests/test_conversation_api.py \
  <new step-6.8-A focused test files>

uv run pytest <D-090 PostgreSQL integration tests>

uv run pytest tests -q

uv run python -m compileall app
uv lock --check
uv run alembic current
uv run alembic check
```

Use actual current filenames if accepted repository test names differ.

Do not require internet, real provider credentials, or paid LLM/model calls in the standard suite.

Use fake provider/model seams.

---

# 33. Step Documentation

Create/update:

```text
docs/ai/step-6.8-end-to-end-rag.md
```

It must contain the required Step Note sections:

## Objective

Internal Lesson Chat RAG orchestration + calibration score seam.

## Why

Explain why retrieval/rerank/prompt/memory/generation/citation components require an application orchestration layer and why calibration must precede learner evidence selection.

## Mental Model

Include:

```text
Candidate generation
→ rerank
→ evidence decision
→ grounded generation OR deterministic no-evidence
```

and:

```text
runtime result
!=
persistence transaction
```

## Core Knowledge

Classify only concepts actually used.

Expected important concepts:

| Concept | Category | Role |
|---|---|---|
| RAG orchestration | AI | Coordinates existing RAG stages without merging their responsibilities |
| Evidence gate | AI | Converts reranker scores into tier usability after calibration |
| Calibration score seam | AI | Supplies retrieval/rerank evidence for Step 7.3 without generation |
| Runtime DTO boundary | BOTH | Separates AI execution result from DB persistence |
| Atomic finalization | SYSTEM | Prevents partial successful Assistant state |
| PostgreSQL session advisory lock | SYSTEM | Cross-process duplicate-processing guard without schema state |
| Short transaction boundary | BOTH | Prevents slow AI work from holding DB transactions |

Do not add concepts merely mentioned but not used.

## Data Flow

Document calibration and normal learner flow separately.

## Key Design Decisions

Reference inherited D-084, D-085, D-086 and Step-specific D-087 through D-092.

## Reusable Approach

Explain:

```text
keep model/data stages pure
→ return typed runtime result
→ persist once at application boundary
```

## Common Mistakes

Include at least:

```text
candidate exists = evidence
Top-K = threshold
second rerank for diagnostics
prompt every tier
memory in retrieval query
long DB transaction around LLM
persist rejected-tier trace
mark duplicate caller FAILED
use Python hash() for advisory key
```

## Definition of Done

Reflect this task's acceptance criteria and actual implementation.

---

# 34. Concepts Discovered / Tools Used

Update project records only with concepts/tools actually used by the final implementation.

Likely tools actually used:

| Tool | Category | Role |
|---|---|---|
| PostgreSQL advisory locks | SYSTEM | D-090 processing guard |
| SQLAlchemy AsyncSession / AsyncConnection | BOTH | Short reads, Transaction B, dedicated lock connection |
| pgvector | BOTH | Existing semantic retrieval storage/query path |
| tiktoken | AI | Existing model-aware prompt/memory token counting |
| OpenAI async provider integration | AI | Existing Step-6.7 generation path |

Do not add external retrieval/search tools.

---

# 35. Explicit Non-Goals

Do NOT implement:

```text
Step 6.8-B
external retrieval provider
trusted-domain configuration
web search
external URL runtime evidence
Phase 7 dataset/evaluation runner
RAG_MIN_RERANK_SCORE numeric value
regression quality thresholds
rag_runs table
processing-lock table
PROCESSING Message status
Redis lock
queue/worker
background generation
SSE/WebSocket/streaming
query rewriting from conversation memory
history concatenation into retrieval query
unbounded/independent extra LLM generation beyond the accepted bounded transient retry policy
second LLM judge/fact-check/repair call
LLM citation repair
LLM evidence judge
retrieval_score evidence gate
score fusion
candidate dedup/MMR
new prompt-summary/compression step
new schema or migration
new package dependency
```

---

# 36. Acceptance Criteria

The task is complete only when all are true:

- [ ] D-092 dual-view reranker result is implemented with one logical rerank execution.
- [ ] All scored candidates remain available for threshold/trace/calibration.
- [ ] Top-K derives from the same deterministic full ordering.
- [ ] Normal learner mode refuses to retrieve when calibration=true.
- [ ] Normal learner mode refuses to retrieve when threshold is null.
- [ ] Threshold is not guessed.
- [ ] Threshold equality passes.
- [ ] CURRENT_LESSON has strict priority.
- [ ] INTERNAL_KB runs only after semantic insufficiency in CURRENT_LESSON.
- [ ] Technical failure never causes semantic tier fallback.
- [ ] PromptContextBuilder receives selected-tier Top-K only.
- [ ] PromptContextBuilder runs exactly once per grounded run.
- [ ] Semantic NO_EVIDENCE runs zero prompt/memory/LLM/citation work.
- [ ] D-091 exact content is preserved.
- [ ] Conversation memory runs only after evidence/prompt selection.
- [ ] Memory DB read transaction ends before token counting/packing.
- [ ] One RAG orchestration / Assistant processing attempt preserves the bounded Step-6.7 + D-084/D-085 logical generation-attempt policy; no extra retry loop is introduced.
- [ ] ConversationMemoryBuilder runs once per logical generation attempt when memory is eligible, not once per entire RAG run.
- [ ] D-084 zero-memory exact-preflight fallback does not trigger another DB memory selection in the same logical attempt.
- [ ] A transient retry creates a new logical attempt and memory becomes eligible/rebuilt fresh again.
- [ ] OpenAI SDK retries remain disabled (`max_retries=0`) and application transient retry remains max 1.
- [ ] Retrieval, reranking, evidence gating, and PromptContextBuilder are not repeated because generation retries occur.
- [ ] `memory_selected_turn_count` reflects the FINAL successful provider request (normal memory count, zero after zero-memory fallback, or fresh retry-attempt count).
- [ ] Grounded answer must pass citation validation.
- [ ] `RagRunResult` matches the frozen contract.
- [ ] Grounded retrieval trace contains all scored candidates from exactly one selected internal tier.
- [ ] NO_EVIDENCE has zero durable retrieval/citation rows.
- [ ] Technical failure has zero normal retrieval/citation rows.
- [ ] Calibration returns `CalibrationScoreTrace` and persists no production result.
- [ ] Calibration runs both internal tiers independently.
- [ ] ChatRequest contains `assistant_message_id` but no session/ORM/DB connection.
- [ ] D-090 advisory lock is non-blocking, session-level, cross-process, same-connection acquire/release.
- [ ] No DB transaction is intentionally held across slow AI work.
- [ ] Duplicate caller receives `DUPLICATE_RAG_GENERATION` / HTTP 409 and never marks Assistant FAILED.
- [ ] Retry creates a new Assistant attempt/lock identity.
- [ ] Transaction B atomically persists grounded success.
- [ ] Existing Step-6.10 citation API projection continues to work after reload.
- [ ] Existing Conversation business/privacy/retry behavior remains passing.
- [ ] No schema change.
- [ ] No migration.
- [ ] No new dependency.
- [ ] No public calibration API.
- [ ] No external retrieval.
- [ ] Focused + PostgreSQL concurrency + backend regression tests pass.
- [ ] `compileall`, `uv lock --check`, `alembic current`, and `alembic check` pass.
- [ ] Step Note updated to actual implementation.
- [ ] Concepts/Tools records updated only for actually used items.
- [ ] Specialist handoff to PM reports exact files, tests, risks, and remaining calibration release gate.

---

# 37. Stop Conditions During Codex Execution

STOP and report `BLOCKED — DECISION NEEDED` instead of guessing if implementation discovers any requirement for:

```text
new database schema/migration
new public API field/route
new external provider/domain allowlist
new Message lifecycle state
new durable RAG-run table
new persistence representation incompatible with MessageRetrieval/MessageCitation
architecture that cannot preserve D-084 through D-092
```

A small repository-compatible implementation reconciliation is allowed when directly required by the frozen contracts, including:

```text
D-092 RerankResult dual-view exposure
D-090 short memory-read transaction boundary
D-084/D-085 attempt-scoped memory preparation integrated into the existing Step-6.7 application retry owner
ChatRequest assistant_message_id addition
RagRunResult / CalibrationScoreTrace runtime DTOs
flush-only MessageRetrieval repository helper
```

Do not reinterpret these as permission to expand scope.

---

# 38. Required Codex Completion Handoff

When implementation is complete, report to PM:

```text
Step: 6.8-A
Status:
What was done:
Key decisions preserved:
Files/components changed:
Tests run + results:
Concepts added:
Tools added:
Schema/migration/dependency impact:
Problems/risks:
Decisions needed:
Calibration release gate status:
Recommended next action:
```

Expected next action after accepted implementation:

```text
Step 7.1
→ 7.2
→ 7.3 calibration
```

Do NOT start those Steps inside this Codex task.

---

# PM Approval Gate

This task is **READY_FOR_PM_TASK_REVIEW**, not CODEX-READY yet.

Required next state:

```text
PM reviews this file
→ PM approves or returns corrections
→ only then mark CODEX-READY
→ only then run Codex
```
