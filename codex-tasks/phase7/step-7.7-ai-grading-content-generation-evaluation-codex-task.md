# Step 7.7 — AI Grading & Content-Generation Evaluation
## Codex Task Draft — PRE-FREEZE

> Status of this task packet: **SPECIALIST READY_FOR_PM_FREEZE — DRAFT FOR PM REVIEW**
>
> This file is NOT authorization to execute Codex.
>
> After PM review/freeze, execution is limited to **OFFLINE IMPLEMENTATION / DETERMINISTIC TEST MODE ONLY** unless a later PM instruction explicitly authorizes runtime evaluation.

---

# 0. Task Identity

```text
Step:
7.7 — AI Grading & Content-Generation Evaluation

Owner:
DevOps & QA Specialist
AI Engineering consulted

Implementation mode:
OFFLINE IMPLEMENTATION / DETERMINISTIC TEST MODE ONLY

Expected Codex terminal status:
READY_FOR_SPECIALIST_REVIEW — OFFLINE IMPLEMENTATION

or, only for a genuine material blocker:
BLOCKED — DECISION NEEDED
```

Do NOT claim:

```text
Step 7.7 DONE
PM final acceptance
official grading benchmark complete
official generation benchmark complete
```

Do NOT start Step 7.6.

---

# 1. Source-of-Truth Precedence

Use this precedence if repository/spec wording conflicts:

```text
1. PM Decision Log / current PM freeze
2. this frozen Step-7.7 Codex task
3. current accepted production repository implementation
4. current Step specifications
5. older comments/examples
```

The following decisions are frozen and MUST NOT be reopened or altered:

```text
D-079  V0 provider/model baseline
D-095  free-form partial-credit / is_correct semantics
D-096  V0 assessment-generation knowledge sources
D-097  generation question-count bound
D-098  generation difficulty contract
D-099  generation output budget

D-102  later Phase-7 offline implementation authorization

D-106  Step-7.7 primary grading agreement unit
D-107  agreement denominator / UNCERTAIN policy
D-108  Step-7.7 V0 dataset sizes and splits
D-109  generation human-review unit
```

If actual repository behavior materially contradicts a frozen PM decision:

```text
STOP
→ BLOCKED — DECISION NEEDED
```

Do not silently "fix" the PM contract inside evaluation code.

---

# 2. Scope

Step 7.7 contains two independent evaluation tracks.

## Track A — Free-form AI Grading

Evaluate existing Step-6.11 production capability:

```text
human-reviewed grading case
→ production AIGrader/application grading seam
→ normalized GradeResult
→ compare against human ground truth
→ agreement / abstention / technical metrics
→ reproducible artifacts
```

Free-form types:

```text
translate_vi_zh
translate_zh_vi
sentence_writing
```

## Track B — AI Assessment Generation

Evaluate existing Step-6.12 production capability:

```text
frozen generation request + authoritative selected curriculum scope
→ production AssessmentGenerationService/application seam
→ structured generated draft
→ production validation
→ persisted DRAFT lifecycle
→ deterministic policy evaluation
→ question-level human semantic evaluation
→ reproducible artifacts
```

Generation kinds:

```text
LESSON_EXERCISE
PERIODIC_TEST
```

Authoritative sources:

```text
Lesson
Vocabulary
Grammar
```

Explicitly out of source scope:

```text
Documents
RAG
retrieval
vector DB
web
external search
conversation memory
citations
```

Do not add those capabilities to Step 7.7.

---

# 3. Hard Scope Guardrails

Do NOT:

```text
modify production grading behavior
modify production assessment-generation behavior
tune grading/generation prompts to hit the benchmark
change production provider/model/config
fine-tune
add model routing
add another provider
add a new LLM judge
reuse the Step-7.4 judge as Track-B human review
add RAG/retrieval/citations/memory
add web/external generation
change assessment schema or migrations
auto-publish AI content
weaken Admin review
change D-106..D-109
change frozen dataset sizes/splits
invent another release threshold
make paid API calls
make live external calls
create HUMAN_APPROVED annotations
create official benchmark results
start Step 7.6
```

No new framework or service solely for evaluation.

---

# 4. Mandatory Repository Preflight — FAIL CLOSED

The source material available during specialist JIT review did not expose every current Step-6.11/6.12 repository seam.

Before modifying code, inspect the ACTUAL repository and write a concise preflight record in the implementation handoff.

## 4.1 Track A — locate exact current seams

Record exact paths, classes/functions and signatures for:

```text
AIGrader application boundary/protocol
production grading service
grading prompt builder
structured output schema/parser
grading provider protocol/adapter
GradeResult
grading status enum
grading technical error types
production model/config construction
assessment submission integration
AttemptAnswer persistence/status fields
AssessmentAttempt GRADING_FAILED handling
```

Also identify the exact production input object(s) passed to the grader.

Expected production semantics that MUST remain true:

```text
GRADED:
  0 <= score <= max_points
  is_correct = (score == max_points)

UNCERTAIN:
  score = null
  is_correct = null

technical failure:
  NOT UNCERTAIN
  affected AttemptAnswer grading_status = FAILED
  existing AssessmentAttempt GRADING_FAILED semantics remain authoritative
```

## 4.2 Track B — locate exact current seams

Record exact paths, classes/functions and signatures for:

```text
LessonExerciseGenerationRequest
PeriodicTestGenerationRequest
AssessmentGenerationRequest or equivalent

AssessmentGenerationService
generation prompt builder
structured output schemas
MaterializedGenerationScope
validate/map output function
production domain validator
scope materializer/loader
generation provider protocol/adapter
generation technical/validation errors
Admin generate-draft application service/router
generation persistence transaction
Assessment / Question DRAFT lifecycle
source_refs handling
generation settings/config
```

Prior accepted implementation evidence suggests equivalents such as:

```text
build_generation_prompt(...)
AssessmentGenerationService.generate(...)
validate_and_map_output(...)
MaterializedGenerationScope
```

