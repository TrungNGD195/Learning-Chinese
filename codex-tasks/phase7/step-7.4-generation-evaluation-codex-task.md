# Codex Task — Step 7.4 Generation Evaluation

## 0. Status / ownership

Implement **Step 7.4 only — Generation Evaluation**.

Canonical prerequisite:

```text
Phase 6 = COMPLETE
Step 7.1 = DONE
Step 7.2 = DONE
Step 7.3 = DONE

dataset_version = v0.8.0
APPROVED = 60
DEVELOPMENT = 48
HOLDOUT = 12
```

Current execution boundary:

```text
Step 7.4 = CURRENT
Step 7.5 = DO NOT START
Step 7.7 = DO NOT START
Step 7.6 = DO NOT START
```

PM decision `D-100` is frozen:

```text
judge provider = OpenAI API
judge model = gpt-5.4-2026-03-05
API = Responses API
reasoning_effort = none
temperature = 0
max_output_tokens = 1600
structured output = required
tools = none
single judge only
```

Production generator under test remains:

```text
gpt-5.4-mini-2026-03-17
```

Do not reopen these decisions.

---

# 1. Problem

Step 7.3 measured retrieval quality. Step 7.4 must isolate the next layer:

```text
fixed approved evidence
→ production-equivalent prompt/context construction
→ production Lesson Chat generation
→ generation-only evaluation
```

The problem is to answer:

```text
If retrieval had already supplied the correct approved evidence,
how well does the Lesson Chat generator answer?
```

This Step must separate:

```text
retrieval failure
from
generation failure
```

Therefore actual retrieval/reranking output must not be the primary evidence source in Step 7.4.

---

# 2. Objective

Build a reproducible generation-isolated benchmark that:

1. selects exactly the frozen 45 eligible EvaluationCases;
2. materializes fixed approved evidence without running retrieval;
3. materializes fixed conversation memory for MULTI_TURN_CONTEXT;
4. calls the existing production PromptContextBuilder / PromptPackage seam;
5. calls the existing production Lesson Chat LLM generation seam with the production generator model/config;
6. scores generated answers on five independent 0/1/2 dimensions;
7. performs claim-level faithfulness evaluation against fixed evidence only;
8. flags critical generation failures separately;
9. supports the exact frozen 30-case DEVELOPMENT human calibration subset;
10. uses the D-100 single LLM judge through OpenAI Responses API structured output;
11. reports human/judge agreement as a baseline only;
12. writes reproducible run artifacts;
13. introduces no release/regression/pass threshold.

This Step is generation evaluation only.

---

# 3. Repository preflight — reuse existing production seams

Before implementing new evaluation code, inspect the current repository and reuse the accepted equivalents of:

```text
PromptContextBuilder
PromptBudget
TokenCounter
ContextBlock
PromptPackage
source_map

ConversationMemory
MemoryTurn
production memory packing/budget rules

LLMRequestSerializer
GenerationConfig
LLMGenerationService
LLMProvider
LLMGenerationResult
production Lesson Chat generator configuration
```

The accepted architectural flow is:

```text
PromptPackage
→ LLMRequestSerializer
→ LLMGenerationRequest
→ existing production LLM provider
→ LLMGenerationResult
```

Do not write a second production-like answer generator.

The generator evaluation harness may add evaluation-specific adapters for:

```text
fixed evidence
fixed memory
judge
artifacts
```

but those adapters must feed the existing production prompt/generation contracts.

Hard rule:

```text
business/RAG/evaluation code
must not call the production generator vendor SDK directly
when an existing LLMGenerationService/provider boundary already exists
```

For the judge only, D-100 explicitly requires OpenAI Responses API. Keep that judge adapter isolated under evaluation code unless the repository already has an equivalent reusable OpenAI Responses client boundary.

## Generator preflight assertions

The real Step 7.4 run must fail closed if the production generator does not resolve to:

```text
model = gpt-5.4-mini-2026-03-17
```

Record the actual production GenerationConfig.

Expected accepted baseline from Phase 6 unless the current PM-frozen runtime config already records a later accepted equivalent:

```text
temperature = 0.2
max_output_tokens = 800
non-streaming
timeout = 60 seconds
at most one transient retry
no retry for permanent/auth/config/context errors
no automatic model fallback
tools/web search = none
```

Do not silently tune the production generator for evaluation.

If current repository implementation materially contradicts the accepted production seam/config in a way requiring a product/architecture decision:

```text
STOP
→ BLOCKED — DECISION NEEDED
```

Do not hide drift by building a parallel generator.

---

# 4. Frozen eligible-case policy

Official dataset:

```text
dataset_version = v0.8.0
APPROVED only
```

Generation-isolated scoring uses only cases where the expected behavior is to answer from usable fixed evidence.

## Included buckets

```text
CURRENT_LESSON_ANSWERABLE
INTERNAL_KB_FALLBACK
TRUSTED_EXTERNAL_FALLBACK
MULTI_TURN_CONTEXT
```

## Excluded buckets

```text
NO_EVIDENCE_REFUSAL
OUT_OF_DOMAIN_REFUSAL
```

Reason:

```text
Step 7.4
→ answer generation with provided usable evidence

Step 7.5
→ refusal policy
→ fallback/tier correctness
→ citation semantic correctness
→ actual end-to-end behavior
```

Do not score refusal-policy behavior in Step 7.4.

## Exact eligible counts

```text
DEVELOPMENT

CURRENT_LESSON_ANSWERABLE = 16
INTERNAL_KB_FALLBACK      = 8
TRUSTED_EXTERNAL_FALLBACK = 4
MULTI_TURN_CONTEXT        = 8
--------------------------------
TOTAL                     = 36
```

```text
HOLDOUT

CURRENT_LESSON_ANSWERABLE = 4
INTERNAL_KB_FALLBACK      = 2
TRUSTED_EXTERNAL_FALLBACK = 1
MULTI_TURN_CONTEXT        = 2
--------------------------------
TOTAL                     = 9
```

```text
TOTAL eligible = 45
```

The runner must assert these counts for `v0.8.0`.

Do not modify Step 7.2 ground truth to fit the evaluator.

---

# 5. Generation benchmark unit

One eligible `EvaluationCase` produces exactly one generation-under-test output for a given generation run identity.

Logical flow:

```text
EvaluationCase
↓
eligible-case validation
↓
fixed evidence materialization
↓
fixed memory materialization if MULTI_TURN_CONTEXT
↓
production-shaped prompt input
↓
PromptContextBuilder
↓
PromptPackage
↓
existing production generation seam
↓
GeneratedAnswer
↓
generation judge
↓
GenerationEvaluationResult
```

