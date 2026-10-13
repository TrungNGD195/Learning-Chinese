# Codex Execution Task — Step 4.1: Frontend Structure

## Execution Gate

This is the **single current Codex execution task** for:

**Step 4.1 — Frontend Structure**

Owner: **App Engineering Specialist**

Implement Step 4.1 only.

Do **not** begin Step 4.2 or any later Phase-4 feature work.

Before editing, inspect the actual repository. The accepted state after Step 3.6 has no existing `frontend/` application directory. If the execution checkout materially differs from that accepted state, or if the canonical PM Decision Log conflicts with this task, stop and report `BLOCKED` instead of inventing a new frontend architecture.

Do not modify backend code unless a genuine blocking backend contract defect is discovered. A frontend inconvenience is not a backend defect.

---

# 1. Objective

Create the structural frontend foundation for the Chinese-learning application using the frozen Phase-4 frontend baseline.

Step 4.1 establishes:

- a Vite + React + TypeScript browser application under `frontend/`;
- the Phase-4 Node/npm/package-lock workflow;
- React Router Data Mode wiring;
- the exact Public / Learner / Admin route map;
- `PublicLayout`, `LearnerLayout`, and `AdminLayout`;
- lightweight route-resolving page/screen skeletons;
- a feature-oriented source structure;
- a structural Lesson AI Chat region only;
- a structural Admin Documents page only;
- the Phase-4 Vitest + jsdom + React Testing Library baseline;
- focused route/layout/component tests;
- the Step 4.1 documentation note.

This Step is a **frontend structural foundation**, not an API-integration or feature-implementation Step.

Mental model:

```text
Browser
→ React Router
→ Layout
→ Feature Page / Screen
```

Later Steps will extend this to:

```text
Browser
→ React Router
→ Layout
→ Feature Page / Screen
→ frontend API/state layer
→ FastAPI Backend
```

Do not pull the later layers into Step 4.1.

---

# 2. Source of Truth

## Primary authoritative Step

Use:

```text
Spec-CURRENT/Phase4/Step 4.1 — Frontend Structure.md
```

If the execution checkout uses the bundled source-pack form instead, consult the Step-4.1 section in:

```text
02_APP_ENGINEERING_SPECS_PHASE3-4.md
```

## Required project/control sources

Read before editing:

```text
Spec-CURRENT/PROJECT_CONTEXT.md
Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md
Spec-CURRENT/PM-Control/05-Codex-Execution-Protocol.md
```

The canonical Decision Log used for this task must contain:

```text
D-027 — Phase 4 Frontend Runtime and Package Workflow
D-028 — Phase 4 Client-Side Routing Baseline
D-029 — Phase 4 Frontend Unit / Component Testing Baseline
```

Also inspect later Phase-4 specifications only enough to avoid pre-building their responsibilities.

## Precedence

If sources differ, use:

1. canonical PM Decision Log;
2. authoritative Step 4.1 specification;
3. later specification intentionally refining an earlier contract;
4. earlier Phase/project context;
5. notes/examples/plans;
6. this task only as the reviewed execution packet implementing the sources above.

Do not invent a resolution to a material conflict.

---

# 3. Current Accepted Repository State

The accepted backend is complete through Step 3.6.

Expected repository shape before this task is conceptually:

```text
repository-root/
├── backend/
├── Spec-CURRENT/
├── codex-tasks/
├── docs/
└── ...
```

There is **no existing `frontend/` application directory** in the accepted Step-3.6 repository.

Step 4.1 must bootstrap the frontend from this state.

Do not refactor the accepted backend to fit frontend preferences.

---

# 4. Mandatory PM Decisions

## D-027 — Frontend runtime and package workflow

Use:

```text
Node.js >= 22.12
package manager = npm
lockfile = package-lock.json
```

Bootstrap using the stable:

```text
Vite
React
TypeScript
```

template.

Do not introduce:

```text
pnpm
Yarn
Bun
monorepo workspace tooling
experimental React channels
```

