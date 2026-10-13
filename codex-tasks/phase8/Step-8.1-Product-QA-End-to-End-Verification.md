# Step 8.1 — Product QA & End-to-End Verification

## Codex Task

### Status

PM-FREEZE CANDIDATE.

Do not treat this task as Codex execution authorization unless PM explicitly marks it CODEX-READY.

Do NOT claim Step 8.1 DONE.
Do NOT claim PRODUCT RELEASE READY.
Do NOT start Step 8.2.

---

## Context

Phases 0–6 are complete.

Phase 7 deterministic/offline implementation is complete, but several official runtime/human evaluation gates remain deferred.

Step 8.1 verifies the MVP as one integrated system before later deployment work.

Mental model:

```text
Browser
→ React frontend
→ FastAPI
→ PostgreSQL / pgvector
→ deterministic AI boundaries
→ persisted business state
→ assertions
```

Freeze:

```text
STEP 8.1 IMPLEMENTATION ACCEPTED
≠
PRODUCT RELEASE READY
```

---

## Frozen Decision — D-111 Browser E2E Tool

Before modifying frontend tooling, inspect the actual frontend repository.

You MUST inspect at minimum:

```text
frontend/package.json
frontend/package-lock.json
frontend test configuration
existing browser-E2E configuration
existing test scripts
```

Also inspect relevant frontend test directories/config files discovered from those files.

Selection policy:

```text
existing suitable browser E2E framework already configured?
        │
        ├─ YES
        │   → reuse it
        │   → do NOT install Playwright
        │
        └─ NO
            → use Playwright
```

Current project default:

```text
Playwright
```

Do NOT install or maintain multiple browser E2E frameworks.

Examples of prohibited outcomes:

```text
existing usable Cypress
+
new Playwright
```

or:

```text
existing usable Playwright
+
new Cypress
```

Vitest + React Testing Library remain responsible for unit/component testing.

Browser E2E tooling exists only for the small set of true integrated product journeys.

If repository evidence makes D-111 impossible to apply cleanly:

```text
BLOCKED — DECISION NEEDED
```

Do not silently introduce a second framework.

---

## Objective

Build a deterministic QA layer proving that critical learner/Admin journeys work across:

```text
browser
frontend
API
database
AI boundaries
```

while preserving backend-authoritative business, security and failure semantics.

Use:

```text
few high-value browser tests
+
strong API/integration tests
+
existing regression suites
```

Do not duplicate the entire test pyramid at browser level.

---

## Repository Preflight

Before implementation inspect the actual repository.

### Frontend

Inspect:

```text
frontend/package.json
frontend/package-lock.json
Vite config
Vitest config
React Testing Library setup
route structure
auth/session handling
apiClient
TanStack Query setup
generated OpenAPI types
learner routes
Admin routes
existing browser-E2E config/scripts
```

Record the browser E2E framework selected under D-111.

Do not manually duplicate backend DTOs.

Do not change normal frontend architecture merely for tests.

### Backend

Inspect and reuse:

```text
FastAPI startup
pytest configuration
tests/conftest.py
APP_ENV=test convention
TEST_DATABASE_URL convention
database fixtures
async SQLAlchemy fixtures
auth fixtures
dependency_overrides
existing integration test patterns
AI fake/stub/replay seams
document fixtures
grading/generation fake-provider seams
RAG fixtures
```

### Existing tests

Inventory and reuse tests for at least:

```text
auth/session
business/progression
periodic-test gates
conversation
authorization
documents/ingestion
RAG
citations
AI grading
AI assessment generation
Phase-7 evaluation/regression
frontend unit/component behavior
```

Do not rewrite already-adequate coverage solely to place it under Step 8.1.

---

## Scope

### In Scope

- minimal browser E2E framework/config under D-111;
- deterministic frontend/backend startup for E2E;
- isolated PostgreSQL/pgvector E2E DB lifecycle;
- minimal canonical seed fixture;
- five critical browser journeys;
- focused authorization browser smoke;
- API/integration coverage gaps;
- deterministic AI boundaries;
- existing regression preservation;
- QA test plan;
- QA release checklist;
- QA run report;
- Step documentation.

### Out of Scope

Do NOT implement:

- Step 8.2;
- Docker/containerization;
- CI/CD;
- deployment;
- production host/vendor selection;
- cloud database selection;
- production secrets management;
- production monitoring;
- Kubernetes;
- large-scale load testing;
- architecture rewrite;
- production API added solely for testing;
- new AI behavior;
- prompt/model/retrieval tuning;
- official Phase-7 evaluations;
- baseline promotion;
- paid/live provider calls.

