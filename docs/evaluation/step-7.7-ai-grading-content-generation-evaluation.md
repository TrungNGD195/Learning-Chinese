# Step 7.7 — AI Grading & Content-Generation Evaluation

## Objective

Provide offline-only evaluation foundations for the accepted Step 6.11 free-form grader and Step 6.12 assessment draft generator. Preserve frozen D-106 through D-109 metrics, dataset sizes, and human review boundaries.

## Why

The evaluation must distinguish semantic grading outcomes from technical failures and must keep generated-question semantic review at the individual-question level. No fake output is official evidence.

## Mental Model

Track A sends the same production question/answer objects through `LLMGradingService`; only `StructuredGradingProvider` is replaced by a deterministic test provider. Track B calls the existing Admin generation application service; only its provider factory is replaced. Production prompts, schemas, scope materialization, domain validation, and DRAFT persistence remain in use.

## Core Knowledge

- D-106 normalizes `UNCERTAIN`, `ZERO_CREDIT`, `PARTIAL_CREDIT`, and `FULL_CREDIT`; raw score remains diagnostic.
- D-107 counts only exact-bound `HUMAN_APPROVED` annotations and successful model outputs in the semantic denominator. Offline runs always report `OFFLINE_NOT_OFFICIAL`.
- D-108 fixes Track A at 60 cases (45/15; 3 question types × 5 semantic classes × 4) and Track B at 16 requests (12/4; 8 Lesson Exercise and 8 Periodic Test).
- D-109 reviews each generated question and binds non-draft annotations to the SHA-256 of the exact persisted `cases.jsonl` bytes. The writer writes the file, reads it back, hashes those persisted bytes, and records that digest. The canonical frozen-content projection remains a separate comparison for immutable generated content; it is not artifact identity. Whitespace, newline, key-order, or any other byte change makes an existing annotation binding stale.
- Reviewed annotation and rubric versions must match the source-controlled annotation manifest for the appropriate track. DRAFT templates remain unbound, but their declared versions must still match the current annotation contract.
- Official execution eligibility recomputes every request hash from the frozen dataset case and run configuration. Track B independently reconstructs the selected curriculum scope from the controlled fixture and verifies both its canonical content and scope hash; row-provided hashes alone are insufficient.
- All authored source annotations remain `DRAFT`; this implementation creates no human ground truth.

## Data Flow

Track A: case JSONL → production-shaped question and `{text}` answer → `LLMGradingService.grade` → normalized result → D-107 summary → offline artifacts.

Track B: generation case → production discriminated request → existing `generate_assessment_draft` → production curriculum scope materializer → `AssessmentGenerationService` → production output/schema/source-ref/domain validation → `persist_generated_assessment_draft` transaction → DRAFT readback → deterministic checks → deferred human review → offline artifacts.

## Key Design Decisions

- `GradingEvaluationCase.semantic_class` is evaluator metadata and is never passed to the production grader.
- Dataset case curation status is separate from annotation approval.
- Fake providers are injected at the existing protocols; production adapters are not called.
- Generation fixture IDs are stable UUIDv5 values and seed only into the guarded dedicated test DB.
- Replay records require REAL-origin provenance and exact request identity. Grading artifacts bind `case_id`; generation artifacts bind `generation_case_id`. Both verify response and parsed-result hashes. Official eligibility also recomputes dataset-bound requests, exact Track-B scope identity, and frozen annotation/rubric versions. Fake/replay runs cannot become official.
- Provider mode is explicit evaluation-runner context. Production providers need not expose evaluation-only `mode` or `last_result` attributes; provider request IDs and usage metadata remain optional.
- No production code, settings, schema, migration, dependency, provider, model, or API contract changed.

## Reusable approach for similar projects

Keep evaluation contracts and fixtures under a versioned evaluation package, replace only the paid provider boundary, hash canonical normalized requests, and keep human annotations separately versioned and exactly bound to generated outputs.

## Common Mistakes

