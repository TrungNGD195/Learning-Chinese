# Codex Execution Task — Step 4.3: Learning UI

## Execution Gate

This is the **single current Codex execution task** for:

**Step 4.3 — Learning UI**

Owner: **App Engineering Specialist**

Implement Step 4.3 only.

Do **not** begin Step 4.4 AI Chat behavior, Step 4.5 TanStack Query/session/error foundation, Step 4.6 Auth/Profile UI, Step 4.7 Admin UI, or later phases.

Before editing, inspect the actual repository and the canonical PM Decision Log. Expected accepted state:

- backend complete through Step 3.6;
- frontend complete through Step 4.2;
- Step-4.2 `apiClient`, feature API modules and generated `src/types/api.generated.ts` exist and are the required HTTP boundary;
- D-033, D-034, D-035 and D-036 are DECIDED and authoritative;
- Step 4.3 has not yet been implemented;
- TanStack Query is not yet installed/used by the frontend;
- Lesson AI Chat remains structural only.

If the execution checkout materially differs, if actual Step-3.4 runtime payloads contradict D-033, or if D-033 cannot be implemented without service/business-rule/database redesign, stop and report `BLOCKED` with evidence rather than inventing a new contract.

---

# 1. Objective

Implement the learner-facing UI for:

- Dashboard/current learning position needed by this Step;
- HSK curriculum presentation;
- Lesson content;
- Vocabulary;
- Grammar;
- Lesson Exercises;
- Assessments;
- Assessment Results;
- Progress.

Use the accepted Step-4.2 feature API modules and generated OpenAPI contracts.

Required mental model:

```text
Backend-owned state
→ Step-4.2 feature API
→ learner-facing React UI
→ explicit learner interaction
→ Step-4.2 feature API
→ backend-authoritative result
→ render returned/refetched state
```

The frontend remains presentation-focused. It must not become authoritative for:

```text
lesson unlock
curriculum availability
theory completion
assessment grading
correctness
score
pass/fail
HSK progression
next-unit selection
progress percentage
```

---

# 2. Source of Truth

## Primary Step

Use:

```text
Spec-CURRENT/Phase4/Step 4.3 — Learning UI.md
```

If the checkout uses the bundled source pack, use the Step-4.3 section in:

```text
02_APP_ENGINEERING_SPECS_PHASE3-4.md
```

## Required decisions

Read the canonical Decision Log before editing and preserve at least:

```text
D-009 — Canonical question payload/grading contract
D-010 — AI grading unavailable / GRADING_FAILED semantics
D-027 — frontend runtime/package workflow
D-028 — React Router Data Mode / approved routes
D-029 — frontend unit/component testing baseline
D-030 — OpenAPI generation/contract ownership
D-031 — central apiClient / ApiError contract
D-032 — local Uvicorn runner for OpenAPI sync
D-033 — learner-facing OpenAPI contract hardening
D-034 — Vocabulary/Grammar viewed interaction
D-035 — multiple Lesson Exercises + explicit Attempt start
D-036 — AI grading failure / Assessment Result semantics
```

## Precedence

If sources differ:

1. latest canonical PM Decision Log;
2. authoritative Step 4.3 specification;
3. later accepted refinement intentionally changing an earlier contract;
4. accepted backend/frontend implementation and current OpenAPI;
5. earlier project/context notes;
6. this reviewed execution packet.

Do not silently resolve material conflicts.

---

# 3. Current Accepted Repository State

## Backend

Relevant accepted modules include:

```text
backend/app/progress/
├── router.py
├── schemas.py
└── service.py

backend/app/curriculum/
├── router.py
├── repository.py
└── service.py

backend/app/exercise/
├── router.py
├── schemas.py
├── service.py
└── grading.py
```

The actual runtime payloads already contain the stable data required by Step 4.3, but several Pydantic response fields are currently loose `dict`/generic `str` contracts.

D-033 permits public **response-schema hardening only**. Do not redesign the services to manufacture new product data.

## Frontend

Relevant accepted Step-4.2 structure includes:

```text
frontend/src/lib/api/
frontend/src/types/api.generated.ts

frontend/src/features/dashboard/api.ts
frontend/src/features/curriculum/api.ts
frontend/src/features/lesson/api.ts
frontend/src/features/assessment/api.ts
frontend/src/features/progress/api.ts
```

Current structural pages include:

```text
DashboardPage
HskCurriculumPage
LessonPage
AssessmentPage
AssessmentResultPage
ProgressPage
```

Preserve the approved routes:

```text
/dashboard
/hsk/:hskLevel
/lessons/:lessonId
/assessments/:assessmentId
/assessment-attempts/:attemptId/result
/progress
```

Do not add `/learn` or `/chat`.

---

# 4. Mandatory D-033 — Learner-Facing OpenAPI Contract Hardening

## 4.1 Scope

Strengthen Pydantic response typing while preserving the accepted runtime business behavior and persisted data semantics.