Do not PM-freeze or hand-pin every package patch version. The committed:

```text
package.json
package-lock.json
```

is the reproducible resolved dependency set.

Expected package workflow:

```text
npm install / npm ci
npm run build
npm run test -- --run
```

Add an appropriate Node engine constraint to `frontend/package.json` equivalent to:

```json
{
  "engines": {
    "node": ">=22.12"
  }
}
```

Do not create another package-manager workflow.

## D-028 — Client-side routing baseline

Use React Router in **Data Mode**.

Runtime dependency:

```text
react-router
```

Use:

```text
createBrowserRouter()
RouterProvider
Outlet
```

Architecture:

```text
Browser
→ React Router
→ Layout
→ Feature Page / Screen
```

Do not use:

```text
React Router Framework Mode
SSR
server loaders as a FastAPI replacement
Next.js
another full-stack frontend framework
```

Structural root/fallback routing:

```text
/
→ redirect to /dashboard

*
→ lightweight NotFoundPage
```

The root redirect has no authentication meaning in Step 4.1.

Learner navigation is exactly equivalent to:

```text
Dashboard → /dashboard
Learn     → /pronunciation
Progress  → /progress
History   → /history
Profile   → /profile
```

Do not create:

```text
/learn
/chat
```

Lesson AI Chat remains structurally embedded inside:

```text
/lessons/:lessonId
```

## D-029 — Unit/component testing baseline

Use:

```text
Vitest
jsdom
@testing-library/react
@testing-library/dom
@testing-library/jest-dom
```

Testing should focus on rendered behavior:

```text
route resolution
layout ownership
navigation structure
dynamic route matching
visible structural screen behavior
```

Prefer behavior-oriented tests over:

```text
large implementation snapshots
component-internal assertions
source-structure-only assertions
```

Do not introduce:

```text
Playwright
Cypress
browser E2E infrastructure
```

in Step 4.1.

---

# 5. Architectural Boundary

Preserve:

```text
Browser
→ React Frontend
→ FastAPI Backend
```

Frontend is the presentation/client layer.

Frontend must not own or calculate backend responsibilities such as:

```text
business rules
grading
curriculum unlock
progress calculation
authorization
AI provider calls
```

Step 4.1 must contain **no fake implementation** of those responsibilities.

For example, do not write functions such as:

```text
isLessonUnlocked(...)
calculateProgress(...)
canUserAccessAdmin(...)
gradeAnswer(...)
```

merely to make skeleton pages appear realistic.

---

# 6. In Scope

Implement only:

1. `frontend/` bootstrap;
2. package/runtime baseline;
3. React entry point;
4. React Router Data Mode route tree;
5. three layout boundaries;
6. approved page/screen skeletons;
7. minimal structural navigation;
8. minimal structural Lesson AI Chat region;
9. minimal structural Admin Documents page;
10. lightweight NotFound page;
11. feature-oriented source placement;
12. focused route/layout/component tests;
13. Step 4.1 documentation.

Minimal plain styling is allowed only to make layout boundaries/readability obvious.

No design system is required.

---

# 7. Explicitly Out of Scope

Do not implement or install behavior for:

```text
real FastAPI calls
API client layer
VITE_API_BASE_URL integration
OpenAPI generation
openapi-typescript usage
TanStack Query behavior
server-state cache
session restoration
real authentication flow
route guards
ProtectedRoute
AdminRoute authorization logic
JWT/token handling
detailed Lesson UI
real vocabulary/grammar learning interactions
exercise interaction logic
assessment submission logic
progress visualization
history data loading
profile data loading/password change
AI Chat interaction
Conversation API calls
streaming
retry/error framework
document upload/ingestion workflow
advanced design system
GLOBAL chat
future AI/RAG frontend abstractions
backend changes
Phase-5 ingestion UI
```

Do not install/use merely for future Steps:

```text
@tanstack/react-query
openapi-typescript
axios
redux
zustand
tailwindcss
MUI / Material UI
other component framework
Playwright
Cypress
```