but Codex MUST use the actual repository as authority.

## 4.3 Preflight stop conditions

STOP with:

```text
BLOCKED — DECISION NEEDED
```

if:

```text
production repository materially contradicts D-106..D-109;
current supported question types cannot be reconciled with the accepted product contract;
production grading no longer exposes the semantics required by D-095;
production generation no longer has an authoritative selected-scope / DRAFT-only boundary;
reusing the current production seam would require a material architecture/API/schema change.
```

Minor file/signature differences are NOT PM decisions. Adapt evaluation code to the actual accepted seam.

---

# 5. Production Provider Identity

The production V0 model identity remains:

```text
provider = OpenAI API
API = Responses API
model = gpt-5.4-mini-2026-03-17
reasoning_effort = none
temperature = 0.2
request_timeout_seconds = 60
application retry max = 1
SDK retries = 0
store = false
model input limit = 400000
```

Track-A grading max output remains the accepted grading/LLM configuration discovered in repository preflight.

Track-B generation uses:

```text
AI_GENERATION_MAX_OUTPUT_TOKENS = 4000
question_count allowed by production = 1..10
Step-7.7 dataset question_count = 3
```

Do not silently replace the dated model with a floating/newer alias.

OFFLINE tests MUST NOT call OpenAI.

---

# 6. Evaluation Module Structure

Prefer one Step-7.7 package with separate track submodules, for example:

```text
backend/app/evaluation/step77/
├── __init__.py
├── common/
│   ├── artifacts.py
│   ├── hashing.py
│   ├── replay.py
│   └── contracts.py
├── grading/
│   ├── contracts.py
│   ├── dataset.py
│   ├── annotations.py
│   ├── evaluator.py
│   ├── metrics.py
│   ├── runner.py
│   └── artifacts.py
└── assessment_generation/
    ├── contracts.py
    ├── dataset.py
    ├── annotations.py
    ├── evaluator.py
    ├── runner.py
    └── artifacts.py
```

Exact file grouping may follow repository conventions.

Do NOT force Track A and Track B into one case/result schema.

---

# 7. Track A — Dataset Contract

## 7.1 Dataset identity

Create a versioned, repo-controlled grading evaluation dataset.

Suggested logical path:

```text
evaluation/datasets/ai_grading/v0.1.0/
├── development.jsonl
├── holdout.jsonl
└── manifest.json
```

Do NOT reuse the Step-7.2 RAG dataset.

## 7.2 Frozen counts — D-108

Exactly:

```text
60 total
45 DEVELOPMENT
15 HOLDOUT
```

Coverage matrix:

```text
3 free-form question types
×
5 semantic classes
×
4 cases
=
60
```

Each `(question_type, semantic_class)` cell:

```text
3 DEVELOPMENT
1 HOLDOUT
```

Question types:

```text
translate_vi_zh
translate_zh_vi
sentence_writing
```

Semantic classes:

```text
CLEAR_CORRECT
CLEAR_INCORRECT
PARTIAL
AMBIGUOUS
EXPECTED_UNCERTAIN
```

## 7.3 GradingEvaluationCase

Freeze an evaluation-owned schema equivalent to:

```text
GradingEvaluationCase
├── case_id
├── schema_version = "1.0.0"
├── dataset_version
├── split = DEVELOPMENT | HOLDOUT
├── question_type
├── semantic_class
├── question_content
├── reference_answer
├── rubric?
├── max_points
├── learner_answer
├── lesson_context?        # only if actual production grader input supports it
├── production_input_metadata?
├── annotation_ref
└── review_status = APPROVED | DRAFT
```

Rules:

```text
case_id stable and unique
max_points > 0
learner_answer uses the actual production free-form answer shape
question/reference/rubric represent actual production grader inputs
no human semantic label is serialized into provider input
```

If actual production input requires another stable field, add only the minimum needed to construct the exact production request.

Do NOT add RAG context or retrieved evidence.

## 7.4 Dataset authoring under offline mode

The current offline task may create:

```text
60 case fixtures
+
60 DRAFT human annotation templates
```

It MUST NOT fabricate authoritative human decisions.

Human semantic fields in DRAFT annotations may be null/unset.

Dataset validators must prove exact D-108 counts and cell distribution.

---

# 8. Track A — Human Annotation Contract

Suggested path:

```text
evaluation/annotations/ai_grading/v0.1.0/
├── manifest.json
└── annotations.jsonl
```

Annotation identity:

```text
annotation_version = "ai-grading-human/v0.1.0"
rubric_version     = "ai-grading-rubric/v1"
```

Freeze schema equivalent to:

```text
GradingHumanAnnotation
├── case_id
├── annotation_version
├── rubric_version
├── expected_grading_status = GRADED | UNCERTAIN | null
├── human_score              = decimal | null
├── human_is_correct         = bool | null          # derived/validated
├── normalized_state         = UNCERTAIN
│                            | ZERO_CREDIT
│                            | PARTIAL_CREDIT
│                            | FULL_CREDIT
│                            | null                 # derived/validated
├── concise_rationale?
├── reviewer_id?             # opaque/non-secret label only
├── reviewed_at?
├── adjudication_note?
└── review_status = DRAFT
                  | NEEDS_ADJUDICATION
                  | HUMAN_APPROVED
```

Invariants:

```text
DRAFT
→ semantic fields may be incomplete

NEEDS_ADJUDICATION
→ may contain provisional reviewer values
→ denominator-ineligible

HUMAN_APPROVED + expected_grading_status=UNCERTAIN
→ human_score = null
→ human_is_correct = null
→ normalized_state = UNCERTAIN

HUMAN_APPROVED + expected_grading_status=GRADED
→ human_score required
→ 0 <= human_score <= case.max_points
→ human_is_correct = (human_score == case.max_points)
→ normalized_state derived by D-106
```

Codex, fake providers and LLMs MUST NEVER transition an annotation to HUMAN_APPROVED.

