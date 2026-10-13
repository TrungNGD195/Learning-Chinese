# Codex Execution Task — Step 3.2: Configuration & Environment

## Status / Execution Gate

This is the single current Codex execution task for **Step 3.2 — Configuration & Environment**.

Do **not** implement any later Step. Do not proceed if the source-of-truth files materially conflict with the repository state or with a higher-precedence PM decision; report `BLOCKED` instead.

## Owner

App Engineering Specialist.

## Objective

Implement the backend configuration foundation for development, test, and production while preserving the accepted Step 3.1 FastAPI skeleton.

The configuration must be centralized, typed, validated, environment-driven, and reusable. Integrate only the Step 3.2 settings that the current FastAPI application can consume without opening database connections, implementing authentication, or introducing external-service integrations.

## Source of Truth

Primary executable specification:

- `Spec-CURRENT/Phase3/Step 3.2 — Configuration & Environment.md`

Required control/context:

- `Spec-CURRENT/PROJECT_CONTEXT.md`
- `Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md`
- `Spec-CURRENT/PM-Control/05-Codex-Execution-Protocol.md`

Direct dependencies / architecture references:

- accepted `Spec-CURRENT/Phase3/Step 3.1 — Backend Skeleton.md`
- `Spec-CURRENT/Phase1/Step 1.2 — High-Level Architecture Specification.md`
- `Spec-CURRENT/Phase1/Step 1.3 — Component Responsibilities.md`
- `Spec-CURRENT/Phase1/Step 1.5 — Repository / Module Structure.md`

### Precedence

If documents appear to conflict, use PM-Control precedence:

1. PM Decision Log.
2. Current Step 3.2 specification.
3. Later specification that intentionally refines an earlier design.
4. Earlier Phase/Step specifications.
5. Comments/examples/generated plans.

Do not silently resolve a real conflict.

## PM Decisions Affecting This Step

### D-BASE-01 / 02 / 03 / 04

Preserve:

- Python `>=3.12,<3.13`;
- FastAPI;
- `uv` dependency/environment workflow;
- `pydantic-settings` for configuration.

### D-001 — Production Web Topology

V0 uses one logical same-site web topology. Do not introduce a cross-site production architecture or permissive wildcard CORS policy. Development may allow explicitly configured localhost frontend origins.

## Current Repository State

Step 3.1 is PM-accepted and closed.

Relevant current files:

```text
.gitignore
backend/
├── pyproject.toml
├── uv.lock
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── errors.py
│   ├── database/__init__.py
│   ├── auth/__init__.py
│   ├── curriculum/__init__.py
│   ├── exercise/__init__.py
│   ├── progress/__init__.py
│   ├── admin/__init__.py
│   ├── ai/...
│   ├── ingestion/__init__.py
│   └── shared/__init__.py
└── tests/
    ├── test_health.py
    └── test_errors.py

docs/backend/step-3.1-backend-skeleton.md
```

Current `backend/app/main.py`:

- creates one FastAPI application;
- title is currently `Trung Chinese Learning API`;
- registers the accepted application-error handler;
- exposes `GET /health`;
- has no settings layer, CORS middleware, database startup, auth, or external-service integration.

Current `backend/pyproject.toml`:

- Python `>=3.12,<3.13`;
- runtime dependency: FastAPI only;
- dev/test dependencies: pytest and HTTPX;
- pytest `testpaths` and `pythonpath` only.

Current `.gitignore` ignores Python environment/cache artifacts but does **not** yet ignore `backend/.env`.

Existing Step 3.1 regression tests currently pass and must remain passing.

## In Scope

Implement only Step 3.2:

- centralized typed settings using `pydantic-settings`;
- development / test / production environment values;
- environment-variable based configuration;
- optional local `backend/.env` loading;
- committed `backend/.env.example` with placeholders/example values only;
- cached settings accessor (`get_settings()` or equivalent);
- settings for:
  - `APP_NAME`
  - `APP_ENV`
  - `DEBUG`
  - `API_V1_PREFIX`
  - `DATABASE_URL`
  - `SECRET_KEY`
  - `CORS_ORIGINS`
  - `LOG_LEVEL`
  - explicit test-scoped database configuration such as `TEST_DATABASE_URL`;
- FastAPI integration for application name, debug behavior, and CORS where applicable;
- preserve `/api/v1` as the configuration source for future business-router registration without creating fake business routers;
- test-environment setup using `APP_ENV=test` and a dedicated test database configuration value without opening a connection;
- Step 3.2 tests;
- Step 3.2 documentation/Step Note.

## Out of Scope

Do **not** implement or add dependencies for:

- SQLAlchemy;
- psycopg / PostgreSQL driver usage;
- database engine/session/connection/pool;
- database readiness endpoint;
- Alembic or migrations;
- ORM models;
- schema creation;
- database queries;
- authentication/JWT/session behavior;
- password hashing;
- auth-specific secret consumption;
- LLM/provider configuration;
- embedding/retrieval/external-search configuration;
- email-service configuration;
- file-storage configuration;
- business APIs;
- frontend implementation;
- Docker/CI/deployment;
- production secret-manager integration;
- advanced observability/monitoring.

This task must not implement Step 3.3 database access.

## Config / Environment Contracts

### Environment model

Support exactly the Step 3.2 environment identities:

```text
development
test
production
```

Use a typed representation such as a `Literal` or small enum. Unknown values must fail validation.

Use one codebase. Environment differences must come from configuration, not separate application branches/files per environment.

### Settings source

Runtime values come primarily from environment variables.

Local development may load:

```text
backend/.env
```

`backend/.env` must remain untracked.

Commit:

```text
backend/.env.example
```

Do not commit real secrets or credentials.

### Required setting fields

The Settings abstraction must expose typed values equivalent to:

```text
APP_NAME
APP_ENV
DEBUG
API_V1_PREFIX
DATABASE_URL
SECRET_KEY
CORS_ORIGINS
LOG_LEVEL
TEST_DATABASE_URL
```

Do not introduce future provider/API-key settings.

### Current-step requirement boundary for database/auth values

`DATABASE_URL`, `TEST_DATABASE_URL`, and `SECRET_KEY` are **configuration contracts only in Step 3.2**.

- Do not open a PostgreSQL connection.
- Do not import/add SQLAlchemy, psycopg, or Alembic.
- Do not implement auth or cryptographic behavior.
- Do not verify DB reachability.
- Do not use `SECRET_KEY` for tokens/hashing yet.

The Step 3.2 spec says `DATABASE_URL` and `SECRET_KEY` become required where the consuming application Step requires them. Step 3.2 must support them without prematurely implementing their consumers.

Do not give `SECRET_KEY` a real/insecure production secret default. A nullable/absent value at this Step is acceptable until the consuming Step makes it mandatory.

### Test database configuration / safety

Tests must execute with:

```text
APP_ENV=test
```

and an explicitly test-scoped database URL/config value.

No database connection may occur in Step 3.2. Therefore do not add database teardown/setup or destructive DB operations merely to demonstrate the safety guard.

At minimum:

- test configuration must use `TEST_DATABASE_URL` (or an exact equivalent) distinct from normal runtime DB configuration;
- if both normal and test DB URLs are supplied in test mode, reject an exact same-value configuration rather than silently using it;
- do not invent production-hostname heuristics.

The real connection/session safety boundary remains for Step 3.3 when database access exists.

### Safe defaults / accepted Step 3.1 behavior

Preserve the accepted Step 3.1 API identity by default unless the environment overrides it. The current default application title is:

```text
Trung Chinese Learning API
```

`APP_NAME` must make this configurable.

Keep `/health` behavior unchanged.

Use `/api/v1` as the default `API_V1_PREFIX` configuration value.

