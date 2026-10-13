# Codex Execution Task — Step 6.13: AI Feature UI Integration

**Status:** READY_FOR_PM_TASK_REVIEW  
**Owner:** App Engineering Specialist  
**Current step:** 6.13 — AI Feature UI Integration  
**Prerequisites:** Step 6.11 and Step 6.12 are PM FINAL ACCEPTED  
**Do not start:** Step 7.4+  
**Do not run beyond this Step.**

---

# 1. Objective

Integrate the already-accepted AI grading and AI Assessment generation capabilities into the existing frontend flows.

Required flows:

```text
Learner Assessment
→ backend grading
→ canonical Attempt result
→ result UI

Admin generation configuration
→ POST /api/v1/admin/assessments/generate-draft
→ persisted DRAFT Assessment
→ /admin/assessments/:assessmentId
→ existing canonical Admin Assessment editor
```

The frontend remains a presentation/client layer.

Do not move grading, scoring, generation, authorization, scope validation, lifecycle, or AI-provider logic into React.

---

# 2. Current Accepted Architecture to Preserve

Use the existing:

```text
React + TypeScript + Vite
React Router Data Mode
generated OpenAPI contracts
feature API modules
central apiClient
TanStack Query
existing Assessment learner UI
existing Admin Assessment list/editor
existing auth/route guards
```

Canonical Admin editor remains:

```text
/admin/assessments/:assessmentId
```

Do not:

```text
add Redux/Zustand/another state library
add a standalone AI frontend route/app
create an AI-specific draft editor
create a temporary frontend-authoritative Assessment
add provider/model controls
add streaming/progress infrastructure
```

---

# 3. JIT Reconciliation Result

The current accepted API surface is sufficient.

No backend endpoint, schema, migration, or OpenAPI change is required for Step 6.13.

The reviewed current generated contract already exposes:

```http
POST /api/v1/admin/assessments/generate-draft
GET  /api/v1/me/assessment-attempts/{attempt_id}

GET  /api/v1/admin/lessons
GET  /api/v1/admin/lessons/{lesson_id}/vocabulary
GET  /api/v1/admin/lessons/{lesson_id}/grammar
```

The generation request is already a generated discriminated union:

```text
LessonExerciseGenerationRequest
|
PeriodicTestGenerationRequest
```

The 201 response is:

```text
AssessmentGenerationDraftResponse
├── assessment: AssessmentAdminResponse
└── questions: QuestionAdminResponse[]
```

Do not manually duplicate these DTOs.

---

# 4. Part A — Learner AI Grading Result UI

## 4.1 Backend authority

Continue to load canonical result through the existing:

```text
assessmentApi.getAttempt(attemptId)
```

Do not locally recompute:

```text
overall score
score denominator
pass/fail
is_correct
progress
unlock state
next learning target
```

Continue to render the backend-owned:

```text
AttemptDetailResponse.status
AttemptDetailResponse.score
AttemptDetailResponse.passed

answer.grading_status
answer.score
answer.is_correct
answer.feedback
```

The generated Attempt result contract does **not** expose per-answer `max_points`.

Do not invent it and do not calculate it in the frontend.

---

## 4.2 Exact grading-status presentation

Preserve the existing four backend answer grading states:

```text
PENDING
GRADED
UNCERTAIN
FAILED
```

### GRADED + is_correct = true

Render:

```text
Correct
```

using the existing positive presentation.

If `answer.score !== null`, render the backend numeric score exactly as currently done.

### GRADED + is_correct = false

Render:

```text
Incorrect
```

using the existing incorrect presentation.

Still render the backend numeric score when present.

This is important for Step-6.11 partial-credit semantics:

```text
backend score may be partial
backend is_correct may still be false
```

Example:

```text
grading_status = GRADED
score = 1.5
is_correct = false

UI:
Incorrect
Score: 1.5
```

Do not create a frontend correctness threshold.

### UNCERTAIN

Canonical backend semantics:

```text
grading_status = UNCERTAIN
score = null
is_correct = null
```

Render with the existing neutral presentation.

Required learner-facing text must clearly communicate both:

```text
Uncertain
This item was not counted in your score.
```

