# Step 8.2 — Reproducible Development and CI

## Objective

Make local development and hosted checks prove the same backend, frontend, database, API-contract, and browser-test requirements from committed lockfiles.

## Why

Reproducible setup makes failures easier to reproduce and keeps hidden prerequisites from making a local pass differ from a CI pass. Official Phase 7 evaluations are separate gates and remain deferred.

## Mental Model

```text
Git change
→ reproducible dependency setup
→ PostgreSQL/pgvector dependency
→ migrations
→ static checks
→ backend/frontend tests
→ build/API-contract/browser verification
→ CI result
```

Local and CI must prove the same contracts. Tests establish the data prerequisites they consume; a global setup must not hide missing scenario setup.

## Core Knowledge

- Lockfiles make dependency resolution repeatable across machines.
- PostgreSQL with pgvector is a database dependency; app servers and browser tests run natively on the host or CI runner.
- Alembic owns application schema creation and validates migration drift.
- The test database is distinct and dedicated. Reset helpers verify its identity and runtime safety before destructive work.
- Deterministic provider seams keep normal tests independent of paid AI APIs and public retrieval services.
- Required CI gates use ordinary failing exit codes so a broken check fails the job.

## Data Flow

```text
checkout
→ install from uv.lock and package-lock.json
→ start PostgreSQL/pgvector
→ migrate development and test databases
→ verify migration head and vector extension
→ compile and test backend
→ lint, test, and build frontend
→ check live OpenAPI contract
→ run deterministic Chromium suite
→ report CI result
```

## Key Design Decisions

- Docker Compose runs only PostgreSQL 17 with pgvector 0.8.6. FastAPI, Vite, and Playwright run as native processes.
- One GitHub Actions Linux quality workflow reuses the root Compose definition.
- The container initializes `chinese_learning` and creates the separate `chinese_learning_test` database; Alembic owns application schema.
- Backend tests explicitly seed required system data where needed. There is no global CI seed workaround.
- Playwright Chromium is the sole browser E2E framework. Vitest/RTL covers frontend unit and component behavior.
- Caches contain dependency/browser artifacts only, never `.env` files, database volumes, provider credentials, or production data.
- Official Phase 7.4, 7.5, 7.7, and 7.6 gates are not part of normal CI.

## Reusable Approach for Another Project

1. Identify the real external dependencies and keep the container boundary small.
2. Commit lockfiles and document placeholder-only environment setup.
3. Apply migrations to clean databases and verify both the current head and extensions.
4. Make each test own or explicitly establish its data prerequisites.
5. Reuse the same service definition locally and in CI.
6. Run static, unit, integration, contract, and browser gates with normal failure semantics.
7. Keep paid or human evaluation outside routine CI unless separately authorized.

## Common Mistakes

- Depending on tests having run in a particular order to create required system rows.
- Seeding all tests globally and hiding an incomplete scenario setup.
- Using `create_all()` as a replacement for migrations.
- Running app or browser processes inside the database container.
- Caching secrets or database state with dependency caches.
- Treating deferred evaluation gates as passed because ordinary CI is green.

## Definition of Done

The documented implementation evidence shows local runtime and hosted CI gates closed, with matching deterministic contracts and no official Phase 7 evaluation reported as passed. PM final Step acceptance remains pending documentation review.

## Concepts Discovered

- Reproducible Environment | SYSTEM | MUST KNOW
- Container / Container Image | SYSTEM | MUST KNOW
- CI Pipeline | SYSTEM | MUST KNOW
- Environment Variables / Secrets | SYSTEM | MUST KNOW
- Migration Validation | SYSTEM | MUST KNOW
- Deterministic Test Boundary | BOTH | MUST KNOW
- Health Check | SYSTEM | SHOULD KNOW
- Dependency Caching | SYSTEM | SHOULD KNOW

## Tools Used

- Docker | Tool | SYSTEM
- Docker Compose | Tool | SYSTEM
- GitHub Actions | Tool | SYSTEM
- PostgreSQL | Tool | BOTH
- pgvector | Tool | AI
- Alembic | Tool | SYSTEM
- uv | Tool | SYSTEM
- npm | Tool | SYSTEM
- pytest | Tool | SYSTEM
- Vitest / RTL | Tool | SYSTEM
- Playwright | Tool | SYSTEM
- Oxlint | Tool | SYSTEM