No separate calibration subset exists.

---

# 9. Track A — D-106 Normalization

Use one deterministic normalization helper for BOTH human and model semantic results.

```text
UNCERTAIN
→ UNCERTAIN

GRADED + score == 0
→ ZERO_CREDIT

GRADED + 0 < score < max_points
→ PARTIAL_CREDIT

GRADED + score == max_points
→ FULL_CREDIT
```

Reject impossible semantic results, including:

```text
GRADED with null score
GRADED score < 0
GRADED score > max_points
UNCERTAIN with non-null score
provider-supplied is_correct inconsistent with backend D-095 semantics
```

The production backend remains authoritative for `is_correct`.

Raw score is diagnostic only and is NOT the primary agreement unit.

---

# 10. Track A — Execution Result

Freeze an evaluation result equivalent to:

```text
GradingExecutionResult
├── execution_id
├── run_id
├── case_id
├── split
├── question_type
├── semantic_class
├── provider_mode = FAKE | REPLAY | REAL
├── request_sha256
├── provider_response_sha256?
├── grading_status = GRADED | UNCERTAIN | null
├── score?
├── is_correct?
├── normalized_state?
├── feedback?
├── technical_status = SUCCESS | TECHNICAL_FAILURE
├── technical_error_code?
├── provider/model/config identity
├── usage?
├── latency_ms?
├── replay_origin?
└── annotation_review_status
```

Technical failure row:

```text
technical_status = TECHNICAL_FAILURE
grading_status = null
score = null
normalized_state = null
```

Never coerce technical failure to `UNCERTAIN` or `ZERO_CREDIT`.

---

# 11. Track A — D-107 Accounting

## 11.1 Semantic denominator

For an official semantic comparison:

```text
semantic_denominator_eligible(case) =
    human_annotation.review_status == HUMAN_APPROVED
    AND model technical_status == SUCCESS
    AND model grading_status in {GRADED, UNCERTAIN}
```

```text
semantic_denominator_count =
count(semantic_denominator_eligible cases)
```

`DRAFT` and `NEEDS_ADJUDICATION` are denominator-ineligible.

Technical failures are denominator-ineligible.

## 11.2 Agreement

For denominator-eligible cases:

```text
agreement =
human.normalized_state == model.normalized_state
```

```text
agreement_count =
count(agreement == true)
```

```text
agreement_rate =
agreement_count / semantic_denominator_count
```

If denominator is zero:

```text
agreement_rate = null
launch_target_status = UNAVAILABLE
```

Frozen launch target:

```text
agreement_rate >= 0.95
```

Do not apply the target to offline fake output.

## 11.3 Over-abstention

```text
over_abstention =
human expected_grading_status == GRADED
AND
model grading_status == UNCERTAIN
```

```text
over_abstention_count =
count(over_abstention)
```

```text
over_abstention_rate =
over_abstention_count / semantic_denominator_count
```

No threshold.

## 11.4 False confidence

D-107 exact semantics:

```text
FALSE_CONFIDENT when:

human UNCERTAIN + model GRADED

OR

human GRADED + model GRADED
AND
human.normalized_state != model.normalized_state
```

```text
false_confident_count =
count(FALSE_CONFIDENT)
```

```text
false_confident_rate =
false_confident_count / semantic_denominator_count
```

No new threshold.

## 11.5 Model uncertainty

For denominator-eligible cases:

```text
model_uncertainty_count =
count(model grading_status == UNCERTAIN)
```

```text
model_uncertainty_rate =
model_uncertainty_count / semantic_denominator_count
```

No threshold.

## 11.6 Technical failures

Across all executed Track-A cases, independent of human approval:

```text
executed_case_count =
count(cases with an attempted production grading execution)
```

```text
technical_failure_count =
count(technical_status == TECHNICAL_FAILURE)
```

```text
technical_failure_rate =
technical_failure_count / executed_case_count
```

If no cases executed, rate is null.

Technical failure rate is a diagnostic, not a replacement for semantic agreement.

## 11.7 Diagnostics

Allowed without new release gates:

```text
agreement by question_type
agreement by semantic_class
4x4 normalized-state confusion matrix
score distribution
raw/normalized score error where meaningful
technical failures by error code
```

If reporting score error across varying max_points, prefer normalized score diagnostics in addition to raw-point diagnostics.

No diagnostic receives a new pass threshold in Step 7.7.

---

# 12. Track A — Technical Failure Semantics

Preserve production typed failures.

At minimum distinguish in artifacts where production exposes them:

```text
provider timeout
provider auth/unavailable
provider transport failure
malformed structured output
schema-invalid structured output
input/budget validation failure
other typed production grading failure
```

Do not replace production error types with evaluation-only generic exceptions if the exact typed error is available.

Evaluation behavior:

```text
technical failure
→ technical_status = TECHNICAL_FAILURE
→ semantic fields null
→ excluded from semantic denominator
→ counted in technical metrics
```

Assessment-attempt business semantics remain owned by the production submission service.

---

# 13. Track B — Dataset Contract

## 13.1 Dataset identity

Suggested path:

```text
evaluation/datasets/assessment_generation/v0.1.0/
├── development.jsonl
├── holdout.jsonl
└── manifest.json
```

## 13.2 Frozen D-108 counts

Exactly:

```text
16 request cases
12 DEVELOPMENT
4 HOLDOUT

8 LESSON_EXERCISE
8 PERIODIC_TEST

question_count = 3 for every case
```

Suite-level coverage:

```text
EASY
MEDIUM
HARD

AND

every production-supported question type discovered in repository preflight
```

Prior accepted production snapshot supported equivalents of:

```text
multiple_choice
fill_blank
matching
reorder_sentence
translate_vi_zh
translate_zh_vi
sentence_writing
```

Repository preflight must confirm the actual current enum.

## 13.3 GenerationEvaluationCase

Freeze schema equivalent to:

```text
GenerationEvaluationCase
├── case_id
├── schema_version = "1.0.0"
├── dataset_version
├── split = DEVELOPMENT | HOLDOUT
├── generation_kind = LESSON_EXERCISE | PERIODIC_TEST
├── lesson_id?               # Lesson exercise
├── lesson_ids[]             # Periodic test
├── vocabulary_ids[]         # Periodic test
├── grammar_ids[]            # Periodic test
├── question_count = 3
├── allowed_question_types[]
├── difficulty = EASY | MEDIUM | HARD
├── optional title/settings supported by production?
├── expected_policy_constraints
├── fixture_scope_identity
└── review_status
```

Validation:

```text
LESSON_EXERCISE
→ exactly one authoritative lesson_id
→ no Document/RAG/web scope

PERIODIC_TEST
→ uses canonical selected Lesson/Vocabulary/Grammar IDs
→ no Document/RAG/web scope
```

Case data must be sufficient to materialize the exact production scope.

---

# 14. Track B — Production-Shaped Execution

Required flow:

```text
GenerationEvaluationCase
→ production request schema
→ production scope materializer/loader
→ MaterializedGenerationScope
→ production generation prompt/service
→ provider seam
→ production structured schema validation
→ production validate/map/domain validation
→ production persistence transaction
→ Assessment + Question rows
→ evaluation observation/readback
```

Evaluation must NOT:

```text
inject a separately invented scope validator in front of production;
skip production domain validation;
construct a fake Assessment/Question lifecycle outside the real service;
auto-publish;
```

OFFLINE mode replaces only the paid provider network using a deterministic fake/replay behind the existing provider protocol.

---

# 15. Track B — Result / Trace Contract

Freeze a result equivalent to:

```text
AssessmentGenerationExecutionResult
├── execution_id
├── step77_run_id
├── generation_case_id
├── split
├── generation_kind
├── provider_mode = FAKE | REPLAY | REAL
├── request_sha256
├── materialized_scope_sha256
├── provider_response_sha256?
├── generated_output_sha256?
├── generated_draft_sha256?
├── generated_questions[]
│   ├── question_index
│   ├── persisted_question_id?
│   ├── question_type
│   ├── question_sha256
│   └── source_refs[]
├── persisted_assessment_id?
├── persisted_assessment_status?
├── persisted_question_count
├── schema_valid
├── scope_adherent
├── supported_question_types_valid
├── source_refs_valid
├── requested_count_valid
├── draft_lifecycle_valid
├── atomic_persistence_valid
├── technical_ok
├── technical_error_code?
├── critical_failures[]
├── human_review_complete
├── generation_case_status
└── generation_case_pass = true | false | null
```

Do not expose secret provider fields.

---

# 16. Track B — Deterministic Evaluation Checks

Reuse production validators whenever possible.

## 16.1 schema_valid

```text
true
only if provider output satisfies the exact production structured schema/parser contract
```

Do NOT build a looser second schema.

Malformed/schema-invalid generated model content:

```text
→ schema_valid = false
→ SCHEMA_INVALID
```

This is a generated-content contract failure, not automatically an infrastructure outage.

Unexpected parser/runtime exception may still be technical according to the production typed error.

## 16.2 scope_adherent

```text
true
only if every generated dependency/reference remains within the authoritative
MaterializedGenerationScope
and production domain validation passes
```

No Documents/RAG/web.

## 16.3 supported_question_types_valid

```text
true
only if every generated question:
- uses a production-supported question type; and
- is allowed by the request's allowed_question_types
```

## 16.4 source_refs_valid

Use production source-ref semantics.

Prior accepted V0 references include equivalents of:

```text
vocab:<UUID>
grammar:<UUID>
```

The evaluator must validate against actual current production representation.

No invented source type.

## 16.5 requested_count_valid

Step-7.7 cases freeze:

```text
question_count = 3
```

Therefore:

```text
requested_count_valid =
exactly 3 valid generated questions returned/persisted
```

## 16.6 draft_lifecycle_valid

Success requires:

```text
persisted Assessment.status == DRAFT
AND
no automatic REVIEW/APPROVED/PUBLISHED transition
```

## 16.7 atomic_persistence_valid

Successful generation:

```text
Assessment + expected Question rows persist as one valid DRAFT result
```

Any provider/schema/domain/persistence failure:

```text
must not leave a half-valid generated Assessment/Question set
must not publish anything
```

Verify actual PostgreSQL state when DB integration is available.

## 16.8 technical_ok

Technical provider/persistence/runtime failure:

```text
technical_ok = false
```

Generated-content policy/schema failures remain represented by their deterministic checks/critical failures and are not silently reclassified as infrastructure failure.

---

# 17. Track B — Critical Failures

Canonical Step-7.7 evaluation names:

```text
SCHEMA_INVALID
OUT_OF_SCOPE_GENERATION
UNSUPPORTED_QUESTION_TYPE
ANSWER_REFERENCE_INCONSISTENT
UNANSWERABLE_QUESTION
AUTO_PUBLISH_VIOLATION
PARTIAL_PERSISTENCE_ON_FAILURE
```

Before implementation, map to an existing repository canonical error name if an EXACT equivalent already exists.

Do not create duplicate synonyms.

Classification:

```text
SCHEMA_INVALID
→ deterministic

OUT_OF_SCOPE_GENERATION
→ deterministic

UNSUPPORTED_QUESTION_TYPE
→ deterministic

AUTO_PUBLISH_VIOLATION
→ deterministic persisted-state invariant

PARTIAL_PERSISTENCE_ON_FAILURE
→ deterministic persisted-state invariant

ANSWER_REFERENCE_INCONSISTENT
→ human-derived from D-109 annotation

UNANSWERABLE_QUESTION
→ human-derived from D-109 annotation
```

Every critical failure independently blocks a passing Track-B generation case.

No numeric generation quality threshold exists.

---

# 18. Track B — D-109 Human Annotation Contract

Suggested path:

```text
evaluation/annotations/assessment_generation/v0.1.0/
├── manifest.json
└── questions.jsonl
```

Identity:

```text
annotation_version = "assessment-generation-human/v0.1.0"
rubric_version     = "assessment-generation-rubric/v1"
```

Freeze per-question schema:

```text
GenerationQuestionAnnotation
├── step77_run_id?
├── generation_case_id
├── execution_id?
├── question_index
├── persisted_question_id?
├── generated_draft_sha256?
├── generated_question_sha256?
├── materialized_scope_sha256?
├── generation_output_sha256?
├── cases_artifact_sha256?
├── annotation_version
├── rubric_version
├── answer_reference_consistency
│   = CONSISTENT | INCONSISTENT | null
├── answerability
│   = ANSWERABLE | UNANSWERABLE | null
├── concise_rationale?
├── reviewer_id?
├── reviewed_at?
├── adjudication_note?
└── review_status
    = DRAFT | NEEDS_ADJUDICATION | HUMAN_APPROVED
```

## 18.1 Offline DRAFT template

Current OFFLINE implementation is before an official real-provider generation run.

Therefore source-controlled DRAFT templates MAY be unbound:

```text
step77_run_id = null
execution_id = null
generated_draft_sha256 = null
generated_question_sha256 = null
materialized_scope_sha256 = null
generation_output_sha256 = null
cases_artifact_sha256 = null
semantic labels may be null
review_status = DRAFT
```

Do NOT fabricate official run IDs/hashes.

## 18.2 NEEDS_ADJUDICATION / HUMAN_APPROVED

These statuses require exact bindings:

```text
step77_run_id
generation_case_id
execution_id
question_index
generated_draft_sha256
generated_question_sha256
materialized_scope_sha256
generation_output_sha256
cases_artifact_sha256
annotation_version
rubric_version
```

If the persisted question has a stable ID, also bind it.

Before accepting HUMAN_APPROVED:

```text
recompute exact question hash
recompute exact draft/output hash
recompute exact materialized-scope hash
verify step77_run_id
verify generation_case_id
verify execution_id
verify question index/id
verify cases.jsonl artifact hash
```

Any mismatch:

```text
→ HUMAN ANNOTATION STALE / INVALID
→ fail closed
```

Fake/offline provider output must never become official human evidence.

---

# 19. Track B — Human Semantic Checks

For each generated question:

```text
answer_reference_consistency =
CONSISTENT | INCONSISTENT
```

Meaning:

```text
CONSISTENT
→ the canonical/reference answer is semantically correct for the generated question
```

and:

```text
answerability =
ANSWERABLE | UNANSWERABLE
```

Meaning:

```text
ANSWERABLE
→ a learner can reasonably answer the question from the question itself
  plus the allowed selected curriculum context represented by the generation scope
```

No extra LLM judge is used.

DRAFT/NEEDS_ADJUDICATION values are not authoritative semantic ground truth.

---

# 20. Track B — Generation Case Status / Pass

Use exact ordering so deferred human review is never fabricated into PASS.

Suggested statuses:

```text
TECHNICAL_FAILURE
DETERMINISTIC_FAILURE
DEFERRED_HUMAN_REVIEW
HUMAN_SEMANTIC_FAILURE
PASS
```

Rules:

## 20.1 Technical failure

```text
technical_ok == false
→ generation_case_status = TECHNICAL_FAILURE
→ generation_case_pass = false
```

## 20.2 Deterministic failure

If any deterministic check fails or deterministic critical exists:

```text
→ generation_case_status = DETERMINISTIC_FAILURE
→ generation_case_pass = false
```

## 20.3 Human review unavailable

If deterministic checks pass but ANY generated question lacks valid exact-bound HUMAN_APPROVED annotation:

```text
→ generation_case_status = DEFERRED_HUMAN_REVIEW
→ generation_case_pass = null
```

This is the expected official semantic state before real human review.

## 20.4 Human semantic failure

If all required question annotations are exact-bound HUMAN_APPROVED and any has:

```text
answer_reference_consistency = INCONSISTENT
or
answerability = UNANSWERABLE
```

then:

```text
→ add matching critical failure(s)
→ generation_case_status = HUMAN_SEMANTIC_FAILURE
→ generation_case_pass = false
```

## 20.5 Pass

Only when ALL are true:

```text
schema_valid
scope_adherent
supported_question_types_valid
source_refs_valid
requested_count_valid
draft_lifecycle_valid
atomic_persistence_valid
technical_ok
all generated questions have valid exact-bound HUMAN_APPROVED annotations
all answer/reference labels = CONSISTENT
all answerability labels = ANSWERABLE
critical_failures == []
```

then:

```text
generation_case_status = PASS
generation_case_pass = true
```

Offline fake artifacts MUST remain:

```text
official_eligible = false
```

even if synthetic in-test annotations are used to exercise PASS logic.

---

# 21. Zero Auto-Publish / Atomicity Verification

Use actual production persistence boundaries.

## Success path

Query committed DB state and prove:

```text
Assessment.status == DRAFT
persisted Question count == 3
every Question belongs to that Assessment
no automatic REVIEW/APPROVED/PUBLISHED transition occurred
```

## Failure paths

For provider / schema / scope / domain / persistence failure:

```text
no published assessment
no half-valid generated question set
no hidden partial draft accepted as success
production transaction semantics preserved
```

PostgreSQL-backed tests may explicitly skip only when the repository's dedicated test DB configuration is unavailable.

Do NOT substitute SQLite just to make the tests pass.

---

# 22. Offline vs Runtime Boundary

Current authorization:

```text
OFFLINE IMPLEMENTATION ONLY
```

## REAL in offline tests

```text
production AI grading service
grading prompt / normalization / structured parser
production assessment-generation service
generation prompt
scope materializer
production generation schemas/validators
production domain validation
persistence/DRAFT lifecycle when safe test DB is available
evaluation contracts
metric formulas
hashing
artifact writers
replay identity logic
```