Equivalent concise wording is acceptable, but it must not imply incorrectness or a technical failure.

Do not render UNCERTAIN using the red/incorrect style.

Render backend `feedback` when present.

### FAILED

Keep the existing technical per-answer grading-failure presentation.

Do not invent correctness.

### PENDING

Keep the existing safe non-final presentation.

---

# 5. GRADING_FAILED Attempt Semantics

Preserve the accepted learner submission flow.

Current behavior must remain:

```text
submit Attempt
→ backend may persist Attempt as GRADING_FAILED
→ HTTP 503 AI_GRADING_UNAVAILABLE
→ navigate to the same Attempt result route
→ GET canonical Attempt
→ render GRADING_FAILED
```

Do not automatically resubmit the same Attempt.

The Result page must continue to provide only the existing explicit Retry navigation:

```text
Retry
→ /assessments/:assessmentId
→ learner explicitly starts/resumes the next valid Attempt
```

Do not create another Attempt from the Result page.

Do not reinterpret `AI_GRADING_UNAVAILABLE` as UNCERTAIN.

---

# 6. Part B — Admin AI Assessment Generation API

Add the generation path to the existing Admin feature API module:

```ts
const generateAssessmentDraftPath =
  '/api/v1/admin/assessments/generate-draft'
```

Derive types from generated OpenAPI:

```ts
export type AssessmentGenerationRequest =
  RequestBodyOf<typeof generateAssessmentDraftPath, 'post'>

export type AssessmentGenerationDraft =
  ResponseBodyOf<typeof generateAssessmentDraftPath, 'post'>
```

Add:

```ts
export function generateAssessmentDraft(
  body: AssessmentGenerationRequest,
)
```

using the central `apiClient`.

Do not handwrite the request/response object schema.

Do not add a second HTTP client.

---

# 7. Admin Generation UI Location

Keep the existing:

```text
/admin/assessments
```

as the entry surface.

Add an explicit:

```text
Generate AI Draft
```

control alongside the existing manual `Create Assessment` flow.

Do not replace or redesign manual Assessment creation.

Implement a focused child component:

```text
frontend/src/features/admin/AssessmentGenerationForm.tsx
```

The generation form owns only local form/selection state.

The persisted Assessment remains server-owned.

No new route is needed.

---

# 8. Common Generation Fields

The UI must expose:

```text
type
title?
description?
pass_threshold
question_count
allowed_types
difficulty
```

Rules:

```text
pass_threshold
→ 0..100
→ initialize to existing project convention 90

question_count
→ 1..10
→ initialize to 1, the minimum valid value

difficulty
→ EASY | MEDIUM | HARD
→ require explicit selection; no hidden provider default

allowed_types
→ require at least one selected
```

Title and description are optional for AI generation.

When blank, omit them from the request rather than inventing frontend titles.

Backend may supply its accepted default title.

Preserve form state on mutation failure.

---

# 9. Allowed Question Types

Expose exactly these seven canonical values:

```text
multiple_choice
fill_blank
matching
reorder_sentence
translate_vi_zh
translate_zh_vi
sentence_writing
```

Use human-friendly labels, for example:

```text
Multiple Choice
Fill in the Blank
Matching
Reorder Sentence
Translate Vietnamese → Chinese
Translate Chinese → Vietnamese
Sentence Writing
```

Send only the canonical enum values.

At least one must be selected before Generate is enabled.

Do not expose unknown/future question types.

---

# 10. LESSON_EXERCISE Generation Scope UX

Generated request variant:

```text
type = LESSON_EXERCISE
lesson_id
title?
description?
pass_threshold
question_count
allowed_types
difficulty
```

The Lesson is the complete authoritative generation scope.

Use the existing Admin Lesson discovery:

```http
GET /api/v1/admin/lessons
```

and existing Query key:

```text
queryKeys.adminLessons(filters)
```

Use the existing paginated/domain-oriented lesson selector convention.

Recommended query shape:

```text
page
page_size = 50
optional hsk_level_id
```

Selections must show readable Lesson information:

```text
HSK level
Lesson number
Lesson title
```

Do not expose UUID text input.

