# Step 4.3 — Learning UI

## Objective

Implement the learner-facing Dashboard, HSK curriculum, Lesson, Assessment, Assessment Result and Progress flows using the accepted Step-4.2 feature APIs and generated OpenAPI contract.

## Why

Learning state, theory completion, grading and progression belong to the backend. This UI presents those decisions and sends only explicit learner actions back through the established API boundary.

## Mental Model

```text
backend state
→ feature API
→ page-local presentation state
→ explicit learner action
→ backend mutation/grading
→ backend-authoritative response
→ rendered state
```

Assessment answers stay in page-local React form state until explicit submission. They are not persisted by the browser or autosaved.

## Core Knowledge

- Pydantic response schemas remain the source for OpenAPI and generated TypeScript contracts.
- Discriminated unions select Continue Learning routes and question/result rendering without handwritten API DTO copies.
- Vocabulary and Grammar viewed actions are explicit, idempotent learner interactions keyed by Lesson junction IDs.
- Assessment route visits load metadata only. Persistent Attempt creation/resume follows the explicit Start / Resume action.
- `UNCERTAIN` is a neutral backend grading state; `FAILED` and `GRADING_FAILED` represent technical grading failure.
- Backend progress percentages and curriculum states are rendered directly.
- TanStack Query is intentionally deferred to Step 4.5, which owns server-state caching and shared session/error behavior. Step 4.3 uses effect-driven requests and page-local loading, error and form state.

## Data Flow

Dashboard, HSK curriculum, Lesson, Assessment, Result and Progress pages call the accepted feature API functions. Those wrappers use the central Step-4.2 `apiClient`; components do not call `fetch` or construct backend URLs.

Lesson loading is ordered: the page awaits `getLesson` (which may persist `started_at`) before reading `getLessonProgress`. When a learner opens unviewed theory content, the page sends the corresponding LessonVocabulary or LessonGrammar link ID. After a successful viewed mutation, it refetches and replaces the full Lesson progress response, including timestamps and viewed rows. The UI does not derive completion locally.

Assessment drafts map to the accepted generated `SubmitAttemptRequest` shapes by question discriminant. Result review resolves Matching and Reorder answer IDs to readable text using the public result config. The UI renders the backend Attempt result and does not calculate correctness, score, pass/fail or progression; MCQ review does not expose a correct option.

## Key Design Decisions

- **D-033:** Typed learner response schemas now cover nested Vocabulary/Grammar items, theory progress, HSK and curriculum summaries, Dashboard summaries, Continue Learning targets, Assessment/Attempt literals, and type-specific Attempt answer/result variants. Runtime service logic and route contracts remain unchanged. The generated API types were refreshed through the running FastAPI OpenAPI workflow.
- **D-034:** Initial render/fetch and passive viewing do not mark content viewed. The first explicit expansion of an unviewed card sends its junction ID. Failed mutations leave the presentation unviewed and show a local error.
- **D-035:** All returned Lesson Exercise IDs are shown in order. Assessment route mount calls `getAssessment` only; Start / Resume is the only action that calls `startAttempt`.
- **D-036:** A successful graded submission navigates to its Attempt result. `AI_GRADING_UNAVAILABLE` navigates to the same persisted Attempt result and never retries that Attempt automatically. Other failures preserve local draft answers.
- Assessment drafts are local form state because they are temporary input, not server state or persisted learning data.
- Progress summaries display backend values. HSK/periodic units use backend ordering and states; no next unit is selected in React.
- Lesson Chat remains the accepted structural region only.

## Reusable Approach

Keep each page on its feature API boundary, use generated contracts to select variants, and keep temporary interaction state beside the page that owns the interaction. Send mutations only after deliberate learner input, then render their returned state. Keep business authority with backend services.

## Common Mistakes

- Marking theory viewed during data loading, scrolling or viewport observation.
- Passing a base Vocabulary/Grammar ID instead of the Lesson junction ID.
- Treating the first `assessment_ids` entry as a primary exercise.
- Starting an Attempt on Assessment route mount.
- Retrying the same Attempt after `AI_GRADING_UNAVAILABLE`.
- Showing `UNCERTAIN` as incorrect or deriving score/progression in the browser.
- Editing `api.generated.ts` by hand, calling `fetch` in a component, or persisting Assessment drafts in browser storage.

## Definition of Done

- Dashboard and backend-directed Continue Learning targets render without automatic redirects.
- HSK curriculum and Progress include backend LESSON and PERIODIC_TEST units and backend states/percentages.
- Lesson theory, Exercise links, Assessment lifecycle, all seven question renderers and result review are implemented.
- D-033 schemas validate the existing runtime shapes; the generated API contract matches live OpenAPI.
- Backend and frontend regression suites pass; frontend build and tests pass with FastAPI stopped.
- No database migration or dependency addition was required.
- Implementation is ready for independent App Engineering Specialist review; PM acceptance remains separate.

## Concepts Discovered

| Concept | Category | Role |
|---|---|---|
| Backend-authoritative state | SYSTEM | Keeps completion, grading and progression decisions in the backend. |
| Local UI/form state | SYSTEM | Holds expanded cards, question navigation and temporary answers. |
| Discriminated union | SYSTEM | Selects Continue Learning destinations and safe question/result variants. |
| Idempotent mutation | SYSTEM | Records explicit Vocabulary/Grammar viewing with junction IDs. |
| Assessment lifecycle | SYSTEM | Separates metadata loading, explicit Attempt start, submit and persisted result. |
| Derived presentation | SYSTEM | Displays viewed counts without creating a completion transition. |
| AI grading uncertainty | AI | Presents `UNCERTAIN` neutrally. |
| Technical grading failure | BOTH | Presents persisted `GRADING_FAILED` state without duplicate submission. |
| Generated API contract | SYSTEM | Keeps frontend response types aligned with FastAPI OpenAPI. |

## Tools Used

| Tool | Category | Role |
|---|---|---|
| Python / Pydantic | SYSTEM | Refined public response schema types. |
| FastAPI OpenAPI | SYSTEM | Supplied the generated API contract. |
| uv / Uvicorn | SYSTEM | Ran backend verification and local OpenAPI synchronization. |
| openapi-typescript | SYSTEM | Regenerated `api.generated.ts` through the accepted workflow. |
| React / TypeScript | SYSTEM | Built learner pages, local interaction state and typed rendering. |
| React Router | SYSTEM | Resolved approved routes and backend-directed navigation. |
| Step-4.2 feature APIs | SYSTEM | Kept page requests behind the established client. |
| CSS | SYSTEM | Added responsive, dependency-light presentation. |
| pytest | SYSTEM | Verified response schemas and backend regressions. |
| Vitest / React Testing Library | SYSTEM | Tested learner interactions and routing behavior. |
