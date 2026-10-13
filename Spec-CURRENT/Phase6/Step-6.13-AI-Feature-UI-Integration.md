# Step 6.13 — AI Feature UI Integration

## Context
RAG chat UI exists from 4.4; assessment result UI and Admin core UI exist. Steps 6.11 and 6.12 add real AI grading and assessment-generation capabilities that now need explicit product UI states.

## Objective
Connect AI grading feedback/uncertainty and Admin AI generation into existing frontend flows without placing AI/business logic in React.

## Current State
Steps 4.2–4.7, 6.11 and 6.12 are complete. OpenAPI types are regenerated.

## In Scope
- learner assessment submit/result display for AI-graded free-form items.
- visually distinct `UNCERTAIN` state; do not label incorrect.
- feedback display.
- Admin generation form for lesson exercise / periodic test.
- generated DRAFT preview/edit handoff into existing assessment editor.
- generation loading/error/retry UX.

## Out of Scope
Prompt editing UI, model/provider selection UI, streaming generation, auto-publish, human grading queue.

## Functional Requirements
Learner sees overall valid score and per-question status; UNCERTAIN clearly explains that the question was excluded from score. Admin chooses generation scope/config explicitly and reviews a DRAFT before publish. UI never fabricates grading/generation state while backend is pending/failed.

## Technical Requirements
Use generated OpenAPI types, existing feature API modules and TanStack Query. No provider keys/model calls in frontend. Regenerate types after backend API changes.

## Inputs / Outputs
Inputs: grading result API, generation request fields, generated DRAFT response. Outputs: learner feedback UI and Admin draft editor state.

## Data Flow
```text
Learner submit → backend grading → result API → learner result UI
Admin scope → generate-draft API → DRAFT assessment → existing Admin editor
```

## Interfaces / API / Schema
Use canonical Step 3.4/6.11 attempt-result schema and Step 6.12 generation endpoint.

## Files / Components
Existing assessment result feature + `features/admin/assessments` generation components + tests.

## Config / Env
No new frontend provider configuration.

## Error Handling
Technical AI failure is shown as retryable/non-final where backend contract permits; semantic UNCERTAIN is a successful grading state, not a red technical error.

## Testing
Cover graded correct/incorrect/uncertain rendering, generation success/failure, draft handoff, no auto-publish and learner/admin authorization UX.

## Acceptance Criteria
- [ ] Learner can distinguish incorrect vs UNCERTAIN.
- [ ] Valid score excludes uncertain items consistently with backend.
- [ ] Admin can configure and request AI draft generation.
- [ ] Generated content enters existing DRAFT editor/review flow.
- [ ] No LLM/provider logic exists in frontend.

## Constraints / Non-goals
Do not add another frontend state library or standalone AI admin app.

## Open Questions
None that block this Step.