Actual retrieval/reranking must not run.

No external retrieval/network source fetch may run.

---

# 6. Fixed-evidence materialization

## 6.1 Core rule

Evidence source of truth:

```text
EvaluationCase.required_evidence[]
```

Materialize the exact approved evidence represented by the Step 7.2 fixture/evidence registry.

Do not:

```text
query vector DB to rediscover evidence
call SemanticRetrievalService
call RerankingService
live-fetch arbitrary external pages
call Tavily or any external search
substitute semantically similar chunks
use current runtime retrieval results
```

## 6.2 Internal evidence

For:

```text
source_kind = INTERNAL_CHUNK
```

resolve:

```text
stable_locator
→ exact accepted Step 7.2 fixture block/source content
→ production-shaped candidate/context provenance
```

Use the exact source-derived content from the accepted fixture pack.

Preserve at minimum:

```text
evidence_id
stable_locator
fixture source identity
source type
source title
lesson locator/title when applicable
section/locator when applicable
content_type
exact source-derived content
requirement_id
```

Do not use text/fuzzy matching as evidence identity.

## 6.3 Trusted-external evidence

For:

```text
source_kind = EXTERNAL_URL
```

use the accepted evaluation-only trusted-external registry.

Materialize only the frozen reviewed source representation:

```text
evidence_id
source_id
url
domain
title
reviewed claims accepted by Step 7.2
```

Do not live-fetch the URL.

Do not call runtime external retrieval.

Do not broaden the reviewed claims.

The source URL remains provenance identity; reviewed claims are the deterministic evidence content supplied for Step 7.4.

## 6.4 REQUIRED equivalence groups

Preserve the already-frozen policy:

```text
materialize all REQUIRED evidence refs
in deterministic EvaluationCase order
```

If two refs resolve to the exact same physical fixture locator/source representation, deduplicate the duplicate physical evidence object while preserving all associated:

```text
evidence_id
requirement_id
```

Do not drop a REQUIRED evidence ref merely because another member shares the same `requirement_id`.

This Step is evaluating generation from the approved evidence packet, not retrieval hit selection.

## 6.5 ACCEPTABLE evidence

Do not automatically add `acceptable_evidence[]` to the prompt.

It may remain in artifact metadata for evaluator inspection, but fixed generation context is driven by REQUIRED evidence.

## 6.6 Production-shaped bridge

`PromptContextBuilder` normally receives already-ranked candidates.

Implement a small evaluation-only bridge equivalent to:

```text
FixedEvidenceCandidateFactory
```

that converts the approved evidence packet into the existing candidate type accepted by `PromptContextBuilder`.

Rules:

```text
order = deterministic required_evidence order
no semantic search score is invented for evaluation meaning
no score participates in ordering
```

If the existing candidate schema permits nullable/non-applicable score fields, use them.

If the existing schema requires numeric score fields, use a documented evaluation-only sentinel solely to satisfy the structural type and mark:

```text
score_semantics = NOT_APPLICABLE_FIXED_EVIDENCE
```

The sentinel must:

```text
not be reported as retrieval quality
not be used by the judge
not be used to reorder evidence
not be interpreted as model confidence
```

Do not change the production candidate schema solely for Step 7.4.

---

# 7. Production PromptContextBuilder use

Fixed evidence must still pass through the existing production-equivalent prompt/context builder.

Expected flow:

```text
FixedEvidenceCandidate[]
+
current question
+
LearningContext?
+
PromptBudget
+
fixed ConversationMemory?  # via the current PromptPackage/memory seam
↓
PromptContextBuilder
↓
ContextBlock[]
↓
source labels S1..Sn
↓
source_map
↓
PromptPackage
```

Reuse existing:

```text
whole-block packing
token counting
context block formatting
source label assignment
source_map construction
grounding/system instructions
retrieved-content-as-reference safety rule
```

Do not hand-write a second evaluation prompt that approximates production.

## Prompt budget

Use the model-aware production budget for:

```text
gpt-5.4-mini-2026-03-17
```

Record actual:

```text
model input budget identity
reserved output tokens
token counter identity/version
context builder version
```

If a REQUIRED fixed evidence block cannot fit the production prompt budget:

```text
generator_status = TECHNICAL_FAILURE
error_code = FIXED_EVIDENCE_CONTEXT_BUDGET_EXHAUSTED
```

Do not silently drop required evidence and then score the generator.

This is a technical evaluation setup failure, not a semantic generation score.

---

# 8. LearningContext

When an eligible case contains `lesson_context`, map it deterministically to the existing backend-owned `LearningContext` equivalent.

Use only semantic fields available from Step 7.2 / fixture metadata, such as:

```text
lesson title
lesson locator
synthetic HSK identity where applicable
```

Do not require live learner progress/assessment state.

Do not expose backend/database IDs to the model.

Record the learning-context identity used in the per-case artifact.

---

# 9. MULTI_TURN_CONTEXT fixed memory

MULTI_TURN_CONTEXT remains eligible.

Its dataset `conversation_context` is fixed evaluation input.

Do not query live Conversation/Message history.

Create an evaluation-only adapter equivalent to:

```text
FixedConversationMemoryFactory
```

that converts dataset turns:

```text
{user_text, assistant_text}
```

into the existing:

```text
ConversationMemory
→ MemoryTurn[]
```

contract.

Rules:

```text
preserve chronological user/assistant roles
treat prior assistant text as conversational context, not evidence
do not create S1/S2 citation labels for memory
current fixed evidence remains authoritative
do not merge memory into context_blocks
do not expose internal IDs/status/timestamps
```

Apply the same production memory budget/max-turn rules where they affect serialization.

For the fixed dataset packet:

```text
all prior turns are conceptually completed historical turns
```

If the production memory budget drops a turn, record the selected/omitted turn counts in the artifact.

Do not concatenate memory into a retrieval query because retrieval is not called in Step 7.4.

---

# 10. Generator-under-test seam

Call the existing production generation flow:

```text
PromptPackage
↓
existing LLMRequestSerializer
↓
existing LLMGenerationService
↓
existing production LLMProvider
↓
gpt-5.4-mini-2026-03-17
↓
LLMGenerationResult
```

Do not call the provider SDK directly from the evaluator.

Do not create/update learner Conversation or Message persistence.

Generation evaluation is an offline evaluation flow.

## Generator result to retain

Minimum:

```text
generated text
provider
model
generation config
attempt_count
latency_ms
finish_reason if available
provider input token usage if available
output token usage if available
total token usage if available
normalized technical status/error
```