unless the current Step has a concrete requirement that cannot be satisfied without one. The reviewed Step 4.1 has no such requirement.

The standard stable Vite React-TypeScript template's normal build/lint support may remain, but do not expand it into a new lint/format/design-system project.

---

# 8. Exact Public Route Group

All routes below must exist as structural route boundaries.

Use `PublicLayout`.

```text
/login
/register
/forgot-password
/reset-password
```

Expected pages:

```text
LoginPage
RegisterPage
ForgotPasswordPage
ResetPasswordPage
```

These are structural pages only.

Do not implement functioning auth forms, API submission, session state, fake authentication, or redirect-after-login behavior.

Each page may contain:

- page heading;
- one short sentence explaining its eventual purpose.

Avoid realistic fake credentials or fake account state.

---

# 9. Exact Learner Route Group

Use `LearnerLayout`.

```text
/dashboard
/pronunciation
/hsk/:hskLevel
/lessons/:lessonId
/assessments/:assessmentId
/assessment-attempts/:attemptId/result
/progress
/history
/profile
```

## `/dashboard`

Create a `DashboardPage` structural screen.

Reserve visible sections for:

```text
Current HSK
Current curriculum unit
Current lesson
Overall progress
Continue Learning
```

Do not invent values, percentages, learner names, lesson numbers or unlock states.

## `/pronunciation`

Create a `PronunciationPage`.

Represent the three required foundations structurally:

```text
TONES
INITIALS
FINALS
```

Do not merge Pronunciation into Lesson 1.

Do not implement pronunciation-learning interactions yet.

## `/hsk/:hskLevel`

Create an `HskCurriculumPage`.

Reserve the screen for:

```text
Lesson
Periodic Test
```

and explain structurally that backend-derived unit states will later be:

```text
LOCKED
AVAILABLE
COMPLETED
```

Do not calculate or fake those states.

The page may visibly render the route parameter for structural verification, but do not use it to simulate real curriculum data.

## `/lessons/:lessonId`

Create one `LessonPage` containing structural regions for:

```text
Vocabulary
Grammar
Exercise
AI Chat
```

Do not create separate learner routes for vocabulary/grammar items.

The AI Chat region must be embedded in this Lesson page.

A small component under the `conversation` feature may be used for the AI Chat skeleton if it is actually rendered by `LessonPage`.

Do not implement:

```text
conversation creation
message history
message send
retry
loading states
streaming
fake AI answers
```

## `/assessments/:assessmentId`

Create one `AssessmentPage` for the structural assessment screen.

It represents both future:

```text
LESSON_EXERCISE
PERIODIC_TEST
```

Do not create separate route families.

Do not implement questions/answers/submission behavior.

## `/assessment-attempts/:attemptId/result`

Create an `AssessmentResultPage` separate from `AssessmentPage`.

Reserve structural regions for eventual:

```text
score
passed state
answer review
feedback
uncertain grading state
```

Do not display fake results or calculate scores.

## `/progress`

Create `ProgressPage`.

Meaning:

```text
current learning state
```

Do not implement charts, percentages or progress derivation.

## `/history`

Create `HistoryPage`.

Meaning:

```text
historical assessment attempts/results
```

Do not merge Progress and History.

Do not invent attempt rows.

## `/profile`

Create `ProfilePage`.

Reserve structural regions for eventual:

```text
full name
email
current HSK/progress summary
password change entry
```

Do not create fake user data or auth/session state.

---

# 10. Exact Admin Route Group

All Admin routes must remain under `/admin` and use `AdminLayout`.

```text
/admin
/admin/lessons
/admin/lessons/:lessonId
/admin/assessments
/admin/assessments/:assessmentId
/admin/documents
/admin/stats
```

No Admin route guard or role check is implemented in Step 4.1.

Server authorization remains authoritative; frontend role-aware UX comes later.

## `/admin`

Create `AdminDashboardPage` structural shell.

## `/admin/lessons`

Create `AdminLessonsPage` structural shell.

## `/admin/lessons/:lessonId`