## FAKE / REPLAY

```text
paid LLM provider network only
```

No OpenAI call.

No fake/replay result may be marked official.

Official target evaluation later requires:

```text
REAL provider outputs
+
valid HUMAN_APPROVED grading annotations
```

Track-B official semantic evaluation later requires:

```text
REAL generated outputs
+
exact-bound HUMAN_APPROVED per-question annotations
```

---

# 23. Provider Replay / Cache Contract

Do NOT add Redis or another external cache service.

Use repo/runtime files under evaluation artifacts.

## 23.1 Canonical request identity

Create a canonical JSON payload containing:

```text
track
normalized production input
provider
model
prompt identity/version/hash
structured-schema identity/version
temperature
max_output_tokens
reasoning/config
```

Canonical serialization:

```text
UTF-8
sorted keys
compact separators
```

Then:

```text
request_sha256 = SHA256(canonical_json_bytes)
```

Never include API key or secret values.

## 23.2 Replay record

Freeze a record equivalent to:

```text
ProviderReplayRecord
├── replay_schema_version
├── track
├── request_sha256
├── response_sha256
├── provider
├── model
├── generation_config
├── prompt_identity
├── structured_schema_identity
├── normalized_input_sha256
├── sanitized_provider_metadata
├── parsed_result
├── finish/status metadata?
├── input_tokens?
├── output_tokens?
├── total_tokens?
├── latency_ms?
├── provider_request_id?
├── origin_execution_mode
├── origin_run_id?
└── created_at?
```

Do NOT persist:

```text
API keys
authorization headers
hidden chain-of-thought
unnecessary learner secrets
raw stack traces
```

## 23.3 Modes

```text
FAKE
REPLAY
REAL
```

Identity mismatch:

```text
→ reject replay as stale
```

`FAKE`:

```text
→ never official
```

`REPLAY`:

```text
→ may reproduce evaluator behavior from an earlier REAL output
→ must retain provenance to the origin REAL run
→ cannot establish a new provider-performance baseline
```

---

# 24. Artifact Layout

Use separate track directories:

```text
evaluation/runs/<step77_run_id>/
├── grading/
│   ├── manifest.json
│   ├── cases.jsonl
│   └── summary.json
│
└── assessment_generation/
    ├── manifest.json
    ├── cases.jsonl
    └── summary.json
```

Default tests SHOULD write to temp directories, not create fake official run artifacts.

---

# 25. Track A Artifact Schemas

## 25.1 grading/manifest.json

At minimum:

```text
run_id
track = "grading"
timestamp
execution_mode = OFFLINE_TEST | OFFICIAL_RUNTIME
official_eligible
dataset_version
dataset_schema_version
dataset_case_count
development_case_count
holdout_case_count
code_commit?                  # null/unavailable if no .git
provider_mode = FAKE | REPLAY | REAL
provider
model
generation_config
prompt_version/hash
structured_schema_version
evaluator_version
agreement_policy_version      # includes D-106/D-107 identity
annotation_version
rubric_version
replay_origin?
runtime_api_calls
```

Offline:

```text
execution_mode = OFFLINE_TEST
official_eligible = false
runtime_api_calls = 0
```

## 25.2 grading/cases.jsonl

Per execution:

```text
GradingExecutionResult
+
human annotation status
+
human normalized state when HUMAN_APPROVED
+
agreement?
+
false_confident?
+
over_abstention?
```

Do not copy unresolved human labels into official semantic values.

## 25.3 grading/summary.json

At minimum:

```text
planned_case_count
executed_case_count

technical_failure_count
technical_failure_rate
technical_failures_by_code

human_approved_count
draft_count
needs_adjudication_count

semantic_denominator_count
agreement_count
agreement_rate
launch_target = 0.95
launch_target_status =
  PASS | FAIL | UNAVAILABLE | OFFLINE_NOT_OFFICIAL

false_confident_count
false_confident_rate

over_abstention_count
over_abstention_rate

model_uncertainty_count
model_uncertainty_rate

agreement_by_question_type
agreement_by_semantic_class
normalized_state_confusion_matrix
optional score diagnostics
```

Rules:

```text
OFFLINE_TEST
→ launch_target_status = OFFLINE_NOT_OFFICIAL

no valid semantic denominator
→ agreement_rate = null
→ launch target unavailable
```

---

# 26. Track B Artifact Schemas

## 26.1 assessment_generation/manifest.json

At minimum:

```text
run_id
track = "assessment_generation"
timestamp
execution_mode
official_eligible
dataset_version
dataset_schema_version
dataset_case_count = 16
development_case_count = 12
holdout_case_count = 4
lesson_exercise_count = 8
periodic_test_count = 8
question_count_per_case = 3
production_supported_question_types[]
difficulty_coverage[]
code_commit?
provider_mode
provider
model
generation_config
prompt version/hash
structured schema identity
scope/domain validator identity
evaluator version
annotation version
rubric version
replay origin?
runtime_api_calls
```

## 26.2 assessment_generation/cases.jsonl

Per execution:

```text
AssessmentGenerationExecutionResult
```

Include sufficient sanitized diagnostic data to reproduce:

```text
selected scope identity/hash
generated question identities/hashes/types/source_refs
deterministic check results
persisted lifecycle state
critical failures
human annotation coverage/status
case status/pass
technical error code
usage/latency when available
```

No private CoT.

## 26.3 assessment_generation/summary.json

At minimum:

```text
planned_case_count = 16
executed_case_count

counts by split
counts by generation kind
counts by difficulty
question-type coverage

technical_failure_count/rate

schema_valid_count/rate
scope_adherent_count/rate
supported_question_types_valid_count/rate
source_refs_valid_count/rate
requested_count_valid_count/rate
draft_lifecycle_valid_count/rate
atomic_persistence_valid_count/rate

critical_failure_count/rate
critical_failures_by_type

human_annotation_counts
human_review_complete_case_count
deferred_human_review_case_count

generation_case_status_counts
generation_case_pass_count
generation_case_fail_count
generation_case_pass_rate among semantically finalizable cases
```