- Treating `UNCERTAIN` as a technical failure or zero score.
- Counting DRAFT or adjudication labels in agreement metrics.
- Passing semantic class metadata into the model request.
- Reimplementing generation scope or validation inside the evaluator.
- Treating a canonical content projection as the byte identity of a persisted artifact.
- Treating a non-empty execution hash as proof that the request matches its dataset case.
- Treating fake output or unbound labels as official evidence.
- Reusing RAG evaluation data for grading or assessment generation.

## Definition of Done

- The frozen datasets and annotations structurally validate at exact counts and splits.
- Offline runner artifacts are hashed and marked ineligible.
- Focused tests cover D-106/D-107, request identity/replay, exact persisted-byte D-109 binding, annotation/rubric versions, dataset-bound Track-A requests, Track-B requests/scopes, production seam usage, DRAFT lifecycle, and critical failures.
- PostgreSQL integration either passes against `chinese_learning_test` or skips with the explicit safe-database-unavailable reason. SQLite is never used.
- No Step 7.6, paid provider call, external request, or human approval is performed.

## Repository Preflight — Exact Production Seams

### Track A — Step 6.11

| Contract | Current repository seam |
|---|---|
| AIGrader protocol | `backend/app/exercise/grading.py`: `AIGrader.grade(*, question: dict, answer: dict) -> GradeResult` |
| Application grading service | `backend/app/ai/grading/service.py`: `LLMGradingService(provider: StructuredGradingProvider, settings: Settings).grade(*, question, answer)` |
| Prompt builder | `backend/app/ai/grading/prompt.py`: `build_grading_prompt(...) -> (system_content, user_content)`; version `v1` |
| Structured schema/parser | `backend/app/ai/grading/schemas.py`: `StructuredGradingOutput`, `StructuredGradingRequest`, `StructuredGradingProviderResult`; OpenAI adapter parses the schema |
| Provider protocol/adapter | `backend/app/ai/grading/provider.py`: `StructuredGradingProvider.grade(request)`; production adapter `OpenAIResponsesGradingProvider` |
| Result/status | `GradeResult(grading_status, score, is_correct, feedback)`; provider enum `GRADED` / `UNCERTAIN` |
| Technical errors | `backend/app/ai/grading/errors.py`: `StructuredGradingProviderError` with typed `AI_GRADING_*` codes; application boundary maps failure to `GradingUnavailable` |
| Model/config | `backend/app/core/config.py`: `llm_model`, temperature, output budget, reasoning effort, timeout, retry, input limit; factory in `backend/app/ai/grading/factory.py` |
| Submission integration | `backend/app/exercise/service.py`: `submit_attempt(session, user_id, attempt_id, body, ai_grader=None)` builds question `{type,prompt,reference_answer,rubric,points}` and answer `{text}` |
| Persistence/status | `AttemptAnswer` stores status/score/correctness/feedback; `AssessmentAttempt` transitions to `GRADING_FAILED` and public error `AI_GRADING_UNAVAILABLE` on grading failure |

### Track B — Step 6.12

| Contract | Current repository seam |
|---|---|
| Request DTOs | `backend/app/ai/generation/schemas.py`: `LessonExerciseGenerationRequest`, `PeriodicTestGenerationRequest`, discriminated `AssessmentGenerationRequest` |
| Generation service/prompt | `AssessmentGenerationService.generate(request, scope)` and `build_generation_prompt(scope, request)` |
| Output schema | `StructuredAssessmentGenerationOutput` and seven frozen generated-question variants in the same schemas module |
| Materialized scope | `MaterializedGenerationScope` in `backend/app/ai/generation/schemas.py` |
| Validation/map | `validate_and_map_output(result, *, request, scope, domain_validator)` in `backend/app/ai/generation/service.py` |
| Scope loader | `backend/app/curriculum/service.py`: `materialize_generation_scope(session, request)`; repositories load selected Lesson/Vocabulary/Grammar entities and canonical source refs |
| Provider/errors | `StructuredAssessmentGenerationProvider.generate(request)`; `OpenAIResponsesAssessmentGenerationProvider`; typed errors in `backend/app/ai/generation/errors.py` |
| Admin application/router | `backend/app/admin/service.py`: `generate_assessment_draft(session, request)`; route in `backend/app/admin/router.py` |
| Persistence boundary | `exercise_service.persist_generated_assessment_draft(...)` commits Assessment and all Questions atomically as DRAFT |
| Lifecycle/source refs | Assessment status is `DRAFT`; generated `source_refs` are validated against materialized scope and not persisted |
| Supported types/config | `multiple_choice`, `fill_blank`, `matching`, `reorder_sentence`, `translate_vi_zh`, `translate_zh_vi`, `sentence_writing`; model/config in `Settings` |

