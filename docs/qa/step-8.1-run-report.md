# Step 8.1 — Product QA & End-to-End Verification: Run Report

## Run metadata

- Timestamp: 2026-10-13 10:14:46 Asia/Bangkok (2026-10-13 03:14:46 UTC).
- Repository revision: unavailable; workspace has no usable Git repository metadata.
- Browser: Playwright 1.64.0, Chromium.
- App environment: `APP_ENV=test`, `DEBUG=false`.
- Safe database identity: `localhost:5432/chinese_learning_test`; PostgreSQL 17.6, pgvector 0.8.6, migration head `0012_vector_storage_readiness`.
- AI boundary mode: deterministic test-only chat/grading/generation; paid/live calls = 0.
- Database test lifecycle: preflight-guarded reset, fixture seed, final guarded reset. Only the dedicated loopback test DB was used.

## Test results

| Test ID | Journey | Test level | Launch-blocking | Command | Result | Evidence | Failure reason | Deferred gate |
|---|---|---|---:|---|---|---|---|---|
| T01 | Frontend regression | Unit/component | Yes | `npm run test -- --run` | PASS | 14 files, 326 passed | Vitest reports its standard multiple jsdom-environment startup notice | None |
| T01 | Frontend build | Build | Yes | `npm run build` | PASS | TypeScript and Vite build completed | Existing >500 kB JS chunk warning | None |
| T01 | Frontend lint | Static analysis | Yes | `npm run lint` | PASS | Exit 0 | Existing six Oxlint warnings | None |
| T01 | API contract | OpenAPI | Yes | `npm run api:check` with FastAPI at localhost:8000 | PASS | Generated types match live OpenAPI | None | None |
| T02 | Auth/business/conversation/grading/RAG/regression | PostgreSQL integration | Yes | `pytest -q tests/test_auth_flows.py tests/test_business_flow.py tests/test_progression_gates.py tests/test_conversation_api.py tests/test_conversation_concurrency.py tests/test_admin_document_read_contracts.py tests/test_step611_ai_grading.py tests/test_step612_ai_assessment_generation.py tests/test_step68a_rag.py tests/test_step68b_external_retrieval.py tests/test_step76_regression.py` | PASS | 198 passed | Pytest cache write permission warning | None |
| T02/T12 | Source policy/document ingestion/pipeline/reprocessing | PostgreSQL integration | Yes | `pytest -q tests/test_step51_source_policy.py tests/test_step52_document_ingestion.py tests/test_step56_document_pipeline.py tests/test_step57_reprocessing_execution.py tests/test_admin_document_read_contracts.py` | PASS | 61 passed | Pytest cache write permission warning | None |
| T02 | Full backend suite | PostgreSQL integration | Yes | `python -m pytest -q` from `backend/` | PASS | 1,152 passed, 1 skipped | Pytest could not write its local cache directory; suite completed successfully | None |
| T03 | Browser infrastructure | Browser/API/DB | Yes | `npm run test:e2e -- --grep-invert "B1 new learner"` | PASS | Playwright launched Vite + deterministic FastAPI server and completed DB-backed flows | Windows runner uses SelectorEventLoop for psycopg async | None |
| T04 | New learner | Browser | Yes | `npm run test:e2e -- --grep "B1|B4"` | PASS | New learner completes TONES, INITIALS, FINALS; Dashboard reports Lesson AVAILABLE and Continue Learning opens seeded Lesson A; B1+B4 rerun: 2 passed | Existing SQLAlchemy reset warning about cyclic metadata foreign keys; guarded reset and teardown passed | None |
| T05 | Periodic gate | Browser | Yes | `npm run test:e2e -- --grep-invert "B1 new learner"` | PASS | B2 fails first attempt, remains LOCKED, retries and passes, HSK2 becomes AVAILABLE | None | None |
| T06 | Lesson Chat | Browser | Yes | `npm run test:e2e -- --grep-invert "B1 new learner"` | PASS | B3 deterministic no-evidence response and message history survive reload; Lesson context rendered | No citation expected for semantic no-evidence | None |
| T07 | Admin lifecycle / learner visibility | Browser/API | Yes | B4 in `npm run test:e2e -- --grep "B1|B4"` | PASS | Publish alone leaves the Lesson absent; explicit Add + Save membership makes the Lesson visible in the learner HSK curriculum | Newly added Lesson is locked until prior progression gates pass; membership and listing are verified from persisted reads | None |
| T16 | Step 8.1 B1+B4 focused regressions | Frontend/API integration | Yes | Focused Vitest B1/Admin/progression files; `python -m pytest -q tests/test_business_flow.py` | PASS | Frontend 90 passed; backend business-flow 1 passed, including repeated pronunciation completion, canonical completion reads, publish-without-membership, membership add/remove/order persistence | Pytest cache write permission warning | None |
| T08 | Generated assessment | Browser | Yes | B5 in Playwright suite | PASS | Starts DRAFT, learner cannot load it, Admin explicitly reviews/publishes, learner can then load it | None | None |
| T09 | Auth/authorization/isolation | Browser/API | Yes | T09 in Playwright suite plus auth/conversation regression groups | PASS | Learner UI receives Access denied; backend auth and ownership tests pass | None | None |
| T10 | AI grading | API/integration | Yes | Focused Step 6.11/progression tests in T02 | PASS | Existing regression suite passes | None | None |
| T11 | RAG semantics | API/integration | Yes | Focused Step 6.8-A/B tests in T02 | PASS | Existing deterministic RAG and external-boundary tests pass | No live provider/search | None |
| T12 | Document trust | API/integration | Yes | Focused document group | PASS | 61 tests pass | None | None |
| T13 | Generation failure/no-auto-publish | Browser/API | Yes | B5 and Step 6.12 tests in T02 | PASS | Browser proves explicit publish; backend generation regression passes | None | None |
| T14 | Persistence | Browser/API | Yes | B2/B3/B5 plus T02 | PASS | Fresh browser reload/read reflects persisted state | None | None |
| T15 | Report integrity | Documentation | Yes | Manual cross-reference of this report and checklist | PASS | B1/B4 now have passing focused browser/API evidence; deferred evaluation gates remain separately listed | No product-release conclusion is made | Step 7.4, 7.5, 7.7, 7.6 |

## Safety confirmations

- `paid/live provider calls = 0`
- `production DB used = NO`
- `SQLite introduced = NO`
- `Step 8.2 started = NO`
- `CI/CD added = NO`
- `deployment work added = NO`
- `official Phase-7 evaluation run = NO`
- `PRODUCT RELEASE READY claimed = NO`

## Remaining decisions / work

1. Independent App Engineering Specialist review of this focused B1+B4 rework and updated ZIP.
2. Keep official Phase-7 evaluation and product-release decisions with their designated reviewers; this focused rework did not execute an official evaluation.