---

## Test-Level Strategy

Use three levels.

### Browser E2E

Only real user journeys requiring confidence in:

```text
real browser navigation
HttpOnly cookie/session behavior
frontend ↔ backend integration
route transitions
refresh/persistence behavior
```

### API / Integration

Use existing pytest/FastAPI/PostgreSQL patterns for backend-authoritative:

```text
business rules
authorization
persistence
negative paths
failure semantics
AI boundary behavior
```

### Existing Unit / Regression

Reuse current tests where logic is already adequately covered.

Do not force every invariant through the browser.

---

## Browser E2E Environment

Target topology:

```text
Browser E2E runner
→ isolated frontend test/dev server
→ FastAPI test process
→ dedicated PostgreSQL + pgvector test DB
→ deterministic AI boundaries
```

### Frontend

Use repository-normal Vite/npm workflow.

Do not create a second frontend application or E2E-only product architecture.

Configure browser E2E `baseURL` or equivalent against the isolated frontend server.

If Playwright is selected, configure it minimally.

Prefer one browser project sufficient for Step 8.1 unless the existing project convention already requires otherwise.

Do not introduce a broad cross-browser matrix in this Step.

### Backend

Reuse the accepted local FastAPI runner and repository dependency workflow.

Run with:

```text
APP_ENV=test
TEST_DATABASE_URL=<dedicated test database>
```

The backend process must use deterministic AI boundary configuration.

Do not use production environment variables or credentials.

---

## Test Database

Use:

```text
PostgreSQL
+
pgvector
```

Do NOT substitute SQLite.

Requirements:

```text
dedicated test DB
not production DB
no production learner data
current migrations applied
deterministic seed
deterministic reset/cleanup
```

Reuse current backend fixture/database conventions wherever possible.

Conceptual lifecycle:

```text
verify test environment
→ prepare/reset DB
→ migrate
→ seed canonical fixture
→ run browser/integration tests
→ cleanup/reset
```

Do not modify application schema solely for Step-8.1 tests.

Environment inability to prepare the DB must be reported as:

```text
ENVIRONMENT_GATE
```

not PASS.

---

## Deterministic AI Strategy

No paid/live LLM or external provider calls.

Reuse current fake/stub/replay seams.

### Free-Form Grading

Provide deterministic scenarios for:

```text
GRADED
UNCERTAIN
TECHNICAL_FAILURE
```

For technical failure verify:

```text
no fake grading success
score/business state remains correct
learner progression does not unlock
```

### AI Assessment Generation

Provide:

```text
success
→ DRAFT generated content

technical failure
→ safe technical failure
```

Generated content must never auto-publish.

### Lesson RAG

Provide deterministic scenarios for:

```text
normal grounded answer
internal fallback
no evidence
out-of-domain if currently supported
retrieval/provider technical failure
citations
multi-turn/history isolation
```

Do not treat technical failure as successful no-evidence refusal.

### External Boundaries

Mock/fake/replay external systems unless an existing deterministic local provider is already part of the accepted test architecture.

No random public Internet dependency.

---

## Canonical Minimal Seed

Use the smallest shared fixture capable of exercising all launch-blocking journeys.

Include:

### Users

```text
1 Admin
2 Learners
```

Two learners are required to verify isolation.

### Curriculum

```text
pronunciation foundation
HSK 1
HSK 2 minimal unlock target
Lesson A
Lesson B
```

### Learning Content

Minimal:

```text
theory
vocabulary
grammar
objective exercise
free-form exercise
```

### Assessments

```text
1 Lesson Exercise
1 Periodic Test
```

with data supporting fail/retry/pass/unlock.

### Documents

```text
1 approved/trusted Document
1 unapproved Document
```

### AI Fixtures

```text
RAG grounded
RAG no-evidence
RAG technical failure

grading GRADED
grading UNCERTAIN
grading technical failure

generation success
generation failure
```

Avoid giant fixture packs.

Do not seed unrelated product data.

---

## Browser Journeys

### B1 — New Learner

Flow:

```text
register
→ authenticated session
→ dashboard
→ pronunciation foundation
→ complete required pronunciation flow
→ initial Lesson unlocked
→ open Lesson
→ consume Lesson content
→ complete objective exercise
→ progression visible
→ refresh/revisit
→ persisted state remains correct
```

Verify:

- registration establishes browser session;
- route transitions work;
- backend is authoritative;
- progression survives reload.

Launch-blocking: YES.

---

