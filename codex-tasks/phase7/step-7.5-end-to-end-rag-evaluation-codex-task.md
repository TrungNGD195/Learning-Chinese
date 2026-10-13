# Codex Task Draft — Step 7.5 End-to-End RAG Evaluation

> **STATUS: DRAFT FOR PM REVIEW / FREEZE ONLY**
>
> **DO NOT EXECUTE THIS TASK UNTIL PM EXPLICITLY FREEZES IT.**
>
> This task authorizes only **OFFLINE IMPLEMENTATION / DETERMINISTIC TEST MODE** after PM freeze. It does **not** authorize paid API calls, live external search, official benchmark execution, HUMAN_APPROVED annotation creation, Step 7.6, Step 7.7, or a claim that Step 7.5 is DONE.

---

# 1. Context

Project: **LLM + RAG Web App học tiếng Trung cho người mới bắt đầu**.

Step 7.5 evaluates the actual production-shaped Lesson Chat RAG lifecycle rather than an isolated retriever or generator.

Relationship:

```text
Step 7.3 = retriever isolated
Step 7.4 = generator isolated
Step 7.5 = actual end-to-end system behavior
```

Current Phase-7 state:

```text
7.1 DONE
7.2 DONE
7.3 DONE
7.4 OFFLINE IMPLEMENTATION VERIFIED; overall NOT DONE
7.5 CURRENT PREPARATION
7.7 NOT STARTED
7.6 NOT STARTED
```

D-101 keeps paid runtime evaluation deferred.

D-102 permits downstream Phase-7 work in:

```text
OFFLINE IMPLEMENTATION / DETERMINISTIC TEST MODE
```

Fake/mock outputs must never be represented as official benchmark/baseline evidence.

---

# 2. Objective

Implement the Step 7.5 evaluation harness, schemas, deterministic evaluator logic, artifact writer, fresh human-calibration package, and offline integration tests needed to evaluate:

```text
EvaluationCase
→ conversation/persistence setup
→ trusted lesson/domain context
→ CURRENT_LESSON retrieval
→ INTERNAL_KB fallback when required
→ TRUSTED_EXTERNAL fixture fallback when required
→ reranking + frozen evidence gate
→ prompt/context + conversation memory
→ LLM generation boundary
→ CitationValidator
→ persistence/finalization
→ final assistant state
→ E2E evaluator
```

The offline implementation must exercise as much real local production behavior as possible while replacing only paid/network dependencies with deterministic fakes/fixtures.

The implementation must be ready for a later official runtime run, but **this task must not perform that run**.

---

# 3. Current State / Frozen Inputs

## Dataset

```text
dataset_version = v0.8.0
APPROVED = 60
DEVELOPMENT = 48
HOLDOUT = 12
```

All six buckets are in scope:

```text
CURRENT_LESSON_ANSWERABLE
INTERNAL_KB_FALLBACK
TRUSTED_EXTERNAL_FALLBACK
NO_EVIDENCE_REFUSAL
OUT_OF_DOMAIN_REFUSAL
MULTI_TURN_CONTEXT
```

`120` cases is a portfolio expansion target only and is **not** the Step-7.5 implementation gate.

Do not modify Step 7.2 ground truth.

## Execution plan

```text
DEVELOPMENT: 48 cases × 1 execution = 48
HOLDOUT:     12 cases × 3 executions = 36
TOTAL planned official executions    = 84
```

Freeze deterministic planner identity:

```text
execution_plan_version = step75-execution-plan/v1
```

Use:

```text
execution_id = <case_id>#r<repeat_index>
repeat_index = 1 for DEVELOPMENT
repeat_index = 1..3 for HOLDOUT
```

The offline implementation must support this plan deterministically. It must not perform paid official executions.

## RAG evidence gate

```text
RAG_MIN_RERANK_SCORE = -1.0815147161483765
```

Do not recalibrate, round, reinterpret, or change it.

## Tier priority

```text
CURRENT_LESSON
→ INTERNAL_KB
→ TRUSTED_EXTERNAL
```

Only broaden when the current tier has no usable evidence.

## No-evidence response

Preserve the frozen exact deterministic response:

```text
Hiện tại mình chưa có đủ nguồn đáng tin cậy để trả lời câu hỏi này.
```

## Memory

```text
Conversation Memory != Retrieved Evidence
```

Memory is conversational context only and never becomes current citation evidence.

---

# 4. Frozen Decisions

## D-103 — Per-case pass semantics

For answer-producing executions:

```text
generation_ok =
semantic generation evaluation completed
AND no critical generation failure
```

The five 0/1/2 generation scores remain recorded:

```text
Answer Correctness
Faithfulness / Groundedness
Completeness
Language Quality
Learning Usefulness
```

Do **not** convert these scores into a numeric pass threshold in Step 7.5.

```text
context_ok =
context contract satisfied
AND no material context-adherence violation
AND memory/evidence isolation preserved
```

```text
e2e_case_pass =
retrieval_ok
AND generation_ok
AND citation_ok
AND context_ok
AND fallback_ok
AND refusal_ok
AND technical_ok
AND critical_failures is empty
```

`e2e_case_pass=true` means the execution satisfied the frozen hard validity/policy/technical contracts. It is **not** a release-quality gate.

Numeric quality/regression thresholds belong to Step 7.6.

### Non-answer/refusal applicability rule

The booleans above remain total booleans for every execution.

For a correct deterministic refusal where LLM generation is intentionally not applicable:

```text
generation_applicable = false
generation_ok = true only when generation_called = false
```

For a correct refusal with no evidence-based answer:

```text
citation_applicable = false
citation_ok = true only when current citations are empty
                 AND no MessageCitation rows are persisted
                 AND no citation-validation contract is violated
```

For a correct refusal before prompt construction:

```text
context_applicable = false
context_ok = true only when no inappropriate prompt/evidence/memory generation path ran
```

If the system incorrectly generates an answer for a refusal case, the relevant semantic evaluator may still run for diagnostics, but `refusal_ok=false` and the appropriate critical failure must independently block E2E PASS.

## D-104 — Step-7.5 semantic judge + human calibration

Reuse exact D-100 provider/model/config:

```text
provider = OpenAI API
API = Responses API
model = gpt-5.4-2026-03-05
reasoning_effort = none
temperature = 0
max_output_tokens = 1600
structured_output = required
tools = none
single judge
```

D-100 itself must remain unchanged.

Step 7.5 must use:

```text
same D-100 provider/model/request identity
+
new Step-7.5-specific judge prompt
+
new Step-7.5-specific schema/rubric
```

Offline implementation uses a deterministic fake semantic judge only. No real judge calls are allowed in this task.

Human calibration:

- use exactly the same 30 DEVELOPMENT case IDs frozen in Step 7.4;
- use fresh Step-7.5 annotations;
- do not reuse Step-7.4 semantic labels;
- no HOLDOUT annotation;
- Codex/LLM must never set `HUMAN_APPROVED`.

---

# 5. Mandatory Fail-Closed Repository Preflight

Before writing Step-7.5 implementation code, inspect the **actual current repository** and record the current exact files/classes/functions/signatures for all items below.

Do not guess missing paths or create parallel substitutes.

Preflight must resolve:

```text
1. learner Lesson Chat message application-service entry point
2. conversation ownership/domain/test gates
3. Lesson-context derivation
4. RagOrchestrator
5. CURRENT_LESSON retrieval
6. INTERNAL_KB retrieval
7. ExternalRetrievalProvider boundary
8. RerankingService
9. RAG_MIN_RERANK_SCORE usable-evidence logic
10. tier/fallback selection
11. PromptContextBuilder / PromptPackage
12. ConversationMemoryBuilder / ConversationMemory
13. LLMGenerationService / LLMProvider
14. CitationValidator / CitationValidationResult
15. assistant-message persistence/finalization
16. normalized technical error handling
17. MessageRetrieval and MessageCitation persistence contracts
18. Step-7.3 evaluation fixture/bootstrap utilities
```

Create an implementation note or test-visible preflight record listing the resolved symbols. Do not introduce a new production registry/table merely for preflight.

If a required production seam is absent or materially incompatible with this frozen task in a way that requires architecture/product/evaluation-methodology choice:

```text
STOP
→ BLOCKED — DECISION NEEDED
```

Minor repository naming differences are not blockers; use the actual current names.

## Production seams already observed in accepted review artifacts

These signatures are known and should be reused if unchanged in the actual repository:

### Retrieval call shape observed in Step 7.3 integration code

```python
SemanticRetrievalService(
    session,
    provider=<EmbeddingProvider>,
    settings=settings,
).retrieve(
    query_text,
    retrieval_filter=<RetrievalFilter | None>,
)
```

Production filter/scope primitives observed:

```text
RetrievalScope.CURRENT_LESSON
RetrievalScope.INTERNAL_KB
build_scope_filter(scope, trusted_lesson_id=...)
```

### Reranking call shape observed

```python
RerankingService(
    provider=<RerankerProvider>,
    settings=settings,
).rerank(query_text, candidates)
```

### Prompt construction

Current accepted signature:

```python
PromptContextBuilder(token_counter=...)

PromptContextBuilder.build(
    *,
    user_query: str,
    candidates: Sequence[RerankedCandidate],
    prompt_budget: PromptBudget,
    learning_context: LearningContext | None = None,
) -> ContextBuildResult
```

Current code also exposes the common internal/external evidence path:

```python
PromptContextBuilder.build_from_evidence(
    *,
    user_query: str,
    evidence: Sequence[ContextEvidence],
    prompt_budget: PromptBudget,
    learning_context: LearningContext | None = None,
) -> ContextBuildResult
```

Do not replace this with a Step-7.5-specific prompt builder.

### PromptPackage

Current accepted shape:

```text
PromptPackage
├── system_instructions
├── learning_context
├── context_blocks
├── user_query
├── selected_chunk_ids
├── omitted_chunk_ids
├── source_map
├── budget_usage
└── conversation_memory?
```

### Memory

Current accepted builder signature:

```python
ConversationMemoryBuilder(
    session,
    *,
    token_counter: TokenCounter,
    repository=conversation_repository,
)

await builder.build(
    *,
    conversation_id: UUID,
    current_user_sequence_number: int,
    memory_token_budget: int,
    max_turns: int,
) -> ConversationMemory
```

Current composition helpers:

```python
derive_memory_token_budget(package: PromptPackage) -> int
with_conversation_memory(package: PromptPackage, memory: ConversationMemory) -> PromptPackage
```

### Generation

Current accepted provider contract:

```python
class LLMProvider(Protocol):
    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult: ...
```

Current accepted service:

```python
LLMGenerationService(provider, serializer=...)

await service.generate(
    package: PromptPackage,
    config: GenerationConfig,
) -> LLMGenerationResult
```

The accepted production generation config remains:

```text
model = gpt-5.4-mini-2026-03-17
temperature = 0.2
max_output_tokens = 800
reasoning_effort = none
model_input_limit = 400000
request_timeout_seconds = 60
max_transient_retries = 1
```

Offline Step 7.5 must inject a deterministic fake `LLMProvider` through this same production seam. Do not call the vendor SDK.

### D-100 judge infrastructure

Step 7.4 already has a judge protocol/provider implementation and exact request-identity validation for:

```text
gpt-5.4-2026-03-05
Responses API
reasoning_effort=none
temperature=0
max_output_tokens=1600
structured output
tools=[]
```

Reuse provider/config/request mechanics where practical without changing Step-7.4 prompt/schema behavior.

---

# 6. In Scope

Implement only Step 7.5 offline readiness:

1. normalized Step-7.5 specification for 60 cases / 84 executions;
2. deterministic 60-case/84-execution planner;
3. evaluation-only conversation/persistence setup helpers for the dedicated evaluation database;
4. actual E2E execution trace capture around existing production seams;
5. deterministic trusted-external fixture provider behind the existing `ExternalRetrievalProvider` abstraction;
6. deterministic fake LLM provider behind existing `LLMProvider`;
7. Step-7.5 semantic judge contracts + offline fake judge + real D-100 adapter implementation/config validation without calling it;
8. expected-vs-actual comparison logic;
9. per-execution hard validity/policy booleans under D-103;
10. semantic citation correctness/coverage evaluation;
11. context/multi-turn isolation evaluation;
12. critical-failure classification;
13. fresh source-controlled Step-7.5 human-calibration template for the frozen 30 DEVELOPMENT cases;
14. manifest/cases/summary artifact schemas and writers;
15. offline/test artifact protections;
16. deterministic unit tests;
17. local database-backed integration tests using real local retrieval/reranking/persistence where the environment supports the existing test database;
18. Step Note and implementation-facing Step specification.

---

# 7. Out of Scope

Do **not**:

- make paid OpenAI/API calls;
- make live Tavily/vendor/search calls;
- inject gold/fixed evidence as internal retrieval output;
- make fake/mock outputs official benchmark artifacts;
- create `HUMAN_APPROVED` annotations;
- alter Step 7.2 dataset ground truth;
- expand dataset to 120;
- recalibrate/change/round `RAG_MIN_RERANK_SCORE`;
- add query rewriting;
- tune embeddings/reranker/RAG models;
- add numeric generation-quality pass thresholds;
- add citation score thresholds;
- add release thresholds;
- add regression thresholds;
- implement Step 7.6;
- implement Step 7.7;
- add CI quality gates;
- add production monitoring;
- select/change a production external-search vendor;
- change production architecture;
- add queue/microservice/framework without demonstrated need;
- create a `rag_runs` production DB table;
- claim Step 7.5 DONE;
- claim PM acceptance;
- claim an official E2E baseline.

---

# 8. Offline / Runtime Boundary

Use this boundary exactly unless actual repository constraints require a PM decision.

| Component | Offline Step 7.5 mode |
|---|---|
| PostgreSQL evaluation DB | REAL LOCAL EXECUTION |
| Step-7.3 fixture bootstrap / ACTIVE internal corpus | REAL LOCAL EXECUTION |
| BAAI/bge-m3 query embedding | REAL LOCAL EXECUTION |
| SemanticRetrievalService | REAL LOCAL EXECUTION |
| RetrievalScope / filters | REAL LOCAL EXECUTION |
| BAAI/bge-reranker-v2-m3 | REAL LOCAL EXECUTION |
| RAG evidence gate | REAL, exact frozen threshold |
| RagOrchestrator | REAL LOCAL EXECUTION |
| PromptContextBuilder | REAL LOCAL EXECUTION |
| ConversationMemoryBuilder | REAL LOCAL EXECUTION |
| CitationValidator | REAL LOCAL EXECUTION |
| Message persistence/finalization | REAL LOCAL EXECUTION |
| Trusted external network provider | DETERMINISTIC FIXTURE PROVIDER |
| Production LLM network provider | DETERMINISTIC FAKE `LLMProvider` |
| Step-7.5 semantic judge network call | DETERMINISTIC FAKE JUDGE |

Do not fake internal retrieval merely because the LLM is fake.

Do not let the fixture external provider inspect:

```text
case.expected_tier
case.expected_behavior
case.expected_scope
```

to decide what actual production path should do.

The external fixture provider may deterministically map the **actual normalized query** to known reviewed fixture results/empty results. It must return production-shaped `ExternalCandidate` objects through the existing provider interface and allow the normal downstream trust/rerank/context/citation path to run.

The fake LLM must operate through `LLMProvider`. A scripted test fake may be keyed by actual request/query/request-hash, but must not branch on expected labels.

---

# 9. Dedicated Evaluation Database Safety

Local integration tests/evaluation setup must use the existing test/evaluation database protections.

Require:

```text
APP_ENV=test
TEST_DATABASE_URL configured
```

Fail closed if the database identity is unsafe or resolves to the normal/production database.

Reuse Step-7.3 fixture bootstrap instead of building a second corpus bootstrap.

Expected accepted corpus remains the reviewed fixture pack:

```text
3 Lesson sources
1 Internal-KB source
26 source blocks
ACTIVE vector-ready runtime representation
```

Do not modify normal production data.

Each E2E execution must use isolated synthetic Conversation/Message state so repeats do not contaminate one another.

For MULTI_TURN cases, materialize the dataset conversation context as completed historical turns using the existing Conversation/Message persistence contracts so the **real `ConversationMemoryBuilder`** reconstructs memory.

Do not bypass the memory builder with a Step-7.5-only in-memory ConversationMemory object in integration tests intended to verify production behavior.

---

# 10. Data Flow

## Offline implementation/integration flow

```text
EvaluationCase v0.8.0
↓
ExecutionPlan entry
  case_id + split + repeat_index
↓
run-scoped synthetic user/conversation/message setup
↓
existing learner message application-service entry point
↓
production business/domain/test gates
↓
RagOrchestrator
├── CURRENT_LESSON real retrieval + real rerank + threshold
├── INTERNAL_KB real retrieval + real rerank + threshold if needed
└── TRUSTED_EXTERNAL fixture provider + real downstream rerank if needed
↓
real PromptContextBuilder
↓
real ConversationMemoryBuilder / composition
↓
fake LLM through real LLMGenerationService / LLMProvider seam
↓
real CitationValidator
↓
real MessageRetrieval / MessageCitation / assistant finalization
↓
final persisted assistant state
+
runtime trace
↓
Step-7.5 deterministic expected-vs-actual evaluator
↓
fake Step-7.5 semantic judge for generated-answer semantic/citation/context labels
↓
per-execution E2E result
↓
test-only artifact writer / summary
```

Official runtime later replaces only the deferred runtime dependencies. It is not part of this task.

---

# 11. E2E Execution Planner

Implement a deterministic planner.

Input:

```text
60 APPROVED EvaluationCases from v0.8.0
```

Output:

```text
84 E2EExecutionPlanItem rows
```

Logical shape:

```text
E2EExecutionPlanItem
├── execution_id
├── case_id
├── split
├── bucket
└── repeat_index
```

Rules:

```text
DEVELOPMENT → exactly repeat_index=1
HOLDOUT     → exactly repeat_index=1,2,3
```

Assertions:

```text
unique execution_id count = 84
case count = 60
development execution count = 48
holdout execution count = 36
no unapproved case
all six buckets represented
```

Do not duplicate a DEVELOPMENT case to simulate repeats.

---

# 12. Frozen E2EExecutionTrace Schema

Freeze version:

```text
e2e_trace_schema_version = 1.0.0
```

The trace must reflect **actual runtime events only**. It must not read expected labels while recording execution.

Logical schema:

```text
E2EExecutionTrace
├── schema_version = "1.0.0"
├── execution_id
├── case_id
├── repeat_index
├── conversation
│   ├── conversation_id
│   ├── current_user_message_id
│   ├── assistant_message_id?
│   ├── lesson_id?
│   └── current_user_sequence_number
├── domain_guard
│   ├── status
│   ├── out_of_domain_detected?
│   └── error_code?
├── tiers_attempted[]
│   └── TierAttemptTrace
├── selected_tier?
├── selected_evidence[]
├── prompt
│   ├── built
│   ├── prompt_package_sha256?
│   ├── source_map_snapshot?
│   ├── source_map_sha256?
│   ├── selected_context_count
│   ├── omitted_context_count
│   └── context_build_duration_ms?
├── memory
│   ├── applied
│   ├── selected_turn_count
│   ├── omitted_turn_count
│   ├── token_count
│   └── historical_citation_markers_removed?
├── generation
│   ├── called
│   ├── provider?
│   ├── model?
│   ├── answer?
│   ├── answer_sha256?
│   ├── latency_ms?
│   ├── token_usage?
│   └── error_code?
├── citation_validation
│   ├── attempted
│   ├── valid?
│   ├── error_code?
│   ├── cited_labels[]
│   └── validated_citations[]
├── persistence
│   ├── final_message_status
│   ├── message_retrieval_count
│   ├── message_citation_count
│   └── error_code?
├── actual_behavior
├── technical_error
│   ├── stage?
│   └── code?
└── timings
    ├── total_latency_ms
    ├── retrieval_latency_ms
    ├── rerank_latency_ms
    ├── llm_latency_ms
    └── citation_finalization_latency_ms
```

## TierAttemptTrace

```text
TierAttemptTrace
├── tier = CURRENT_LESSON | INTERNAL_KB | TRUSTED_EXTERNAL
├── attempt_index
├── scope_identity
├── retrieval_status = SUCCESS | TECHNICAL_FAILURE
├── semantic_candidates[]
├── candidate_count
├── rerank_status = SUCCESS | TECHNICAL_FAILURE | NOT_APPLICABLE
├── reranked_evidence[]
├── max_rerank_score?
├── evidence_gate_threshold?
├── evidence_gate_passed
├── scope_violation
├── retrieval_latency_ms?
├── rerank_latency_ms?
└── error_code?
```

For each internal candidate/evidence trace retain only evaluation-safe fields needed for audit:

```text
chunk_id/runtime identity
stable locator/provenance identity when available
source_type
lesson/source provenance
semantic rank / retrieval score
distance if already available
rerank rank / rerank score
```

For external evidence retain:

```text
source_id if available
title
url
domain
content/reviewed-claim hash
rerank rank / rerank score
```

Do not store secrets/raw vectors.

## actual_behavior

Derive from actual trace only:

```text
CURRENT_LESSON selected + generated answer
→ ANSWER

INTERNAL_KB selected + generated answer
→ FALLBACK_INTERNAL

TRUSTED_EXTERNAL selected + generated answer
→ FALLBACK_EXTERNAL

semantic no-evidence deterministic refusal
→ REFUSE_NO_EVIDENCE

explicit production out-of-domain refusal
→ REFUSE_OUT_OF_DOMAIN

infrastructure/technical failure
→ TECHNICAL_FAILURE
```

Never derive `actual_behavior` from `expected_behavior`.

---

# 13. Expected vs Actual Comparison

Expected labels are read **only after execution trace is complete**.

Canonical expected tiers:

```text
CURRENT_LESSON
INTERNAL_KB
TRUSTED_EXTERNAL
NONE
```

Canonical expected behaviors:

```text
ANSWER
FALLBACK_INTERNAL
FALLBACK_EXTERNAL
REFUSE_NO_EVIDENCE
REFUSE_OUT_OF_DOMAIN
```

Implement deterministic comparison that detects at minimum:

```text
skipped usable higher-priority tier
wrong selected tier
unnecessary lower-tier attempt after usable evidence
answered instead of required refusal
refused despite usable allowed evidence
technical failure treated as semantic no-evidence
scope violation
```

Expected labels must never control the orchestrator, fake LLM, external provider, retrieval filters, or tier selection.

---

# 14. Frozen Per-Execution Result Schema

Freeze:

```text
e2e_result_schema_version = 1.0.0
e2e_policy_version = lesson-chat-e2e-policy/v1
```

Logical schema:

```text
E2ECaseResult
├── schema_version = "1.0.0"
├── execution_id
├── case_id
├── split
├── bucket
├── repeat_index
├── expected
│   ├── tier
│   ├── behavior
│   └── scope
├── actual
│   ├── behavior
│   ├── selected_tier?
│   └── final_message_status
├── trace
├── retrieval_ok
├── generation_applicable
├── generation_ok
├── citation_applicable
├── citation_correctness_ok
├── citation_coverage_ok
├── citation_ok
├── context_applicable
├── context_ok
├── fallback_ok
├── refusal_ok
├── technical_ok
├── generation_dimension_scores?
├── semantic_claims?
├── critical_failures[]
├── e2e_case_pass
└── evaluator_errors[]
```

Do not collapse these into one score.

---

# 15. Exact Boolean Semantics

## retrieval_ok

### Answer-producing expected tiers

`retrieval_ok=true` only when all are true:

1. all required retrieval/rerank stages needed to reach the selected tier completed without technical failure;
2. no retrieval scope violation occurred;
3. selected evidence passed the frozen runtime evidence gate;
4. selected evidence respects `expected_scope` constraints;
5. after execution, selected evidence contains at least one Step-7.2 relevant evidence identity (`required_evidence` or `acceptable_evidence`, respecting exact internal locator / external URL identity).

This comparison happens after actual execution and must not influence retrieval.

Do not require an invented numeric evaluation threshold beyond the already-frozen runtime evidence gate.

### REFUSE_NO_EVIDENCE

`retrieval_ok=true` only when:

```text
all applicable evidence tiers complete semantically
AND no tier produces usable accepted evidence
AND no technical failure occurred
AND no scope violation occurred
```

### REFUSE_OUT_OF_DOMAIN

`retrieval_ok=true` when:

```text
selected_tier = NONE
AND no prohibited evidence is selected
AND no retrieval scope violation occurred
```

Do not force a new architecture rule about exactly when the existing production domain guard must run. `refusal_ok` evaluates the explicit out-of-domain behavior.

## fallback_ok

`fallback_ok=true` only when actual transitions satisfy strict tier priority and the expected tier/behavior transition.

Examples:

```text
expected CURRENT_LESSON
→ CURRENT_LESSON usable/selected
→ INTERNAL_KB and external NOT attempted
```

```text
expected INTERNAL_KB
→ CURRENT_LESSON attempted and insufficient
→ INTERNAL_KB usable/selected
→ external NOT attempted
```

```text
expected TRUSTED_EXTERNAL
→ CURRENT_LESSON insufficient
→ INTERNAL_KB insufficient
→ TRUSTED_EXTERNAL selected
```

For `REFUSE_NO_EVIDENCE`, every applicable tier must end semantically insufficient, not technically failed.

For explicit `REFUSE_OUT_OF_DOMAIN`, `selected_tier=NONE`; an existing production domain-guard short-circuit is valid.

## refusal_ok

For answer-producing expected behavior:

```text
refusal_ok = true only when the system did not return a semantic refusal
```

For `REFUSE_NO_EVIDENCE`:

```text
actual_behavior = REFUSE_NO_EVIDENCE
generation_called = false
assistant final status = COMPLETED
assistant content = exact frozen no-evidence response
citations = []
```

For `REFUSE_OUT_OF_DOMAIN`:

```text
actual_behavior = REFUSE_OUT_OF_DOMAIN
generation_called = false
selected_tier = NONE
assistant result follows the existing production out-of-domain contract discovered in preflight
```

Do not invent a new OOD response text if production does not already freeze one.

## generation_ok

If generation is called for an answer-producing execution:

```text
generation_applicable = true

generation_ok =
Step-7.5 semantic generation evaluation completed successfully
AND no critical generation failure
```

No 0/1/2 score threshold is allowed.

For a correct deterministic refusal:

```text
generation_applicable = false
generation_ok = (generation_called == false)
```

## context_ok

For answer-producing executions:

```text
context_ok =
production prompt/context contract satisfied
AND source_map corresponds only to currently selected evidence
AND conversation memory remains separate from context_blocks/source_map
AND historical assistant citation markers do not become current citations
AND current evidence is authoritative over conflicting history
AND Step-7.5 semantic judge reports no material context-adherence violation
```

For a correct refusal where no prompt should be built:

```text
context_applicable = false
context_ok = true only when no inappropriate prompt/generation context path ran
```