Do not persist:

```text
API keys
hidden chain-of-thought
provider private reasoning
```

The generated answer itself is an evaluation artifact and may be stored.

---

# 11. Production generator configuration

For the Step 7.4 run:

```text
model = gpt-5.4-mini-2026-03-17
```

Use the current accepted production Lesson Chat GenerationConfig.

Expected accepted defaults unless the PM-frozen current runtime config already contains a later approved value:

```text
temperature = 0.2
max_output_tokens = 800
non-streaming
timeout = 60 seconds
max transient retries = 1
tools = none
web search = none
automatic model fallback = none
```

Record the actual resolved config in the run manifest.

Do not tune generator parameters during Step 7.4.

If the current production generator config differs from the accepted project state, surface it in the completion handoff instead of silently changing production configuration.

---

# 12. Five frozen generation dimensions

Use exactly these five independent dimensions:

```text
ANSWER_CORRECTNESS
FAITHFULNESS_GROUNDEDNESS
COMPLETENESS
LANGUAGE_QUALITY
LEARNING_USEFULNESS
```

Score each:

```text
2 = meets expectation
1 = partially meets / minor issue
0 = significant failure
```

Do not replace them with one overall LLM score.

Do not average them into a release decision.

---

# 13. Rubric v1 — exact scoring rules

Set:

```text
rubric_version = lesson-chat-generation-rubric/v1
```

## 13.1 Answer Correctness

Primary ground truth:

```text
expected_information[]
```

Do not exact-match `reference_answer`.

### Score 2

- the information actually presented is correct;
- core Chinese-learning explanation is factually/linguistically correct;
- no material misleading statement about the requested concept;
- paraphrase is allowed.

### Score 1

- mostly correct;
- contains a minor imprecision/error that does not materially change the core teaching;
- or gives a partially correct framing while avoiding a materially false core claim.

### Score 0

- a material factual/linguistic error affects the requested concept;
- answer misstates expected information;
- answer is misleading about the core teaching;
- or core answer is wrong even if prose is fluent.

Correctness does not reward unsupported material claims merely because they may be true outside the fixed evidence; faithfulness handles support separately.

## 13.2 Faithfulness / Groundedness

Source of truth:

```text
fixed provided evidence only
```

Evaluate at claim level first.

### Score 2

- every material factual/instructional claim is SUPPORTED by the fixed evidence;
- no contradicted claims;
- no material unsupported claims.

### Score 1

- core teaching is supported;
- at most minor/peripheral unsupported detail exists;
- unsupported detail does not materially change learner understanding;
- no material contradicted claim.

### Score 0

- a core/material claim is unsupported;
- or any material claim is CONTRADICTED by fixed evidence;
- or answer relies materially on information absent from the fixed evidence.

Invariant:

```text
factually true in the real world
but unsupported by fixed evidence
→ faithfulness failure
```

Do not use external knowledge to rescue unsupported claims.

## 13.3 Completeness

Primary ground truth:

```text
atomic expected_information[]
```

### Score 2

- all required expected-information units are covered adequately.

### Score 1

- core answer is present;
- one or more expected-information units are omitted or materially underexplained;
- enough required information remains to be partially useful.

### Score 0

- most/core required information is missing;
- or response barely addresses the request.

Correctness and completeness remain separate.

Example:

```text
A/B/C expected
answer correctly covers A/B
misses C

→ correctness may remain high
→ completeness decreases
```

## 13.4 Language Quality

Evaluate suitability for a beginner Chinese learner, not generic literary fluency.

### Score 2

- Vietnamese explanation is clear and natural;
- Chinese examples/pinyin/meaning are presented clearly when relevant;
- concise enough for a beginner;
- no wording/formatting problem likely to confuse the learner.

### Score 1

- understandable overall;
- minor awkwardness, verbosity, organization, formatting, or wording issue;
- issue does not materially distort the learning content.

### Score 0

- difficult to understand;
- language/formatting errors materially obscure or distort learning content;
- response is substantially inappropriate for beginner comprehension.

Do not let fluent wording compensate for wrong or unsupported teaching.

## 13.5 Learning Usefulness

Evaluate pedagogical usefulness for the learner's actual question.

### Score 2

- directly addresses the learner intent;
- makes the requested rule/meaning/usage actionable;
- uses explanation/example/contrast where supported and helpful;
- appropriate depth for a beginner.

### Score 1

- useful but limited;
- explanation/example is incomplete, somewhat generic, or somewhat verbose;
- learner can still obtain practical value.

### Score 0

- does not help the learner apply/understand the concept;
- materially off-topic/confusing;
- or explanation is too advanced/irrelevant to be useful.

Learning Usefulness never compensates for correctness or faithfulness failure.

---

# 14. Claim-level faithfulness schema

Every successful judge result must include claim-level evaluation.

Logical schema:

```text
ClaimFaithfulness
├── claim_id
├── claim_text
├── verdict
│   ├── SUPPORTED
│   ├── UNSUPPORTED
│   └── CONTRADICTED
├── supporting_evidence_ids[]
└── concise_rationale
```

Rules:

```text
claim_id
→ deterministic inside the judge response, e.g. C1, C2, ...

supporting_evidence_ids
→ may contain only evidence IDs provided to the judge

UNSUPPORTED
→ supporting_evidence_ids normally []

CONTRADICTED
→ may reference the evidence that contradicts the claim
```

Claim extraction covers material:

```text
factual claims
Chinese-language claims
grammar/usage claims
instructional claims
```

Do not require claim objects for pure conversational glue such as:

```text
"Hy vọng ví dụ này dễ hiểu."
```

Judge rationale must be concise evaluation rationale, not hidden chain-of-thought.

---

# 15. Critical generation failure rules

Support exactly these Step 7.4 critical failures:

```text
SERIOUS_FACTUAL_ERROR
UNSUPPORTED_CONFIDENT_CLAIM
CONTRADICTED_BY_EVIDENCE
```

## SERIOUS_FACTUAL_ERROR

Flag when a material error in the core requested teaching would likely misteach the learner.

## UNSUPPORTED_CONFIDENT_CLAIM

Flag when a material factual/instructional claim is not supported by the provided fixed evidence and is stated as established fact/instruction rather than explicitly uncertain.

Do not flag trivial conversational wording.

## CONTRADICTED_BY_EVIDENCE

Flag when a material generated claim directly conflicts with the fixed evidence.

Critical failures may co-occur.

Deterministic case rule:

```text
critical_failures non-empty
→ generation_case_status = CRITICAL_FAILURE
→ generation_case_pass = false
```

When no critical failure exists:

```text
generation_case_status = BASELINE_SCORED
generation_case_pass = null
```

Why `null`:

```text
Step 7.4 has no overall/minimum-dimension release threshold
```

Do not silently define:

```text
average >= X
all dimensions >= Y
```

as a PASS rule.

Do not move these Step 7.5 failures into Step 7.4:

```text
fabricated citation/source
citation provenance mismatch
tier/fallback policy violation
refusal-policy failure
```

Citation text generated incidentally may remain in the output, but official citation semantic scoring belongs to Step 7.5.

---

# 16. Frozen 30-case DEVELOPMENT human calibration subset

Use exactly these 30 case IDs.

## CURRENT_LESSON_ANSWERABLE — 10

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
```

## INTERNAL_KB_FALLBACK — 8

```text
ikb-fallback-de-ge-001
ikb-fallback-de-ge-002
ikb-fallback-numbers-er-liang-001
ikb-fallback-numbers-er-liang-002
ikb-fallback-numbers-er-liang-003
ikb-fallback-pronouns-001
ikb-fallback-pronouns-002
ikb-fallback-pronouns-003
```

## TRUSTED_EXTERNAL_FALLBACK — 4

```text
trusted-external-bi-comparison-001
trusted-external-dou-placement-001
trusted-external-shenme-placement-001
trusted-external-zai-location-001
```

## MULTI_TURN_CONTEXT — 8

```text
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
all 30 exist
all 30 are APPROVED
all 30 are DEVELOPMENT
all 30 are eligible Step 7.4 cases
no HOLDOUT case appears
```

Do not replace cases automatically if one is missing.

A mismatch is:

```text
BLOCKED — CALIBRATION SUBSET DRIFT
```

---

# 17. Human annotation storage

Use source-controlled files, not a DB table.

Create:

```text
evaluation/annotations/lesson_chat_generation/v0.1.0/
├── manifest.json
└── calibration.jsonl
```

Logical annotation version:

```text
human_annotation_version = lesson-chat-generation-human/v0.1.0
```

## manifest.json minimum

```text
annotation_name
annotation_version
dataset_version = v0.8.0
rubric_version = lesson-chat-generation-rubric/v1
case_count = 30
case_ids[]
review_policy
created_at
updated_at
```

## calibration.jsonl logical schema

```text
HumanGenerationAnnotation
├── case_id
├── generation_run_id
├── generated_answer_sha256
├── annotation_version
├── rubric_version
├── scores
│   ├── answer_correctness: 0|1|2
│   ├── faithfulness_groundedness: 0|1|2
│   ├── completeness: 0|1|2
│   ├── language_quality: 0|1|2
│   └── learning_usefulness: 0|1|2
├── claim_faithfulness[]
│   ├── claim_id
│   ├── claim_text
│   ├── verdict = SUPPORTED|UNSUPPORTED|CONTRADICTED
│   ├── supporting_evidence_ids[]
│   └── concise_note?
├── critical_failures[]
├── concise_notes?
└── review_status
    ├── DRAFT
    ├── NEEDS_ADJUDICATION
    └── HUMAN_APPROVED
```

Do not store human hidden reasoning.

## Human approval gate

Only:

```text
HUMAN_APPROVED
```

counts toward the 30-case agreement report.

Codex/LLM must never self-approve human annotations.

---

# 18. Two-stage human calibration workflow

Human calibration requires generated outputs first.

Therefore Step 7.4 execution is intentionally staged.

## Stage A — generation preparation

Run all 45 eligible cases through the production generator with fixed evidence.

Write generator outputs and immutable answer hashes.

For the 30 calibration IDs, create/update DRAFT human annotation rows that bind:

```text
case_id
generation_run_id
generated_answer_sha256
```

Do not auto-fill human semantic scores.

Return:

```text
REVIEW_REQUIRED — HUMAN CALIBRATION
```

until 30 annotations are HUMAN_APPROVED.

## Stage B — judge evaluation

Before judge calls:

```text
validate exactly 30 HUMAN_APPROVED annotations
validate generated_answer_sha256 matches Stage-A artifact
```

If any annotated answer changed:

```text
STOP
→ REVIEW_REQUIRED — HUMAN CALIBRATION STALE
```

Then:

```text
freeze the Stage-A generated answers
→ call judge on all technically successful eligible cases
→ compute human/judge agreement on the exact 30
→ write final generation evaluation artifacts
```

Do not regenerate answers between human calibration and judge scoring unless the human calibration is redone.

---

# 19. D-100 judge provider

Implement/reuse one Step 7.4 judge seam equivalent to:

```text
GenerationJudge
```

The semantic evaluator should depend on a judge interface, not directly scatter OpenAI calls through runner code.

D-100 concrete implementation:

```text
provider = OpenAI API
API = Responses API
model = gpt-5.4-2026-03-05

reasoning_effort = none
temperature = 0
max_output_tokens = 1600
structured output = required
tools = none
```

Single judge only.

Do not implement:

```text
multi-judge voting
judge fallback model
web search
tools
external retrieval
second judge for disagreement
```

## Judge credentials

Reuse backend secret/config conventions.

Do not put API key into:

```text
source files
evaluation artifacts
logs
frontend
```

Judge configuration may be evaluation-specific so production generator config remains unchanged.

Do not overwrite the application's production `LLM_MODEL`.

---

# 20. Judge prompt contract

Set:

```text
judge_prompt_version = lesson-chat-generation-judge/v1
```

Judge input must contain:

```text
case_id
question
expected_information[]
fixed_evidence[]
generated_answer
five exact dimension rubrics
critical-failure definitions
```

Optional secondary input:

```text
reference_answer
```

if present.

The judge instruction must explicitly state all of:

```text
- Score the five dimensions independently on 0/1/2.
- expected_information[] is the primary correctness/completeness ground truth.
- reference_answer is secondary and wording does not need to match it.
- Evaluate faithfulness only against the fixed evidence supplied here.
- Do not use outside knowledge to rescue unsupported claims.
- A fact may be true in the real world and still be UNSUPPORTED here.
- Identify material factual/instructional claims and classify them as
  SUPPORTED, UNSUPPORTED, or CONTRADICTED.
- Only cite evidence IDs present in the fixed evidence packet.
- Apply the exact critical failure definitions.
- Language Quality and Learning Usefulness cannot compensate for
  factual/faithfulness failures.
- Do not evaluate retrieval, tier fallback, refusal policy, or citation
  semantic correctness.
