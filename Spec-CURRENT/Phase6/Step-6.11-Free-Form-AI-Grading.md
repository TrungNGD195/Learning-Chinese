# Step 6.11 — Free-form AI Grading

## Context
Objective question types are graded deterministically in Step 3.4. Vietnamese↔Chinese translation and sentence-writing questions require an LLM grader with an explicit UNCERTAIN state that never silently counts as wrong.

## Objective
Replace the Phase-3 `AIGrader` stub with a production-shaped structured LLM grading service while preserving assessment transaction and scoring semantics.

## Current State
Step 3.4 grading boundary exists; Step 6.7 has selected/configured the single V0 LLM provider/model and structured-output mechanism.

## In Scope
- free-form question types only.
- structured grading output.
- uncertainty/abstention.
- prompt construction from question/reference/rubric/learner answer.
- safe provider errors/validation.
- integration through existing `AIGrader` boundary.

## Out of Scope
Objective grading via LLM, learner chat/RAG grading, human review workflow, multi-provider routing, fine-tuning.

## Functional Requirements
Canonical result:
```text
grading_status = GRADED | UNCERTAIN
score           = 0..max_points when GRADED, null when UNCERTAIN
is_correct      = boolean when GRADED, null when UNCERTAIN
feedback        = learner-safe Vietnamese feedback
reasoning_summary? = short non-chain-of-thought rationale if needed for audit
```
Provider/parse/schema failure is `FAILED`, not `UNCERTAIN`. UNCERTAIN is a semantic grader abstention. Existing score calculation excludes UNCERTAIN from numerator and denominator. Grader may use the stored expected/reference answer and question rubric but must not invent curriculum requirements outside them.

## Technical Requirements
One provider/model only (D-002). Require structured/schema-validated output; reject invalid JSON/schema. Keep provider adapter separate from `GradingService`. Do not persist or request hidden chain-of-thought. Apply input-length/config bounds and structured logging without learner secrets.

## Inputs / Outputs
Inputs: question type/content, reference answer/rubric/max points, learner answer, optional lesson metadata. Output: canonical grading result above.

## Data Flow
```text
Assessment submit → deterministic graders for objective items
                  → AIGrader for free-form item
                  → validated GradeResult
                  → short DB transaction persists AttemptAnswer/final score
```

## Interfaces / API / Schema
Preserve Step 3.4 `AIGrader` application interface and `attempt_answers` fields. Do not create a second grading persistence model.

## Files / Components
Expected under `app/ai/grading` + existing assessment service integration + tests.

## Config / Env
Reuse selected LLM provider/model config from 6.7 plus grading-specific timeout/max-output/prompt-version settings if required.

## Error Handling
Provider timeout/auth/unavailable/schema-invalid → typed technical failure → affected grading operation/attempt follows Step 3.4 `GRADING_FAILED` semantics; never reinterpret as UNCERTAIN. Semantic ambiguity → UNCERTAIN.

## Testing
Mock provider deterministically. Cover confident correct, confident incorrect, UNCERTAIN, invalid output, timeout, prompt input boundaries, exclusion of uncertain from score, and objective questions never calling LLM.

## Acceptance Criteria
- [ ] Only free-form types call AIGrader.
- [ ] Structured result validates before persistence.
- [ ] UNCERTAIN is distinct from incorrect and excluded from score.
- [ ] Technical failure is distinct from UNCERTAIN.
- [ ] Existing assessment/progress business rules remain authoritative.
- [ ] Single provider/model strategy is preserved.

## Constraints / Non-goals
Do not add a second LLM vendor or model-routing system.

## Open Questions
None once Step 6.7 provider/model selection is recorded by PM.