## citation_ok

See the exact semantic rules below.

For correct deterministic refusals:

```text
citation_applicable = false
citation_ok = true only when citations are empty and no MessageCitation rows exist
```

## technical_ok

`technical_ok=true` only when no infrastructure/config/provider/DB/unexpected technical failure occurred.

A deterministic model-output validation failure such as malformed/unknown citation is a semantic/contract validation failure and may leave `technical_ok=true` while `citation_ok=false` and final assistant status becomes FAILED according to production behavior.

Unexpected validator exception, DB failure, provider failure, context-budget failure, retrieval exception, or reranker exception is technical and sets `technical_ok=false`.

## e2e_case_pass

Implement D-103 exactly:

```text
e2e_case_pass =
retrieval_ok
AND generation_ok
AND citation_ok
AND context_ok
AND fallback_ok
AND refusal_ok
AND technical_ok
AND critical_failures is empty
```

No numeric generation/citation/latency threshold may be inserted.

---

# 16. Citation Semantic Evaluation

Production `CitationValidator` remains authoritative for structural validation:

```text
syntax
label existence
current source_map membership
provenance resolution
```

Step 7.5 supplements it with claim-level semantics.

Freeze:

```text
citation_semantics_version = lesson-chat-citation-semantics/v1
```

## Claim contract

```text
E2EClaimEvaluation
├── claim_id                 # deterministic C1..Cn
├── claim_text
├── requires_grounding: bool
├── cited_labels[]
├── supporting_labels[]
├── verdict = SUPPORTED | UNSUPPORTED | CONTRADICTED
└── concise_rationale
```

Rules:

- `cited_labels` may contain only labels structurally parsed from the current generated answer;
- `supporting_labels` may contain only labels in the current `PromptPackage.source_map`;
- conversation memory labels/text are never supporting labels;
- historical `[S<number>]` markers cannot resolve against the current source map;
- concise rationale is evaluation rationale, not hidden chain-of-thought.

## citation_correctness_ok

Exact rule:

```text
citation_correctness_ok = true
iff
for every material claim that cites one or more current labels:
    claim verdict = SUPPORTED
    AND every cited label is included in supporting_labels
```

A current label that resolves structurally but does not support the attached claim makes citation correctness fail.

No numeric correctness threshold.

## citation_coverage_ok

Exact rule:

```text
citation_coverage_ok = true
iff
for every material claim with requires_grounding=true:
    at least one current cited label exists
    AND at least one cited label is in supporting_labels
```

No percentage threshold.

## citation_ok

```text
citation_ok =
production CitationValidator PASS
AND citation_correctness_ok
AND citation_coverage_ok
```

If production structural validation fails:

```text
citation_ok = false
```

Do not use the semantic judge to override/repair a structural citation failure.

---

# 17. Critical Failure Contract

Freeze version:

```text
critical_failure_policy_version = lesson-chat-e2e-critical/v1
```

Use the canonical enum below and avoid synonym duplicates:

```text
SERIOUS_FACTUAL_ERROR
UNSUPPORTED_CONFIDENT_CLAIM
CONTRADICTED_BY_EVIDENCE
FABRICATED_CITATION_OR_SOURCE
CITATION_PROVENANCE_MISMATCH
REQUIRED_CITATION_MISSING
RETRIEVAL_SCOPE_VIOLATION
TIER_FALLBACK_POLICY_VIOLATION
OUT_OF_DOMAIN_ANSWER
CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE
TECHNICAL_FAILURE_TREATED_AS_NO_EVIDENCE
```

Critical failures are independently blocking.

Do not allow high dimension scores to compensate.

## Deterministic critical mappings

At minimum:

```text
unknown/malformed invented current citation label or invented trusted provenance
→ FABRICATED_CITATION_OR_SOURCE
```

```text
persisted citation provenance does not match the current runtime source_map entry
→ CITATION_PROVENANCE_MISMATCH
```

```text
material grounded claim has no supporting current citation
→ REQUIRED_CITATION_MISSING
```

```text
candidate/evidence outside allowed runtime scope
→ RETRIEVAL_SCOPE_VIOLATION
```

```text
wrong/skipped tier or lower tier used despite usable higher-priority evidence
→ TIER_FALLBACK_POLICY_VIOLATION
```

```text
expected REFUSE_OUT_OF_DOMAIN but actual answer produced
→ OUT_OF_DOMAIN_ANSWER
```

```text
runtime trace establishes insufficient evidence but a confident generated answer is produced
→ CONFIDENT_ANSWER_WITH_INSUFFICIENT_EVIDENCE
```

```text
retrieval/reranker/provider/DB technical failure is reclassified as semantic no-evidence and fallback/refusal continues
→ TECHNICAL_FAILURE_TREATED_AS_NO_EVIDENCE
```

Generation-semantic criticals reuse the same meanings already used in Step 7.4:

```text
SERIOUS_FACTUAL_ERROR
UNSUPPORTED_CONFIDENT_CLAIM
CONTRADICTED_BY_EVIDENCE
```

Do not create duplicate aliases.

---

# 18. Step-7.5 Semantic Judge Contract

Freeze:

```text
judge_prompt_version = lesson-chat-e2e-judge/v1
e2e_rubric_version = lesson-chat-e2e-rubric/v1
judge_schema_version = 1.0.0
```

Reuse D-100 provider/model/config exactly.

Do not reuse Step-7.4 prompt/schema as-is.

## Judge input

The judge receives only evaluation-relevant material:

```text
case_id
repeat_index
question
expected_information[]
reference_answer?              # optional secondary reference
actual_current_evidence[]      # exact evidence visible to the generator/current source_map
current_source_map
validated_current_citations
sanitized_conversation_memory? # clearly marked context-only, non-authoritative
learning_context?
generated_answer
five generation rubrics
citation/context rubric
critical semantic-failure definitions
```

Do not pass human annotations to the judge.

Do not pass expected tier/behavior as a mechanism for grading semantic answer quality. Expected tier/behavior comparison is deterministic outside the judge.

Judge instructions must explicitly state:

```text
- score the five generation dimensions independently on 0/1/2;
- no numeric pass threshold exists here;
- expected_information[] is primary correctness/completeness ground truth;
- evaluate grounding against actual current evidence only;
- conversation memory is context, not evidence;
- a true outside fact unsupported by current evidence remains UNSUPPORTED;
- only current source_map labels may support current citations;
- historical citation markers cannot support current claims;
- identify material factual/instructional claims;
- classify each claim SUPPORTED / UNSUPPORTED / CONTRADICTED;
- mark which claims require grounding;
- return cited_labels and supporting_labels from the supplied current labels only;
- detect material context-adherence/memory-authority violation;
- do not evaluate retrieval tier selection/fallback policy;
- do not reveal chain-of-thought;
- return concise evaluation rationale only.
```

## Structured judge result

```text
E2EJudgeResult
├── schema_version = "1.0.0"
├── case_id
├── repeat_index
├── generation_dimension_scores
│   ├── answer_correctness {score:0|1|2, rationale}
│   ├── faithfulness_groundedness {score:0|1|2, rationale}
│   ├── completeness {score:0|1|2, rationale}
│   ├── language_quality {score:0|1|2, rationale}
│   └── learning_usefulness {score:0|1|2, rationale}
├── claims[]
│   └── E2EClaimEvaluation
├── context_adherence
│   ├── material_violation: bool
│   ├── memory_used_as_evidence: bool
│   ├── historical_citation_label_leak: bool
│   ├── current_evidence_overridden_by_history: bool
│   └── concise_rationale
├── semantic_critical_failures[]
└── concise_overall_rationale
```

Allowed judge-origin semantic critical failures:

```text
SERIOUS_FACTUAL_ERROR
UNSUPPORTED_CONFIDENT_CLAIM
CONTRADICTED_BY_EVIDENCE
FABRICATED_CITATION_OR_SOURCE
REQUIRED_CITATION_MISSING
```

Other critical failures are deterministic runtime/evaluator classifications.

## Judge validation

Validate at minimum:

```text
case_id/repeat_index match request
all five dimensions exist exactly once
score ∈ {0,1,2}
claim IDs are C1..Cn without gaps/duplicates
claim verdict enum valid
cited_labels ⊆ structural current citations
supporting_labels ⊆ current source_map
no historical-only label accepted as current support
critical-failure enum valid
```

Cross-field consistency:

```text
CONTRADICTED claim
→ faithfulness_groundedness = 0
→ CONTRADICTED_BY_EVIDENCE present
```

```text
faithfulness_groundedness = 2
→ no UNSUPPORTED / CONTRADICTED material claim
```

```text
SERIOUS_FACTUAL_ERROR
→ answer_correctness = 0
```

```text
material requires_grounding claim
AND no supporting cited current label
→ REQUIRED_CITATION_MISSING
```

```text
memory_used_as_evidence OR historical_citation_label_leak OR current_evidence_overridden_by_history
→ context_adherence.material_violation = true
```

Invalid/inconsistent judge result is:

```text
JUDGE_INVALID_RESPONSE
```

It is a judge technical failure, never semantic score `0`.