For LESSON_EXERCISE:

```text
do NOT query Vocabulary/Grammar merely to build the request
do NOT send vocabulary_ids
do NOT send grammar_ids
```

---

# 11. PERIODIC_TEST Mandatory Discovery Flow

The current accepted API is sufficient.

Do not add a backend discovery/catalog endpoint.

Required flow:

```text
Admin selects one or more Lessons
→ fetch Vocabulary and Grammar only for those explicitly selected Lessons
→ merge/dedupe by canonical entity IDs
→ Admin explicitly selects Vocabulary/Grammar items
→ generate request
```

Use existing APIs:

```http
GET /api/v1/admin/lessons
GET /api/v1/admin/lessons/{lesson_id}/vocabulary
GET /api/v1/admin/lessons/{lesson_id}/grammar
```

Use existing Query keys:

```text
queryKeys.adminLessons(filters)
queryKeys.adminLessonVocabulary(lessonId)
queryKeys.adminLessonGrammar(lessonId)
```

Use `useQueries` or equivalent TanStack Query composition only for currently selected Lessons.

Do not recursively crawl all Lessons.

Do not load every Lesson page in the background.

Do not build a hidden client-side global catalog.

---

# 12. PERIODIC_TEST ID Semantics

This distinction is mandatory.

Current Admin Lesson content response contains:

```text
id
→ LessonVocabulary / LessonGrammar association ID

vocabulary_id
→ canonical Vocabulary ID

grammar_id
→ canonical Grammar ID
```

Step-6.12 generation request expects:

```text
vocabulary_ids[]
→ canonical Vocabulary IDs

grammar_ids[]
→ canonical Grammar IDs
```

Therefore:

```text
NEVER send LessonContentAdminResponse.id
as vocabulary_ids[] / grammar_ids[].
```

Use only:

```text
item.vocabulary_id
item.grammar_id
```

Ignore/null-guard the opposite nullable identity field.

---

# 13. PERIODIC_TEST Picker UX

Generated request variant:

```text
type = PERIODIC_TEST
lesson_ids[]
vocabulary_ids[]
grammar_ids[]
title?
description?
pass_threshold
question_count
allowed_types
difficulty
```

Rules:

```text
at least one Lesson selected
AND
at least one Vocabulary or Grammar item selected
```

The Lesson selector may remain paginated.

Selections must persist while the Admin navigates Lesson pages/filter choices.

After Lesson selection:

```text
Vocabulary picker
→ readable hanzi / pinyin / Vietnamese meaning

Grammar picker
→ readable name / structure / explanation
```

No raw UUID controls.

No raw JSON editor.

No junction-table UI.

No database terminology in the user-facing labels.

---

# 14. Deduplication Across Selected Lessons

The same canonical Vocabulary/Grammar item may belong to multiple selected Lessons.

Build the discovery presentation using canonical IDs as the merge key:

```text
Vocabulary:
key = vocabulary_id

Grammar:
key = grammar_id
```

Do not show duplicate checkbox rows for the same canonical entity.

It is acceptable to show readable Lesson membership context for a deduped item.

Do not mutate server data.

This is local form/catalog presentation only.

---

# 15. Selected-Lesson Changes

If a selected Lesson is removed, the generation request must not contain Vocabulary/Grammar IDs that are no longer discoverable from the remaining selected Lessons.

Implementation may either:

```text
prune stale selected item IDs
```

or derive the submitted arrays as:

```text
selected IDs ∩ currently discovered canonical IDs
```

The visible checked state and the submitted payload must remain consistent.

Do not silently submit hidden stale IDs.

---

# 16. Discovery Loading / Error State

For PERIODIC_TEST:

```text
selected Lessons
→ per-selected-Lesson Vocabulary/Grammar queries
```

While required discovery is loading:

```text
show explicit loading state
disable Generate
```

If one or more discovery queries fail:

```text
show actionable safe error state
preserve Lesson/item selections
allow explicit query retry
disable Generate until current discovery state is trustworthy
```

Do not fall back to raw UUID input.

---

# 17. Generation Mutation

Use TanStack Query:

```text
useMutation
retry: false
```