No material conflict with D-106..D-109 was observed. Repository metadata has no usable Git repository identity in this workspace; manifests record `code_commit: null`.

## Files / Components

Evaluation implementation: `backend/app/evaluation/step77/`.
Datasets/annotations/fixtures: `evaluation/datasets`, `evaluation/annotations`, `evaluation/fixtures`.
Focused tests: `backend/tests/test_step77_*.py`.
Documentation: this Step Note and `docs/evaluation/step-7.7-specification.md`.

## Config / Environment

No settings schema or production configuration changed. The grading track can run with a non-secret offline Settings object. Track B requires `APP_ENV=test`, a distinct `TEST_DATABASE_URL` targeting `chinese_learning_test`, and a reachable PostgreSQL test DB. It fails closed otherwise.

## Error Handling

Grading technical failures retain safe typed codes where available and have null semantic fields; Step 6.11 currently normalizes provider errors to `GradingUnavailable` at its app boundary. Generation preserves the production `ApplicationError` code. Schema/policy failures remain deterministic failures, not infrastructure failures.

## Testing

Focused tests cover dataset shape, production request normalization, D-106 normalization, D-107 denominator, typed technical failure, canonical replay identity, fake-official guards, generation schema/domain/source references, exact D-109 bindings, and PostgreSQL DRAFT/rollback behavior when safe test DB access exists.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Four-state grading normalization | AI | 7.7 | Primary D-106 agreement unit |
| Human-eligible semantic denominator | SYSTEM | 7.7 | Keeps DRAFT/adjudication labels and technical failures out of D-107 |
| Provider replay identity | SYSTEM | 7.7 | Rejects stale results when request/config/prompt/schema changes |
| Question-bound generation annotation | AI | 7.7 | Applies D-109 at exact output/question granularity |
| Atomic DRAFT persistence | BOTH | 7.7 | Verifies generated content cannot be partly saved or auto-published |
| Content-derived annotation binding | SYSTEM | 7.7 | Recomputes reviewed-content hashes from the actual output and frozen artifact |
| REAL-origin replay provenance | SYSTEM | 7.7 | Requires replay to resolve to hash-verified REAL run artifacts |
| Complete benchmark coverage gate | SYSTEM | 7.7 | Requires exact dataset, execution, and annotation coverage before eligibility |
| Provider observer/proxy | SYSTEM | 7.7 | Preserves typed diagnostics across the production grading error boundary |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| Python | SYSTEM | 7.7 | Evaluation contracts, deterministic execution, hashing, and artifact writing |
| Pydantic | SYSTEM | 7.7 | Strict evaluation-owned DTO validation and reuse of production DTOs |
| pytest | SYSTEM | 7.7 | Deterministic contract and integration verification |
| PostgreSQL | SYSTEM | 7.7 | Dedicated isolated test verification for scope/persistence behavior |

## Acceptance Criteria

See the frozen task and test cases. Offline run artifacts have `official_eligible=false`, `runtime_api_calls=0`, and `human_approved_count=0`. This implementation does not claim official benchmark results or PM acceptance.

## Focused Offline Rework