## Offline mode

Implement the real D-100 adapter/config validation if required for future runtime readiness, but **do not call it**.

Default deterministic tests inject a fake Step-7.5 judge implementing the Step-7.5 judge protocol.

---

# 19. Fresh Step-7.5 Human Calibration Contract

Create source-controlled package:

```text
evaluation/annotations/lesson_chat_e2e/v0.1.0/
├── manifest.json
└── calibration.jsonl
```

Freeze:

```text
annotation_version = lesson-chat-e2e-human/v0.1.0
rubric_version = lesson-chat-e2e-rubric/v1
```

Use exactly these 30 DEVELOPMENT IDs:

```text
current-hsk1-l01-001
current-hsk1-l01-005
current-hsk1-l01-006
current-hsk1-l02-001
current-hsk1-l02-003
current-hsk1-l02-004
current-hsk1-l02-005
current-hsk1-l03-001
current-hsk1-l03-004
current-hsk1-l03-005
ikb-fallback-de-ge-001
ikb-fallback-de-ge-002
ikb-fallback-numbers-er-liang-001
ikb-fallback-numbers-er-liang-002
ikb-fallback-numbers-er-liang-003
ikb-fallback-pronouns-001
ikb-fallback-pronouns-002
ikb-fallback-pronouns-003
trusted-external-bi-comparison-001
trusted-external-dou-placement-001
trusted-external-shenme-placement-001
trusted-external-zai-location-001
multiturn-age-question-jisui-001
multiturn-family-introduction-zheshi-001
multiturn-family-possession-measure-word-001
multiturn-name-confirmation-ma-001
multiturn-numbers-counting-to-quantity-001
multiturn-reciprocal-question-ne-001
multiturn-self-introduction-jiao-001
multiturn-teacher-greeting-politeness-001
```

Assertions:

```text
30 unique IDs
all APPROVED
all DEVELOPMENT
0 HOLDOUT
all present in v0.8.0
```

Do not auto-replace a missing ID.

## Annotation workflow

```text
DRAFT
→ human review
→ HUMAN_APPROVED

uncertain
→ NEEDS_ADJUDICATION
→ manual resolution
→ HUMAN_APPROVED
```

Codex, test fake, and LLM judge may create only DRAFT templates. They must never set HUMAN_APPROVED.

Offline task completion requires:

```text
HUMAN_APPROVED = 0
```

## Run/output binding

Human labels must bind to the exact Step-7.5 E2E execution reviewed.

For the DEVELOPMENT calibration execution (`repeat_index=1`) persist binding fields equivalent to:

```text
case_id
repeat_index = 1
e2e_run_id
execution_id
generated_answer_sha256
source_map_sha256
validated_citations_sha256
evidence_snapshot_sha256
execution_output_sha256
cases_artifact_sha256
annotation_version
rubric_version
review_status
```

Define `execution_output_sha256` as SHA-256 over a canonical deterministic serialization of at least:

```text
case_id
repeat_index
question
generated_answer
actual selected evidence/source_map snapshot
validated current citations
sanitized memory snapshot/identity used for judge context
```

Before using HUMAN_APPROVED annotations later, recompute hashes from the frozen run artifacts and fail closed on drift.

## Human semantic labels

For HUMAN_APPROVED rows require:

```text
five 0/1/2 generation scores
claim-level E2EClaimEvaluation equivalents
context-adherence fields
semantic critical failures
concise notes optional
```

Derive human citation correctness/coverage from human claim labels using the same deterministic rules as judge outputs.

Apply the same cross-field consistency checks as the judge schema where applicable.

Step 7.5 agreement reporting later may compare:

```text
five dimension exact agreement / MAE / confusion matrices
citation_correctness_ok agreement
citation_coverage_ok agreement
context_ok agreement
critical-failure-set agreement
```

Do not add a hard agreement threshold. Step 7.6 owns later gating policy.

---

# 20. Trusted External Fixture Adapter

Use the accepted evaluation registry:

```text
evaluation/fixtures/lesson_chat_rag/trusted_external/v0.1.0/
```

The fixture provider must implement the existing `ExternalRetrievalProvider` boundary discovered in preflight.

Input:

```text
actual normalized query
limit
```

Output:

```text
production-shaped ExternalCandidate[]
```

The adapter may use a deterministic query-to-fixture-result mapping for evaluation, but it must not read expected tier/behavior/scope while serving the request.

Preserve exact fixture provenance:

```text
source_id
url
domain
title
reviewed claims/content
```

Then let normal downstream external trust/provenance/reranking/prompt/citation behavior run.

No HTTP request.

Do not add a new external-search vendor.

---

# 21. MULTI_TURN_CONTEXT Contract

For MULTI_TURN cases:

1. seed the dataset historical turns as persisted completed messages;
2. use the real `ConversationMemoryBuilder`;
3. preserve chronological roles;
4. do not merge memory into retrieved evidence/context blocks;
5. preserve current-query-only retrieval behavior;
6. sanitize historical assistant citation markers through the production memory path;
7. only current `source_map` resolves current citations;
8. prior assistant facts unsupported by current evidence remain unsupported;
9. current evidence overrides conflicting historical assistant content.

Do not add history-aware query rewriting.

---

# 22. Artifact Contract

Support canonical future run shape:

```text
evaluation/runs/<run_id>/e2e/
├── manifest.json
├── cases.jsonl
└── summary.json
```

Default automated offline tests must write only to temporary test directories.

Do not commit fake run outputs under `evaluation/runs/` as official evidence.

## manifest.json

Minimum logical schema:

```text
run_id
run_status
execution_mode = OFFLINE_TEST | OFFICIAL_RUNTIME
official_baseline_eligible: bool
operational_metrics_official: bool

timestamp_started
timestamp_finalized?
evaluation_step = "7.5"

dataset_name = lesson_chat_rag
dataset_version = v0.8.0
dataset_schema_version
dataset_case_count = 60
development_case_count = 48
holdout_case_count = 12
execution_plan_version = step75-execution-plan/v1
development_execution_count = 48
holdout_execution_count = 36
total_execution_count = 84

code_commit?
fixture_bootstrap_id
internal_fixture_version/hash
trusted_external_fixture_version/hash

embedding_provider/model/revision/profile/dimensions
retrieval_candidate_k
retrieval_scope_policy_version
reranker_provider/model/revision/top_k
rag_min_rerank_score = -1.0815147161483765

prompt/system identity/hash
context_builder identity
memory_policy/max_turns

llm_mode = DETERMINISTIC_FAKE | REAL_PROVIDER
llm_provider
llm_model
llm_generation_config

external_mode = FIXTURE | RUNTIME
external_provider_identity
external_allowed-domain identity if applicable

citation_validator identity/version
judge_mode = DETERMINISTIC_FAKE | REAL_PROVIDER
judge provider/API/model/config
judge_prompt_version = lesson-chat-e2e-judge/v1
judge_schema_version = 1.0.0
e2e_rubric_version = lesson-chat-e2e-rubric/v1
e2e_policy_version = lesson-chat-e2e-policy/v1
critical_failure_policy_version = lesson-chat-e2e-critical/v1

human_annotation_version = lesson-chat-e2e-human/v0.1.0
human_calibration_case_count_expected = 30
human_approved_count
```

Offline/test identity must be unambiguous:

```text
execution_mode = OFFLINE_TEST
official_baseline_eligible = false
operational_metrics_official = false
llm_mode = DETERMINISTIC_FAKE
external_mode = FIXTURE
judge_mode = DETERMINISTIC_FAKE
human_approved_count = 0
```

## cases.jsonl

One row per execution, so a future official complete run contains 84 rows.

Minimum:

```text
execution_id
case_id
repeat_index
split
bucket
conversation input identity
expected_tier
expected_behavior
expected_scope
trace
actual_behavior
actual_selected_tier
retrieval_ok
generation_applicable
generation_ok
citation_applicable
citation_correctness_ok
citation_coverage_ok
citation_ok
context_applicable
context_ok
fallback_ok
refusal_ok
technical_ok
generation_dimension_scores?
semantic_claims?
critical_failures[]
e2e_case_pass
latencies
token_usage
final_message_status
error_stage?
error_code?
```

Do not store:

```text
API keys
credentials
raw vectors
hidden chain-of-thought
raw private production learner data
```

## summary.json

Aggregate at least:

```text
run_id
execution_mode
total planned/executed counts
case/execution counts by split/bucket
overall e2e hard-validity pass rate
pass rate by bucket
retrieval_ok rate
generation_ok rate
citation_correctness/coverage rates
context_ok rate
fallback_ok rate
refusal_ok rate
technical failure rate
critical failure count/rate/by type
five generation dimension means/distributions for judged answer executions
p50/p95 total latency
stage latency summaries
token usage summary when available
holdout repeat summaries
```

For each HOLDOUT case report raw repeat stability evidence without a Step-7.6 gate:

```text
case_id
execution_count = 3
pass_count 0..3
pass_rate
critical_failure_repeat_count
critical_failure_types_by_repeat
generation_dimension_variance where available
```

Do not classify regression or compare to a baseline in Step 7.5.