- Return concise evaluation rationale only.
- Do not provide or expose hidden chain-of-thought.
```

Do not ask the judge to compare to production retrieval output.

Do not include HOLDOUT human labels in the prompt.

Do not include any human calibration labels in judge prompts.

The judge must score independently; human labels are used only afterward for agreement reporting.

---

# 21. Judge structured output schema

Require schema-validated structured output.

Logical response:

```text
GenerationJudgeResult
├── schema_version = "1.0.0"
├── case_id
├── dimension_scores
│   ├── answer_correctness
│   │   ├── score: 0|1|2
│   │   └── rationale
│   ├── faithfulness_groundedness
│   │   ├── score: 0|1|2
│   │   └── rationale
│   ├── completeness
│   │   ├── score: 0|1|2
│   │   └── rationale
│   ├── language_quality
│   │   ├── score: 0|1|2
│   │   └── rationale
│   └── learning_usefulness
│       ├── score: 0|1|2
│       └── rationale
├── claims[]
│   ├── claim_id
│   ├── claim_text
│   ├── verdict
│   ├── supporting_evidence_ids[]
│   └── concise_rationale
├── critical_failures[]
└── concise_overall_rationale
```

Allowed critical values:

```text
SERIOUS_FACTUAL_ERROR
UNSUPPORTED_CONFIDENT_CLAIM
CONTRADICTED_BY_EVIDENCE
```

Validate deterministically:

```text
all 5 dimensions present exactly once
score ∈ {0,1,2}
claim verdict in enum
supporting evidence IDs exist in same judge input
critical failure enum valid
case_id matches request
```

Invalid/malformed judge output is a technical judge failure.

Do not coerce invalid semantic values silently.

---

# 22. Judge technical behavior

Use one logical judge operation per generated answer.

No judge model fallback.

A network retry for a transient transport/provider error, if already provided by the repository's standard provider policy, is a technical retry and not multi-judge voting.

Reuse the existing normalized technical error style where practical.

Record:

```text
judge_status = SUCCESS | TECHNICAL_FAILURE | NOT_RUN
judge_attempt_count
judge_latency_ms
judge provider/model
judge request ID if safe/available
judge token usage if available
judge normalized error code if failed
```

Do not convert judge technical failure into semantic score `0`.

---

# 23. Technical-failure semantics

Semantic quality and infrastructure success remain separate.

## Generator technical failure

Examples:

```text
provider timeout
auth/config error
provider unavailable
invalid/blank provider response
context overflow
fixed evidence cannot fit required production context
unexpected generation exception
```

Artifact:

```text
generator_status = TECHNICAL_FAILURE
generated_answer = null
dimension_scores = null
claims = null
critical_failures = []
generation_case_status = TECHNICAL_FAILURE
generation_case_pass = null
judge_status = NOT_RUN
```

Do not score it as a bad semantic answer.

## Judge technical failure

If generator succeeded but judge failed:

```text
generator_status = SUCCESS
generated_answer = preserved
judge_status = TECHNICAL_FAILURE
dimension_scores = null
claims = null
generation_case_status = JUDGE_TECHNICAL_FAILURE
generation_case_pass = null
```

Do not hide this as judge disagreement.

## Human annotation missing

Missing/unapproved human calibration annotation is:

```text
REVIEW_REQUIRED
```

not a provider technical failure.

---

# 24. Human/judge agreement baseline

Step 7.4 records baseline only.

No agreement threshold.

On the exact 30 HUMAN_APPROVED cases report at least:

## Per dimension

```text
exact_agreement_rate
mean_absolute_score_difference
3x3 score confusion matrix
human mean score
judge mean score
```

## Across all 150 dimension labels

```text
macro_exact_agreement_rate
overall_mean_absolute_score_difference
```

## Critical failures

Report:

```text
case-level exact critical-failure-set agreement
human critical-failure case count
judge critical-failure case count
```

Do not introduce:

```text
agreement >= X → PASS
agreement < X → FAIL
```

Regression/gating policy belongs to Step 7.6.

Do not tune the judge on HOLDOUT.

---

# 25. Runner flow

Follow the repository-native Step 7.3 evaluation conventions where useful.

Suggested module boundary, adapting to current repository conventions:

```text
backend/app/evaluation/step74/
├── __init__.py
├── cli.py
├── eligibility.py
├── fixed_evidence.py
├── fixed_memory.py
├── generator.py
├── judge.py
├── rubrics.py
├── annotations.py
├── evaluation.py
└── runner.py
```

Do not create files mechanically if equivalent modules already exist.

## Stage A command capability

Equivalent:

```text
run Step 7.4 generation stage
→ validate dataset v0.8.0
→ select exact 45 eligible cases
→ materialize fixed evidence
→ materialize fixed memory
→ production prompt build
→ production generation
→ write immutable generated outputs
→ create/validate 30-case human annotation packet
→ stop pending human calibration
```

## Stage B command capability

Equivalent:

```text
resume same Step 7.4 run
→ validate 30 HUMAN_APPROVED annotations
→ validate answer hashes
→ judge all successful generated answers
→ compute five-dimension summaries
→ compute claim/critical-failure summaries
→ compute human/judge agreement
→ finalize artifacts
```

Do not regenerate the production answers during Stage B.

---

# 26. Run artifact location

Use:

```text
evaluation/runs/<run_id>/generation/
├── manifest.json
├── cases.jsonl
├── summary.json
└── calibration-agreement.json
```

If Stage A is awaiting human review, the directory may contain:

```text
manifest.json
cases.jsonl
```

with:

```text
run_status = REVIEW_REQUIRED_HUMAN_CALIBRATION
```

Final successful evaluation adds/finishes summary/agreement artifacts.

Do not create a DB table for evaluation runs.

---

# 27. manifest.json schema

Minimum logical fields:

```text
run_id
run_status
timestamp_started
timestamp_finalized?
evaluation_step = "7.4"

dataset_name
dataset_version = "v0.8.0"
dataset_schema_version
eligible_case_policy_version
eligible_case_count = 45
development_case_count = 36
holdout_case_count = 9
excluded_buckets

code_commit if available

fixed_evidence_policy_version
internal_fixture_pack/version/hash
trusted_external_registry version/hash
fixed_memory_policy_version

generator_provider
generator_model = "gpt-5.4-mini-2026-03-17"
generator_temperature
generator_max_output_tokens
generator_timeout
generator_retry_policy
generator_streaming = false
generator_tools = none
generator_prompt_version_or_hash
context_builder_version
token_counter identity
prompt_budget identity

