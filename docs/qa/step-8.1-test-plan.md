# Step 8.1 — Product QA & End-to-End Verification: Test Plan

## Environment and boundaries

- Database: local dedicated PostgreSQL `chinese_learning_test`, pgvector 0.8.6, Alembic head `0012_vector_storage_readiness`.
- Browser: Playwright 1.64.0, Chromium; unit/component: Vitest + React Testing Library.
- AI: deterministic test-only chat, grading, and assessment-generation boundaries; no paid provider or live external search.
- Reset and seed are explicit guarded Python commands invoked by Playwright global setup/teardown. The reset rechecks environment, database identity, loopback host, PostgreSQL/pgvector, and migration head before truncation.

## Test groups

| Test ID | Test group | Journey | Test level | Setup | Input/action | Expected user-visible result | Expected persisted/business state | Deterministic boundary | Cleanup | Launch-blocking |
|---|---|---|---|---|---|---|---|---|---|---|
| T01 | Frontend regression | Existing UI behavior | Unit/component | `npm ci` | `npm run test -- --run`, build, lint | Components compile and regressions pass | None | Vitest/RTL | None | Yes |
| T02 | Backend relevant regression | Auth, ownership, progression, conversation, AI, documents, evaluation regression | API/integration | Verified isolated PostgreSQL | Focused pytest groups | Frozen API and failure contracts hold | Fresh DB assertions | Existing fakes and fixtures | Per-test cleanup | Yes |
| T03 | Browser infrastructure smoke | Browser → frontend → FastAPI → PostgreSQL | Browser/API | Guarded reset + canonical seed | Start Playwright servers and use real UI/API | Routes and API calls respond | PostgreSQL-backed reads/writes | Test-only deterministic AI | Global teardown guarded reset | Yes |
| T04 | New learner | Register → pronunciation → Lesson → objective exercise → persisted progression | Browser | Fresh learner; required curriculum fixture | Register and complete pronunciation | Learner can complete three required sections and see Lesson A unlocked | Pronunciation and progress rows persist after refresh | Real auth/session; DB fixture | Guarded reset | Yes |
| T05 | Periodic-Test gate | Fail → remain locked → retry → pass → unlock | Browser | Seeded learner and HSK curriculum | Submit wrong then correct option | Failure stays gated; pass opens HSK 2 | Attempts and progression persist | Deterministic objective scoring | Guarded reset | Yes |
| T06 | Lesson Chat | Lesson-scoped conversation and refresh | Browser | Seeded learner + Lesson A | Start conversation, send, reload | No-evidence response and history render in Lesson context | Conversation/messages persist for that user and lesson | Test-only no-evidence AI chat | Guarded reset | Yes |
| T07 | Admin lifecycle | Create/edit/publish Lesson; learner sees published state | Browser/API | Seeded Admin and learner | Create Lesson, save metadata, publish; check learner view | Admin lifecycle succeeds and learner sees trusted published content | Status is PUBLISHED and learner API serves permitted content | PostgreSQL only | Guarded reset | Yes |
| T08 | Generated assessment | Generate → DRAFT → explicit review/publish | Browser | Seeded Admin and Lesson vocabulary | Generate, inspect as learner before/after publish | Draft is unavailable to learner; after explicit publish it is available | DRAFT then REVIEW then PUBLISHED | Test-only structured generation provider | Guarded reset | Yes |
| T09 | Auth/authorization/isolation | Session, Admin denial, cross-user ownership | Browser/API | Seeded users plus API fixtures | Access Admin as learner; attempt cross-user resources | Admin UI denied; private resources remain unavailable | Ownership enforced by backend | Real auth; DB fixtures | Test cleanup/reset | Yes |
| T10 | AI grading | GRADED, UNCERTAIN, technical failure | API/integration | PostgreSQL fixtures | Exercise deterministic outcomes | Status and feedback distinguish outcomes | Technical failure does not unlock progress | Existing grading fakes | Per-test cleanup | Yes |
| T11 | RAG semantics | Normal/fallback/no-evidence/technical failure/citations/history | API/integration | PostgreSQL fixtures | Run fixed offline scenarios | Technical error is distinct from semantic refusal | Lesson/user scope and citations persist correctly | Existing RAG/replay fakes | Per-test cleanup | Yes |
| T12 | Document trust | Unapproved vs approved evidence | API/integration | PostgreSQL + storage fixture | Exercise source policy and approval lifecycle | Unapproved content is not trusted | Approval/knowledge state follows lifecycle | In-memory storage/provider fakes | Per-test cleanup | Yes |
| T13 | Generation failure/no-auto-publish | AI generation success/failure | API/integration | PostgreSQL fixtures | Generate success and provider failure | Safe failure; success returns draft only | No partial or automatic publication | Existing fake generation providers | Per-test cleanup | Yes |
| T14 | Persistence | Fresh reads after mutation | Browser/API | DB fixtures | Refresh/re-read chat, assessment, progress | Current server state is shown | Persisted mutation matches response | PostgreSQL | Test cleanup/reset | Yes |
| T15 | Report integrity | Evidence/status mapping | Documentation/check | Final report and test results | Verify each launch blocker maps to evidence | FAIL/environment/deferred are not presented as PASS | N/A | Manual cross-check | N/A | Yes |

## B1 + B4 rework coverage

B1 now uses the canonical pronunciation GET and existing completion POST. The browser completes TONES, INITIALS, and FINALS, then follows the backend Dashboard Continue Learning destination to Lesson A. Component tests cover pending, safe failure, persisted completion, invalidation, and backend-owned availability.

B4 now discovers only published Lessons for the selected HSK and published PERIODIC_TEST assessments. Admin can add, detach, reorder, and save one local full-membership draft through the existing PUT. Browser coverage verifies publishing alone does not add the Lesson, then verifies explicit curriculum membership appears in the learner curriculum. Backend integration coverage verifies add/remove/order persistence and leaves the published Lesson intact after detachment.

## Deferred gates

Step 7.4 official runtime/human evaluation, Step 7.5 official E2E AI evaluation, Step 7.7 official grading/generation evaluation, and Step 7.6 official regression comparison remain `DEFERRED_EVALUATION_GATE`. This QA did not execute them.