Offline latency/token summaries must be labeled test-only and must not be described as production baseline evidence.

---

# 23. Operational Metrics Capture

Capture per execution:

```text
total_latency
retrieval_latency
rerank_latency
llm_latency
citation/finalization_latency
token_usage
technical_status
```

Prefer existing production stage timings/log metadata where available.

Do not redesign production architecture solely to obtain nanosecond-perfect instrumentation.

If a required timing is not currently returned, evaluation-local timing may wrap the existing seam without altering behavior.

Offline fake LLM/judge latency and token data are test data only:

```text
operational_metrics_official = false
```

---

# 24. Technical Failure Semantics

Always preserve:

```text
technical failure != semantic no-evidence
```

## Retrieval exception

```text
current tier → TECHNICAL_FAILURE
no semantic fallback to next tier
no LLM call
assistant follows production FAILED lifecycle
technical_ok = false
actual_behavior = TECHNICAL_FAILURE
```

If the system instead continues fallback/refusal:

```text
TECHNICAL_FAILURE_TREATED_AS_NO_EVIDENCE
```

## Reranker exception/invalid output

Same policy:

```text
no semantic substitute
no broader tier
no LLM
technical_ok = false
```

## CONTEXT_BUDGET_EXHAUSTED

Technical/configuration failure:

```text
no broader tier fallback
no LLM
default assistant failure lifecycle
technical_ok = false
```

## LLM provider failure

```text
selected evidence remains traceable
generation_called = true
assistant failure lifecycle
technical_ok = false
no semantic score 0 substitution
```

## CitationValidator model-output validation failure

Examples:

```text
CITATION_FORMAT_INVALID
CITATION_UNKNOWN_SOURCE
CITATION_MISSING
```

These are deterministic answer/citation contract failures, not infrastructure outages:

```text
citation_ok = false
appropriate citation critical failure when applicable
technical_ok may remain true if validator itself executed normally
assistant final state follows production citation policy
```

Do not silently repair citations.

## Citation validator unexpected exception

```text
technical_ok = false
```

## Persistence/finalization failure

```text
technical_ok = false
no semantic fallback/refusal substitution
record stage/code
```

Do not represent a failed persistence as a successful E2E answer even if generated text exists in memory.

---

# 25. Testing

Default test suites must not require:

```text
OpenAI credentials
paid API calls
internet access
live Tavily/vendor access
production learner data
```

## A. Deterministic unit tests

### Planner

- exactly 60 approved cases loaded;
- exactly 48 DEVELOPMENT / 12 HOLDOUT;
- exactly 84 execution items;
- development only repeat 1;
- holdout repeats 1/2/3;
- all six buckets represented;
- no duplicate execution IDs.

### Trace

- actual behavior derives only from trace;
- evaluator cannot pass expected labels into production/fake provider selection;
- tier traces preserve order;
- technical error stage/code retained.

### Expected vs actual

Cover:

- correct CURRENT_LESSON;
- correct INTERNAL_KB fallback;
- correct external fallback;
- wrong fallback tier;
- lower-tier attempted after higher usable;
- answer instead of refusal;
- refusal despite usable evidence;
- technical failure treated as no-evidence.

### D-103 booleans

- no numeric generation threshold;
- answer execution with valid semantic eval/no critical → generation_ok true regardless of non-critical 0/1 dimension values;
- any generation critical → generation_ok false;
- correct deterministic refusal → generation_applicable=false and generation_ok=true only if LLM not called;
- context material violation → context_ok false;
- every critical failure independently blocks e2e_case_pass;
- exact AND formula enforced.

### Citation semantics

- all cited claims supported by all cited labels → correctness true;
- structurally valid but irrelevant cited label → correctness false;
- material grounded claim with no citation → coverage false + REQUIRED_CITATION_MISSING;
- at least one supporting current citation per required claim → coverage true;
- historical labels never satisfy coverage;
- unknown/malformed source → structural failure and fabricated-source critical;
- provenance persistence mismatch → critical;
- deterministic rules contain no numeric threshold.

### Judge schema

- D-100 request identity exact;
- Step-7.5 prompt/schema version differs from Step 7.4;
- five dimensions exactly once;
- claim IDs contiguous C1..Cn;
- cited labels subset structural current citations;
- supporting labels subset source_map;
- cross-field contradictions rejected;
- judge technical failure never becomes score 0;
- fake judge only in default tests.

### Human calibration

- exact 30 frozen IDs;
- all DEVELOPMENT, no HOLDOUT;
- fresh Step-7.5 version;
- all templates DRAFT;
- HUMAN_APPROVED count remains 0 after Codex task;
- run/output/evidence hashes validated;
- stale output/source_map/citation artifact rejected;
- LLM/Codex cannot self-approve;
- approved contract, when synthetically tested in unit tests, requires complete consistent semantic fields.

### Artifact protection

- OFFLINE_TEST cannot set `official_baseline_eligible=true`;
- fake LLM/judge cannot write an artifact marked OFFICIAL_RUNTIME;
- 84-row official contract validated structurally without running official calls;
- summary denominators derive from actual rows;
- no secrets/CoT/raw vectors.

## B. Local integration tests

Use the actual evaluation/test PostgreSQL and real production local AI seams wherever possible.

Required representative scenarios across all six buckets:

### CURRENT_LESSON

```text
real retrieval
→ real rerank
→ threshold pass
→ selected CURRENT_LESSON
→ no INTERNAL_KB/external attempt
→ real prompt/memory
→ fake LLM through LLMProvider
→ real CitationValidator
→ real persistence/finalization
```

### INTERNAL_KB_FALLBACK

```text
CURRENT_LESSON real retrieval/rerank → insufficient
INTERNAL_KB real retrieval/rerank → usable
external not called
```

### TRUSTED_EXTERNAL_FALLBACK

```text
CURRENT_LESSON insufficient
INTERNAL_KB insufficient
fixture ExternalRetrievalProvider returns production-shaped external result
normal downstream rerank/evidence/context/citation path
```

### NO_EVIDENCE_REFUSAL

```text
all applicable tiers semantically insufficient
generation provider not called
exact deterministic no-evidence response
assistant COMPLETED
citations=[]
```

### OUT_OF_DOMAIN_REFUSAL

Exercise the actual production domain/OOD seam discovered in preflight. Do not fake the expected behavior inside the evaluator.

### MULTI_TURN_CONTEXT

- persist history;
- real memory builder loads it;
- current-query-only retrieval;
- historical assistant citation labels sanitized/not current;
- current evidence remains authority.

## C. Technical-failure integration cases

At minimum:

- retrieval exception → no broader fallback;
- reranker failure → no broader fallback;
- context budget failure → no broader fallback;
- fake LLM technical failure → assistant failure;
- structural citation failure → no silent repair;
- persistence/finalization failure observable;
- no technical failure treated as semantic refusal.

Use deterministic failure-injection fakes only at the narrow failing seam. Keep the rest of the path real.

## D. Application-service entry test

At least one integration test must enter through the **same application-service path used by learner message submission**, rather than only calling `RagOrchestrator` directly.

Verify:

```text
business/domain gates
USER message persistence
ASSISTANT PENDING lifecycle
RAG execution outside long DB transaction
ASSISTANT COMPLETED or FAILED finalization
MessageRetrieval persistence when applicable
MessageCitation persistence when applicable
```

## E. DB-unavailable behavior

If `TEST_DATABASE_URL` or required local models are unavailable in the execution environment, database/model-backed integration tests may be explicitly skipped with a clear reason.

Do **not** substitute SQLite/in-memory retrieval or a fake vector DB to make them pass.

Unit/offline contract tests must still run.

---

# 26. Spec Normalization

Update the implementation-facing Step-7.5 specification to current PM truth.

Replace stale assumptions:

```text
120 approved cases
→ 60 APPROVED current gate
```

```text
96 DEVELOPMENT / 24 HOLDOUT
→ 48 DEVELOPMENT / 12 HOLDOUT
```

```text
168 executions
→ 84 planned official executions
```

Preserve:

```text
120 = later portfolio expansion target
```

Add D-103 and D-104 explicitly.

Do not modify Step-7.2 dataset files merely to normalize the spec.

Expected spec path follows current repository conventions, likely equivalent to:

```text
Spec-CURRENT/Phase7/Step-7.5-End-to-End-RAG-Evaluation.md
```

Use the actual repository path discovered in preflight.

---

# 27. Step Note

Create/update:

```text
docs/evaluation/step-7.5-end-to-end-rag-evaluation.md
```

Include:

## Objective

Evaluate actual Lesson Chat RAG behavior across retrieval, fallback/refusal, generation, citations, memory, persistence, and technical failure semantics.

## Why

Layer-isolated metrics cannot prove the composed system follows the product policy.

## Mental Model

```text
real local system path
+
only unavoidable deterministic dependency substitution offline
→ expected vs actual trace
→ hard-validity E2E result
```

## Core Knowledge

Cover:

```text
end-to-end evaluation
execution tracing
expected-vs-actual policy evaluation
semantic vs technical failure
citation correctness vs coverage
memory/evidence isolation
stochastic repeat evaluation
artifact reproducibility
```