judge_provider = "OpenAI API"
judge_api = "Responses API"
judge_model = "gpt-5.4-2026-03-05"
judge_reasoning_effort = "none"
judge_temperature = 0
judge_max_output_tokens = 1600
judge_structured_output = true
judge_tools = none
judge_prompt_version = "lesson-chat-generation-judge/v1"

rubric_version = "lesson-chat-generation-rubric/v1"

human_annotation_version
human_calibration_case_count = 30
human_calibration_case_ids[]
human_calibration_status

technical_failure_policy_version
```

Do not record API keys.

## Prompt reproducibility

Record:

```text
generator_prompt_version_or_hash
```

from the existing production prompt/system-instruction contract.

Also record per-case:

```text
prompt_package_sha256
```

computed from a deterministic serialization of the provider-independent PromptPackage used for generation.

Do not persist hidden system secrets; prompts must not contain secrets.

---

# 28. cases.jsonl schema

One row per one of the 45 eligible EvaluationCases.

Logical shape:

```text
GenerationEvaluationCaseResult
├── case_id
├── split
├── bucket
├── question
├── expected_information[]
├── reference_answer?  # optional secondary eval reference
│
├── fixed_evidence[]
│   ├── evidence_id
│   ├── requirement_id?
│   ├── source_kind
│   ├── stable/source locator
│   ├── source identity/title
│   ├── content_sha256
│   └── llm_visible_content
│
├── fixed_memory?
│   ├── original_turn_count
│   ├── selected_turn_count
│   ├── omitted_turn_count
│   ├── selected_turns
│   └── token_count
│
├── learning_context?
├── prompt_package_sha256
├── source_map_snapshot
│
├── generator
│   ├── status
│   ├── provider
│   ├── model
│   ├── temperature
│   ├── max_output_tokens
│   ├── attempt_count
│   ├── latency_ms
│   ├── finish_reason?
│   ├── token_usage?
│   └── error?
│
├── generated_answer?
├── generated_answer_sha256?
│
├── judge
│   ├── status
│   ├── provider
│   ├── api
│   ├── model
│   ├── config
│   ├── latency_ms
│   ├── attempt_count
│   ├── token_usage?
│   └── error?
│
├── dimension_scores?
├── claim_faithfulness?
├── critical_failures[]
├── generation_case_status
├── generation_case_pass  # false | null
│
└── calibration?
    ├── in_human_subset
    ├── human_review_status?
    └── human_annotation_version?
```

Per-case artifact may include the fixed evidence text and generated answer because they are required evaluation inputs/outputs.

Do not persist hidden CoT from generator or judge.

---

# 29. summary.json schema

Minimum:

```text
run_id
run_status
dataset_version

eligible_case_count = 45
case_counts_by_split
case_counts_by_bucket

generator_success_count
generator_technical_failure_count
generator_technical_success_rate

judge_success_count
judge_technical_failure_count
judge_not_run_count
judge_technical_success_rate_on_generated_answers

mean_score_by_dimension
score_distribution_by_dimension
cases_with_score_0_by_dimension

metrics_by_split
metrics_by_bucket

claim_verdict_counts
cases_with_unsupported_claims
cases_with_contradicted_claims

critical_failure_case_count
critical_failure_rate_among_judged_cases
critical_failure_counts_by_type

generation_case_status_counts

human_calibration_case_count = 30
human_approved_count
human_judge_agreement_headline

latency summary
token usage summary when available
```

Do not add:

```text
overall generation score
overall PASS threshold
release gate
minimum dimension gate
```

A simple unweighted dimension mean may be reported separately per dimension only.

---

# 30. calibration-agreement.json schema

Minimum:

```text
agreement_artifact_version
run_id
dataset_version
human_annotation_version
rubric_version
judge_prompt_version

case_count_expected = 30
case_count_compared = 30

per_dimension:
  answer_correctness:
    exact_agreement_rate
    mean_absolute_score_difference
    confusion_matrix
    human_mean
    judge_mean
  faithfulness_groundedness: ...
  completeness: ...
  language_quality: ...
  learning_usefulness: ...

macro_exact_agreement_rate
overall_mean_absolute_score_difference

critical_failure_set_exact_agreement_rate
human_critical_failure_case_count
judge_critical_failure_case_count