### B2 — Periodic-Test Gate

Flow:

```text
learner reaches gate
→ Periodic Test required
→ further progression blocked

submit failing attempt
→ still blocked

retry
→ passing result
→ next permitted state unlocked
```

Verify persisted state before/after refresh.

Launch-blocking: YES.

---

### B3 — Lesson Chat

Flow:

```text
open Lesson
→ open AI Chat
→ explicit start/select Conversation
→ send question
→ deterministic Assistant answer
→ render answer
→ render source/citation behavior where applicable
→ navigate away/return or refresh
→ conversation/history persists
```

Verify:

```text
Conversation remains Lesson-scoped
```

Do not build Global Chat.

Technical/fallback/no-evidence branches belong primarily in integration tests.

Launch-blocking: YES.

---

### B4 — Admin Content Lifecycle

Flow:

```text
Admin login
→ create/edit supported content
→ perform accepted lifecycle transition
→ publish
→ learner sees trusted published state
```

Also perform browser smoke:

```text
ordinary Learner
→ navigate to Admin route
→ Forbidden / unavailable
```

Backend authorization tests remain authoritative.

Launch-blocking: YES.

---

### B5 — AI-Generated Assessment Lifecycle

Flow:

```text
Admin Generate
→ deterministic generated assessment/questions
→ DRAFT
→ Admin review/edit
→ explicit publish
```

Verify learner does not consume generated DRAFT as published content.

Launch-blocking: YES.

---

## API / Integration Groups

### A1 — Auth / Session

Cover:

```text
invalid credentials
missing/invalid Access Token
expired-session path
accepted refresh behavior
logout/session boundary where relevant
```

### A2 — Authorization

Cover:

```text
Learner → Admin endpoint
→ denied

Admin → accepted Admin endpoint
→ permitted
```

Do not rely on frontend guards as security.

### A3 — Cross-User Isolation

Using Learner A and Learner B verify:

```text
conversations
history/state
owned resources
```

cannot leak.

### A4 — Progression

Verify backend-authoritative:

```text
pronunciation completion
Lesson progression
exercise completion
Periodic gate
unlock state
```

### A5 — Free-Form AI Grading

Verify:

```text
GRADED
UNCERTAIN
technical failure
```

Technical failure:

```text
→ no progression unlock
```

### A6 — Lesson RAG

Verify:

```text
normal answer
internal fallback
no-evidence refusal
out-of-domain where supported
technical failure
citation behavior
history/context isolation
```

Technical failure is not no-evidence success.

### A7 — Documents

Verify:

```text
unapproved Document
→ cannot become trusted evidence

approved Document
→ normal accepted trust behavior
```

### A8 — AI Generation

Verify:

```text
success
→ DRAFT

failure
→ safe technical result

DRAFT
→ never automatic publish
```

### A9 — Persistence

After business mutation, issue a fresh authoritative read and verify persisted truth.

---

## Authorization Matrix

Test equivalent cases:

| Actor | Own learner state | Other user state | Admin API | Admin UI |
|---|---|---|---|---|
| unauthenticated | denied | denied | denied | protected |
| Learner A | allowed | denied | denied | Forbidden |
| Learner B | allowed | denied | denied | Forbidden |
| Admin | contract-based | no unintended privacy bypass | allowed | allowed |

Frontend Admin guard is UX only.

Backend remains security authority.

---

## Failure-Path Matrix

Cover at minimum:

### Auth

```text
invalid login
invalid/expired session
unauthorized Admin access
```

### API / DB

```text
validation failure
representative API/server technical failure
```

### Grading

```text
grading provider/service unavailable
```

Verify technical grading failure is not `UNCERTAIN`.

### Generation

```text
generation unavailable
```

Verify no successful DRAFT/published state is fabricated.

### RAG

```text
no evidence
out of domain where supported
retrieval/provider technical failure
```

Technical failure must not be classified as semantic refusal.

### Content

```text
unapproved Document
DRAFT generated assessment
invalid publication transition
```

---

## Launch-Blocking Invariants

Verify these authoritative invariants where actual product contracts expose them:

1. frontend cannot determine trusted publication state;
2. AI-generated content never auto-publishes;
3. unapproved documents cannot become trusted evidence;
4. technical AI failure is not no-evidence;
5. technical grading failure does not unlock learner progression;
6. learner cannot execute Admin-only mutations;
7. progression/unlock persists server-side;
8. Lesson Chat remains Lesson-scoped;
9. user state/conversation state is isolated;
10. chat memory/history is context, not evidence;
11. historical citation identity is not incorrectly resolved against a different current source map.