Allowed backend code changes should be limited to the learner-facing response schemas needed for D-033, expected primarily in:

```text
backend/app/progress/schemas.py
backend/app/exercise/schemas.py
```

Backend tests may be added/updated to verify the refined public contract.

Do **not** modify merely for D-033:

```text
SQLAlchemy models
Alembic migrations
repositories
service business rules
route paths/methods
progression/grading algorithms
authentication
Conversation behavior
```

If an actual runtime payload cannot validate against the hardened model without changing service/domain behavior, stop and report `BLOCKED`.

## 4.2 Progress/Lesson response types

Replace targeted loose dictionary fields with typed models matching the current runtime payloads exactly.

Define equivalent literals/types such as:

```text
UnitState
→ LOCKED | AVAILABLE | COMPLETED

UnitType
→ LESSON | PERIODIC_TEST

LessonStatus
→ DRAFT | PUBLISHED | ARCHIVED

AssessmentType
→ LESSON_EXERCISE | PERIODIC_TEST

AssessmentLifecycleStatus
→ DRAFT | REVIEW | PUBLISHED | ARCHIVED
```

Use the actual accepted runtime nullability.

### Vocabulary item

Typed payload equivalent to current runtime:

```text
VocabularyItemResponse
- id: UUID
- hanzi: string
- pinyin: string
- vietnamese_meaning: string
- part_of_speech: string | null
```

`VocabularyLessonItem` remains responsible for Lesson-specific fields:

```text
id                # LessonVocabulary link ID
order_index
note
example
item               # typed VocabularyItemResponse
```

Do not move `note`/`example` into the base Vocabulary item if runtime does not do that.

### Grammar item

Typed payload equivalent to current runtime:

```text
GrammarItemResponse
- id: UUID
- name: string
- structure: string | null
- explanation: string
- usage: string | null
```

`GrammarLessonItem` keeps:

```text
id                # LessonGrammar link ID
order_index
note
example
item               # typed GrammarItemResponse
```

### Theory-content progress

Use a typed model equivalent to:

```text
TheoryContentProgressResponse
- id: UUID       # LessonVocabulary or LessonGrammar link ID
- viewed: bool
```

Then:

```text
LessonProgressResponse.vocabulary
→ TheoryContentProgressResponse[]

LessonProgressResponse.grammar
→ TheoryContentProgressResponse[]
```

Do not change the runtime IDs from junction IDs to base entity IDs.

### HSK summary

Type the existing runtime shape equivalent to:

```text
HskSummaryResponse
- id: UUID
- level_number: int
- title: string | null
```

Use it for `CurriculumResponse.hsk` and the Dashboard `current_hsk` summary where runtime fields match.

Do not change `ProgressOverviewResponse.current_hsk`, which currently represents the HSK level number (`int | null`), into an object merely for consistency.

### Curriculum unit nested summaries

Type existing runtime Lesson summary:

```text
CurriculumLessonSummary
- id: UUID
- lesson_number: int
- title: string
- status: LessonStatus
```

Type existing runtime Assessment summary:

```text
CurriculumAssessmentSummary
- id: UUID
- title: string
- type: AssessmentType
- status: AssessmentLifecycleStatus
```

Then:

```text
UnitProgress.unit_type
→ UnitType

UnitProgress.lesson
→ CurriculumLessonSummary | null

UnitProgress.assessment
→ CurriculumAssessmentSummary | null
```

Do not invent fields not returned by the service.

### Dashboard current Lesson

The accepted Dashboard runtime currently includes a distinct current-Lesson shape containing:

```text
id
lesson_number
title
description
```

Use a dedicated typed Dashboard/current-Lesson summary if necessary so schema hardening does not add `description: null` to other runtime payloads that never returned a `description` field.

Preserve existing runtime field sets as closely as possible.

## 4.3 Continue Learning discriminated target

Make `DashboardResponse.continue_learning` type-safe enough to discriminate these backend-owned variants:

```text
PRONUNCIATION
→ section_id
→ code

LESSON
→ lesson_id

PERIODIC_TEST
→ assessment_id
```

Prefer an explicit Pydantic discriminated union on `type`.

The current response model historically serialized unrelated optional target fields as `null`. If needed to preserve the accepted serialized field set while obtaining TypeScript discrimination, variant models may keep irrelevant fields constrained to `None`.

Do not change target-selection logic in `progress.service.dashboard()`.

## 4.4 Assessment and Attempt literals

Harden:

```text
AssessmentResponse.type
AttemptResponse.status
AttemptHistoryItem.assessment_type
AttemptHistoryItem.status
AttemptDetailResponse.status
AttemptAnswerResult.grading_status
```

using accepted literals.

Attempt status set:

```text
IN_PROGRESS
SUBMITTED
GRADED
GRADING_FAILED
```

Answer grading status set:

```text
PENDING
GRADED
UNCERTAIN
FAILED
```

