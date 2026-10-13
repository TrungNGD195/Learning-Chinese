# Step 8.2 — Containerized Development & CI

## Codex Task

**Mode:** IMPLEMENT STEP 8.2 ONLY

Do not start Step 8.3.
Do not change product API/schema/business semantics.
Do not run paid/live Phase-7 evaluation.
Do not add backend/frontend Dockerfiles.
Do not add Kubernetes, Terraform, Redis, Celery, queues, workers, or a second browser E2E framework.

---

## Frozen decisions

### D-112 — CI Provider
Use **GitHub Actions** only.

Target:

```text
.github/workflows/ci.yml
```

### Container boundary
Use **DB-only Docker Compose**:

```text
Docker Compose
└── PostgreSQL + pgvector

Host / GitHub runner
├── FastAPI + uv
├── React/Vite + npm
└── Playwright Chromium
```

Backend/frontend remain native processes.

---

## Mandatory latest-working-tree preflight

Before modifying files, inspect the actual current repository, not an older review snapshot.

Verify at minimum:

```text
git status / repository root
backend/.env.example
frontend/.env.example
backend/pyproject.toml
backend/uv.lock
backend/tests/conftest.py
backend/tests/step81/
backend/migrations/
frontend/package.json
frontend/package-lock.json
frontend/playwright.config.ts
frontend/e2e/database-lifecycle.ts
frontend/e2e/database-teardown.ts
frontend/e2e/step81.spec.ts
docs/qa/step-8.1-*
```

Confirm the accepted Step-8.1 B1/B4 fixes are present and do not alter them.

If actual current repository materially contradicts this task, stop with:

```text
BLOCKED — DECISION NEEDED
```

Do not redesign silently.

---

## Objective

Make this flow reproducible:

```text
clean checkout
→ configure placeholder/test environment
→ start PostgreSQL + pgvector
→ apply migrations
→ deterministic backend/frontend checks
→ OpenAPI contract check
→ deterministic Playwright E2E
→ PASS / FAIL
```

Step 8.2 is development reproducibility + CI, not production deployment.

---

## Runtime baseline

Use:

```text
Python 3.12
uv
Node 22
npm
PostgreSQL 17
pgvector 0.8.6
```

Use a pinned DB image equivalent to:

```text
pgvector/pgvector:0.8.6-pg17
```

Do not use SQLite.

---

## Local container design

Create a minimal root-level:

```text
compose.yaml
```

with one PostgreSQL/pgvector service.

Requirements:

- expose PostgreSQL to loopback/local development;
- healthcheck with `pg_isready`;
- persistent local named volume is acceptable;
- use placeholder/local-development credentials only;
- create:
  - `chinese_learning`
  - `chinese_learning_test`;
- do not hard-code production credentials;
- migrations, not `create_all`, own application schema;
- migration `0001` remains responsible for `CREATE EXTENSION vector`.

If needed, add a tiny init script only for creating the second test database, e.g.:

```text
infra/postgres/init/01-create-test-database.sql
```

Do not duplicate application schema in init SQL.

---

## Test DB safety

Preserve current guards:

```text
APP_ENV=test
TEST_DATABASE_URL required
database name = chinese_learning_test
TEST_DATABASE_URL != DATABASE_URL
PostgreSQL + psycopg only
```

Do not weaken loopback/dedicated-test safety in Step-8.1 helpers.

---

## Environment templates

Inspect the actual latest templates first.

Update only if required so a new developer can discover the variables needed for local development/testing.

Expected backend placeholders include the actually-used values such as:

```text
APP_ENV
DATABASE_URL
TEST_DATABASE_URL
SECRET_KEY
CORS_ORIGINS
```

Expected frontend placeholder:

```text
VITE_API_BASE_URL
```

Rules:

- placeholders only;
- no real provider/API credentials;
- no production secret;
- `.env` remains untracked;
- do not add unused future variables.

---

## Cross-platform Playwright requirement

Current historical Step-8.1 evidence used Windows-only paths such as:

```text
.venv\Scripts\python.exe
```

The final Step-8.2 CI-required flow must contain **no Windows-only Python path**.

Use repository-normal `uv` execution, conceptually:

```text
uv run python -m ...
```

for:

- Playwright backend test server;
- database reset helper;
- E2E fixture seed;
- teardown/reset.

Keep:

```text
Playwright = sole browser E2E framework
Chromium only
Vitest/RTL = unit/component stack
```

Do not modify accepted B1/B4 product behavior to make CI pass.

---

## Migration validation

CI must prove a clean database can reach the current schema using Alembic only.

Required validation:

```text
fresh database
→ alembic upgrade head
→ alembic current
→ expected current head
→ alembic check
→ PASS
```

Also verify:

```text
SELECT extversion FROM pg_extension WHERE extname = 'vector'
```

returns a version.

No `Base.metadata.create_all()` migration substitute.

Use the repository's current migration head dynamically where practical rather than duplicating a stale hard-coded head in new Step-8.2 infrastructure.

---

## GitHub Actions CI

Create exactly one V0 workflow:

```text
.github/workflows/ci.yml
```

Keep it a simple Linux quality pipeline.

Recommended structure:

```text
checkout
→ Python 3.12
→ uv setup/cache
→ Node 22 + npm cache
→ docker compose up PostgreSQL/pgvector
→ wait healthy
→ uv sync --frozen
→ npm ci
→ migrate clean development/test databases
→ migration validation
→ backend compile/checks
→ full backend pytest
→ frontend lint
→ frontend Vitest
→ frontend build
→ start deterministic FastAPI
→ npm run api:check
→ install Playwright Chromium dependencies/browser
→ full deterministic Playwright suite
→ final cleanup
```