Create `AdminLessonEditorPage`.

Reserve use-case-oriented sections for:

```text
Lesson metadata
Vocabulary
Grammar
Exercises
Preview
Publish / Archive actions
```

These are labels/skeleton regions only.

Do not expose database junction-table concepts as the UI model.

Do not implement mutations or lifecycle business logic.

## `/admin/assessments`

Create `AdminAssessmentsPage` structural shell.

## `/admin/assessments/:assessmentId`

Create `AdminAssessmentEditorPage`.

Reserve structural lifecycle context for:

```text
DRAFT
→ REVIEW
→ PUBLISHED
```

Do not implement transitions or API actions.

## `/admin/documents`

Create `AdminDocumentsPage` as **structural only**.

It may display a concise note equivalent to:

```text
Document management will be implemented in Phase 5.
```

Do not implement:

```text
upload
parsing
processing
review
approval
ingestion status
knowledge activation
```

## `/admin/stats`

Create `AdminStatsPage` structural shell.

Do not invent statistics or aggregate them in React.

---

# 11. Root and Fallback Routes

Implement the D-028 structural behavior:

```text
/
→ /dashboard
```

Use a router redirect mechanism appropriate to React Router Data Mode.

This redirect has no auth/session meaning.

Unknown URLs:

```text
*
→ NotFoundPage
```

`NotFoundPage` should be lightweight and should not introduce a fourth business layout or an error framework.

---

# 12. Layout Boundaries

Implement exactly three top-level product layout boundaries:

```text
PublicLayout
LearnerLayout
AdminLayout
```

Each uses React Router's:

```text
Outlet
```

for nested page rendering.

## PublicLayout

Presentation-only shell for:

```text
/login
/register
/forgot-password
/reset-password
```

Keep it minimal.

No marketing-site framework.

## LearnerLayout

Presentation-only shell with learner navigation equivalent to:

```text
Dashboard
Learn
Progress
History
Profile
```

Navigation destinations:

```text
Dashboard → /dashboard
Learn     → /pronunciation
Progress  → /progress
History   → /history
Profile   → /profile
```

Do not add:

```text
Chat
AI Chat
Learn → /learn
```

to the top-level nav.

## AdminLayout

Presentation-only shell with navigation:

```text
Dashboard
Lessons
Assessments
Documents
Stats
```

Do not expose internal engineering concepts such as:

```text
Chunks
Embeddings
Knowledge Versions
```

as product navigation.

## Layout responsibility rule

Layouts may own only presentation concerns such as:

```text
navigation
header
content shell
page container
Outlet
```

Layouts must not own:

```text
authentication/session state
role authorization
progress calculation
curriculum unlock logic
grading
backend permission logic
AI logic
```

---

# 13. Router Design

Use React Router Data Mode.

Recommended implementation shape:

```text
src/app/router/
├── routes.tsx (or equivalent route-tree module)
└── ...only additional files that are actually needed
```

Production runtime must use:

```text
createBrowserRouter(...)
RouterProvider
```

The route tree should nest pages under the appropriate layout boundaries.

For tests, it is acceptable and recommended to reuse the same route objects with React Router's in-memory router capability so route/layout behavior can be tested deterministically without a real browser server.

Do not duplicate a separate test-only route map that can drift from production.

No route loader/action should call FastAPI in Step 4.1.

No router-level auth loader/guard should exist yet.

---

# 14. Feature-Oriented Source Structure

Use the authoritative feature-oriented direction.

The final tree does not need to contain empty directories.

A reasonable implemented shape is equivalent to:

```text
frontend/
├── src/
│   ├── app/
│   │   ├── layouts/
│   │   │   ├── PublicLayout.tsx
│   │   │   ├── LearnerLayout.tsx
│   │   │   └── AdminLayout.tsx
│   │   └── router/
│   │       └── ...actual route files
│   │
│   ├── features/
│   │   ├── auth/
│   │   │   └── ...public auth page skeletons
│   │   ├── dashboard/
│   │   │   └── ...DashboardPage
│   │   ├── pronunciation/
│   │   │   └── ...PronunciationPage
│   │   ├── curriculum/
│   │   │   └── ...HskCurriculumPage
│   │   ├── lesson/
│   │   │   └── ...LessonPage
│   │   ├── assessment/
│   │   │   └── ...AssessmentPage + AssessmentResultPage
│   │   ├── progress/
│   │   │   └── ...ProgressPage
│   │   ├── history/
│   │   │   └── ...HistoryPage
│   │   ├── profile/
│   │   │   └── ...ProfilePage
│   │   ├── conversation/
│   │   │   └── ...only an actually-used structural AI Chat region component if useful
│   │   └── admin/
│   │       └── ...Admin pages/editors
│   │
│   ├── test/
│   │   └── ...test setup/helper only if needed
│   ├── main.tsx
│   └── ...minimal styles/assets actually used
│
├── package.json
├── package-lock.json
├── index.html
├── tsconfig*.json
├── vite.config.*
└── ...normal stable Vite template support files actually used
```

Important:

- Do not create `components/`, `lib/`, `types/`, or any feature directory merely because the conceptual architecture mentions it.
- Create a directory only when Step-4.1 code actually lives there.
- Do not create placeholder API files.
- Do not create future Query hooks.
- Do not create OpenAPI-generated type files.
- Do not create fake `services/` abstractions.

Keep each page small enough that later Steps can evolve it without a rewrite.

---

# 15. Minimal Skeleton Strategy

Skeleton pages must be real renderable React components but intentionally shallow.

Preferred page pattern:

```text
semantic page heading
one short purpose sentence
required section headings/labels only
```

Do not create realistic fake domain data to make screens look complete.

Forbidden examples:

```text
fake learner name
fake score
fake current HSK
fake locked/unlocked state
fake assessment questions
fake assessment results
fake chat messages
fake Admin statistics
fake auth/session state
```

Static domain labels required by the Step are acceptable, for example:

```text
TONES
INITIALS
FINALS
Vocabulary
Grammar
Exercise
AI Chat
DRAFT
REVIEW
PUBLISHED
```

These are structural vocabulary, not fake runtime data.

---

# 16. Styling Boundary

Use only minimal styling needed to make:

```text
layout boundaries
navigation
page headings
section boundaries
```

readable.

Plain CSS from/alongside the stable Vite template is sufficient.

Do not add:

```text
Tailwind
MUI
CSS-in-JS framework
design-token system
component library
advanced responsive design system
```

in Step 4.1.

Visual polish is not an acceptance criterion.

---

# 17. Package / Dependency Expectations

## Runtime dependencies actually needed now

Expected minimal runtime dependencies include:

```text
react
react-dom
react-router
```

plus stable Vite/TypeScript template dependencies needed for the application toolchain.

## Test/dev dependencies actually needed now

Expected test dependencies:

```text
vitest
jsdom
@testing-library/react
@testing-library/dom
@testing-library/jest-dom
```

Use only the minimum supporting Vite/React/TypeScript development packages required by the stable template.

## Not yet installed merely for future use

Do not add just because later Steps will use them:

```text
@tanstack/react-query
openapi-typescript
axios
Redux
Zustand
Tailwind
MUI
Playwright
Cypress
```

A later Step installs/configures a future tool when it actually becomes part of that Step's implementation.

---

# 18. Package Scripts

Ensure `frontend/package.json` supports at least:

```text
npm run build
npm run test -- --run
```

The stable Vite template's normal development script should remain available, typically:

```text
npm run dev
```

A suitable minimal test script is equivalent to:

```json
{
  "scripts": {
    "test": "vitest"
  }
}
```

Do not require watch mode for CI verification.

The build must perform TypeScript checking through the normal Vite React-TypeScript build workflow/template configuration rather than bypassing type errors.

---

# 19. Test Environment Setup

Configure Vitest to use:

```text
jsdom
```

and load:

```text
@testing-library/jest-dom
```