Flow:

```text
Generate Draft click
→ one POST /generate-draft
→ pending
→ disable duplicate Generate
→ show "Generating draft…" or equivalent
```

No streaming.

No fake progress percentage.

No optimistic generated questions.

No temporary authoritative Assessment object.

---

# 18. Generation Success UX

On 201 success:

```text
response.assessment.id
→ invalidate Admin Assessment list
→ navigate /admin/assessments/{assessment.id}
→ existing editor performs canonical backend reads
```

Use existing:

```text
invalidateAssessmentList(queryClient)
```

Do not seed generated response into the editor as authoritative state.

Do not create a new preview route.

Do not auto-publish.

The response `questions` may be ignored for navigation purposes; the existing editor must load the canonical persisted Assessment/questions.

---

# 19. Generation Failure Semantics

Do not automatically replay the generation mutation.

Preserve all current form selections/configuration.

Use `ApiError.code`, not message parsing.

Create a small generation-specific error presentation helper local to the generation feature/component.

Do not change the existing Document-specific meaning of the shared Admin `INVALID_REQUEST` text merely to support this Step.

Required mapping:

```text
422 INVALID_REQUEST
→ "Check the generation settings and try again."
→ form/request validation state

422 INVALID_GENERATION_SCOPE
→ actionable selected-scope error
→ tell Admin to review selected Lessons/Vocabulary/Grammar

422 AI_GENERATION_INPUT_TOO_LARGE
→ explain selected generation scope/input is too large
→ Admin must reduce selection

502 AI_GENERATION_INVALID_OUTPUT
→ technical generation failure
→ explicit retry allowed

503 AI_GENERATION_UNAVAILABLE
→ temporary AI/provider failure
→ explicit retry allowed

500 AI_GENERATION_PERSISTENCE_FAILED
→ generated draft could not be saved
→ do not claim a draft exists
→ explicit retry allowed
```

For unknown network/server errors, fall back to the existing safe Admin/ApiError presentation.

No provider/internal error details.

No prompt/model/raw-output details.

---

# 20. Explicit Retry Meaning

“Explicit Retry allowed” means:

```text
form remains populated
error is visible
Generate Draft button becomes enabled again
Admin chooses to click Generate Draft again
```

It does **not** mean:

```text
automatic TanStack mutation retry
automatic timer
automatic replay after error
```

One click must result in at most one generation mutation attempt, aside from the already-accepted central authentication refresh/replay semantics.

---

# 21. Auth / Authorization

Preserve existing behavior:

```text
401
→ central authentication/session flow

403 ADMIN_REQUIRED
→ existing forbidden/Admin authorization behavior
→ do not log out an otherwise authenticated User
```

Do not add frontend token handling.

Do not parse JWTs.

No provider credentials/configuration belong in frontend source.

---

# 22. Existing Admin Editor Handoff

Canonical route:

```text
/admin/assessments/:assessmentId
```

Existing editor remains responsible for:

```text
canonical Assessment GET
canonical Question GET
metadata editing
question editing
review/publish/archive lifecycle
```

Generated Assessment status is already persisted as:

```text
DRAFT
```

Do not create an AI-only draft lifecycle/editor.

---

# 23. API / Query Changes

## API wrapper

Modify:

```text
frontend/src/features/admin/api.ts
```

Add generated-path-derived generation request/response types and `generateAssessmentDraft()`.

## Query keys

No new Query key is required for the generation mutation.

Reuse:

```text
adminLessons
adminLessonVocabulary
adminLessonGrammar
adminAssessmentsRoot
```

Do not add a persistent “AI generation result” query/cache.

## Invalidation

Reuse:

```text
invalidateAssessmentList()
```

after successful draft creation.

No global Query clear.

---

# 24. Exact Production Files Expected

Modify:

```text
frontend/src/features/assessment/AssessmentResultPage.tsx

frontend/src/features/admin/api.ts
frontend/src/features/admin/AdminAssessmentsPage.tsx
```

Create:

```text
frontend/src/features/admin/AssessmentGenerationForm.tsx
```

Tests:

```text
frontend/src/features/step43-learning.test.tsx
frontend/src/features/admin/step613-ai-feature-ui.test.tsx
```

Documentation:

```text
docs/frontend/step-6.13-ai-feature-ui-integration.md
```

Modify other files only if actual repository implementation requires a narrow, directly related change.

Do not change:

```text
backend application code
database models
Alembic migrations
frontend/src/types/api.generated.ts manually
routes
auth architecture
Step 7.x code
```

No new runtime dependency is expected.

---

# 25. Learner-Focused Tests

Extend existing learner tests to cover at minimum:

1. `UNCERTAIN` renders neutral, not Incorrect.
2. `UNCERTAIN` visibly says the item was not counted in score.
3. `UNCERTAIN` renders backend feedback when present.
4. `UNCERTAIN` does not render a fabricated numeric item score.
5. Partial free-form result:
   ```text
   GRADED
   score = 1.5
   is_correct = false
   ```
   renders:
   ```text
   Incorrect
   Score: 1.5
   ```
   without frontend threshold logic.
6. `GRADING_FAILED` Attempt still renders the accepted technical-failure state.
7. `AI_GRADING_UNAVAILABLE` still navigates to the same Attempt result.
8. Same failed Attempt is submitted only once.
9. Result Retry only navigates back to `/assessments/:assessmentId`.
10. Result page does not calculate overall score/pass/fail.

Retain existing Step-4.3 result regressions.

---

# 26. Admin Generation Tests

Create focused behavior tests covering at minimum:

## Contract / wrapper

1. `generateAssessmentDraft()` uses the generated request/response contract.
2. Request goes through central `apiClient`.
3. No handwritten duplicate generation DTO exists.

## LESSON_EXERCISE

4. Human-readable paginated Lesson selection.
5. Exact request uses:
   ```text
   type=LESSON_EXERCISE
   lesson_id
   ```
6. Request does not contain:
   ```text
   lesson_ids
   vocabulary_ids
   grammar_ids
   ```
7. Optional blank title/description are not fabricated.
8. `question_count` validation 1..10.
9. `pass_threshold` validation 0..100.
10. difficulty required.
11. at least one allowed type required.

## PERIODIC_TEST discovery

12. One or more Lessons can be selected without raw UUID input.
13. Only explicitly selected Lessons trigger Vocabulary/Grammar discovery.
14. The UI does not recursively fetch every Lesson page.
15. Vocabulary rows display readable domain content.
16. Grammar rows display readable domain content.
17. `vocabulary_id`, not association `id`, is sent in `vocabulary_ids[]`.
18. `grammar_id`, not association `id`, is sent in `grammar_ids[]`.
19. Duplicate canonical Vocabulary across Lessons appears once.
20. Duplicate canonical Grammar across Lessons appears once.
21. At least one Vocabulary or Grammar item is required.
22. Stale item selections from deselected Lessons are not submitted.
23. Discovery loading disables Generate.
24. Discovery failure preserves selections and exposes explicit retry.
25. No UUID text input / raw JSON scope editor exists.

## Seven question types

26. Exactly the seven accepted generation types are exposed.
27. Human labels map to canonical enum values.
28. At least one type must remain selected for valid submit.

## Mutation

29. Generate pending state disables duplicate submission.
30. One click causes one mutation call.
31. No fake generated-question preview is created.
32. Success invalidates Admin Assessment list.
33. Success navigates to:
    `/admin/assessments/{response.assessment.id}`.
34. Existing editor remains the destination.
35. No auto-publish action occurs.

## Errors

36. `INVALID_REQUEST` → generation form validation message.
37. `INVALID_GENERATION_SCOPE` → actionable scope message.
38. `AI_GENERATION_INPUT_TOO_LARGE` → reduce-selection message.
39. `AI_GENERATION_INVALID_OUTPUT` → technical error + explicit retry.
40. `AI_GENERATION_UNAVAILABLE` → temporary error + explicit retry.
41. `AI_GENERATION_PERSISTENCE_FAILED` → save failure + no draft-success UI.
42. Failure preserves all form state/selections.
43. No generation error auto-replays the mutation.
44. Explicit second click may perform a second attempt.
45. `ADMIN_REQUIRED` retains existing authorization/session semantics.

