# Step 8.1 implementation handoff

## Status

`READY_FOR_SPECIALIST_REVIEW — B1+B4 PRODUCT REWORK`

This status covers the B1+B4 focused product rework and review evidence. Step 8.1 is not claimed DONE, and product release readiness is not claimed.

## Frontend preflight / D-111

- Existing frontend had Vitest and React Testing Library but no configured browser E2E runner.
- Exactly one browser framework was selected: Playwright 1.64.0 with Chromium. Vitest/RTL remain unit/component tools; Vitest is scoped to `src/`.
- Vite API client uses the backend API prefix and current generated OpenAPI DTOs. `npm run api:check` passed against current FastAPI OpenAPI.

## Implemented

- Added Playwright config and five browser cases for B1–B5 plus an Admin-route denial case.
- Added deterministic test-only chat, grading, and assessment generation boundaries at existing backend seams.
- Added guarded PostgreSQL/pgvector reset and minimal seed. The test password is generated ephemerally at Playwright global setup and is not logged or packaged.
- Added Windows-only ASGI test launcher using SelectorEventLoop for psycopg async. Production app/config are unchanged.
- B1 now completes pronunciation through the existing GET/POST contract and uses canonical completion state plus backend-owned progression reads.
- B4 now edits complete curriculum membership from published Lesson / Periodic Test candidates through the existing PUT contract; publish does not auto-add membership.
- Added QA plan, checklist, run report, Step Note, this handoff, and reconciled Phase 8 specification.

### Focused B1+B4 files changed

- Frontend: `src/features/pronunciation/PronunciationPage.tsx`, `src/features/pronunciation/invalidation.ts`, `src/features/pronunciation/step81-pronunciation.test.tsx`, `src/app/query/keys.ts`.
- Frontend: `src/features/admin/AdminCurriculumPage.tsx`, `src/features/admin/invalidation.ts`, `src/features/admin/step47-admin.test.tsx`, `e2e/step81.spec.ts`.
- Backend tests only: `tests/test_business_flow.py`.
- Evidence: `docs/qa/step-8.1-run-report.md`, `step-8.1-handoff.md`, `step-8.1-test-plan.md`, `step-8.1-release-checklist.md`, `step-8.1-step-note.md`.

### Contract and scope checks

- B1 uses existing `GET /api/v1/pronunciation` and `POST /api/v1/pronunciation/{section_id}/complete`. Pending requests disable duplicate actions; success refetches canonical completion state and invalidates pronunciation, dashboard, curriculum, and progress reads. Errors stay safe and do not mark completion locally.
- B4 discovers published Lessons with selected `hsk_level_id` and published `PERIODIC_TEST` assessments without an invented HSK filter. It stores Add/Remove/Move edits locally, then sends the full desired membership as `{ units: [{ unit_type, target_id, order_index }] }` with normalized `1..N` ordering to the existing PUT. Unit identity comes from Lesson/Assessment IDs, never the CurriculumUnit row ID.
- Successful save refetches canonical curriculum and invalidates Admin curriculum, learner curriculum, progress, and dashboard. Failed save preserves the draft and requires an explicit retry.
- Backend production changes: NO. API/OpenAPI changes: NO. Migration/schema changes: NO. Runtime dependencies or lockfiles changed: NO. AI/RAG changed: NO. Progression semantics changed: NO.

## Test results

- Frontend focused B1/Admin/progression tests: 90 passed. Full Vitest: 326 passed.
- Backend focused business-flow test: 1 passed, including repeated pronunciation completion, canonical persistence reads, publish alone not creating membership, and curriculum add/remove/order persistence.
- Playwright B1 + B4 rerun: 2 passed. B1 completes all sections and follows backend Dashboard availability to Lesson A. B4 confirms explicit membership is required and becomes visible in learner curriculum after save.
- Production build passed (existing >500 kB chunk warning); lint exited 0 with existing warnings; API contract check matches live OpenAPI.
- Full backend pytest: 1,152 passed, 1 skipped. Pytest emitted a cache-directory permission warning; tests completed successfully.
- The `uv run pytest` launcher could not initialize the external user uv cache due to Windows access denial; equivalent required pytest commands ran with the existing `backend/.venv` Python interpreter.
- B2/B3/B5 and learner-to-Admin denial remain covered by the previously accepted Step 8.1 browser run; this task reran only B1 and B4 as authorized.
- Backend focused auth/business/progression/conversation/grading/RAG/regression group: 198 passed.
- Backend document/source-policy/ingestion/reprocessing group: 61 passed.
- Backend `compileall app`: passed.

## Environment / safety

- Verified target: local `chinese_learning_test`, PostgreSQL 17.6, pgvector 0.8.6, migration head `0012_vector_storage_readiness`.
- Production DB used: NO. SQLite introduced: NO. Paid/live AI calls: 0. Live external search: 0.
- Playwright reset revalidates environment, database identity, loopback host, pgvector, and migration head immediately before truncation.
- The reset emits an existing SQLAlchemy warning for cyclic foreign keys across documents/parsing/transformation run metadata. Reset completed successfully.
- Repository Git revision unavailable in this workspace.

## Remaining work / gates

- Independent App Engineering review of the focused B1+B4 changes and evidence is recommended.
- Official Step 7.4, 7.5, 7.7, and 7.6 gates remain `DEFERRED_EVALUATION_GATE`.
- Step 8.2, CI/CD, deployment, and release approval were not started.
- Official Phase-7 evaluation run: NO. `HUMAN_APPROVED` annotations: unchanged.

Recommended next action: Independent App Engineering Specialist review of the B1+B4 implementation and updated review ZIP.