No numeric generation-quality launch threshold.

Offline fake result:

```text
official_eligible = false
```

---

# 27. Official-Eligibility Guards

A run MUST NOT be official when any of the following is true:

```text
provider_mode == FAKE
execution_mode == OFFLINE_TEST
runtime provider identity differs from frozen production identity
dataset count/split validation fails
artifact identity validation fails
grading official evaluation lacks HUMAN_APPROVED labels
Track-B semantic evaluation lacks exact-bound HUMAN_APPROVED question annotations
```

OFFLINE implementation tests may use synthetic HUMAN_APPROVED objects in memory/temp fixtures ONLY to test evaluator branches.

They must never be written into the source-controlled official annotation package.

---

# 28. Offline Test Plan — Track A

At minimum add deterministic tests for:

## Dataset

```text
60 total
45 DEV / 15 HOLDOUT
3 types
5 semantic classes
3 DEV + 1 HOLDOUT in every cell
stable unique IDs
```

## D-106 normalization

```text
UNCERTAIN
ZERO_CREDIT
PARTIAL_CREDIT
FULL_CREDIT
invalid score/status combinations rejected
```

## D-107 transitions

```text
human UNCERTAIN + model UNCERTAIN
→ agreement

human GRADED + model UNCERTAIN
→ disagreement + over-abstention

human UNCERTAIN + model GRADED
→ disagreement + false-confident

human GRADED + model GRADED same state
→ agreement

human GRADED + model GRADED different state
→ disagreement + false-confident
```

## Denominator

```text
DRAFT excluded
NEEDS_ADJUDICATION excluded
technical failure excluded
HUMAN_APPROVED + semantic model result included
zero denominator handled without divide-by-zero
```

## Technical failure

```text
provider timeout
provider unavailable/auth failure where safely fakeable
malformed structured output
schema-invalid output
typed production grading failure
technical != UNCERTAIN
```

## Replay / artifacts

```text
request hash deterministic
config/model/prompt change invalidates replay
fake never official
artifact cross-file run identity
summary math reproducible
launch target unavailable/offline when appropriate
```

No paid calls.

---

# 29. Offline Test Plan — Track B

At minimum:

## Dataset

```text
16 total
12 DEV / 4 HOLDOUT
8 Lesson / 8 Periodic
question_count == 3
all three difficulties covered
all current production-supported question types covered
```

## Valid execution

```text
valid LESSON_EXERCISE
valid PERIODIC_TEST
production scope materialization used
production validators used
3 questions persisted
Assessment remains DRAFT
```

## Deterministic failure checks

```text
malformed/schema-invalid provider output
out-of-scope source/reference
unsupported question type
request allowed-type violation
generated count != 3
invalid source_ref
auto-publish violation detection
```

## Human evaluation logic

```text
unbound DRAFT template valid
DRAFT does not require fabricated hashes
NEEDS_ADJUDICATION missing binding rejected
HUMAN_APPROVED missing binding rejected
stale question hash rejected
stale scope hash rejected
stale cases-artifact hash rejected
wrong run/case/question identity rejected

synthetic valid HUMAN_APPROVED question labels
→ evaluator PASS branch can be exercised in temp/in-memory test only

INCONSISTENT
→ ANSWER_REFERENCE_INCONSISTENT

UNANSWERABLE
→ UNANSWERABLE_QUESTION
```

## Provider/transaction/lifecycle

With safe dedicated PostgreSQL integration when available:

```text
provider failure
→ no draft persisted

schema/domain failure
→ no partial draft

persistence failure
→ rollback
→ detect any partial persistence

success
→ DRAFT only
→ no automatic review/publish
```

DB integration tests may skip only when dedicated test DB settings are unavailable.

No SQLite substitute.

## Replay / artifact

```text
request identity deterministic
prompt/config/scope change invalidates replay
fake never official
artifact hashes reproducible
summary aggregates reproducible
```

No paid calls.

---

# 30. Dataset / Annotation Content Review

The current Codex offline task may scaffold the complete frozen case counts and DRAFT templates.

However:

```text
human labels are human ground truth
```

Therefore Codex MUST NOT write authoritative semantic values and mark them HUMAN_APPROVED.

If case authoring involves judgment-sensitive examples:

```text
case input may be scaffolded
→ annotation remains DRAFT
→ PM/Specialist/Human reviewer later reviews/adjudicates
```

Holdout details must not be used to tune production grading/generation behavior.

---

# 31. Expected Implementation Documentation

When offline implementation is complete, produce:

## A. Step Note

Must contain:

```text
Objective
Why
Mental Model
Core Knowledge
Data Flow
Key Design Decisions
Reusable approach for similar projects
Common Mistakes
Definition of Done
```

Keep it concise and reusable.

## B. Concepts Discovered

Table:

```text
Concept | Category | Step | Role / Why it matters
```

Allowed categories only:

```text
DE
AI
BOTH
SYSTEM
```

Only include concepts actually used.

## C. Tools Used

Table:

```text
Tool | Category | Step | Role / Why used
```

Only include tools actually used by implementation.

## D. Step Specification