Do not remove accepted status values merely because one current synchronous service path does not normally materialize every intermediate status.

## 4.5 Typed Attempt answer/result details

Replace `AttemptAnswerResult.answer: dict | None` and `config: dict | None` with type-safe public result variants keyed by the existing `type` field.

Use a discriminated union equivalent to:

```text
multiple_choice result
fill_blank result
matching result
reorder_sentence result
translate_vi_zh result
translate_zh_vi result
sentence_writing result
```

Reuse compatible existing answer/config models where doing so preserves runtime serialization.

Expected answer shapes remain:

```text
multiple_choice
→ { option_id }

fill_blank
→ { text }

matching
→ { pairs: [{ left_id, right_id }] }

reorder_sentence
→ { item_ids }

translate_vi_zh
translate_zh_vi
sentence_writing
→ { text }
```

For submitted result/config review, type only material already present in the accepted public response. Do not expose new private answer-key data.

Important:

- current submitted Attempt detail already exposes `reference_answer`, `rubric`, and stored `config` where the accepted service includes them;
- preserve that existing public behavior;
- do not expose correct MCQ option flags because the accepted public result does not expose them.

The hardened result models should preserve common output fields:

```text
question_id
type
prompt
answer
grading_status
score
is_correct
feedback
reference_answer
rubric
config
```

with type-specific `answer`/`config` typing.

## 4.6 Backend/OpenAPI verification

Add/update focused backend tests proving:

- targeted schemas no longer expose loose generic objects for Step-4.3 fields;
- actual service/runtime payloads validate under the hardened response models;
- question learner payload answer-key safety remains unchanged before submission;
- accepted literal enums appear in OpenAPI;
- Continue Learning is discriminated/type-safe;
- Attempt answer result is type-safe enough for frontend review rendering;
- no route/method/schema business behavior changed.

Run the full backend regression suite.

After the backend response-schema refinement, use the existing D-030 flow:

```text
Terminal 1:
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000

Terminal 2:
cd frontend
npm ci
npm run api:generate
npm run api:check
```

Commit the regenerated:

```text
frontend/src/types/api.generated.ts
```

Do not manually edit generated TypeScript.

---

# 5. Frontend State Boundary for Step 4.3

Step 4.3 intentionally predates the Step-4.5 server-state foundation.

Allowed now:

```text
React useState
React useEffect
route params
navigate()
page-local data/loading/error state
component-local expanded/collapsed state
page-local mutation pending flags
temporary Assessment answer state
```

Do not introduce:

```text
TanStack Query
Redux
Zustand
custom global server-state store
query cache
query invalidation framework
session bootstrap
route guards
automatic 401 refresh/replay
global loading/error framework
```

Server data may be fetched page-locally through the accepted Step-4.2 API modules.

Do not call `fetch` directly from components.

Do not extend `apiClient` with new policy merely for Step 4.3.

Because `AbortSignal` remains deferred, a component may use a simple effect-lifetime guard to avoid applying stale results after unmount; do not redesign transport cancellation.

---

# 6. Dashboard / Current Learning Position

Upgrade the existing structural Dashboard only as needed for the Step-4.3 current-learning-position requirement.

Use:

```text
dashboardApi.getDashboard()
```

Render backend-owned values such as:

```text
current HSK
current curriculum unit
current Lesson when provided
progress_percentage
Continue Learning target
```

Do not reconstruct current/next curriculum logic locally.

Continue Learning routing must use the D-033 discriminated target:

```text
PRONUNCIATION
→ /pronunciation

LESSON + lesson_id
→ /lessons/:lessonId

PERIODIC_TEST + assessment_id
→ /assessments/:assessmentId
```

Do not automatically redirect.

If `continue_learning` is `null`, render an appropriate no-current-target/completed state without inventing a next target.

Use simple page-local loading/error states only.

---

# 7. HSK Curriculum Page

The approved route already exists:

```text
/hsk/:hskLevel
```

Make this learner-facing screen useful for the Step-4.3 learning flow.

The route parameter represents the visible HSK level number. Resolve it by:

```text
getHskLevels()
→ find level where level_number == route hskLevel
→ getCurriculum(level.id) or getHskProgress(level.id)
```

This ID lookup is navigation/presentation mapping, not progression authority.

Render ordered backend curriculum units with:

```text
LESSON
PERIODIC_TEST
LOCKED
AVAILABLE
COMPLETED
```

Use backend `order_index` and state.

For navigation:

```text
available/completed LESSON
→ /lessons/:lessonId

available/completed PERIODIC_TEST
→ /assessments/:assessmentId
```

Do not make a LOCKED unit actionable merely because it appears in the UI.

Do not calculate state from preceding units.

---

# 8. Lesson UI

Expected composition:

```text
LessonPage
├── LessonHeader
├── VocabularySection
├── GrammarSection
├── ExerciseSection
└── existing LessonChatRegion
```

AI Chat remains structural only.