agreement_gate = null
notes = "Baseline only; regression/gating deferred to Step 7.6"
```

No hard agreement threshold.

---

# 31. Tests

Add focused deterministic tests.

Standard test suites must not require paid network/API calls.

Use fakes/mocks for generator/judge unit tests, plus separate opt-in real API smoke tests where appropriate.

## 31.1 Eligible-case policy

- v0.8.0 selects exactly 45 eligible cases;
- DEVELOPMENT = 36;
- HOLDOUT = 9;
- exact included bucket counts match frozen contract;
- NO_EVIDENCE_REFUSAL excluded;
- OUT_OF_DOMAIN_REFUSAL excluded;
- only APPROVED cases accepted.

## 31.2 Fixed evidence

- INTERNAL_CHUNK resolves exact stable fixture locator;
- external evidence resolves accepted reviewed registry without network;
- no retrieval service is called;
- no reranker is called;
- required evidence order deterministic;
- duplicate physical locator deduplicates without losing evidence IDs;
- ACCEPTABLE evidence not injected automatically;
- provenance/identity preserved;
- content hash stable.

## 31.3 PromptContextBuilder integration

At least one integration test must use the actual existing PromptContextBuilder boundary.

Verify:

- fixed evidence becomes real production ContextBlocks;
- source labels contiguous;
- source_map preserved;
- reference data remains outside system authority;
- whole-block packing preserved;
- required evidence budget exhaustion is technical failure;
- no retrieval call occurs.

## 31.4 MULTI_TURN_CONTEXT

- dataset history maps to ConversationMemory / MemoryTurn schema;
- chronological roles preserved;
- memory remains separate from context blocks;
- prior assistant is not evidence;
- current evidence remains authoritative;
- no live conversation DB load;
- memory budget/max-turn policy applied;
- current question appears once.

## 31.5 Production generator seam

- evaluator calls existing LLMGenerationService, not vendor SDK directly;
- model preflight enforces gpt-5.4-mini-2026-03-17;
- production GenerationConfig recorded;
- no tools/web/external retrieval;
- no model fallback;
- generator technical failure preserved separately;
- blank response technical failure;
- token/latency metadata retained.

## 31.6 Five rubrics

Test canonical examples for each dimension:

- fully correct → correctness 2;
- minor imprecision → correctness 1;
- material wrong teaching → correctness 0;
- A/B of A/B/C → completeness decreases;
- true-but-unsupported claim → faithfulness failure;
- contradicted claim → faithfulness 0 + critical flag;
- fluent wrong answer does not pass correctness;
- beginner-clear answer receives higher Language Quality than confusing equivalent;
- actionable beginner explanation receives higher Learning Usefulness than unhelpful generic prose.

These tests may validate rubric evaluator/result-processing behavior with fake judge responses; do not encode a second heuristic semantic judge.

## 31.7 Judge schema

- exactly five dimension outputs required;
- only scores 0/1/2 allowed;
- claim verdict enum enforced;
- unknown evidence IDs rejected;
- critical failure enum enforced;
- wrong case_id rejected;
- missing/invalid JSON/schema = technical judge failure;
- concise rationale persisted;
- no CoT field accepted/required.

## 31.8 D-100 judge config

Assert:

```text
OpenAI API
Responses API
gpt-5.4-2026-03-05
reasoning_effort=none
temperature=0
max_output_tokens=1600
structured output required
tools none
```

Assert:

```text
no multi-judge voting
no judge fallback
no web search
no tools
```

## 31.9 Human calibration subset

- exact 30 IDs;
- all DEVELOPMENT;
- no HOLDOUT;
- all eligible;
- HUMAN_APPROVED gate required;
- missing approval → REVIEW_REQUIRED;
- generated-answer hash mismatch → HUMAN_CALIBRATION_STALE;
- Codex/LLM cannot mark annotation HUMAN_APPROVED.

## 31.10 Agreement

- exact agreement computed per dimension;
- mean absolute score difference correct;
- confusion matrix correct;
- macro exact agreement correct;
- critical failure set agreement correct;
- no agreement pass threshold created.

## 31.11 Technical failures

- generator failure does not become score 0;
- judge not called after generator failure;
- judge failure preserves generated answer;
- judge failure does not become score 0;
- human-review-required is not technical failure.

## 31.12 Artifacts

- manifest required fields;
- exactly 45 case rows;
- deterministic case order;
- prompt/answer hashes stable;
- no secrets;
- no hidden CoT;
- summary denominators correct;
- calibration agreement only uses 30 frozen DEVELOPMENT cases.

---

# 32. Real API smoke tests

Real paid/API tests must be opt-in and separate from default CI/unit tests.

Before the official Step 7.4 run:

1. verify production generator provider can generate one fixed-evidence case using:
   ```text
   gpt-5.4-mini-2026-03-17
   ```
2. verify D-100 judge can produce schema-valid structured output using:
   ```text
   gpt-5.4-2026-03-05
   Responses API
   ```

Do not use tools/web in either smoke test.

If credentials/API access are unavailable:

```text
BLOCKED — EVALUATION RUNTIME UNAVAILABLE
```

Do not fabricate generation/judge results.

---

# 33. Documentation — Step Note

Create/update:

```text
docs/evaluation/step-7.4-generation-evaluation.md
```

The Step Note must contain:

## Objective

Evaluate Lesson Chat generation quality independently from retrieval using fixed approved evidence.

## Why

Without isolation:

```text
bad answer
```

cannot be attributed confidently to:

```text
retriever
or
generator
```

## Mental Model

```text
gold/fixed evidence
→ production prompt
→ production generator
→ generation judge
```

This is a controlled experiment on the generator layer.

## Core Knowledge

Include:

```text
generation-isolated evaluation
ground truth vs reference answer
claim-level faithfulness
graded rubric
LLM-as-a-Judge calibration
human calibration
technical vs semantic failure
reproducible evaluation artifacts
```

## Data Flow

Document the exact implemented Stage A / human review / Stage B flow.

## Key Design Decisions

Include:

```text
45 answerable cases only
fixed evidence, no retrieval
MULTI_TURN gets fixed memory
five independent 0/1/2 rubrics
claim-level faithfulness
single gpt-5.4 judge per D-100
30 human-approved DEVELOPMENT cases
no release threshold
```

## Reusable approach

Explain how to isolate one component of an AI pipeline by fixing its upstream input.

## Common Mistakes

Include at least:

```text
using actual retrieval in generator-isolated evaluation
using exact reference-answer string match
using external knowledge to rescue unsupported claims
treating technical error as score 0
tuning judge against HOLDOUT
letting one overall score hide critical failures
using the same "generation evaluation" for Step 6.12 assessment generation
```

## Definition of Done

Reflect actual acceptance criteria below.

---

# 34. Concepts Discovered

Add only concepts actually used.

Expected table:

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Generation-isolated evaluation | AI | 7.4 | Measures generator quality with upstream evidence fixed |
| LLM-as-a-Judge | AI | 7.4 | Semantic evaluator for generation dimensions |
| Human calibration | BOTH | 7.4 | Anchors judge credibility against reviewed labels |
| Claim-level faithfulness | AI | 7.4 | Separates supported, unsupported, contradicted claims |
| Evaluation rubric | AI | 7.4 | Makes 0/1/2 dimension scoring explicit and reproducible |
| Technical vs semantic failure | SYSTEM | 7.4 | Prevents infrastructure failure from contaminating quality scores |
| Evaluation run artifact | SYSTEM | 7.4 | Preserves reproducibility/debug evidence |

Use only:

```text
DE / AI / BOTH / SYSTEM
```

Do not create `QA` as a category.

---

# 35. Tools Used

Record only tools actually used during implementation/run.

Likely examples if truly used:

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| Python | SYSTEM | 7.4 | Evaluation runner/schema/metrics |
| pytest | SYSTEM | 7.4 | Deterministic evaluator tests |
| uv | SYSTEM | 7.4 | Existing project environment workflow |
| OpenAI API | AI | 7.4 | Frozen D-100 judge provider |
| Existing production LLM provider/client | AI | 7.4 | Generator under test |

Do not add a library/service merely to make the table larger.

---

# 36. Step Specification

Update the implementation-facing Step 7.4 specification so actual code and the frozen contract match.

Include at minimum:

```text
Context
Objective
Current state
In Scope
Out of Scope
Functional Requirements
Technical Requirements
Inputs / Outputs
Data Flow
Interfaces / schema
Files/components
Config/env
Error handling
Testing
Acceptance Criteria
Constraints / Non-goals
Open Questions
```

Open Questions should be:

```text
None
```

unless implementation discovers a genuinely material new PM decision.

Do not rewrite Step 7.2 ground truth.

---

# 37. Acceptance Criteria

Step 7.4 implementation is ready for specialist review only when:

- dataset v0.8.0 remains unchanged;
- exactly 45 APPROVED eligible cases selected;
- exact 36 DEVELOPMENT / 9 HOLDOUT split;
- NO_EVIDENCE and OOD excluded;
- MULTI_TURN included with fixed memory;
- exact fixed approved evidence supplied without retrieval;
- no SemanticRetrievalService call during generation benchmark;
- no RerankingService call during generation benchmark;
- no external retrieval/live URL fetch;
- existing PromptContextBuilder reused;
- existing PromptPackage structure reused;
- existing production Lesson Chat generation seam reused;
- generator model is exactly `gpt-5.4-mini-2026-03-17`;
- production generator config is not silently tuned;
- all five exact rubrics implemented;
- expected_information is primary correctness/completeness truth;
- faithfulness evaluated claim-by-claim against fixed evidence;
- three exact critical generation failure classes supported;
- critical failure cannot be hidden by averages;
- no overall/min-dimension/release threshold introduced;
- exact 30 DEVELOPMENT human subset enforced;
- no HOLDOUT human calibration;
- human annotations are manually HUMAN_APPROVED;
- generated answer hashes bind annotations to the correct outputs;
- D-100 judge config exact;
- single judge only;
- judge structured output schema validated;
- judge sees no human labels;
- judge uses no tools/web/external retrieval;
- judge technical failures are separate from semantic scores;
- human/judge agreement baseline reported;
- no hard agreement gate introduced;
- generator/judge latency and token usage captured where available;
- manifest/cases/summary/agreement artifacts reproducible;
- no hidden chain-of-thought requested or persisted;
- focused tests pass;
- relevant existing prompt/generation tests pass;
- real generator/judge smoke tests pass before official run;
- Step Note completed;
- Concepts/Tools tables updated;
- implementation-facing Step spec reflects actual code;
- Step 7.5 not started;
- Step 7.7 not started;
- Step 7.6 not started.

---

# 38. Explicit non-goals

Do NOT:

- modify Step 7.2 dataset ground truth;
- expand official dataset to 120;
- run actual retrieval for fixed evidence;
- run reranker for fixed evidence;
- evaluate retrieval metrics;
- implement citation semantic scoring;
- evaluate fallback correctness;
- evaluate refusal correctness;
- implement end-to-end RAG evaluation;
- implement Step 6.11 free-form grading evaluation;
- implement Step 6.12 assessment-content generation evaluation;
- start Step 7.5;
- start Step 7.7;
- start Step 7.6;
- tune production generator prompt/model/decoding;
- change production model configuration;
- add judge voting;
- add judge fallback;
- add judge tools;
- add web search;
- add external retrieval;
- use HOLDOUT to tune judge prompt/rubric;
- add a judge agreement threshold;
- add overall generation pass/release threshold;
- add regression thresholds;
- add CI quality gates;
- request/persist hidden chain-of-thought;
- add a new framework/service without demonstrated necessity.

---

# 39. Execution states

Use clear terminal statuses.

## Implementation/runtime blocked

```text
BLOCKED — EVALUATION RUNTIME UNAVAILABLE
```

Examples:

```text
production generator credentials unavailable
judge API credentials/access unavailable
frozen exact model unavailable
```

## Material repository contradiction

```text
BLOCKED — DECISION NEEDED
```

Use only when actual repository evidence requires a PM architecture/product/evaluation-validity decision.

## Stage A complete

```text
REVIEW_REQUIRED — HUMAN CALIBRATION
```

This is the expected state after generation outputs exist but before 30 human annotations are approved.

## Human annotation stale

```text
REVIEW_REQUIRED — HUMAN CALIBRATION STALE
```

## Final implementation/run ready

```text
READY_FOR_SPECIALIST_REVIEW
```

Only after:

```text
30/30 HUMAN_APPROVED
judge run complete
artifacts complete
tests pass
```

---

# 40. Required Codex completion handoff

Return:

```text
Step:
7.4 — Generation Evaluation

