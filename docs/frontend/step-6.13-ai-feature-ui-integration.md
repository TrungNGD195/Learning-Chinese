# Step 6.13 — AI Feature UI Integration

## Objective

Connect the learner assessment result and the Admin AI draft-generation workflow to the already accepted backend contracts. The frontend presents canonical results and submits explicit generation intent; backend services continue to own grading, scope validation, generation, and persistence.

## Why

Learners need clear, honest grading outcomes, including abstention and partial credit. Admins need a readable way to select curriculum content for draft generation and then review the persisted draft through the existing editor.

## Mental Model

```text
Learner answer
→ backend grader
→ backend authoritative grading semantics
→ canonical Attempt result
→ React renders result
```

```text
Admin generation intent
→ typed generation request
→ backend validates scope + generates + persists DRAFT
→ returned Assessment ID
→ existing Admin editor
→ canonical backend read
```

```text
selected Lessons
→ per-selected-Lesson discovery
→ canonical Vocabulary/Grammar IDs
→ explicit item selection
→ backend scope validation
```

## Core Knowledge

- `GRADED` result labels use backend `is_correct`; the UI does not calculate correctness or a score threshold. Per-answer numeric score can coexist with `is_correct = false`.
- `UNCERTAIN` is neutral, renders backend feedback when present, and states that the item was not counted in the score. It is distinct from technical `FAILED` / `GRADING_FAILED` states.
- `AI_GRADING_UNAVAILABLE` returns the learner to the same canonical Attempt result. The UI does not automatically resubmit that Attempt.
- Admin generation request and response types derive from the generated OpenAPI operation. `LESSON_EXERCISE` sends `lesson_id`; `PERIODIC_TEST` sends selected `lesson_ids` and explicitly selected canonical `vocabulary_ids` / `grammar_ids`.
- Periodic Test discovery runs only for selected Lessons. Association `id` values are not submitted; canonical `vocabulary_id` and `grammar_id` values are deduplicated across Lessons.
- A generation mutation uses `retry: false`, disables duplicate submission while pending, preserves form state on failure, and maps known `ApiError.code` values to safe guidance. A successful response invalidates the Admin Assessment list and navigates to the existing editor by the returned Assessment ID.

## Data Flow

The learner result page reads the current Attempt result and renders its grading state, score, correctness, feedback, and available reference details. It does not derive pass/fail or correctness.

The Admin form reads HSK and Lesson discovery data through existing API wrappers. In Periodic Test mode it queries Vocabulary and Grammar only after each Lesson is selected, deduplicates by canonical entity ID, and submits the selected canonical IDs. The backend remains responsible for authoritative scope validation and draft generation.

## Key Design Decisions

- Keep the generated OpenAPI DTO as the request/response type authority; no generated file was hand-edited.
- Reuse existing Admin discovery endpoints, `apiClient`, query keys, list invalidation, and canonical Assessment editor.
- Keep generation controls limited to the frozen form inputs; no raw ID/JSON, provider, model, or prompt controls are exposed.
- Disable automatic mutation retry so a failed generation is replayed only after an explicit user action.
- Keep generated assessments as Admin-reviewable drafts; generation does not publish them.

## Reusable Approach

For future UI integrations, begin with the generated operation and frozen state semantics. Use readable discovery data, submit canonical IDs, keep unsaved form state local, make mutation retry policy explicit, and hand successful writes back to canonical reads.

## Common Mistakes

- Treating `UNCERTAIN` as incorrect or assigning a local score/pass threshold.
- Hiding partial credit when backend correctness is false.
- Automatically resubmitting a grading-failed Attempt.
- Submitting Lesson association IDs instead of canonical Vocabulary/Grammar IDs.
- Loading every Lesson’s content before the Admin selects it.
- Replaying generation automatically after a network/provider error.
- Navigating using a client-created identifier instead of the returned Assessment ID.

## Definition of Done

- Learner result rendering preserves backend grading semantics, including neutral uncertainty and partial scores.
- Admin generation uses generated DTOs, selected-Lesson discovery, canonical item IDs, safe error states, and non-retrying mutation behavior.
- Successful generation opens the existing canonical Admin Assessment editor.
- Focused and full frontend tests, build, lint, and `api:check` pass.
- No backend, schema, migration, dependency, generated contract, or Step 7.4+ change is introduced.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Semantic grader abstention (`UNCERTAIN`) | AI | 6.13 | Distinguishes uncertain AI judgment from incorrect answers and technical failure |
| Partial-credit grading result | AI | 6.13 | UI renders backend numeric score without inventing correctness thresholds |
| AI generation scope | AI | 6.13 | Admin selects the curriculum content the backend may use for generation |
| Backend-authoritative AI state | BOTH | 6.13 | React presents grading/generation results while backend owns business semantics |
| Canonical entity ID vs association ID | DE | 6.13 | Prevents Lesson association IDs from being sent where reusable Vocabulary/Grammar IDs are required |
| Generated API contract | SYSTEM | 6.13 | Keeps frontend generation/result DTOs aligned with the backend OpenAPI contract |
| Server-state mutation handoff | SYSTEM | 6.13 | Generated DRAFT transitions immediately to the existing canonical editor |
| Mutation retry safety | SYSTEM | 6.13 | Avoids accidental duplicate AI generation requests |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| React | SYSTEM | 6.13 | Learner/Admin presentation and local form state |
| TypeScript | SYSTEM | 6.13 | Generated contract-safe frontend integration |
| React Router | SYSTEM | 6.13 | Navigate generated draft to canonical Admin editor |
| TanStack Query | SYSTEM | 6.13 | Discovery queries, mutation state, and bounded invalidation |
| central `apiClient` | SYSTEM | 6.13 | Shared HTTP/Auth/error boundary |
| openapi-typescript generated contracts | SYSTEM | 6.13 | Request/response DTO authority |
| Vitest | SYSTEM | 6.13 | Focused/frontend regression testing |
| React Testing Library | SYSTEM | 6.13 | Behavior-oriented UI tests |
| npm | SYSTEM | 6.13 | Frontend scripts and verification |