Use:

```text
lessonApi.getLesson(lessonId)
progressApi.getLessonProgress(lessonId)
```

The Lesson request already uses backend access rules and may materialize accepted Lesson-start state. Do not duplicate those rules in React.

The header may display backend-provided:

```text
lesson number
title
description
HSK label when resolved from backend HSK data
started/theory-complete/completed state
```

Do not invent a client-owned `AVAILABLE` or `COMPLETED` transition.

---

# 9. Mandatory D-034 — Vocabulary Viewed Interaction

## 9.1 Presentation

Use learner-readable cards/list presentation.

Collapsed Vocabulary card should show concise supported content, e.g.:

```text
hanzi
pinyin
Vietnamese meaning
```

Expanded details may show existing public fields:

```text
part of speech
Lesson-specific example
Lesson-specific note
```

Do not invent missing fields.

## 9.2 Mutation semantics

Use LessonProgress backend state to determine whether the **LessonVocabulary link ID** is already viewed.

Rules:

```text
initial render
→ no mutation

initial fetch
→ no mutation

passive scroll/viewport
→ no mutation

first explicit expand/open of unviewed item
→ markVocabularyViewed(lessonId, lessonVocabularyLinkId)

already viewed
→ no mutation needed

mutation success
→ update presentation from the successful backend result/current link

mutation failure
→ keep item unviewed as persisted state
→ show a local action error
```

Do not pass base `Vocabulary.id` to the mark-viewed API.

If mutation fails while the card remains expanded, do not fake success. A later explicit re-open may retry; no global retry architecture is required.

Prevent duplicate same-item mutations while the local action is pending.

---

# 10. Mandatory D-034 — Grammar Viewed Interaction

Use the same semantics as Vocabulary.

Collapsed Grammar presentation:

```text
name
structure
```

Expanded content may show:

```text
explanation
usage
Lesson-specific example
Lesson-specific note
```

Use the **LessonGrammar link ID**, not base `Grammar.id`.

No mutation on render/fetch/scroll.

---

# 11. Theory State

Use backend `LessonProgressResponse`.

Frontend may derive purely presentational counts from backend-provided rows:

```text
Vocabulary: viewed N / total
Grammar: viewed N / total
```

These are display summaries only.

Authoritative theory completion is:

```text
theory_completed_at != null
```

Do not implement:

```text
local viewed count == total
→ mark/declare authoritative theory transition
```

When a successful mark-viewed response returns an updated `theory_completed_at`, the page may reflect that returned backend state.

There is no frontend `markTheoryComplete()` operation.

---

# 12. Mandatory D-035 — Lesson Exercises

`LessonResponse.assessment_ids` may contain:

```text
zero
one
multiple
```

Render **every** returned Lesson Exercise in backend-returned presentation order.

Do not use:

```text
assessment_ids[0]
```

as a primary/canonical Assessment.

Because LessonResponse currently exposes IDs rather than exercise titles, a simple learner-facing presentation is sufficient:

```text
Exercise 1
Exercise 2
...
```

Do not make additional requests merely to invent a primary exercise.

Selecting an exercise navigates to:

```text
/assessments/:assessmentId
```

Do not create an Attempt from LessonPage.

---

# 13. Assessment Route / Explicit Attempt Start

On route:

```text
/assessments/:assessmentId
```

initial mount must:

```text
getAssessment(assessmentId)
→ render Assessment metadata/questions preview/start state
```

It must **not** call `startAttempt()` on mount.

Before an Attempt begins, expose an explicit action:

```text
Start Assessment
or
Start / Resume Assessment
```

Only that action calls:

```text
assessmentApi.startAttempt(assessmentId)
```

The backend determines whether this returns an existing `IN_PROGRESS` Attempt or creates the next Attempt.

After successful start/resume, retain the returned `attempt.id` in page-local state and enter the question workflow.

Do not persist that ID in browser storage.

Disable duplicate Start/Resume clicks while the action is pending.

---

# 14. Assessment Shell

Use one shared shell for:

```text
LESSON_EXERCISE
PERIODIC_TEST
```

Do not create separate assessment architectures.

Suggested responsibilities:

```text
AssessmentPage
├── AssessmentHeader
├── question number/progress
├── QuestionRenderer
├── Previous/Next navigation
└── Submit action
```

Question navigation is local UI state only.

Do not grade locally while moving between questions.

---

# 15. QuestionRenderer

Use the exact backend discriminants:

```text
multiple_choice
fill_blank
matching
reorder_sentence
translate_vi_zh
translate_zh_vi
sentence_writing
```

Type-driven mapping:

```text
multiple_choice
→ MultipleChoiceQuestion

fill_blank
→ FillBlankQuestion

matching
→ MatchingQuestion

reorder_sentence
→ ReorderQuestion

translate_vi_zh
translate_zh_vi
sentence_writing
→ FreeTextQuestion
```

Do not compare against invented uppercase frontend enum values.