## Data Flow

Document the implemented flow.

## Key Design Decisions

Include D-103, D-104, 60/84 plan, real local retrieval/rerank, fake LLM/judge offline, fixture external provider, no gold injection, no numeric Step-7.6 gates.

## Reusable approach

Explain how to evaluate a composed AI pipeline while replacing only unavailable paid/network boundaries.

## Common Mistakes

Include at least:

```text
injecting gold evidence into E2E retrieval
letting expected labels drive actual execution
faking retrieval because LLM is fake
using memory as evidence
allowing historical citations to resolve in current message
turning technical failure into no-evidence fallback
using one overall average to hide critical failures
calling offline latency a production baseline
using a judge instead of CitationValidator for structural validity
adding release thresholds in Step 7.5
```

## Definition of Done

Reflect acceptance criteria below and explicitly state that offline implementation acceptance is not final Step 7.5 DONE.

---

# 28. Concepts Discovered

Document only concepts actually used.

Expected initial table:

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| End-to-end evaluation | BOTH | 7.5 | Measures behavior across the complete RAG request path |
| Execution trace | SYSTEM | 7.5 | Makes actual tier/failure behavior observable and auditable |
| Tier-policy evaluation | AI | 7.5 | Verifies strict evidence-priority/fallback behavior |
| Semantic citation evaluation | AI | 7.5 | Checks claim-to-current-source correctness and coverage |
| Memory/evidence isolation | AI | 7.5 | Prevents conversation history becoming evidence authority |
| Deterministic dependency substitution | SYSTEM | 7.5 | Replaces only paid/network seams in offline tests |
| Stochastic repeat evaluation | AI | 7.5 | Measures holdout consistency across three executions |
| Semantic vs technical failure | SYSTEM | 7.5 | Prevents infrastructure faults becoming semantic no-evidence |
| Reproducible E2E artifact | BOTH | 7.5 | Preserves trace/config identity for later regression evaluation |

Use only:

```text
DE / AI / BOTH / SYSTEM
```

---

# 29. Tools Used

Record only tools actually used.

Likely when truly used:

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| Python | SYSTEM | 7.5 | Evaluation harness/schemas/artifacts |
| pytest | SYSTEM | 7.5 | Deterministic and local integration verification |
| uv | SYSTEM | 7.5 | Existing project environment workflow |
| PostgreSQL + pgvector | BOTH | 7.5 | Real persistence + vector retrieval path |
| BAAI/bge-m3 | AI | 7.5 | Real local query embedding |
| BAAI/bge-reranker-v2-m3 | AI | 7.5 | Real local reranking/evidence gating |
| OpenAI Responses judge adapter | AI | 7.5 | D-104 runtime-ready judge contract; no calls in offline task |

Do not add a new framework/service merely to enlarge this list.

---

# 30. Acceptance Criteria

Offline Step-7.5 implementation is ready for Specialist review only when all applicable items are satisfied:

## Dataset / plan

- [ ] Step 7.2 v0.8.0 ground truth unchanged.
- [ ] 60 APPROVED cases supported.
- [ ] 48 DEVELOPMENT / 12 HOLDOUT.
- [ ] all six buckets represented.
- [ ] planner produces exactly 84 execution items.
- [ ] development 1× / holdout 3×.

## Production-path reuse

- [ ] actual current production seams recorded by fail-closed preflight.
- [ ] no parallel RagOrchestrator/retriever/prompt/memory/citation/persistence implementation.
- [ ] internal retrieval uses real `SemanticRetrievalService` locally.
- [ ] real local BGE embedding is used in DB integration coverage.
- [ ] real local `RerankingService` is used.
- [ ] exact frozen `RAG_MIN_RERANK_SCORE` is used.
- [ ] `PromptContextBuilder` reused.
- [ ] `ConversationMemoryBuilder` reused.
- [ ] `LLMGenerationService`/`LLMProvider` seam reused.
- [ ] `CitationValidator` reused.
- [ ] message persistence/finalization path reused.
- [ ] at least one integration path enters through learner message application-service path.

## Offline substitution

- [ ] fake LLM only behind production `LLMProvider`.
- [ ] fake Step-7.5 semantic judge only behind judge protocol.
- [ ] trusted external fixture only behind production external-provider boundary.
- [ ] no live external network request.
- [ ] no paid OpenAI request.
- [ ] no expected-label leakage into actual execution dependencies.

## Trace / evaluator

- [ ] E2EExecutionTrace records actual events without expected labels.
- [ ] actual_behavior derived from trace only.
- [ ] expected tier/behavior/scope compared only after execution.
- [ ] retrieval/fallback/refusal/context/technical results remain separate.
- [ ] D-103 exact boolean semantics implemented.
- [ ] no numeric generation pass threshold.
- [ ] critical failures independently block e2e_case_pass.

## Citations / context

- [ ] production CitationValidator remains structural authority.
- [ ] semantic citation correctness exact rule implemented.
- [ ] semantic citation coverage exact rule implemented.
- [ ] citation_ok = structural + correctness + coverage.
- [ ] current source_map only resolves current citations.
- [ ] historical citation labels never satisfy current citations.
- [ ] memory remains context-only.
- [ ] unsupported history-only facts remain grounding/context failures.

## Judge

- [ ] D-104 exact D-100 provider/model/config reused.
- [ ] Step-7.5-specific prompt/schema/rubric versions exist.
- [ ] structured schema validation exists.
- [ ] cross-field consistency exists.
- [ ] judge technical failures do not become semantic zeros.
- [ ] default tests use fake judge only.
- [ ] no real judge call made.

## Human calibration

- [ ] fresh Step-7.5 annotation package exists.
- [ ] exact 30 frozen DEVELOPMENT IDs.
- [ ] no HOLDOUT annotations.
- [ ] run/output/evidence hash binding contract implemented.
- [ ] DRAFT / NEEDS_ADJUDICATION / HUMAN_APPROVED workflow exists.
- [ ] Codex/LLM cannot self-approve.
- [ ] repository state after offline implementation has HUMAN_APPROVED=0.

## Artifacts

- [ ] manifest/cases/summary schemas exist.
- [ ] execution mode cannot be confused.
- [ ] offline/test artifacts cannot be official-baseline eligible.
- [ ] fake LLM/judge implies OFFLINE_TEST.
- [ ] official contract expects 84 rows without running them now.
- [ ] no secret/raw vector/CoT/private production learner data is written.
- [ ] operational fake timing/token data marked non-official.

## Failure semantics

- [ ] retrieval technical failure does not trigger semantic fallback.
- [ ] reranker failure does not trigger semantic fallback.
- [ ] context-budget failure does not trigger semantic fallback.
- [ ] LLM provider failure remains technical.
- [ ] CitationValidator model-output validation failure remains citation/contract failure, not hidden repair.
- [ ] unexpected validator/persistence failure remains technical.
- [ ] TECHNICAL_FAILURE_TREATED_AS_NO_EVIDENCE is detected.

## Tests / docs

- [ ] focused deterministic Step-7.5 tests pass.
- [ ] relevant existing retrieval/rerank/prompt/memory/LLM/citation/conversation regressions pass where environment permits.
- [ ] DB-backed tests use real PostgreSQL+pgvector or explicitly skip for missing `TEST_DATABASE_URL`; no SQLite substitute.
- [ ] compile/import checks pass.
- [ ] dependency lock unchanged unless a concrete need is discovered and PM-approved.
- [ ] no schema/migration change unless a genuine blocker is escalated first.
- [ ] Step Note complete.
- [ ] normalized Step-7.5 spec complete.
- [ ] Concepts/Tools updated.

## Scope

- [ ] RAG_MIN_RERANK_SCORE unchanged.
- [ ] production generator configuration unchanged.
- [ ] D-100/D-101/D-102/D-103/D-104 unchanged.
- [ ] Step 7.6 not started.
- [ ] Step 7.7 not started.
- [ ] Step 7.5 not claimed DONE.
- [ ] no official E2E baseline claimed.

---

# 31. Constraints / Non-goals

This task is an **evaluation implementation** task, not a production RAG redesign.

Prefer evaluation-local adapters and observers around existing seams.

Do not change public APIs/database schema merely to make evaluation convenient unless the actual repository proves that the required production trace is impossible otherwise. If such a material change is required, stop and return `BLOCKED — DECISION NEEDED`.

Do not instrument by logging full production private conversation/evidence text by default.

Do not introduce OpenTelemetry/monitoring infrastructure in Step 7.5.

Do not create a new external search abstraction if `ExternalRetrievalProvider` already exists.

Do not introduce LangChain/LlamaIndex.

---

# 32. Deferred Runtime Gates

The following are **not** part of this offline Codex task:

```text
real production generator smoke
real D-100/D-104 judge smoke
official 84-execution Step-7.5 runtime run
fresh 30-case Step-7.5 human review
30/30 HUMAN_APPROVED
official semantic judge run
official latency/token baseline
final Specialist runtime review
PM acceptance
```

A future official run must use real runtime dependencies authorized by PM and must never promote prior fake/offline artifacts.