Do not add invented invariants that the current product does not actually implement.

---

## Existing Regression Preservation

Do not replace existing tests.

Run appropriate existing suites for:

```text
frontend unit/component
backend auth
business/progression
conversation
document pipeline
RAG/citations
AI grading
AI generation
Phase-7 evaluation/regression
```

Exact commands must be derived from actual repository scripts/configuration.

Frontend baseline should include the repository equivalents of:

```text
npm ci
npm run build
npm run test -- --run
```

Do not invent package scripts without necessity.

---

## QA Evidence States

Use exactly these Step-8.1 evidence meanings:

```text
PASS
FAIL
ENVIRONMENT_GATE
DEFERRED_EVALUATION_GATE
```

### PASS

Test/criterion executed successfully with valid deterministic evidence.

### FAIL

Test executed and behavior violated the frozen product contract.

### ENVIRONMENT_GATE

Could not execute because Step-8.1 environment/infrastructure was unavailable.

Examples:

```text
browser runtime unavailable
test DB unavailable
required local test process cannot start
```

Do not call this PASS.

### DEFERRED_EVALUATION_GATE

The product path can be deterministically tested but release evidence still depends on a known deferred official Phase-7 evaluation.

Known deferred gates:

```text
Step 7.4 official runtime/human evaluation
Step 7.5 official E2E AI evaluation
Step 7.7 official grading/generation evaluation
Step 7.6 official regression comparison
```

Do not convert these to PASS merely because deterministic Step 8.1 tests pass.

---

## QA Artifacts

Create/update:

```text
docs/qa/
├── step-8.1-test-plan.md
├── step-8.1-release-checklist.md
└── step-8.1-run-report.md
```

Follow existing repository documentation conventions if an equivalent QA location already exists.

Do not create duplicate documentation structures unnecessarily.

### Test Plan Schema

For every test/group record:

```text
test_id
test_group
journey
test_level
setup
input/action
expected user-visible result
expected persisted/business state
deterministic boundary
cleanup
launch_blocking
```

### Release Checklist Schema

For every launch criterion:

```text
criterion_id
criterion
launch_blocking
required_test_ids
status
evidence
notes
```

Status must use:

```text
PASS
FAIL
ENVIRONMENT_GATE
DEFERRED_EVALUATION_GATE
```

### Run Report Schema

For each executed test/group:

```text
test_id
journey
test_level
launch_blocking
command
result
evidence
failure_reason
deferred_gate
```

Report metadata should record safe values equivalent to:

```text
timestamp
code revision when available
browser E2E framework selected
browser/version when applicable
APP_ENV
safe test DB identity
AI boundary mode
```

Never log:

```text
passwords
tokens
DSN credentials
provider API keys
secrets
```

---

## Overall Step-8.1 Result Logic

The Step-8.1 run report must not collapse incomplete evidence into PASS.

Conceptually:

```text
any launch-blocking FAIL
→ deterministic QA fails

no launch-blocking FAIL
but required QA execution blocked by environment
→ ENVIRONMENT_GATE remains visible

deterministic tests pass
but Phase-7 official evaluation remains deferred
→ deterministic Step-8.1 implementation may be accepted
→ release checklist retains DEFERRED_EVALUATION_GATE

all deterministic QA criteria pass
→ does NOT mean PRODUCT RELEASE READY
```

Do not create a production release approval field that bypasses PM governance.

---

## Deterministic Test Plan

Implement/execute the following logical groups.

### T01 — Frontend Existing Regression

```text
install from lockfile
build
Vitest/RTL suite
```

Expected:

```text
PASS
```

or explicit environment/failure evidence.

### T02 — Backend Existing Regression

Run focused/current backend suites covering accepted product behavior.

### T03 — Browser Infrastructure Smoke

Verify:

```text
browser
→ frontend
→ FastAPI
→ test PostgreSQL
```

works before product journeys.

### T04 — New Learner Journey

Execute B1.

### T05 — Periodic-Test Gate

Execute B2.

### T06 — Lesson Chat Journey

Execute B3.

### T07 — Admin Lifecycle

Execute B4.

### T08 — AI-Generated Assessment

Execute B5.

### T09 — Auth / Authorization

Cover:

```text
invalid session
Learner → Admin
cross-user isolation
```

### T10 — AI Grading

Cover:

```text
GRADED
UNCERTAIN
technical failure
```

### T11 — RAG

Cover:

```text
normal
fallback
no evidence
technical failure
citation
multi-turn isolation
```

### T12 — Document Trust

