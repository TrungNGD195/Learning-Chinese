# Step 8.2 — Containerized Development and CI

## Frozen Implementation Boundary

Use D-112 GitHub Actions and database-only Docker Compose. Compose runs PostgreSQL 17 with pgvector 0.8.6. FastAPI/uv, React/Vite/npm, and Playwright Chromium run as native host or CI-runner processes. Do not add application Dockerfiles, deployment infrastructure, product API/schema/business changes, or Step 8.3 work.

## Context and Objective

Provide reproducible local database startup and deterministic CI gates from committed `uv.lock` and `package-lock.json`, including clean migrations, database/extension checks, backend and frontend verification, live OpenAPI type comparison, and Playwright Chromium E2E.

## Current State

### Local Runtime

- Root `compose.yaml` defines one database-only service using `pgvector/pgvector:0.8.6-pg17`.
- The container exposes PostgreSQL on loopback, has a `pg_isready` health check, and uses a persistent local named volume.
- The service initializes `chinese_learning`; its init SQL creates only the separate `chinese_learning_test` database.
- Alembic owns application schema and installs the vector extension through migration history.
- Accepted fresh local verification migrated both development and test databases from 0001 through 0012. Current head is `0012_vector_storage_readiness`; `alembic check` reports no new upgrade operations. pgvector 0.8.6 was verified in both databases.
- Backend and frontend tools run natively on the host using Python 3.12/uv and Node 22/npm.

### Hosted CI

- `.github/workflows/ci.yml` defines one Linux GitHub Actions quality pipeline with no matrix or sharding in V0.
- The workflow reuses the root Compose database and performs locked installs, migrations/current/check, database and pgvector verification, backend compile/full pytest, frontend lint/Vitest/build, live API contract verification, and deterministic Chromium Playwright.
- Accepted GitHub-hosted quality job passed in approximately 3m05s. Hosted Vitest passed 14/14 files and 326/326 tests.
- CI test scenarios establish required seed data explicitly. Step 7.7 manifest tests use a deterministic fake commit identity; the production runner is unchanged.

### Verification Evidence

- Local backend: 1,152 passed, 1 skipped, 0 failed.
- Local frontend: `npm ci`, lint, 326 Vitest tests, production build, and live `api:check` passed.
- Local deterministic Playwright Chromium: 6/6 passed with one worker.
- Non-blocking warnings and the dependency advisory are recorded in the [Step 8.2 run report](../../docs/devops/step-8.2-run-report.md).
- Implementation and verification criteria are satisfied; PM final Step acceptance is pending documentation review. Step 8.3 has not been opened.

## In Scope

- Root database-only Compose service and initialization of the dedicated local test database.
- Placeholder-only environment setup and cross-platform Playwright commands using uv.
- Current-head Alembic and pgvector verification.
- One GitHub Actions workflow for backend, frontend, API-contract, and Chromium gates.
- Reproducibility documentation and run evidence.

## Out of Scope

Backend/frontend Dockerfiles, Kubernetes, Terraform, Redis, queues/workers, deployment configuration, another CI provider or browser E2E framework, paid/live Phase-7 evaluation, and Step 8.3.

## Runtime and Container Boundary

```text
Docker Compose
└── PostgreSQL 17 + pgvector 0.8.6

Native host / GitHub runner
├── FastAPI + uv (Python 3.12)
├── React/Vite + npm (Node 22)
└── Playwright Chromium
```

Development and test databases are `chinese_learning` and `chinese_learning_test`. The init SQL creates only the latter; it does not duplicate application schema. Alembic migrations remain the only schema owner.

## Configuration and Safety

- Test execution uses `APP_ENV=test` and `TEST_DATABASE_URL` targeting `chinese_learning_test`; the test and development database identities differ.
- PostgreSQL+psycopg is required. SQLite is not used.
- Environment templates contain placeholders only. Local `.env` files are ignored.
- Workflow database/signing values are CI-local test values; no production secret is committed, logged, cached, or baked into an image.
- Normal CI uses deterministic test seams. It requires no live LLM/provider credentials and makes no live external retrieval calls.
- Database reset helpers validate dedicated database identity, loopback, PostgreSQL+psycopg, pgvector, and the checked-out migration head before destructive work.
- Dependency caches may contain package/browser downloads only; they exclude `.env`, database volumes, provider credentials, and production data.

## Functional Requirements

Developers can start the database dependency, apply migrations, and run documented checks. CI fails normally on migration, backend, frontend, API-contract, or browser-test failure. Deterministic AI and network seams remain offline in routine CI.

## Acceptance Criteria

- [x] **AC1** — Local PostgreSQL supports pgvector and clean Alembic migrations.
- [x] **AC2** — Backend/frontend install, test, and build commands are reproducible from committed lockfiles.
- [x] **AC3** — CI runs required database, static/test/build, API-contract, and E2E gates.
- [x] **AC4** — No production secret is committed, logged, cached, or baked into an image.
- [x] **AC5** — No unnecessary distributed service is introduced.
- [x] No Windows-only Python executable path remains in the CI-required E2E flow.
- [x] Accepted Step 8.1 B1/B4 behavior and Playwright as the only browser framework remain intact.
- [x] Official Phase-7 evaluations remain deferred.

## Deferred Evaluation Gates

Step 8.2 CI does not execute or claim PASS for:

- Step 7.4 official generation evaluation
- Step 7.5 official end-to-end RAG evaluation
- Step 7.7 official grading/generation evaluation
- Step 7.6 official regression evaluation

## Documentation

- [Setup guide](../../docs/devops/step-8.2-container-ci.md)
- [Run report](../../docs/devops/step-8.2-run-report.md)
- [Step Note](../../docs/devops/step-8.2-step-note.md)

## Open Questions

NONE
