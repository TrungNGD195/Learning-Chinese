# Step 8.2 — Containerized Development and CI Run Report

## Repository and scope

- Frozen task: `codex-tasks/phase8/step-8.2-containerized-development-ci-codex-task.md`.
- Scope: DB-only Compose plus one GitHub Actions workflow; backend/frontend remain native processes.
- Git commit identity: unavailable in this workspace snapshot; repository files report as untracked.
- Docker/Compose and GitHub-hosted workflow execution: not available in this implementation environment.

## Verification results

| Gate | Command / evidence | Result |
|---|---|---|
| Backend dependency lock | `uv sync --frozen` | PASS — 81 packages checked |
| Database identity | `uv run python -m tests.step81.verify_database --environment test` | PASS — dedicated `chinese_learning_test`; identity distinct from `DATABASE_URL` |
| PostgreSQL / pgvector | Same verification helper | PASS — PostgreSQL 17 (`server_version_num=170006`) and pgvector 0.8.6 |
| Migration upgrade | `APP_ENV=test uv run alembic upgrade head` | PASS — database was already current; no upgrade operations were needed |
| Migration current | `APP_ENV=test uv run alembic current` | PASS — `0012_vector_storage_readiness` |
| Migration drift | `APP_ENV=test uv run alembic check` | PASS — no new upgrade operations detected; existing cyclic-FK sort warning remains |
| Dynamic migration guard | Reset and verification helpers resolve `ScriptDirectory.get_heads()` | PASS — current repository head matched `0012_vector_storage_readiness` |
| Backend compile | `uv run python -m compileall -q app` | PASS |
| Backend full suite | `uv run pytest -q` | PASS — 1,152 passed, 1 skipped; pytest cache permission warning |
| Frontend locked install | `npm ci` | PASS — 222 packages installed; npm reported one high-severity advisory in the existing lockfile; no dependency change was made |
| Frontend lint | `npm run lint` | PASS — exit 0, six existing Oxlint warnings |
| Frontend tests | `npm run test -- --run` | PASS — 14 files, 326 tests |
| Frontend build | `npm run build` | PASS — TypeScript/Vite completed; existing >500 kB bundle warning |
| OpenAPI contract | `npm run api:check` against deterministic FastAPI | PASS — generated types match live OpenAPI |
| Playwright browser suite | `npm run test:e2e` against the guarded test DB | PASS — 6 tests; reset, fixture seed, and teardown passed |
| Compose/workflow syntax | YAML parser loaded `compose.yaml` and `.github/workflows/ci.yml` | PASS — syntax only |
| Compose runtime | `docker compose config` / `docker compose up -d --wait db` | BLOCKED — Docker CLI is unavailable; fresh container and first-volume initialization not exercised |
| GitHub Actions runtime | Workflow execution | NOT RUN — no hosted runner was available from this workspace |

## Playwright ordering finding

The first full browser run passed 5 of 6 tests. B2 passed when run alone. B4 deliberately adds a Lesson to the shared HSK 1 curriculum; when B2 ran after B4, that state made B2's baseline next-HSK assertion fail. The B2 test block was moved before B4 without changing any test action or assertion. The complete suite then passed 6 of 6. B1 and B4 product behavior and assertions are unchanged.

## Secrets and safety

- Compose binds its PostgreSQL port to loopback and uses local-only defaults matching the placeholder backend template.
- CI database/signing values are test-only; no provider keys are needed or configured.
- `.env` files, database volume, and provider credentials are excluded from package caches.
- Test DB lifecycle revalidates environment, dedicated database, loopback, PostgreSQL+psycopg, distinct DB identity, pgvector, and current migration head before reset.
- No real credential values were printed or included in the handoff artifact.

## Deferred gates

No official Step 7.4, 7.5, 7.7, or 7.6 evaluation was run. No paid/live LLM or external retrieval call was made. The local container boot and actual hosted CI execution remain unverified until a Docker-enabled machine/runner executes the workflow.