Step 7.4's deferred runtime baseline is not required for the offline implementation of Step 7.5 under D-102.

---

# 33. Expected Codex Handoff

Return exactly one focused handoff:

```text
Step:
7.5 — End-to-End RAG Evaluation

Status:
READY_FOR_SPECIALIST_REVIEW — OFFLINE IMPLEMENTATION
or
BLOCKED — DECISION NEEDED

Repository preflight:
- learner message application-service entry point:
- domain/gate component:
- RagOrchestrator:
- retrieval services/scopes:
- ExternalRetrievalProvider:
- RerankingService:
- evidence gate implementation:
- PromptContextBuilder / PromptPackage:
- ConversationMemoryBuilder:
- LLMGenerationService / LLMProvider:
- CitationValidator:
- persistence/finalization:
- technical error boundaries:

What was implemented:
- ...

Files created:
- ...

Files modified:
- ...

Dependencies added/removed:
- ...

Dataset:
- version:
- approved:
- development:
- holdout:
- ground truth changed: MUST be NO

Execution planner:
- cases:
- DEV executions:
- HOLDOUT executions:
- total planned:

Offline boundary:
- internal retrieval real:
- reranking real:
- threshold exact:
- external fixture provider:
- fake LLM through production seam:
- fake semantic judge:
- paid calls: MUST be 0
- live external calls: MUST be 0

E2E trace/result:
- schema versions:
- expected-vs-actual logic:
- D-103 formula:

Citation semantics:
- structural validator reused:
- correctness rule:
- coverage rule:
- context/memory isolation:

Critical failures:
- enum/policy version:

Judge:
- provider/API/model config implemented:
- prompt version:
- rubric version:
- schema version:
- real judge called: MUST be NO

Human calibration:
- annotation version:
- exact subset count:
- DRAFT count:
- NEEDS_ADJUDICATION count:
- HUMAN_APPROVED count: MUST be 0
- binding/hash policy:

Artifacts:
- OFFLINE_TEST protections:
- official_baseline_eligible: MUST be false for fake/offline output
- test artifact location:

Verification:
- focused tests:
- local DB integration tests:
- production regression tests:
- compile/import:
- lock/dependency check:

Runtime production config modified:
- MUST be NO

RAG_MIN_RERANK_SCORE changed:
- MUST be NO

Schema/migration changed:
- MUST be NO unless task was stopped for PM decision

Official Step-7.5 run executed:
- MUST be NO

Official baseline created:
- MUST be NO

Step 7.6 started:
- MUST be NO

Step 7.7 started:
- MUST be NO

Step Note:
Concepts added:
Tools added:

Problems / risks:
Decisions needed:
Recommended next action:
```

Do not claim PM acceptance.

---

# 34. Stop Conditions

Stop rather than guess if implementation reveals a new material ambiguity affecting:

```text
architecture
database/schema
dataset ground truth
production public interface
LLM/judge provider/model
evaluation validity
deployment
cost
```

Return:

```text
BLOCKED — DECISION NEEDED
```

with:

```text
Decision
→ Context
→ Options
→ Trade-offs
→ Recommended default
→ What PM must decide
```

Do not use this stop condition for minor file naming or reversible internal implementation details.

---

# 35. Final Prohibitions

This draft, even after PM freeze for offline implementation, explicitly prohibits:

```text
paid API calls
live external vendor/search calls
gold-evidence injection into internal retrieval
fake official benchmark results
HUMAN_APPROVED self-generation
dataset ground-truth changes
RAG_MIN_RERANK_SCORE changes
numeric quality/regression thresholds
Step 7.6 work
Step 7.7 work
claiming Step 7.5 DONE
claiming PM acceptance
```

Workflow remains:

```text
Specialist
→ PM review/freeze
→ Codex offline implementation
→ Specialist offline review
→ later runtime gates when PM authorizes them
```

# PM Freeze Patch — Step 7.5

The following PM clarifications are mandatory and override any conflicting wording in this task.

No new architecture/product decision is introduced.

==================================================
PATCH 1 — retrieval_ok MUST REUSE STEP-7.3 EVIDENCE-SATISFACTION SEMANTICS
==================================================

Replace any rule equivalent to:

```text
selected evidence contains at least one required_evidence
or acceptable_evidence identity
→ retrieval_ok may pass
```

with the following rule.

For answer-producing cases, `retrieval_ok` must reuse the existing
Step-7.3 ground-truth matching / evidence-satisfaction semantics against the
FINAL evidence actually selected by the production-shaped Step-7.5 path.

Do NOT create a second Step-7.5 evidence matcher.

Required behavior:

```text
actual final selected evidence
→ existing Step-7.3 evidence identity / relevance / equivalent-group matcher
→ required evidence requirements satisfied?
```

Preserve Step-7.2 / Step-7.3 semantics:

- `required_evidence` represents evidence requirements needed for a complete answer;
- equivalent evidence groups are satisfied when at least one valid member of that group is present;
- acceptable/equivalent evidence may satisfy a requirement only according to the already-implemented Step-7.3 ground-truth matching semantics;
- scope correctness remains independently mandatory;
- the frozen runtime rerank-score evidence gate remains independently mandatory.

Therefore, for an answer-producing case:

```text
retrieval_ok = true
```

only when all are true:

1. all required retrieval/rerank stages completed without technical failure;
2. no retrieval scope violation occurred;
3. selected evidence passed the frozen runtime evidence gate;
4. selected evidence respects expected_scope;
5. the FINAL selected evidence satisfies the case's required evidence
   requirements using the existing Step-7.3 evidence/equivalent-group matcher.

Do NOT reduce requirement #5 to:

```text
at least one relevant evidence item exists
```

when the case contains multiple required evidence requirements.

Do NOT require a specific physical Chunk when Step-7.3 already recognizes
valid equivalent evidence.

If the actual repository does not expose the Step-7.3 matcher in reusable form:

- first reuse/extract the existing deterministic logic without changing its semantics;
- do not independently redefine relevance;
- if reuse would require a material methodology change, STOP:
  `BLOCKED — DECISION NEEDED`.

Add focused tests:

- all required evidence requirements satisfied → retrieval_ok may pass;
- only one of multiple required requirements satisfied → retrieval_ok=false;
- valid equivalent-group member satisfies its requirement;
- irrelevant evidence above threshold does not satisfy ground truth;
- scope violation still fails independently;
- expected labels are read only after actual execution and never influence retrieval.

==================================================
PATCH 2 — OFFLINE HUMAN ANNOTATION TEMPLATES MUST NOT FABRICATE RUN BINDINGS
============================================================================

The source-controlled Step-7.5 annotation package created during the current
OFFLINE IMPLEMENTATION task is a HUMAN-REVIEW TEMPLATE only.

Because no official Step-7.5 E2E run is authorized in this task, Codex must NOT
fabricate:

```text
e2e_run_id
execution_id binding to a fake official run
generated_answer_sha256
source_map_sha256
validated_citations_sha256
evidence_snapshot_sha256
execution_output_sha256
cases_artifact_sha256
```

as if they came from an official runtime execution.

For source-controlled DRAFT rows created now:

```text
review_status = DRAFT
```

The future-runtime binding fields may be null / absent according to the chosen
schema representation.

This is valid ONLY for an unreviewed DRAFT template.

Semantic human-label fields may also remain incomplete/empty for DRAFT rows.

The validator must distinguish:

```text
DRAFT template before official output exists
→ incomplete/unbound fields allowed

NEEDS_ADJUDICATION
or
HUMAN_APPROVED
→ exact runtime/output binding required
```

Before a row may become HUMAN_APPROVED later, require all frozen bindings:

```text
case_id
repeat_index = 1
e2e_run_id
execution_id
generated_answer_sha256
source_map_sha256
validated_citations_sha256
evidence_snapshot_sha256
execution_output_sha256
cases_artifact_sha256
annotation_version
rubric_version
```

and recompute/validate all applicable hashes against the exact frozen official
Step-7.5 run artifacts.

An official runtime workflow later must populate/bind the DRAFT packet from the
actual E2E outputs before human approval.

No fake/offline execution may become the source of official HUMAN_APPROVED
annotations.

Add focused tests:

- unbound DRAFT template is valid;
- DRAFT does not require fabricated runtime hashes;
- HUMAN_APPROVED with any required binding missing is rejected;
- HUMAN_APPROVED with stale/mismatched hashes is rejected;
- Codex/fake judge cannot transition a row to HUMAN_APPROVED;
- current offline repository state remains exactly 30 DRAFT / 0 HUMAN_APPROVED.

==================================================
PM FREEZE STATUS
================

After applying both patches, this task is:

PM FROZEN — CODEX-READY
OFFLINE IMPLEMENTATION / DETERMINISTIC TEST MODE ONLY

All other frozen requirements remain unchanged.

Codex may execute only after these two patches are present in the task.

Expected Codex terminal status remains:

READY_FOR_SPECIALIST_REVIEW — OFFLINE IMPLEMENTATION

or, for a genuine material blocker:

BLOCKED — DECISION NEEDED

Do not claim Step 7.5 DONE.
Do not claim PM final acceptance.