## Learner controls

Keep dependency-light:

```text
multiple choice
→ radio controls

fill blank
→ text input

matching
→ simple accessible pairing controls/selectors

reorder sentence
→ simple move-up/move-down or equivalent dependency-free ordering control

free text
→ textarea
```

Do not add a drag-and-drop package solely for reorder.

The learner Assessment payload before submission must not expose answer-key material beyond what the accepted backend already provides.

---

# 16. Temporary Answer State

Use page-local React state equivalent to:

```text
questionId
→ DraftAnswer | undefined
```

A small frontend-only `DraftAnswer` type is allowed because this is temporary form/UI state, **not** a duplicate backend DTO.

At submission, map drafts to the generated `SubmitAttemptRequest` using `question.type`.

Exact outbound answer shapes:

```text
multiple_choice
→ { option_id }

fill_blank
→ { text }

matching
→ { pairs: [{ left_id, right_id }] }

reorder_sentence
→ { item_ids }

translate_vi_zh
translate_zh_vi
sentence_writing
→ { text }
```

Before submit, require one valid local answer for every question because the accepted backend requires exactly one answer per Question.

This client validation is usability only; backend validation remains authoritative.

Do not store temporary answers in:

```text
localStorage
sessionStorage
backend autosave
global store
```

Do not calculate correctness or score.

---

# 17. Submission Semantics

Submission flow:

```text
page-local draft answers
→ map to generated SubmitAttemptRequest
→ assessmentApi.submitAttempt(attemptId, body)
→ backend grading
```

Disable duplicate Submit while the action is pending.

## Successful graded submission

For successful `GRADED` response:

```text
navigate /assessment-attempts/:attemptId/result
```

Do not use locally calculated score/pass state.

## Non-special submission failure

For network/validation/other business failures:

```text
remain on Assessment page
preserve temporary answers
show a simple page/action-local error
no automatic retry
```

Do not clear answers on failure.

---

# 18. Mandatory D-036 — AI_GRADING_UNAVAILABLE

If `submitAttempt()` throws `ApiError` with:

```text
code == AI_GRADING_UNAVAILABLE
```

respect the accepted backend semantics:

```text
answers already persisted
Attempt already persisted as GRADING_FAILED
HTTP response is 503
```

Frontend behavior:

```text
AI_GRADING_UNAVAILABLE
→ navigate /assessment-attempts/:attemptId/result
→ Result page calls getAttempt(attemptId)
→ render GRADING_FAILED
```

Do not blindly submit the same Attempt again.

Do not treat this specific 503 as proof that no business state was persisted.

---

# 19. Assessment Result Page

Route:

```text
/assessment-attempts/:attemptId/result
```

Load authoritative result through:

```text
assessmentApi.getAttempt(attemptId)
```

Also use backend state such as `getDashboard()` where necessary to determine a backend-owned Continue Learning target after completion.

Do not calculate a next target from curriculum arrays locally.

## 19.1 Attempt status

Render backend status explicitly.

Important terminal cases:

```text
GRADED
GRADING_FAILED
```

If a non-terminal historical/hand-entered route such as `IN_PROGRESS`/`SUBMITTED` is encountered, render a safe state without inventing a grade.

## 19.2 Per-answer result

Use backend fields:

```text
grading_status
score
is_correct
feedback
reference_answer/config where public
```

Rules:

```text
grading_status == UNCERTAIN
→ neutral "Uncertain" / "Needs review"
→ never render as Incorrect

grading_status == FAILED
→ grading failure state
→ do not invent correctness

GRADED + is_correct == true
→ correct presentation

GRADED + is_correct == false
→ incorrect presentation
```

Do not infer hidden answer keys.

For MCQ, do not invent the correct option because the accepted result contract does not expose correct-option flags.

## 19.3 Failed/Retry flow

For:

```text
passed == false
or
status == GRADING_FAILED
```

provide learner-facing Retry behavior:

```text
Retry
→ /assessments/:assessmentId
```

The learner then explicitly Start/Resumes through D-035.

Do not automatically create or submit another Attempt.

## 19.4 Passed flow

For a backend-passed result, show completion/result state and a Continue Learning action **only when backend Dashboard returns a target**.

Use the same D-033 target routing:

```text
PRONUNCIATION → /pronunciation
LESSON → /lessons/:lessonId
PERIODIC_TEST → /assessments/:assessmentId
```

Do not automatically redirect.

If backend returns no target, do not invent Next Lesson.

---

# 20. Progress Page

Route:

```text
/progress
```

Use:

```text
progressApi.getProgressOverview()
progressApi.getHskProgress(hskId)
```

Use `getLessonProgress()` where a Lesson-specific detail is genuinely rendered.

The Progress page should visibly represent:

```text
Pronunciation Foundations
HSK1
HSK2
HSK3
LESSON curriculum units
PERIODIC_TEST curriculum units
```

