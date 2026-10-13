# Step 8.2 — Containerized Development and CI

## Boundary

Docker Compose runs only PostgreSQL 17 with pgvector 0.8.6. FastAPI, Vite, and Playwright run natively through `uv` and `npm`. No application Dockerfiles or deployment infrastructure are part of this step.

The same root `compose.yaml` is used locally and by GitHub Actions. Its database listens only on loopback, persists local data in the `postgres_data` volume, and creates the empty `chinese_learning_test` database through the PostgreSQL image's first-initialization hook. Alembic migrations own all application schema and install the `vector` extension.

## Local setup (PowerShell)

Prerequisites: Docker Desktop with Compose, Python 3.12, `uv`, Node 22, and npm.

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
docker compose up -d --wait db
```

The backend example uses local-only `user` / `password` credentials, matching the Compose defaults. Keep those values local and replace them for any shared environment. `.env` files are ignored by Git. Provider keys are not needed for the deterministic test suite.

Install and prepare both databases:

```powershell
Push-Location backend
uv sync --frozen
$env:APP_ENV = 'development'
uv run alembic upgrade head
uv run alembic current
uv run python -m tests.step81.verify_database --environment development
uv run alembic check
$env:APP_ENV = 'test'
$env:DEBUG = 'false'
uv run alembic upgrade head
uv run alembic current
uv run python -m tests.step81.verify_database --environment test
uv run alembic check
uv run pytest -q
uv run python -m compileall -q app
Pop-Location
```

Run frontend checks and the browser suite:

```powershell
Push-Location frontend
npm ci
npm run lint
npm run test -- --run
npm run build
npx playwright install chromium
npm run test:e2e
Pop-Location
```

Playwright starts its deterministic FastAPI and Vite servers. Global setup generates an ephemeral test password, verifies and resets only the guarded `chinese_learning_test` database, then seeds the Step 8.1 fixture. Teardown runs the same guarded reset. The helper confirms `APP_ENV=test`, loopback PostgreSQL+psycopg, the dedicated database name, distinct development/test database identities, pgvector, and the current repository Alembic head before destructive work.

`npm run api:check` compares generated frontend types with live OpenAPI. Start the deterministic FastAPI server from `backend/` in a separate terminal before running this command:

```powershell
$env:APP_ENV = 'test'
$env:DEBUG = 'false'
$env:CORS_ORIGINS = 'http://127.0.0.1:4173'
uv run python -m tests.step81.run_e2e_server
```

Then run `npm run api:check` from `frontend/`.

## CI flow

`.github/workflows/ci.yml` runs on pushes, pull requests, and manual dispatch. It provisions Python 3.12, uv, Node 22, and npm; starts the shared Compose database; installs from `uv.lock` and `package-lock.json`; migrates and verifies both databases; and runs backend compile, Alembic drift, pytest, frontend lint, Vitest, build, OpenAPI contract, and the complete Chromium Playwright suite. Required gates fail the workflow normally.

CI credentials are fixed local-only values scoped to the ephemeral runner. They are not production secrets and are not logged, cached, or placed in image layers. The uv cache contains dependency artifacts; the npm cache uses `package-lock.json`. Database volumes and `.env` files are not cached. CI requires no LLM or external retrieval credentials and does not call paid providers or public retrieval services.

## Database reset and lifecycle

Compose keeps development data in a named volume. To stop services while retaining it, use `docker compose down`. For a clean disposable local database pair, use `docker compose down --volumes` and then start the service again; PostgreSQL will rerun its initialization hook. This removes the local database volume, so do not use the volume removal command for data you need.

`verify_database.py` derives the expected Alembic head(s) from the checked-out migration graph rather than maintaining a second version string. It prints only safe database name, pgvector version, and migration revision metadata; it never prints a DSN.

## Deferred gates

The official Phase 7.4, 7.5, 7.7, and 7.6 evaluations remain deferred. Normal CI does not perform human annotation, paid model calls, live external search, or official benchmark evaluation.