through a focused test setup file/configuration.

Do not install browser E2E tooling.

When testing routes, prefer rendering with the real route definitions and an in-memory router suitable for test navigation.

The tests must not require FastAPI/PostgreSQL/network access.

---

# 20. Required Tests

Add focused tests covering at least the D-029 baseline.

## Route resolution

Verify all approved static routes resolve:

```text
/login
/register
/forgot-password
/reset-password
/dashboard
/pronunciation
/progress
/history
/profile
/admin
/admin/lessons
/admin/assessments
/admin/documents
/admin/stats
```

Verify dynamic routes resolve with representative path parameters:

```text
/hsk/:hskLevel
/lessons/:lessonId
/assessments/:assessmentId
/assessment-attempts/:attemptId/result
/admin/lessons/:lessonId
/admin/assessments/:assessmentId
```

Do not assert fake backend values from those parameters.

## Layout ownership

Verify:

```text
Public routes
→ PublicLayout

Learner routes
→ LearnerLayout

Admin routes
→ AdminLayout
```

Tests may use stable visible layout landmarks/navigation text rather than implementation-only class names.

## Navigation structure

Verify Learner navigation includes:

```text
Dashboard
Learn
Progress
History
Profile
```

and:

```text
Learn href/to = /pronunciation
```

Verify Admin navigation includes:

```text
Dashboard
Lessons
Assessments
Documents
Stats
```

Verify there is no top-level AI Chat navigation.

## Root/fallback behavior

Verify:

```text
/
→ /dashboard
```

and an unknown path renders `NotFoundPage`.

## Screen responsibility boundaries

Verify the Lesson page visibly contains structural regions:

```text
Vocabulary
Grammar
Exercise
AI Chat
```

Verify:

```text
/progress
```

and:

```text
/history
```

render distinct screens/responsibilities.

Verify:

```text
/assessments/:assessmentId
```

and:

```text
/assessment-attempts/:attemptId/result
```

render distinct Assessment vs Assessment Result pages.

Verify Admin Documents is structural only; it must not expose upload/ingestion controls.

## Explicit absence tests

Verify the route configuration has no supported route for:

```text
/learn
/chat
```

A request/navigation to those paths should fall through to `NotFoundPage`, not render a hidden prebuilt feature.

## Boundary checks

Add a focused, maintainable source/architecture check only if useful to prevent obvious Step-4.1 scope creep, but do not build a brittle source-code parser merely to test file layout.

The primary tests should be rendered-behavior tests.

---

# 21. No API / Auth / Server-State Implementation

This is a hard scope boundary.

Step 4.1 must not contain:

```text
fetch(...)
backend base URL config
credentials: "include"
/auth/me session restoration
refresh-token behavior
route guards based on current User
TanStack Query provider/query hooks
OpenAPI generated types
feature API modules
business error mapping
API retry logic
```

Those belong to later Steps.

If a page needs data to look structurally meaningful, use labels/headings only rather than fake request results.

---

# 22. Files / Components Expected to Change

Create frontend files only as actually needed.

Expected categories:

```text
frontend/package.json
frontend/package-lock.json
frontend/index.html
frontend/tsconfig*.json
frontend/vite.config.*
frontend/src/main.tsx
frontend/src/app/router/*
frontend/src/app/layouts/*
frontend/src/features/**/actual Step-4.1 pages/components
frontend/src/test/* if required
frontend/**/*.test.tsx or equivalent focused test files
frontend/minimal CSS/assets actually used
```

Also create/update:

```text
docs/frontend/step-4.1-frontend-structure.md
```

Do not edit backend files for normal Step-4.1 implementation.

Do not create future API/state files.

---

# 23. Step Note Requirement

Create:

```text
docs/frontend/step-4.1-frontend-structure.md
```

It must contain concise, reusable knowledge rather than a file-by-file diary.

Include:

## Objective

Why the frontend structural foundation exists.

## Why

Why route/layout/feature boundaries are established before API and detailed UI work.

## Mental Model

Use:

```text
Browser
→ Router
→ Layout
→ Feature Page
```

and explain that later the Feature Page will consume frontend API/state layers without becoming the backend authority.

## Core Knowledge

Cover only concepts actually used, such as:

```text
SPA
client-side routing
nested routes
layouts
route parameters
feature-oriented structure
presentation vs business logic
component composition
component testing
```

## Data / UI Flow

Step 4.1 is mostly structural navigation flow:

```text
URL
→ Router match
→ Layout
→ Page component
```

Do not pretend real backend data flow exists yet.

## Key Design Decisions

Record D-027 through D-029 and the frozen route/layout boundaries.

## Reusable Approach

Explain how to bootstrap a feature-oriented SPA without prematurely building future application layers.

## Common Mistakes

Include:

```text
putting business rules in React
inventing routes
creating empty architecture folders
pre-installing future state/API frameworks
building fake auth guards
creating standalone chat
using fake domain data in skeletons
```

## Definition of Done

Reflect the actual implementation and tests.

---

# 24. Concepts Discovered

The completion report and Step Note should identify only concepts actually used in Step 4.1.

Expected concepts:

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Single Page Application | SYSTEM | 4.1 | One browser application resolves multiple product screens client-side. |
| Client-side routing | SYSTEM | 4.1 | Maps URL paths to React screens without adding a second backend. |
| Nested routes | SYSTEM | 4.1 | Groups page screens under shared Public/Learner/Admin layouts. |
| Layout | SYSTEM | 4.1 | Provides shared presentation shell and navigation through `Outlet`. |
| Route parameter | SYSTEM | 4.1 | Represents structural IDs/HSK level in approved dynamic routes. |
| Feature-oriented structure | SYSTEM | 4.1 | Organizes source by product responsibility instead of framework layer alone. |
| Presentation vs business logic | SYSTEM | 4.1 | Keeps FastAPI/backend authoritative for product rules. |
| Component composition | SYSTEM | 4.1 | Builds pages/layouts from small React components. |
| Skeleton UI | SYSTEM | 4.1 | Establishes screen structure without fake application behavior. |
| Component testing | SYSTEM | 4.1 | Verifies route/layout/rendered behavior before backend integration. |

Do not add DE or AI concepts simply because the product eventually contains DE/AI features; Step 4.1 does not implement them.

---

# 25. Tools Used

Expected tools actually used:

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| Node.js | SYSTEM | 4.1 | Frontend build/test runtime. |
| npm | SYSTEM | 4.1 | Package installation and lockfile workflow. |
| React | SYSTEM | 4.1 | UI component layer. |
| TypeScript | SYSTEM | 4.1 | Typed frontend implementation. |
| Vite | SYSTEM | 4.1 | SPA development/build tooling. |
| React Router | SYSTEM | 4.1 | Route tree, nested layouts and navigation. |
| Vitest | SYSTEM | 4.1 | Frontend unit/component test runner. |
| jsdom | SYSTEM | 4.1 | Browser-like DOM test environment. |
| React Testing Library | SYSTEM | 4.1 | Rendered user-facing component/route testing. |

Do not list future tools that are not actually installed/used in this Step.

---

# 26. Verification Commands

Run from the `frontend/` directory.

Required:

```text
node --version
npm --version
npm ci
npm run build
npm run test -- --run
```

`node --version` must satisfy:

```text
>= 22.12
```

Also verify:

```text
package-lock.json exists
```

and the lockfile is committed in the handoff.

If the environment initially requires `npm install` to generate the first lockfile during bootstrap, that is acceptable. Final clean verification must use:

```text
npm ci
```

Do not claim reproducibility without successfully running the clean lockfile install.

Do not require backend/database services for frontend Step-4.1 tests.

---

# 27. Acceptance Criteria

All must pass.

## Runtime/package

- [ ] `frontend/` is a React + TypeScript + Vite application.
- [ ] Node engine baseline is `>=22.12`.
- [ ] npm is the package workflow.
- [ ] `package-lock.json` exists.
- [ ] `npm ci` passes.
- [ ] `npm run build` passes.
- [ ] `npm run test -- --run` passes.

