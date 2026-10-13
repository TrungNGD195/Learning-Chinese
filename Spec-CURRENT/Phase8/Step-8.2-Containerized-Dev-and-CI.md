# Step 8.2 — Containerized Development & CI

## Frozen implementation boundary

Use D-112 GitHub Actions and DB-only Docker Compose. Compose contains PostgreSQL 17 with pgvector 0.8.6 only. FastAPI/uv, React/Vite/npm, and Playwright Chromium run as native host/runner processes. Do not add application Dockerfiles, deployment infrastructure, product API/schema/business changes, or Step 8.3 work.

## Context

The project needs reproducible setup and automated verification without Kubernetes or distributed infrastructure.

## Objective

Provide reproducible local database startup and deterministic CI gates from the committed `uv.lock` and `package-lock.json`, including fresh migrations, database/extension identity, full tests/builds, live OpenAPI type comparison, and Playwright Chromium E2E.

## Current State

Backend, frontend, PostgreSQL/pgvector requirements, lockfiles, deterministic tests, and the accepted Step 8.1 browser suite are present.

## In Scope

Root Compose database service; dedicated local test database initialization; placeholder-only environment setup; cross-platform Playwright commands using uv; current-head Alembic and pgvector verification; one GitHub Actions workflow for backend/frontend/API-contract/Chromium gates; run report and Step Note.

## Out of Scope

Backend/frontend Dockerfiles, Kubernetes, Terraform, Redis, queues/workers, deployment configuration, another CI provider or browser E2E framework, paid/live Phase-7 evaluation, and Step 8.3.

## Functional Requirements

A developer can start the local database dependency, apply migrations, and run documented checks. CI fails on migration, backend, frontend, OpenAPI contract, or browser-test failure. AI and network seams remain deterministic in normal CI.

## Technical Requirements

Use `pgvector/pgvector:0.8.6-pg17`, bind the database to loopback, include a `pg_isready` health check, and persist local development data in a named volume. Alembic owns application schema. CI uses Python 3.12, uv, Node 22/npm, and lockfiles; required gates use normal failing status; no production secrets enter caches or images; no Windows-only Python path remains in the Playwright flow. Resolve the expected migration head dynamically where practical.

## Interfaces / API / Schema

No product API or database schema changes. The database init hook creates only the separate `chinese_learning_test` database; migration `0001` remains responsible for `CREATE EXTENSION vector`.

## Files / Components

Root `compose.yaml`, optional second-database init SQL, one `.github/workflows/ci.yml`, uv-driven Playwright lifecycle/server commands, a safe database verification helper, and `docs/devops` setup/report/Step Note.

## Config / Env

`.env.example` files contain placeholders only. Local `.env` files are ignored. CI uses runner-local test-only DB/signing values, no provider credentials, and does not cache environment files or database volumes.

## Error Handling

Fail fast with actionable command output. Do not use `|| true` to bypass a required gate.

## Required Verification

Run locked backend/frontend installs; apply and inspect Alembic migrations on development and test databases; verify current migration head and pgvector; run backend compile/full pytest; frontend lint/Vitest/build; live `npm run api:check`; and the full deterministic Chromium Playwright suite. CI must use the same root Compose database definition.

## Acceptance Criteria

- [ ] Fresh local PostgreSQL container supports pgvector and current clean Alembic migrations.
- [ ] Backend/frontend install, test, and build commands use committed lockfiles.
- [ ] The single GitHub Actions workflow runs database, static/test/build, API-contract, and E2E gates.
- [ ] No production secret is committed, logged, cached, or baked into an image.
- [ ] No unnecessary distributed service is introduced.
- [ ] No Windows-only Python executable path remains in the CI-required E2E flow.
- [ ] Accepted Step 8.1 B1/B4 behavior and Playwright as the only browser framework remain intact.
- [ ] Official Phase-7 evaluations remain deferred.

## Learning Deliverables

See [setup and CI guide](../../docs/devops/step-8.2-container-ci.md), [run report](../../docs/devops/step-8.2-run-report.md), and [Step Note](../../docs/devops/step-8.2-step-note.md).