Use the IDs returned in `ProgressOverviewResponse.hsk_levels` to obtain HSK progress. With the current V0 three-level scope, a simple page-local parallel load is acceptable; do not introduce a cache framework.

Render backend values directly:

```text
progress_percentage
HSK state
unit state
unit order
pronunciation_complete
```

Do not independently recompute authoritative percentages.

Lesson progress currently supports:

```text
started_at
theory_completed_at
completed_at
viewed Vocabulary links
viewed Grammar links
```

Do not fabricate unsupported metrics such as:

```text
latest assessment score
best assessment score
attempt count
```

unless the actual accepted/hardened contract explicitly starts returning them through an approved backend change. D-033 alone does not add those metrics.

Periodic Tests must remain visible as real curriculum units.

---

# 21. Responsive Scope

Use existing simple CSS conventions and make the learner flows functionally usable on:

```text
desktop
tablet
mobile
```

Allowed small CSS extensions:

- readable content cards;
- wrapping controls;
- stacked mobile layouts;
- touch-friendly buttons/inputs;
- simple status badges/labels;
- assessment navigation layout.

Do not introduce:

```text
Tailwind
MUI
new design system
animation framework
pixel-perfect redesign
```

No new UI dependency is expected.

---

# 22. Error / Loading Scope

Step 4.3 needs only local usability states.

Allowed:

```text
Loading lesson...
Could not load lesson
Saving viewed state...
Could not save viewed state
Submitting...
Could not submit
```

Use `ApiError.code` for the D-036 special behavior.

Do not build:

```text
global toast system
global Error Boundary architecture
global retry policy
query retry policy
401 refresh orchestration
```

Those remain Step 4.5 responsibilities.

---

# 23. Files / Components

Exact filenames may differ, but preserve feature boundaries and avoid giant page components.

Expected areas may include:

```text
frontend/src/features/dashboard/
frontend/src/features/curriculum/
frontend/src/features/lesson/
frontend/src/features/assessment/
frontend/src/features/progress/
```

Reasonable decomposition:

```text
lesson/
├── LessonPage
├── LessonHeader
├── VocabularySection
├── VocabularyCard
├── GrammarSection
├── GrammarCard
└── ExerciseSection

assessment/
├── AssessmentPage
├── AssessmentResultPage
├── QuestionRenderer
└── question-types/

progress/
├── ProgressPage
├── HskProgress
└── CurriculumProgress
```

Do not create empty files/directories merely to match this suggestion.

Preserve:

```text
features/conversation/LessonChatRegion
```

as structural only.

---

# 24. Testing Requirements

Use existing:

```text
Vitest
jsdom
React Testing Library
```

Mock Step-4.2 feature API functions/responses. Normal frontend component tests must not require FastAPI/PostgreSQL.

## 24.1 D-033 backend/OpenAPI tests

Cover at minimum:

```text
Vocabulary nested item typed
Grammar nested item typed
LessonProgress theory rows typed
UnitProgress lesson/assessment typed
Dashboard summaries typed
ContinueLearning variants discriminated
Assessment type literal
Attempt status literals
grading_status literals
Attempt answer/result type-safe variants
runtime payload validation remains compatible
```

Retain the existing D-009 tests proving answer-key material is not exposed before submission.

## 24.2 Lesson tests

Cover:

```text
Lesson content renders from mocked backend data
LessonChatRegion remains present but structural
no Vocabulary viewed mutation on mount/fetch
no Grammar viewed mutation on mount/fetch
first explicit unviewed Vocabulary expansion calls markVocabularyViewed
first explicit unviewed Grammar expansion calls markGrammarViewed
already-viewed item does not require mutation
mutation failure does not fake viewed success
mark-viewed calls use junction/link IDs
backend theory_completed_at drives theory-complete presentation
local counts do not create a theory-complete mutation
```

## 24.3 Exercise/Assessment tests

Cover:

```text
zero/one/multiple assessment_ids render safely
all multiple Lesson Exercises are represented
assessment_ids[0] is not treated as canonical business target
selecting an exercise navigates to selected assessment
Assessment route mount calls getAssessment but not startAttempt
explicit Start/Resume calls startAttempt
returned attempt ID enters local question workflow
```

QuestionRenderer must test every accepted type:

```text
multiple_choice
fill_blank
matching
reorder_sentence
translate_vi_zh
translate_zh_vi
sentence_writing
```

Test exact temporary-answer → submission request shape for every family.

Assert no frontend grading/correctness calculation is used.

## 24.4 Submission/result tests

Cover:

```text
successful GRADED submit → result route
AI_GRADING_UNAVAILABLE → same attempt result route
AI_GRADING_UNAVAILABLE does not re-submit same Attempt
other submit failure preserves draft answers
GRADING_FAILED renders from getAttempt backend state
UNCERTAIN renders neutral and not Incorrect
FAILED grading status does not invent correctness
failed/not-passed result exposes Retry
Retry navigates to assessment and does not create Attempt itself
passed result exposes Continue only from backend target
null Continue target does not invent Next Lesson
```