Do not create an empty/fake `/api/v1` router just to consume the prefix. The prefix is the source of truth for future router registration.

### Debug behavior

Configuration must make debug behavior explicit and typed.

Required policy:

```text
development -> DEBUG may be enabled
test        -> controlled, normally disabled
production  -> DEBUG disabled
```

A production configuration that explicitly enables debug must fail validation rather than silently exposing debug behavior.

Tests should run with debug disabled unless a focused config test is intentionally testing debug validation.

### CORS

`CORS_ORIGINS` must be configurable and normalized to a collection suitable for FastAPI/Starlette CORS middleware.

For the V0 environment-variable contract, accept a comma-separated string; a single origin is simply a one-item value. Example:

```text
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Trim surrounding whitespace, discard empty items, and expose the normalized result to application setup as a list/collection. Do not require JSON-array syntax in `.env`.

Requirements:

- no unrestricted `*` origin default for production;
- local development may explicitly configure `http://localhost:5173`;
- production origins remain environment-provided;
- preserve D-001 same-site production topology;
- add only the minimal FastAPI CORS integration required by Step 3.2;
- do not implement authentication/CSRF/session behavior here.

The committed `.env.example` may show the localhost Vite development origin as an example.

### Logging

Expose a typed/validated `LOG_LEVEL` setting with normal values such as:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

Do not build observability, structured logging infrastructure, metrics, tracing, or external logging integration in this Step.

A small standard-library logging integration is acceptable only if needed to make `LOG_LEVEL` affect the current process; do not introduce another logging dependency.

### Time convention

Document/preserve the project convention:

```text
internal application/database timestamps -> UTC
presentation layer -> may convert for display
```

There is no timestamp persistence in the current Step 3.1 code. Do not create a speculative datetime utility solely to satisfy this documentation requirement.

## Exact Files / Components

### Inspect before editing

```text
.gitignore
backend/pyproject.toml
backend/uv.lock
backend/app/main.py
backend/app/core/errors.py
backend/tests/test_health.py
backend/tests/test_errors.py
docs/backend/step-3.1-backend-skeleton.md
```

### Create

```text
backend/.env.example
backend/app/core/config.py
backend/tests/conftest.py
backend/tests/test_config.py
docs/backend/step-3.2-configuration-environment.md
```

Package-marker files already exist; do not recreate duplicate package trees.

### Modify

```text
.gitignore
backend/pyproject.toml
backend/uv.lock
backend/app/main.py
```

Modify existing tests only if required by the new configuration integration while preserving their Step 3.1 assertions. Prefer adding focused Step 3.2 tests rather than rewriting the accepted Step 3.1 tests.

### Do not touch

Unless a focused test import update is strictly necessary, do not modify domain package markers or create files under:

```text
backend/app/database/   (except the existing package marker remains untouched)
backend/app/auth/
backend/app/curriculum/
backend/app/exercise/
backend/app/progress/
backend/app/admin/
backend/app/ai/
backend/app/ingestion/
backend/app/shared/
```

Do not create:

```text
alembic.ini
migrations/
ORM model files
engine.py
session.py
database repositories
JWT/auth modules
provider configuration files
```

## Dependency Changes

Add only the Step 3.2 runtime dependency required by the authoritative spec:

```text
pydantic-settings
```

Use a compatible v2 range consistent with the current FastAPI/Pydantic stack; do not add speculative dependencies.

Update `uv.lock` through the normal `uv` workflow.

Do not add database drivers/ORM/migration/auth/AI libraries.

## Application Integration

Update `backend/app/main.py` minimally so the accepted FastAPI app consumes Step 3.2 Settings.

At minimum:

- app title comes from `APP_NAME`;
- FastAPI debug behavior comes from `DEBUG`;
- configured CORS origins are applied via FastAPI/Starlette's existing CORS middleware capability;
- existing application-error registration remains;
- existing `GET /health` route remains unchanged in contract and dependency-free;
- OpenAPI remains available in development/test; production documentation exposure is not a Step 3.2 deployment decision.

