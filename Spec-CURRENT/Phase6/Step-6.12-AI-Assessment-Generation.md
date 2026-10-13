# Step 6.12 — AI Assessment Generation

## Context
Admins must be able to generate lesson exercises and periodic-test drafts from explicitly selected curriculum knowledge. AI-generated content must always enter reviewable DRAFT state and can never auto-publish.

## Objective
Implement constrained structured generation of assessment/questions through the existing Admin/assessment domain model.

## Current State
Admin assessment/question CRUD and lifecycle from 3.4 exist; selected LLM provider/model from 6.7 exists; internal knowledge/content records are available.

## In Scope
- lesson-exercise draft generation.
- periodic-test draft generation across admin-selected lessons/vocabulary/grammar.
- configuration: selected scope, count, supported types, difficulty.
- schema validation and domain validation.
- persistence as DRAFT assessment/questions.

## Out of Scope
Automatic publish, autonomous curriculum coverage selection, generation from arbitrary web content, bulk course generation, multi-agent workflows.

## Functional Requirements
Admin supplies authoritative generation scope. The model may generate only from the supplied selected knowledge. Output must use supported question types and required answer/reference/explanation fields. Generated assessment/questions are persisted as `DRAFT`; Admin may edit, submit-review, approve/publish through normal lifecycle APIs. If generation produces invalid/out-of-scope items, reject the generation result rather than partially auto-publishing.

## Technical Requirements
Use one structured LLM call or the minimum bounded calls needed for schema size; no unbounded agent loop. Prompt includes stable prompt version + selected knowledge only. Validate IDs/references against current content and enforce question-type schemas before persistence. Transaction persists the draft atomically after successful validation.

## Inputs / Outputs
Inputs: generation kind (`LESSON_EXERCISE` or `PERIODIC_TEST`), selected lesson/vocab/grammar IDs, question count, allowed types, difficulty, optional title/settings. Output: DRAFT assessment with validated question records.

## Data Flow
```text
Admin selection → load authorized selected knowledge → prompt/package
→ LLM structured generation → schema/domain validation
→ persist DRAFT assessment/questions → Admin review/edit → later publish
```

## Interfaces / API / Schema
Add Admin action(s) equivalent to:
```http
POST /api/v1/admin/assessments/generate-draft
```
Exact request/response shape must be represented in OpenAPI and return the created draft identity plus generated questions. Reuse existing assessment/question tables and lifecycle states.

## Files / Components
`app/ai/generation`, Admin assessment service/router integration, prompt/schema versioning, tests.

## Config / Env
Reuse LLM config; generation max questions/output/timeout may be bounded settings.

## Error Handling
Invalid admin scope → validation/business error. LLM/provider failure → no draft persisted. Structured output/domain violation → typed generation validation failure; no partial draft unless the spec explicitly records an all-or-nothing valid subset policy (V0 default: all-or-nothing).

## Testing
Cover lesson scope, multi-lesson periodic-test scope, unsupported type, out-of-scope generated reference, malformed output, provider failure, atomic persistence, and no auto-publish.

## Acceptance Criteria
- [ ] Admin-selected scope is authoritative.
- [ ] Generated questions stay within selected knowledge.
- [ ] Supported question schemas validate.
- [ ] Result persists as DRAFT only.
- [ ] Admin review/edit/publish remains mandatory.
- [ ] Failure never leaves a published or half-valid generated assessment.

## Constraints / Non-goals
No autonomous curriculum planning and no external web generation source in V0.

## Open Questions
None once Step 6.7 provider/model selection is recorded.