## 24.5 Curriculum/progress tests

Cover:

```text
HSK route resolves backend HSK ID by level_number
LOCKED unit is not made actionable
LESSON and PERIODIC_TEST both render
Periodic Test is not hidden
backend progress_percentage is rendered exactly
frontend does not independently recalculate authoritative percentage
Progress page shows pronunciation/HSK state from backend
Continue Learning routing follows typed backend target
```

## 24.6 Scope/boundary tests

Preserve/extend source-boundary checks as practical so Step 4.3 does not introduce:

```text
direct fetch from components
localStorage/sessionStorage assessment persistence
TanStack Query
Redux/Zustand
/chat route
AI Chat behavior
```

Avoid brittle whole-source snapshots.

---

# 25. Verification Commands

## Backend

From `backend/`:

```text
uv sync
uv run pytest -q
```

If the repository already uses additional accepted backend checks such as app import/OpenAPI assertions, keep them passing.

No Alembic migration is expected for Step 4.3.

## OpenAPI regeneration

Start the accepted backend using D-032:

```text
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then from `frontend/`:

```text
npm ci
npm run api:generate
npm run api:check
```

## Frontend

With the generated artifact committed, verify normal operation independently of the running backend:

```text
npm run build
npm run test -- --run
```

Normal build/test must continue to work with FastAPI stopped.

Do not manually edit `api.generated.ts` to make tests pass.

---

# 26. Explicit Scope Guardrails

Do not implement in Step 4.3:

```text
AI Chat interaction behavior
Conversation list/panel
Message send/retry
streaming
SSE
WebSocket

TanStack Query
server-state cache
query invalidation
session bootstrap
route guards
automatic 401 refresh/replay
global loading/error architecture

Auth/Profile forms
Admin core UI
Document ingestion

XP
streaks
badges
leaderboards
hearts
SRS
vocabulary mastery
weak-vocabulary scoring

assessment autosave
browser-persisted answers

new UI framework/design system
drag-and-drop dependency
```

Do not modify backend business logic under the label of D-033.

Do not create new learner API endpoints.

Do not add a database migration.

---

# 27. Expected Concepts

## MUST KNOW

| Concept | Category | Role |
|---|---|---|
| Backend-authoritative state | SYSTEM | React renders backend decisions instead of becoming business authority |
| Local UI state | SYSTEM | Expanded cards/current question/navigation state |
| Temporary/form state | SYSTEM | Unsubmitted Assessment answers |
| Type-driven rendering | SYSTEM | Question type selects renderer and submission mapping |
| Discriminated union | SYSTEM | Safe Continue Learning/question/result variants |
| Idempotent mutation | SYSTEM | Theory viewed actions |
| Assessment lifecycle | SYSTEM | Explicit start → submit → persisted result |
| Generated API contract | SYSTEM | Pydantic/OpenAPI remains DTO authority |
| AI grading uncertainty | AI | `UNCERTAIN` is distinct from incorrect |
| Technical grading failure | BOTH | `AI_GRADING_UNAVAILABLE` with persisted `GRADING_FAILED` state |

## SHOULD KNOW

| Concept | Category | Role |
|---|---|---|
| Derived presentation | SYSTEM | Display counts from backend facts without creating business transitions |
| Page-local async state | SYSTEM | Temporary pre-TanStack Query loading/error/pending handling |
| Responsive composition | SYSTEM | Functional learner UI across common screen sizes |

## AWARENESS ONLY

```text
TanStack Query will replace/refine page-local server-state handling in Step 4.5.
```

---

# 28. Tools Actually Expected

| Tool | Category | Role |
|---|---|---|
| Python/Pydantic | SYSTEM | D-033 response-contract hardening |
| FastAPI OpenAPI | SYSTEM | Canonical backend contract |
| uv/Uvicorn | SYSTEM | Backend verification + OpenAPI sync |
| openapi-typescript | SYSTEM | Regenerate frontend contract |
| React | SYSTEM | Learner UI/local state |
| TypeScript | SYSTEM | Type-safe question/result rendering |
| React Router | SYSTEM | Lesson/Assessment/Result/Continue navigation |
| native Step-4.2 feature APIs | SYSTEM | Backend integration boundary |
| CSS | SYSTEM | Minimal responsive learner presentation |
| Vitest | SYSTEM | Frontend tests |
| React Testing Library | SYSTEM | Learner interaction tests |
| pytest | SYSTEM | Backend contract/regression tests |

Do not add a new runtime dependency unless a genuine blocker is discovered and reported first.

---

# 29. Step Note

Create/update:

```text
docs/frontend/step-4.3-learning-ui.md
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

Document the central flow:

```text
backend state
→ feature API
→ page-local presentation state
→ explicit learner action
→ backend mutation/grading
→ backend-authoritative response
→ rendered state
```