Must reflect actual implementation and contain:

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
Interfaces / schemas
Files/components changed
Config/env
Error handling
Testing
Acceptance Criteria
Constraints / Non-goals
Open Questions
```

---

# 32. Acceptance Criteria — Offline Implementation

The offline implementation is ready for specialist review only when all applicable items pass.

## Track A

```text
[ ] exact repository grading seams documented
[ ] no production grading behavior changed
[ ] exact 60 / 45 / 15 dataset contract enforced
[ ] exact 3×5×4 cell contract enforced
[ ] 60 DRAFT annotation templates, 0 HUMAN_APPROVED
[ ] D-106 normalization implemented once and reused
[ ] D-107 exact accounting implemented
[ ] >=95% target stored but never claimed official from fake output
[ ] technical failures separated from UNCERTAIN
[ ] production grading seam exercised with fake/replay provider
[ ] replay identity implemented
[ ] grading artifacts implemented
[ ] official-eligibility guards implemented
```

## Track B

```text
[ ] exact repository generation seams documented
[ ] no production generation behavior changed
[ ] exact 16 / 12 / 4 dataset contract enforced
[ ] exact 8 Lesson / 8 Periodic enforced
[ ] question_count=3 enforced
[ ] difficulty and supported-type coverage enforced
[ ] production schema/domain/scope validators reused
[ ] deterministic checks implemented
[ ] canonical critical failures implemented without duplicate synonyms
[ ] per-question D-109 annotation schema implemented
[ ] source-controlled annotations remain DRAFT/unbound before real output
[ ] 0 HUMAN_APPROVED
[ ] case PASS cannot occur officially without exact-bound approved labels
[ ] DRAFT-only/no-auto-publish checks implemented
[ ] atomic persistence checks implemented/test-authored
[ ] replay identity implemented
[ ] generation artifacts implemented
[ ] official-eligibility guards implemented
```

## Cross-cutting

```text
[ ] no paid calls
[ ] no live external calls
[ ] no secret committed
[ ] no schema/migration changes
[ ] no Step 7.6 work
[ ] tests pass or DB-only tests explicitly skip for unavailable safe test DB
[ ] compile/import checks pass
[ ] docs/spec reflect implementation
```

---

# 33. Expected Codex Handoff

Return:

```text
Step:
7.7 — AI Grading & Content-Generation Evaluation

Status:
READY_FOR_SPECIALIST_REVIEW — OFFLINE IMPLEMENTATION
```

Include:

```text
Repository preflight:
- exact Track-A production seams
- exact Track-B production seams
- any repository/spec mismatch

What was implemented:
- Track A
- Track B
- shared replay/artifact pieces

Files created/modified

Datasets:
- Track A exact counts
- Track B exact counts
- ground truth/human approvals created? MUST be NO for HUMAN_APPROVED

Verification:
- focused tests
- DB-backed tests pass/skip reason
- compile/import
- dependency lock check if touched

Runtime:
- paid calls = 0
- live provider = 0
- official benchmark = NOT RUN
- HUMAN_APPROVED = 0

Production config modified:
NO

Schema/migration changed:
NO

Step 7.6 started:
NO

Problems/risks

Decisions needed:
NONE
or genuine blocker only

Recommended next action:
Independent specialist review
```

Do not claim Step 7.7 DONE or PM final acceptance.

---

# 34. Runtime Gates Deferred Beyond This Task

This Codex task does NOT authorize:

```text
real OpenAI grading execution
real OpenAI assessment generation benchmark
official Track-A 60-case result
official Track-B 16-request result
human approval/adjudication
launch-target acceptance
production release decision
Step 7.6
```

Those gates happen only after separate PM/runtime authorization.

---

# 35. Final Stop Rule

Codex is an implementation agent, not the project architect.

If implementation requires changing:

```text
D-106 primary agreement unit
D-107 denominator/accounting
D-108 dataset sizes/splits
D-109 human review unit
production grading behavior
production generation behavior
public API/schema
database schema
provider/model identity
runtime cost policy
```

STOP:

```text
BLOCKED — DECISION NEEDED
```

Do not invent the missing decision.

# PM Freeze Patch — Step 7.7

**Status:** PM FROZEN — CODEX-READY  
**Execution mode:** OFFLINE IMPLEMENTATION / DETERMINISTIC TEST MODE ONLY

Frozen task SHA-256:

`143b541ea0c1f568cd700123cb1259f5c333c06aab35a6a6d8e172d345ffa380`

This PM Freeze Patch overrides any conflicting earlier `PRE-FREEZE`,
`DRAFT FOR PM REVIEW`, or non-authorization wording in this task.

## Clarifications

1. `GradingEvaluationCase.review_status` is dataset-case curation state only.
   It is distinct from `GradingHumanAnnotation.review_status`.
   Only `GradingHumanAnnotation = HUMAN_APPROVED` controls D-107 semantic
   denominator eligibility. Dataset-case `APPROVED` must never be interpreted
   as human semantic approval.

2. Track-A launch-target status precedence:

   ```text
   execution_mode = OFFLINE_TEST
   → launch_target_status = OFFLINE_NOT_OFFICIAL
   ```

   `agreement_rate` may still be `null` when the semantic denominator is zero.

   For an authorized official runtime evaluation:

   ```text
   semantic_denominator_count = 0
   → launch_target_status = UNAVAILABLE
   ```

3. Track-B summary pass rate:

   ```text
   generation_case_pass_rate
   =
   count(generation_case_pass == true)
   /
   count(generation_case_pass is true or false)
   ```

   `DEFERRED_HUMAN_REVIEW` cases have `generation_case_pass = null` and are
   excluded from this denominator.

4. `runtime_api_calls` in Step-7.7 artifacts means external paid LLM-provider
   network calls. In this frozen offline task:

   ```text
   runtime_api_calls = 0
   ```

   Internal application-service calls, PostgreSQL access, and fake/replay
   provider invocations are not counted as paid runtime API calls.

## Frozen Scope

D-106, D-107, D-108 and D-109 remain unchanged.

No authorization for:

- paid OpenAI calls;
- live external calls;
- official benchmark execution;
- creation of HUMAN_APPROVED annotations;
- production prompt/model tuning;
- production grading/generation behavior changes;
- schema/migration changes;
- Step 7.6 work.

Expected Codex terminal status:

`READY_FOR_SPECIALIST_REVIEW — OFFLINE IMPLEMENTATION`

or, only for a genuinely new material blocker:

`BLOCKED — DECISION NEEDED`

Codex must not claim Step 7.7 DONE or PM final acceptance.