Reuse the same `compose.yaml` DB definition in CI rather than defining a second unrelated PostgreSQL service unless repository constraints make that impossible.

Use CI-local non-production credentials via workflow environment/secret mechanisms.
Never expose credentials in logs.

Dependency caches may cache package downloads only:

```text
uv cache
npm cache
Playwright browser cache only if safe/useful
```

Never cache:

```text
.env
tokens
database data volume
provider credentials
production data
```

Required gates must fail normally.
Do not use `|| true`.

---

## Exact CI gates

### CI_REQUIRED

Backend:

```text
uv sync --frozen
uv run python -m compileall -q app
uv run alembic upgrade head
uv run alembic current
uv run alembic check
uv run pytest -q
```

Database:

```text
PostgreSQL reachable
pgvector installed
dedicated chinese_learning_test exists
test DB safety guards pass
```

Frontend:

```text
npm ci
npm run lint
npm run test -- --run
npm run build
npm run api:check
npm run test:e2e
```

For E2E install only Chromium:

```text
npx playwright install --with-deps chromium
```

### DEFERRED_EVALUATION_GATE

Do not run or convert to CI PASS:

```text
Step 7.4 official runtime/human evaluation
Step 7.5 official E2E AI evaluation
Step 7.7 official grading/generation evaluation
Step 7.6 official regression comparison
```

No paid/live LLM or external retrieval calls in normal CI.

---

## Deterministic AI/network boundary

Normal CI must use existing deterministic fake/stub/replay/test-only seams.

Required:

```text
no LLM_API_KEY required
no external retrieval API key required
no random public Internet dependency
no fabricated official evaluation PASS
```

Do not change production provider/model/prompt behavior.

---

## Expected files

Create/update only as justified by the actual latest repo:

```text
compose.yaml
infra/postgres/init/01-create-test-database.sql        # only if needed
.github/workflows/ci.yml

backend/.env.example                                   # update if required
frontend/.env.example                                  # update if required

frontend/playwright.config.ts
frontend/e2e/database-lifecycle.ts
frontend/e2e/database-teardown.ts

docs/devops/step-8.2-container-ci.md
docs/devops/step-8.2-run-report.md
docs/devops/step-8.2-step-note.md

Spec-CURRENT/Phase8/Step-8.2-Containerized-Dev-and-CI.md
```

Update `.gitignore` only if actual repository needs it.

Do NOT create:

```text
backend/Dockerfile
frontend/Dockerfile
Kubernetes manifests
Terraform
Redis/Celery config
deployment vendor config
```

---

## Verification

### Local clean-checkout path

Prove/document:

```text
clean checkout
→ copy env placeholders to local env files
→ docker compose up -d
→ DB healthy
→ both DBs exist
→ migrations apply cleanly
→ pgvector exists
→ backend checks/tests pass
→ frontend checks/build pass
→ API contract check passes
→ Playwright Chromium suite passes
```

### CI verification

Verify the workflow executes the same deterministic gates on Linux.

Also prove required gates fail the job by using normal failing-test/check semantics; do not commit an intentionally failing test.

Record:

```text
commands
runtime environment
PASS / FAIL
migration head
PostgreSQL/pgvector identity
test counts where useful
known deferred evaluation gates
```

Do not claim deferred Phase-7 official gates passed.

---

## Acceptance criteria

AC1:
PostgreSQL container supports pgvector and clean Alembic migrations.

AC2:
Backend/frontend install/build/test commands are reproducible from committed lockfiles.

AC3:
GitHub Actions runs required static/test/build/migration/API-contract/E2E gates.

AC4:
No production secret is committed, logged, cached, or baked into an image.

AC5:
No unnecessary distributed service is introduced.

Additional:

- no Windows-only `.venv\Scripts\python.exe` remains in CI-required E2E flow;
- accepted Step-8.1 B1/B4 behavior remains unchanged;
- Playwright remains the sole browser E2E framework;
- full deterministic Step-8.1 browser suite passes;
- no backend/frontend application Dockerfile is added;
- official Phase-7 evaluation remains deferred.

---

## Documentation / learning deliverables

Update the Step Note with only concepts actually used.

Expected concepts:

```text
Reproducible Environment — SYSTEM — MUST KNOW
Container / Container Image — SYSTEM — MUST KNOW
Docker Compose — SYSTEM — MUST KNOW
CI Pipeline — SYSTEM — MUST KNOW
Environment Variables / Secrets — SYSTEM — MUST KNOW
Migration Validation — SYSTEM — MUST KNOW
Deterministic Test Boundary — BOTH — MUST KNOW
Health Check — SYSTEM — SHOULD KNOW
Dependency Caching — SYSTEM — SHOULD KNOW
```

Tools actually used should include only the implemented tools, expected:

```text
Docker
Docker Compose
GitHub Actions
PostgreSQL
pgvector
Alembic
uv
npm
pytest
Vitest / RTL
Playwright
Oxlint
```

---

## Required handoff

Return:

```text
Step
Status
Latest repository preflight
Files changed
Container boundary
Compose/database lifecycle
Exact local setup commands
GitHub Actions flow
CI gate results
Migration validation results
PostgreSQL/pgvector verification
Backend test results
Frontend test/build/lint results
api:check result
Playwright result
Secrets/config review
Step-8.1 preservation confirmation
Deferred evaluation gates
Documentation paths
Concepts added
Tools added
Problems/risks
Decisions needed
Recommended next action
```

Expected successful implementation status:

```text
READY_FOR_SPECIALIST_REVIEW — STEP 8.2 REPRODUCIBLE DEV/CI IMPLEMENTATION
```

Do not claim Step 8.2 DONE.
Do not claim product release readiness.
Do not start Step 8.3.