Cover approved/unapproved trust behavior.

### T13 — Generation Failure

Cover deterministic generation technical failure and no auto-publish.

### T14 — Persistence

Fresh-read verification for critical persisted state.

### T15 — Report Integrity

Verify every launch-blocking criterion maps to test evidence and accepted status.

Ensure:

```text
FAIL != PASS
ENVIRONMENT_GATE != PASS
DEFERRED_EVALUATION_GATE != PASS
```

---

## Testing Constraints

Do NOT:

- require production DB;
- use SQLite as PostgreSQL replacement;
- call paid providers;
- depend on arbitrary public Internet;
- seed production-like bulk data;
- add sleeps when deterministic state assertions/events can be used;
- test every backend branch through browser;
- create backend endpoints solely to assist browser tests;
- weaken auth/security for tests;
- expose tokens to browser test code if normal UI does not expose them;
- modify production business logic just to make tests pass.

Test-only dependency injection/configuration may use the existing project boundaries.

---

## Step Documentation

Produce/update Step-8.1 documentation.

### A. Step Note

Include:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- reusable testing approach
- Common Mistakes
- Definition of Done

### B. Concepts Discovered

Record only concepts actually used.

Expected candidates:

```text
End-to-End Testing — SYSTEM
Test Pyramid / Test Scope — SYSTEM
Deterministic Test Fixture — BOTH
Test Environment Isolation — SYSTEM
Authorization Boundary Testing — SYSTEM
Failure-Semantics Verification — BOTH
Release Checklist — SYSTEM
```

### C. Tools Used

Record only tools actually used.

Expected existing:

```text
pytest
PostgreSQL
pgvector
Vitest
React Testing Library
```

Browser tool:

```text
existing suitable browser framework
OR
Playwright
```

Do not record Playwright if preflight selects another existing framework.

### D. Step Specification

Reconcile the final implementation back into the Step Specification, including actual filenames, commands, test IDs and selected browser framework.

---

## Acceptance Criteria

The offline/deterministic Step-8.1 implementation is ready for Specialist review when:

- D-111 preflight was performed against actual frontend files;
- exactly one browser E2E framework is used;
- Playwright is used when no suitable browser framework previously existed;
- existing suitable browser framework is reused if one exists;
- Vitest/RTL remains unit/component tooling;
- B1–B5 are covered at browser level;
- browser tests remain intentionally small;
- backend/API business invariants remain integration-tested;
- learner/Admin authorization is verified;
- cross-user isolation is verified;
- progression and periodic-test rules are verified;
- grading GRADED/UNCERTAIN/technical failure are verified;
- technical grading failure cannot unlock progress;
- RAG normal/fallback/no-evidence/technical failure behavior is verified;
- technical RAG failure is not treated as no-evidence success;
- citation/history isolation behavior is verified;
- unapproved documents cannot become trusted evidence;
- generated AI assessment starts as DRAFT;
- no-auto-publish is verified;
- test environment uses dedicated PostgreSQL + pgvector;
- APP_ENV=test and TEST_DATABASE_URL conventions are reused;
- no SQLite replacement is introduced;
- deterministic seed/reset/cleanup exists;
- no paid/live provider calls occur;
- existing relevant regression suites remain passing or their failures are explicitly reported;
- `docs/qa/` evidence artifacts exist;
- every launch-blocking criterion has traceable evidence;
- Phase-7 deferred official gates are represented as `DEFERRED_EVALUATION_GATE`;
- Step-8.1 deterministic PASS is never represented as product release readiness;
- no Step 8.2/deployment/CI work is implemented.

---

## Required Codex Handoff

Return:

```text
Step
Status
Actual frontend preflight findings
Browser E2E framework selected
Why that framework was selected under D-111
What was implemented
Files/components changed
Frontend/backend startup commands
Test DB lifecycle
Fixture/seed summary
Deterministic AI boundaries used
Browser journeys implemented
API/integration groups
Tests run/results
QA artifact paths
Acceptance Criteria status
Concepts added
Tools added
Problems/risks
Environment gates
Deferred evaluation gates
Decisions needed
Recommended next action
```

Expected successful implementation status:

```text
READY_FOR_SPECIALIST_REVIEW — DETERMINISTIC PRODUCT QA IMPLEMENTATION
```

Do not claim:

```text
Step 8.1 DONE
PRODUCT RELEASE READY
```

If actual repository evidence conflicts materially with D-111 or another frozen architecture decision:

```text
BLOCKED — DECISION NEEDED
```

Do not silently redesign.