Do not make `/health` depend on settings whose absence is unrelated to liveness beyond the normal application-startup settings validation.

Do not create DB startup/lifespan hooks.

## Error / Failure Semantics

Configuration parsing/validation errors are startup/configuration failures, not normalized HTTP application errors.

Do not catch Pydantic settings validation failures and convert them to a successful fallback.

Do not add a broad `except Exception` around Settings loading.

Invalid values such as an unknown `APP_ENV`, invalid boolean/config type, invalid CORS shape, or forbidden production debug state must fail clearly.

Do not expose actual secret values in errors, logs, docs, or tests.

## Tests

Add focused configuration tests. Cover at least:

1. accepted environment values: `development`, `test`, `production`;
2. invalid `APP_ENV` fails validation;
3. environment variables override defaults;
4. `DEBUG` is typed as bool;
5. production cannot run with debug enabled;
6. `API_V1_PREFIX` defaults to `/api/v1` and is configurable;
7. `CORS_ORIGINS` is parsed/normalized into the application's expected collection;
8. wildcard production CORS is not introduced by default;
9. `LOG_LEVEL` accepts supported values and rejects an invalid value;
10. `SECRET_KEY` has no real/default production secret;
11. tests run with `APP_ENV=test`;
12. a dedicated `TEST_DATABASE_URL` configuration is present for tests but causes no network/DB connection;
13. exact same normal/test DB URL in test mode is rejected if both are supplied;
14. settings accessor is cached/reused rather than reparsed on every request;
15. FastAPI application consumes configurable app name/debug/CORS settings;
16. existing `GET /health` still returns HTTP 200 and exactly `{"status":"ok"}`;
17. existing OpenAPI test remains valid;
18. application-error foundation regression test remains valid;
19. no test requires PostgreSQL, network access, credentials, or any external service.

When tests manipulate environment variables, clear/reset the cached Settings accessor between cases so tests do not leak configuration state.

Do not create a real database for Step 3.2 tests.

## Verification Commands

From the repository root:

```text
cd backend
uv sync
uv run python -c "from app.main import app; assert app is not None"
uv run pytest -q
```

Also inspect the resolved dependency set and confirm no Step 3.3+ dependency was introduced.

If the repository has no formatter/linter/type-checker configured yet, do not introduce one solely for this Step.

## Acceptance Criteria

Codex must map evidence to every item below:

- [ ] Existing Step 3.1 behavior remains intact.
- [ ] Python remains `>=3.12,<3.13`.
- [ ] Dependency workflow remains `uv`.
- [ ] `pydantic-settings` is added and locked.
- [ ] Configuration is centralized in `backend/app/core/config.py`.
- [ ] `development`, `test`, and `production` are supported as typed/validated environment values.
- [ ] Runtime configuration comes primarily from environment variables.
- [ ] Local `backend/.env` loading is supported.
- [ ] `.gitignore` ignores `backend/.env` without ignoring `backend/.env.example`.
- [ ] `backend/.env.example` exists and contains no real secrets/credentials.
- [ ] `APP_NAME`, `APP_ENV`, `DEBUG`, `API_V1_PREFIX`, `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `LOG_LEVEL`, and explicit test DB configuration are represented.
- [ ] `DATABASE_URL`/`SECRET_KEY` are not consumed by DB/auth implementation in this Step.
- [ ] Settings are not reparsed for every request.
- [ ] Invalid configuration fails clearly; no broad fallback hides it.
- [ ] Production debug cannot be enabled.
- [ ] `API_V1_PREFIX` comes from Settings; no fake business router is created.
- [ ] CORS origins are configurable.
- [ ] No unrestricted production wildcard CORS default exists.
- [ ] D-001 same-site production topology is preserved.
- [ ] Logging level is configurable without adding an observability stack.
- [ ] UTC internal timestamp convention is documented/preserved; no speculative timestamp subsystem is added.
- [ ] Tests run as `APP_ENV=test` with an explicit dedicated test DB config value.
- [ ] Step 3.2 opens no PostgreSQL connection and performs no DB mutation.
- [ ] No SQLAlchemy, psycopg, Alembic, migration, ORM, or DB session implementation exists.
- [ ] No authentication/JWT/password hashing implementation exists.
- [ ] No LLM/external-search/email provider config is added.
- [ ] `GET /health` remains HTTP 200 with exact `{"status":"ok"}` and no external dependency.
- [ ] OpenAPI remains available for current development/test behavior.
- [ ] Existing normalized application-error foundation still works.
- [ ] Step 3.2 tests plus existing Step 3.1 tests pass.
- [ ] Step Note exists at `docs/backend/step-3.2-configuration-environment.md`.
- [ ] Only concepts/tools actually used are reported; do not classify general Python/package/config tooling as DE merely because the project has a DE learning goal.

## Step Note Requirements

`docs/backend/step-3.2-configuration-environment.md` must contain at minimum:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- reusable approach for another project
- Common Mistakes
- Definition of Done

It should explicitly explain the boundary:

```text
Environment / .env
→ typed Settings
→ FastAPI application setup
```

and that database/auth/provider configuration values do not mean those systems are implemented in Step 3.2.

## Architecture Guardrails

- Preserve one FastAPI modular-monolith backend.
- Keep configuration in application-wide `app/core/`, not domain modules.
- Do not put domain state in Settings.
- Do not scatter `os.getenv()` through modules.
- Do not create generic utility/service dumping grounds.
- Do not implement database access.
- Do not implement auth.
- Do not add external-provider config early.
- Do not introduce deployment/vendor-specific configuration.
- Do not alter public business API contracts; Step 3.2 has no new business endpoint.
- Preserve `/health` as process liveness only.
- Preserve D-001 same-site production topology.
- Use the simplest implementation that satisfies the Step.

## Required Codex Completion Report

Return exactly enough evidence for independent specialist review:

```text
Step: 3.2 — Configuration & Environment
Status: DONE | PARTIAL | BLOCKED

Implementation plan executed:
- ...

Files created:
- ...

Files modified:
- ...

Dependencies added/removed:
- ...

Configuration contract implemented:
- APP_NAME: ...
- APP_ENV: ...
- DEBUG: ...
- API_V1_PREFIX: ...
- DATABASE_URL: ...
- TEST_DATABASE_URL: ...
- SECRET_KEY: ...
- CORS_ORIGINS: ...
- LOG_LEVEL: ...

Application integration:
- ...

Step 3.3 boundary check:
- confirm no DB engine/session/connection/migration/ORM/driver implementation

Tests / verification:
- command: uv sync
  result: ...
- command: uv run python -c "from app.main import app; assert app is not None"
  result: ...
- command: uv run pytest -q
  result: ...

Acceptance criteria:
- [PASS/FAIL] ...

Step Note:
- path: docs/backend/step-3.2-configuration-environment.md

Concepts actually used:
- Concept | Category (DE / AI / BOTH / SYSTEM) | Role

Tools actually used:
- Tool | Category (DE / AI / BOTH / SYSTEM) | Role

Deviations from specification:
- none | ...

Problems / risks:
- none | ...

Decisions needed:
- none | ...

Recommended next action:
- return implementation to App Engineering Specialist for independent review; do not begin Step 3.3
```

## Stop Conditions

Return `BLOCKED` instead of inventing a solution if implementation reveals a real conflict affecting:

- deployment topology;
- security model;
- public API contract;
- whether a database connection must exist in Step 3.2;
- whether auth secrets must already be consumed;
- another architecture-significant boundary covered by PM change control.

Do not run or implement Step 3.3.