- Track-A case text and Track-B materialized curriculum text are stored as valid UTF-8 and checked for replacement/mis-decoding markers. The intended dataset counts, splits, IDs, and all-DRAFT annotation state remain unchanged.
- HOLDOUT inputs differ from DEVELOPMENT content/configuration after case IDs, split labels, and schema bookkeeping are removed. A deterministic fingerprint validator rejects duplicates and ID-only copies.
- Track-B pass rate uses only boolean outcomes: `count(pass is true) / count(pass is true or false)`. Deferred/null cases are excluded; fail count is derived only from `pass is false`. Annotation totals count DRAFT, NEEDS_ADJUDICATION, and HUMAN_APPROVED question annotations separately.
- Replay records preserve the request/response digests, exact provider/model/config, prompt and structured-schema identities, normalized-input digest, safe provider metadata, parsed result, available finish/status and usage fields, latency, safe request ID, and REAL-origin mode/run ID. Replay adapters pass through the production grading or generation service and fail closed on stale identity.
- `--track all` creates one run ID for both tracks and all six artifacts. Manifests record dataset/content digests, source prompt hash, schema identity/version, evaluator and frozen policy identities, and explicit null for unavailable repository commit identity.
- The review ZIP uses forward-slash entry names and contains the production modules and configuration needed for independent imports, the exact task/spec, focused tests, DRAFT packages, and the Codex handoff.

## Offline Integrity Rework

- D-109 reviewed annotations are checked against independently recomputed canonical SHA-256 values for generated question content, draft content, structured output, and materialized scope content, plus SHA-256 over the exact actual `cases.jsonl` byte sequence. Verification reads those bytes directly; it does not normalize or reconstruct the file before checking artifact identity. The canonical frozen-content projection is used only to compare the actual row with the evaluated row. Unbound source DRAFT templates remain allowed.
- Track A wraps the existing `StructuredGradingProvider` with an evaluation-only observer. It rethrows provider errors unchanged to `LLMGradingService`, while preserving only safe typed error codes and allowlisted response diagnostics for evaluation artifacts. Production continues to expose its existing `GradingUnavailable` boundary; technical failures retain null semantic fields.
- Replay records now reference a REAL-origin manifest and cases artifact. Replay admission verifies their hashes, REAL execution/provider mode, run/track/case IDs, request and response hashes, parsed-result hash, and provider/model/config/prompt/schema identities. A `REAL` field without a matching artifact is insufficient.
- Official eligibility is a separate fail-closed Track A/B coverage check. It verifies actual dataset source files, frozen counts/matrices, exact execution coverage, unique complete annotations, artifact hashes, and row-level provider provenance. Track A recomputes each request hash from its exact grading case and run configuration. Track B reconstructs the selected fixture scope, validates its exact scope content/hash, and recomputes the production-shaped generation request hash. Both tracks require annotation and rubric versions from their current source-controlled annotation manifests. Offline summaries remain explicitly ineligible.

## Track-B Classification Rework

- The evaluator constructs and classifies the real discriminated `AssessmentGenerationRequest`, using `LessonExerciseGenerationRequest` or `PeriodicTestGenerationRequest`; `request.question_count` is authoritative. `requested_question_count` remains only where the actual downstream provider DTO defines that field, not as a substitute evaluation request contract.
- Only failure to parse into `StructuredAssessmentGenerationOutput` produces `SCHEMA_INVALID`. Parsed count mismatch fails `requested_count_valid` without a new critical-failure enum. A parsed but request-disallowed type produces `UNSUPPORTED_QUESTION_TYPE`; invalid/out-of-scope source refs produce `OUT_OF_SCOPE_GENERATION`; generic production domain validation fails `domain_validation_valid` while preserving `schema_valid=true`.
- The result records each dimension separately. Domain validation is marked unevaluated when an earlier production count/type/source check would have stopped the validation flow. Deterministic failures remain failures even when the frozen critical-failure taxonomy has no dedicated enum for the dimension.
- Regression tests construct both actual request variants, test valid output, count mismatch, parser/schema failure, disallowed type, out-of-scope evidence, and a real production domain-validation rejection.