Explicitly document:

- D-033 typed contract refinement;
- D-034 explicit expansion=viewed semantics;
- D-035 explicit Attempt creation;
- D-036 persisted grading-failure semantics;
- why temporary Assessment answers are local form state;
- why TanStack Query is intentionally deferred to Step 4.5.

Do not document future AI Chat behavior as implemented.

---

# 30. Acceptance Criteria

Step 4.3 is complete only when all are true:

## D-033 contract

- [ ] Target learner-facing `dict`/generic status schemas are hardened with typed Pydantic response models/literals.
- [ ] Hardened schemas match existing runtime payloads without DB/service/business-rule redesign.
- [ ] Continue Learning is type-safe by backend-owned target variant.
- [ ] Attempt answer/result review is type-safe enough for UI without frontend DTO casts.
- [ ] Generated OpenAPI TypeScript is regenerated through D-030, not manually edited.
- [ ] `api:check` passes.

## Lesson/theory

- [ ] Lesson page renders backend Lesson + LessonProgress data.
- [ ] Vocabulary/Grammar are learner-readable.
- [ ] Initial render/fetch/scroll never marks theory content viewed.
- [ ] First explicit expansion of an unviewed item invokes the correct backend mutation with the junction ID.
- [ ] Failed mark-viewed mutation does not fake success.
- [ ] Theory completion is rendered from backend state.
- [ ] Frontend has no `markTheoryComplete` logic.

## Exercise/Assessment

- [ ] All Lesson Exercise IDs are represented; no hidden primary assessment rule exists.
- [ ] Assessment route mount does not create an Attempt.
- [ ] Explicit Start/Resume calls `startAttempt`.
- [ ] One shared Assessment shell handles Lesson Exercises and Periodic Tests.
- [ ] All seven backend Question types render through type-driven logic.
- [ ] Exact accepted answer shapes are submitted.
- [ ] Temporary answers are page-local only.
- [ ] Frontend does not grade or calculate score/pass/fail.

## Result

- [ ] Successful graded submission navigates to the Result route.
- [ ] `AI_GRADING_UNAVAILABLE` navigates to the same Attempt's Result route after persisted failure.
- [ ] The same `GRADING_FAILED` Attempt is not blindly resubmitted.
- [ ] `UNCERTAIN` is not shown as incorrect.
- [ ] Result Retry returns to the selected Assessment for an explicit next Attempt action.
- [ ] Passed Continue/Next behavior uses backend Dashboard target only.

## Progress/navigation

- [ ] HSK Curriculum shows ordered Lessons and Periodic Tests with backend state.
- [ ] Progress page shows Pronunciation + HSK progression and does not hide Periodic Tests.
- [ ] Backend `progress_percentage` values are rendered without independent authoritative recomputation.
- [ ] Dashboard Continue Learning follows the backend discriminated target.

## Boundaries

- [ ] Existing Lesson Chat region remains structural only.
- [ ] No TanStack Query/Redux/Zustand/global cache was added.
- [ ] No route guards/session restoration/401 replay were added.
- [ ] No direct component `fetch` was added.
- [ ] No browser-persisted Assessment answers were added.
- [ ] No database migration or backend business-rule change was added.
- [ ] Backend regression tests pass.
- [ ] Frontend build/tests pass.
- [ ] Step Note reflects actual implementation.

---

# 31. Completion Report Required from Codex

Return a concise handoff containing:

```text
Step
Status
Implementation plan executed
Files created
Files modified
Dependencies added/removed
D-033 schema hardening implemented
Generated OpenAPI changes
Lesson UI implemented
Vocabulary/Grammar viewed behavior
Exercise/Attempt lifecycle behavior
QuestionRenderer coverage
Submission/result behavior
Progress/Continue-Learning behavior
State-management boundary
Tests / verification
Acceptance criteria
Step Note
Concepts actually used
Tools actually used
Deviations
Problems / risks
Decisions needed
Recommended next action
Handoff ZIP path
```

The implementation report must not claim PM acceptance.

Package a handoff ZIP that contains only files needed to review Step 4.3 changes plus a clear manifest; exclude dependency caches/build output/secrets.

---

# 32. Stop Conditions

Stop and report `BLOCKED` instead of inventing a contract if any of these occur:

- actual runtime learner payload materially contradicts D-033;
- typed Pydantic hardening requires database/model/service/business-rule redesign;
- generated OpenAPI cannot represent the required result/question structures without a public API decision;
- actual Step-4.2 wrapper no longer matches accepted backend endpoints;
- Lesson Exercise discovery would require a new primary-assessment rule;
- Attempt lifecycle contradicts D-035;
- `AI_GRADING_UNAVAILABLE` runtime behavior contradicts D-036;
- Step 4.3 cannot be made usable without introducing a global server-state convention owned by Step 4.5;
- another material architecture/public-contract decision is required.

Do not silently choose around any such issue.