## Routing/layout

- [ ] React Router Data Mode is used.
- [ ] Production uses `createBrowserRouter()` + `RouterProvider`.
- [ ] Nested layouts render through `Outlet`.
- [ ] `/` redirects to `/dashboard` structurally.
- [ ] unknown paths render `NotFoundPage`.
- [ ] exact Public routes exist under `PublicLayout`.
- [ ] exact Learner routes exist under `LearnerLayout`.
- [ ] exact Admin routes exist under `AdminLayout`.
- [ ] Admin routes stay under `/admin`.
- [ ] `/learn` does not exist.
- [ ] standalone `/chat` does not exist.

## Structural screens

- [ ] Dashboard reserves the required five structural areas without fake data.
- [ ] Pronunciation structurally represents TONES / INITIALS / FINALS.
- [ ] HSK curriculum is separate from Pronunciation and has no client progression authority.
- [ ] Lesson structurally contains Vocabulary / Grammar / Exercise / AI Chat.
- [ ] AI Chat is embedded in Lesson rather than standalone.
- [ ] Assessment and Assessment Result are separate route responsibilities.
- [ ] Progress and History are separate screens.
- [ ] Profile is structural only.
- [ ] Admin Documents is structural only.
- [ ] Admin Lesson/Assessment editor screens are use-case-oriented structural skeletons.

## Architecture/scope

- [ ] source is feature-oriented.
- [ ] unnecessary empty directory trees are not created.
- [ ] layouts contain only presentation concerns.
- [ ] no frontend business-rule duplication exists.
- [ ] no real API/client/OpenAPI integration exists.
- [ ] no TanStack Query behavior exists.
- [ ] no auth/session/route-guard implementation exists.
- [ ] no detailed Lesson/Assessment/Progress/Chat/Admin behavior exists.
- [ ] no Tailwind/MUI/design-system expansion exists.
- [ ] no Redux/Zustand exists.
- [ ] no Playwright/Cypress/E2E infrastructure exists.
- [ ] no backend files were changed absent a separately reported blocking defect.

## Documentation

- [ ] `docs/frontend/step-4.1-frontend-structure.md` exists and reflects the implementation.
- [ ] Concepts/Tools in the completion report list only items actually used.

---

# 28. Required Completion Report

When implementation is complete, return a handoff containing:

```text
Step
Status
Implementation plan executed
Files created
Files modified
Dependencies added/removed
Node/npm/package-lock state
Route map implemented
Layout boundaries implemented
Source structure implemented
Testing implemented
Verification commands/results
Acceptance criteria
Step Note
Concepts actually used
Tools actually used
Deviations from specification
Problems / risks
Decisions needed
Recommended next action
```

Report the exact frontend test/build counts/results.

If any required test/build command cannot run, say why; do not substitute a different toolchain and claim success.

If implementation reveals a new architecture/tool/route ambiguity, stop and report it instead of expanding scope.

---

# 29. Non-Goals / Guardrail Summary

The Step is complete when the **structure is real but the application behavior is intentionally shallow**.

Correct Step-4.1 mental model:

```text
real React app
+ real route tree
+ real layouts
+ real structural screens
+ real frontend tests

BUT

no real backend integration
no session model
no business-state calculation
no real learning interactions
no real chat behavior
```

Do not make Step 4.1 look more complete by implementing later Steps early.

---

# 30. Final Execution Boundary

Implement **Step 4.1 only**.

After implementation and verification:

```text
stop
→ produce completion report
→ return to App Engineering Specialist for independent review
```

Do not begin:

```text
Step 4.2 — Backend API Integration
Step 4.3 — Lesson Learning UI
Step 4.4 — AI Chat UI
Step 4.5 — Frontend State / Error Handling
Step 4.6 — Auth & Profile UI
Step 4.7 — Admin UI
Phase 5+
```

until PM opens the next gate.
