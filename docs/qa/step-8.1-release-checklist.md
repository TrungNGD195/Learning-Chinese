# Step 8.1 — Product QA & End-to-End Verification: Release Checklist

Statuses: `PASS`, `FAIL`, `ENVIRONMENT_GATE`, `DEFERRED_EVALUATION_GATE`.

| Criterion ID | Criterion | Launch-blocking | Required test IDs | Status | Evidence | Notes |
|---|---|---:|---|---|---|---|
| C01 | Frontend regression, build, lint, generated API contract | Yes | T01 | PASS | 326 Vitest tests; build succeeds; lint exits 0; `api:check` matches live OpenAPI | Existing chunk-size and lint warnings remain |
| C02 | Dedicated PostgreSQL + pgvector lifecycle | Yes | T03, T14 | PASS | Guarded reset and seed pass; loopback DB identity verified; head 0012 | Existing cyclic-FK SQLAlchemy warning |
| C03 | New learner completes pronunciation and unlocks Lesson | Yes | T04 | PASS | B1 Playwright completes all three canonical sections; backend Dashboard returns Lesson AVAILABLE and Continue Learning opens Lesson A | Availability is read from backend progression state |
| C04 | Periodic-Test failure remains gated; retry pass unlocks | Yes | T05 | PASS | Playwright B2 passes against persisted PostgreSQL state | Deterministic multiple-choice scoring |
| C05 | Lesson-scoped Chat persists across refresh | Yes | T06 | PASS | Playwright B3 passes; conversation carries Lesson A context and history survives reload | Deterministic no-evidence scenario; no citation expected |
| C06 | Admin lifecycle publishes content visible to learner | Yes | T07 | PASS | B4 Playwright verifies publish alone does not add membership; Admin explicitly adds/saves the Lesson and learner curriculum then returns it | New unit can remain LOCKED under existing progression rules |
| C07 | Generated assessment remains DRAFT until explicit Admin review/publish | Yes | T08, T13 | PASS | Playwright B5 plus Step 6.12 API tests pass | Learner sees it unavailable before publish and available after publish |
| C08 | Learner cannot use Admin UI/API; user data isolated | Yes | T09 | PASS | Playwright Admin guard; auth, ownership and conversation tests pass | Backend is authorization authority |
| C09 | Grading statuses and technical failure preserve progression rules | Yes | T10 | PASS | Step 6.11 and progression integration tests pass | No local correctness/pass threshold |
| C10 | RAG technical failure differs from no-evidence; scope/citations retained | Yes | T11 | PASS | Step 6.8-A/B focused regression tests pass | No live external search or paid provider |
| C11 | Document approval controls trusted evidence | Yes | T12 | PASS | 61 document/source-policy/pipeline tests pass | No production documents or storage used |
| C12 | Critical mutation persistence checked with fresh read/refresh | Yes | T14 | PASS | Browser B2/B3/B5 and backend integration groups pass | PostgreSQL only |
| C13 | Step 7 official evaluation evidence | Yes | T15 | DEFERRED_EVALUATION_GATE | Frozen official gates remain open | No official evaluation was run |
| C14 | All launch blockers have truthful evidence/status | Yes | T15 | PASS | Current checklist matches focused B1/B4 browser and backend evidence; Phase-7 evaluation gates remain deferred | No Step 8.1 completion or release decision is made |

## Product release decision

No product-release conclusion is made. B1 and B4 passed their focused rework verification; official Phase-7 evaluation gates remain deferred.