---

# 27. OpenAPI / Contract Verification

No backend/OpenAPI modification is expected.

Do not edit:

```text
frontend/src/types/api.generated.ts
```

Run the accepted contract check against the current backend:

```bash
npm run api:check
```

The check must continue to prove the committed generated contract matches the current FastAPI OpenAPI.

If Codex discovers that the runtime OpenAPI materially differs from the current generated file, stop and report:

```text
BLOCKED — Decision Needed
```

Do not patch generated DTOs manually.

---

# 28. Frontend Verification

From `frontend/`:

```bash
npm ci
npm test -- --run src/features/step43-learning.test.tsx src/features/admin/step613-ai-feature-ui.test.tsx
npm test -- --run
npm run build
npm run lint
npm run api:check
```

Keep existing project warning policy.

No backend test suite is required solely for a frontend-only Step unless Codex unexpectedly changes backend code, which should itself trigger stop/review.

---

# 29. Acceptance Criteria

Step 6.13 is complete only when all are true.

## Learner grading

- [ ] Existing canonical Attempt result route remains unchanged.
- [ ] Result uses generated backend contract.
- [ ] Correct / Incorrect / Uncertain are visibly distinct.
- [ ] UNCERTAIN is neutral.
- [ ] UNCERTAIN explicitly says the item was not counted in score.
- [ ] Backend feedback is shown when present.
- [ ] Partial numeric score is displayed without local correctness threshold.
- [ ] Frontend does not calculate overall score/pass/fail.
- [ ] GRADING_FAILED remains a technical failure state.
- [ ] AI_GRADING_UNAVAILABLE does not resubmit the same Attempt.
- [ ] Result Retry remains explicit navigation only.

## Admin generation

- [ ] Generation uses the existing Admin Assessments surface.
- [ ] No new AI route/app/editor exists.
- [ ] `generateAssessmentDraft()` uses generated OpenAPI request/response types.
- [ ] LESSON_EXERCISE uses only authoritative Lesson scope.
- [ ] PERIODIC_TEST uses selected Lessons + explicit selected Vocabulary/Grammar.
- [ ] Discovery uses existing per-Lesson endpoints.
- [ ] No recursive all-Lesson crawl exists.
- [ ] No raw UUID/JSON scope UI exists.
- [ ] Association IDs are never submitted as generation content IDs.
- [ ] Canonical `vocabulary_id` / `grammar_id` values are submitted.
- [ ] Reusable content is deduped by canonical entity ID.
- [ ] Exactly seven allowed generation question types are exposed.
- [ ] At least one allowed type is required.
- [ ] question_count is bounded 1..10.
- [ ] Generation mutation retry is disabled.
- [ ] Duplicate Generate submission is disabled while pending.
- [ ] Form state survives errors.
- [ ] All frozen backend generation error codes have safe UI states.
- [ ] Explicit Retry is user initiated only.
- [ ] Success navigates to existing Admin Assessment editor by returned Assessment ID.
- [ ] Existing editor loads canonical backend state.
- [ ] No auto-publish exists.
- [ ] No provider/model/prompt/temperature/token controls exist.
- [ ] No provider secret/config exists in frontend.

## Regression / scope

- [ ] Existing manual Assessment creation still works.
- [ ] Existing Admin Assessment lifecycle/editor still works.
- [ ] Existing Auth/Admin behavior still works.
- [ ] Existing Step-4.3 learner Assessment behavior still works.
- [ ] No backend change was required.
- [ ] No migration was added.
- [ ] No new runtime dependency was added.
- [ ] `api.generated.ts` was not manually edited.
- [ ] Focused tests pass.
- [ ] Full frontend tests pass.
- [ ] Build passes.
- [ ] Lint passes according to existing policy.
- [ ] `api:check` passes.
- [ ] Step Note reflects actual implementation.
- [ ] No Step 7.4+ work exists.

---

# 30. Step Note

Create:

```text
docs/frontend/step-6.13-ai-feature-ui-integration.md
```

Include:

```text
Objective
Why
Mental Model
Core Knowledge
Data Flow
Key Design Decisions
Reusable Approach
Common Mistakes
Definition of Done
Concepts Discovered
Tools Used
```

Required mental models:

```text
Learner answer
→ backend grader
→ backend authoritative grading semantics
→ canonical Attempt result
→ React renders result
```

and:

```text
Admin generation intent
→ typed generation request
→ backend validates scope + generates + persists DRAFT
→ returned Assessment ID
→ existing Admin editor
→ canonical backend read
```

For PERIODIC_TEST:

```text
selected Lessons
→ per-selected-Lesson discovery
→ canonical Vocabulary/Grammar IDs
→ explicit item selection
→ backend scope validation
```

---

# 31. Concepts Discovered

Record only concepts actually used.

Expected:

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Semantic grader abstention (`UNCERTAIN`) | AI | 6.13 | Distinguishes uncertain AI judgment from incorrect answers and technical failure |
| Partial-credit grading result | AI | 6.13 | UI renders backend numeric score without inventing correctness thresholds |
| AI generation scope | AI | 6.13 | Admin selects the curriculum content the backend may use for generation |
| Backend-authoritative AI state | BOTH | 6.13 | React presents grading/generation results while backend owns business semantics |
| Canonical entity ID vs association ID | DE | 6.13 | Prevents Lesson association IDs from being sent where reusable Vocabulary/Grammar IDs are required |
| Generated API contract | SYSTEM | 6.13 | Keeps frontend generation/result DTOs aligned with FastAPI OpenAPI |
| Server-state mutation handoff | SYSTEM | 6.13 | Generated DRAFT transitions immediately to the existing canonical editor |
| Mutation retry safety | SYSTEM | 6.13 | Avoids accidental duplicate AI generation requests |

Do not add RAG concepts.

Do not claim provider/model configuration as a frontend concept.

---

# 32. Tools Used

Record only tools actually used during implementation.

Expected likely set:

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

Do not list FastAPI/OpenAI/PostgreSQL as Step-6.13 tools unless production implementation actually changes or directly exercises them in this Step Note workflow.

---

# 33. Constraints / Non-goals

Do not implement:

```text
provider/model picker
prompt editor
temperature controls
reasoning controls
AI_GENERATION_MAX_OUTPUT_TOKENS control

Document-backed generation
RAG generation controls
external/web retrieval
source_refs UI
raw model output

streaming
SSE
WebSocket
progress percentage

auto-publish
human grading queue
new AI route/app
new state library
new backend endpoint
new database migration
Step 7.4+ work
```

Frontend must never expose provider secrets.

---

# 34. Stop Conditions

Stop and return:

```text
BLOCKED — Decision Needed
```

if actual repository execution reveals a material conflict such as:

```text
generate-draft request/response differs from the reviewed generated contract
Periodic-Test canonical ID semantics differ
required discovery endpoint is missing
existing Admin editor cannot load generated DRAFT
Attempt result no longer exposes required grading fields
a backend/public API change becomes necessary
a migration becomes necessary
a new dependency becomes materially necessary
auth/session architecture would need change
```

Do not silently invent a replacement contract.

---

# 35. Required Completion Report

Return:

```text
Step
Status
What was implemented

Learner grading-result integration
UNCERTAIN presentation
Partial-credit presentation
GRADING_FAILED / AI_GRADING_UNAVAILABLE behavior

Generation API wrapper
Generation form
LESSON_EXERCISE scope UX
PERIODIC_TEST Lesson discovery
Vocabulary/Grammar canonical-ID handling
Question-type selector
Generation pending state
Generation success handoff
Generation error mapping
Explicit retry behavior

Files changed
Dependencies changed
Backend changes
OpenAPI/generated changes
Migration changes

Focused tests
Full frontend tests
Build
Lint
api:check

Step Note
Concepts added
Tools added

Problems / risks
Deviations
Decisions needed
Recommended next action
Focused handoff ZIP path
```

Do not claim PM acceptance.

Package a focused Step-6.13 handoff ZIP containing only files needed for independent App Engineering Specialist review. Exclude dependency caches, build output, secrets, `.env`, database dumps, and unrelated repository files.