Status:

What was implemented:

Files created:
Files modified:
Dependencies added/removed:

Repository seams reused:
- PromptContextBuilder:
- PromptPackage:
- ConversationMemory schema:
- LLMGenerationService:
- production LLM provider:

Eligible cases:
- total:
- DEVELOPMENT:
- HOLDOUT:
- counts by bucket:

Fixed evidence:
- internal fixture resolver:
- trusted external resolver:
- retrieval called: MUST be NO
- reranker called: MUST be NO
- external live fetch called: MUST be NO

MULTI_TURN:
- fixed memory behavior:
- memory selected/omitted behavior:

Generator:
- provider:
- model:
- temperature:
- max_output_tokens:
- timeout/retry:
- prompt version/hash:
- context builder version:

Human calibration:
- annotation version:
- exact subset count:
- HUMAN_APPROVED count:
- answer hash validation:

Judge:
- provider: OpenAI API
- API: Responses API
- model: gpt-5.4-2026-03-05
- reasoning_effort: none
- temperature: 0
- max_output_tokens: 1600
- structured output: required
- tools: none
- judge prompt version:
- schema version:

Generation metrics:
- technical success/failure:
- five dimension means/distributions:
- critical failure counts:
- claim verdict counts:

Human/judge agreement:
- exact agreement by dimension:
- MAE by dimension:
- macro exact agreement:
- critical failure agreement:
- agreement threshold: MUST be NONE

Run artifact:
- run_id:
- manifest:
- cases:
- summary:
- calibration agreement:

Verification commands/results:
Tests:
Real API smoke tests:

Runtime production generator config modified:
- MUST be NO

Step 7.2 ground truth changed:
- MUST be NO

Step 7.5 started:
- MUST be NO

Step 7.7 started:
- MUST be NO

Step 7.6 started:
- MUST be NO

Documentation:
Concepts added:
Tools added:

Problems / risks:
Decisions needed:
Recommended next action:
```

Do not claim PM acceptance of Step 7.4.

---

# 41. Specialist review expectations

The specialist will independently verify at least:

```text
eligible 45-case selection
fixed evidence identity/content
no retrieval/reranking path
MULTI_TURN memory separation
production generator seam/config
five rubric schemas
claim-level faithfulness
critical failure handling
technical failure separation
exact 30-case calibration subset
human answer hashes
D-100 judge config
structured judge schema
agreement arithmetic
run artifact reproducibility
no premature pass/release threshold
```

The specialist must reject the run if:

```text
human labels are AI-self-approved
HOLDOUT is used to calibrate/tune judge
judge sees human labels
production retrieval is used as gold context
external live fetch is used for fixed evidence
technical failures become semantic zeros
a release/pass threshold is invented
```
