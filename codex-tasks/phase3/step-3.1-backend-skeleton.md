# Codex Execution Task — Step 3.1: Backend Skeleton

> **PM review status:** APPROVED FOR CODEX after minor execution corrections.
>
> **PM approval scope:** Step 3.1 only. Step 3.2+ remains closed until specialist review and PM acceptance of Step 3.1.

> **Purpose:** Execution packet for Codex after PM approval. This is **not** a new Step Specification and must not override or extend the authoritative Step 3.1 specification.
>
> **Execution gate:** Do not run this task until PM explicitly approves this artifact.

## 1. Step identity

- **Step:** 3.1 — Backend Skeleton
- **Owner specialist:** App Engineering
- **Wave:** Wave 1 — Application Foundation
- **Task unit:** one Codex task = this one frozen Step only

## 2. Objective

Create the first runnable backend foundation for the project as a minimal FastAPI modular monolith that:

- boots on Python `>=3.12,<3.13`;
- is managed with `uv`;
- exposes process-liveness `GET /health`;
- establishes the approved backend domain/module boundaries;
- establishes the reusable standard application-error response foundation;
- provides minimal automated tests for boot/health and the concrete error foundation if implemented;
- keeps FastAPI OpenAPI/Swagger available for development;
- contains no implementation belonging to Step 3.2 or later.

## 3. Source of truth

Read these before editing. Do not treat this task file as higher precedence than them.

### Primary authoritative Step specification

1. `02_APP_ENGINEERING_SPECS_PHASE3-4.md`
   - Locate exactly: `# Step 3.1 — Backend Skeleton`
   - Only Step 3.1 is authoritative for implementation scope in this task.
   - Do **not** pull requirements from Step 3.2+ into this implementation.

### Required project/control context

2. `00_PROJECT_CONTEXT.md`
   - project architecture;
   - modular-monolith boundary;
   - approved logical backend modules;
   - frozen V0 technology decisions.

3. `06_PM_CONTROL.md`
   - source-of-truth precedence;
   - Decision Log;
   - Codex execution protocol;
   - Step 3.1 freeze status;
   - only Step 3.1 is currently executable.

### Direct architecture dependencies

4. `01_FOUNDATION_SPECS_PHASE0-2.md`
   - Step 1.2 — High-Level Architecture;
   - Step 1.3 — Component Responsibilities;
   - Step 1.5 — Repository / Module Structure.

### Precedence

If a real conflict is found, follow the precedence defined in `06_PM_CONTROL.md`. Do not silently resolve an architecture-, interface-, product-, or scope-significant conflict. Stop and report `BLOCKED` with the exact conflict.

### Execution input requirement

Before Codex edits code, the Codex session/workspace must have access to the four source files named above:

- `00_PROJECT_CONTEXT.md`
- `01_FOUNDATION_SPECS_PHASE0-2.md`
- `02_APP_ENGINEERING_SPECS_PHASE3-4.md`
- `06_PM_CONTROL.md`

Do not assume ChatGPT Project Sources are automatically visible inside Codex. If these files are not available to Codex, provide/attach/copy them into the Codex task context before implementation. If the task cannot access them, stop and report `BLOCKED` rather than silently relying on incomplete context.

## 4. PM-confirmed current repository state

For this Step, PM has explicitly confirmed the implementation starts from zero:

- no previous backend implementation exists;
- no backend package structure exists that needs reconciliation;
- no FastAPI application exists;
- no project-managed Python environment exists for the backend;
- no backend tests exist;
- Step 3.1 is allowed to create a new backend skeleton according to the authoritative specification.

This permission does **not** authorize architecture redesign. Build only the skeleton required by Step 3.1.

Before editing, still inspect the current working tree to confirm there is no unexpected implementation artifact that contradicts this PM-confirmed state. If such an artifact exists and materially conflicts with this task, report it rather than overwriting it silently.

## 5. In Scope

Implement only the following:

1. A `backend/` Python project managed by `uv`.
2. Python target `>=3.12,<3.13`.
3. FastAPI application entrypoint at `backend/app/main.py`.
4. Approved backend package/domain boundaries:
   - `core`
   - `database`
   - `auth`
   - `curriculum`
   - `exercise`
   - `progress`
   - `admin`
   - `ai`
   - `ingestion`
   - `shared`
5. Approved AI sub-boundaries, without AI implementation:
   - `ai/chat`
   - `ai/retrieval`
   - `ai/grading`
   - `ai/generation`
   - `ai/prompts`
   - `ai/providers`
6. `GET /health` process-liveness endpoint returning exactly:

   ```json
   {
     "status": "ok"
   }
   ```

   with HTTP `200`.
7. Optional minimal development `GET /` API-identification endpoint. It is not required for acceptance and must not replace `/health`.
8. Development OpenAPI/Swagger support using FastAPI defaults.
9. Minimal reusable application-error foundation with response shape:

   ```json
   {
     "error": {
       "code": "ERROR_CODE",
       "message": "Human-readable message",
       "details": null
     }
   }
   ```

10. Minimal automated tests proving application import/boot and `/health` behavior.
11. A focused test for the error response shape if the implementation introduces a concrete application exception/handler.
12. Step Note at `docs/backend/step-3.1-backend-skeleton.md`.
13. Record only concepts/tools actually used in the implementation in the completion report for PM. Do not invent a new Concepts/Tools master-file structure if none exists yet.

## 6. Out of Scope

Do **not** implement or configure any of the following in this task:

- Step 3.2 configuration/settings system;
- `pydantic-settings`;
- `.env` / `.env.example` configuration work;
- PostgreSQL connections;
- SQLAlchemy or any ORM;
- psycopg;
- Alembic or migrations;
- database models/schema materialization;
- authentication or authorization;
- JWT/session behavior;
- password hashing;
- curriculum/business APIs;
- assessment logic;
- progress/unlock business logic;
- conversation APIs;
- LLM provider integration;
- embeddings;
- vector storage/search;
- retrieval/reranking/RAG;
- AI grading/generation;
- document parsing or ingestion execution;
- file-storage implementation;
- queue/worker/scheduler;
- frontend integration;
- CORS configuration;
- Docker;
- CI;
- deployment;
- production infrastructure;
- observability/monitoring stack;
- speculative provider abstractions;
- speculative framework layers for future Steps.

Do not add future dependencies merely because later specifications mention them.

## 7. Architecture and interface contracts to preserve

### 7.1 Architecture

The backend is one **Modular Monolith**, not microservices.

Approved logical ownership remains recognizable:

```text
auth/        → authentication domain (future)
curriculum/  → HSK/lesson/vocabulary/grammar domain (future)
exercise/    → exercise/test/attempt/score domain (future)
progress/    → completion/unlock/progression domain (future)
admin/       → admin workflows (future)
ai/          → AI/RAG capabilities (future)
ingestion/   → document/knowledge processing (future)
database/    → shared DB infrastructure (future)
core/        → application-wide infrastructure only
shared/      → genuinely cross-domain reusable code only
```

Do not put domain business logic in `core/` or `shared/`.

### 7.2 Dependency direction

Preserve the future dependency direction:

```text
Router
→ Service
→ Repository
→ Database
```

Step 3.1 does **not** need to create empty `router.py`, `service.py`, or `repository.py` files in every domain.

Do not create unused layer files merely for visual symmetry.

### 7.3 API contract implemented now

```http
GET /health
```

Response:

```json
{"status":"ok"}
```

Status: `200`.

`/health` is process liveness only. It must not depend on database, LLM, network, filesystem storage, credentials, or any later provider.

### 7.4 Reserved future API prefix

Reserve conceptually:

```text
/api/v1
```

Do not implement future business endpoints simply to populate this prefix.

### 7.5 Error contract

Application errors must be able to produce:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": null
  }
}
```

Keep the implementation minimal. A single reusable application exception type plus a FastAPI handler/registration mechanism is sufficient if that is the smallest coherent solution. Do not create a large exception hierarchy.

Do not wrap successful responses in a generic `data` envelope.

Do not use a broad catch-all `except Exception` handler merely to force all failures into this shape.

## 8. Exact files/components to inspect/create/modify

Because PM confirms there is no previous implementation, the expected Step 3.1 creation set is below. If the working tree unexpectedly contains one of these paths, inspect it first and reconcile rather than overwriting blindly.

### 8.1 Inspect before editing

Inspect at minimum:

```text
.
.gitignore                       # if present
backend/                         # if unexpectedly present
docs/                            # if present
00_PROJECT_CONTEXT.md            # or supplied equivalent source
01_FOUNDATION_SPECS_PHASE0-2.md  # or supplied equivalent source
02_APP_ENGINEERING_SPECS_PHASE3-4.md
06_PM_CONTROL.md
```

### 8.2 Create — backend project/package foundation

Expected files/directories:

```text
backend/
├── pyproject.toml
├── uv.lock                      # generated/updated by uv when dependency resolution is performed
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── errors.py            # or one equivalently minimal core exception module
│   ├── database/
│   │   └── __init__.py
│   ├── auth/
│   │   └── __init__.py
│   ├── curriculum/
│   │   └── __init__.py
│   ├── exercise/
│   │   └── __init__.py
│   ├── progress/
│   │   └── __init__.py
│   ├── admin/
│   │   └── __init__.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── chat/
│   │   │   └── __init__.py
│   │   ├── retrieval/
│   │   │   └── __init__.py
│   │   ├── grading/
│   │   │   └── __init__.py
│   │   ├── generation/
│   │   │   └── __init__.py
│   │   ├── prompts/
│   │   │   └── __init__.py
│   │   └── providers/
│   │       └── __init__.py
│   ├── ingestion/
│   │   └── __init__.py
│   └── shared/
│       └── __init__.py
└── tests/
    ├── conftest.py              # only if useful for minimal shared test setup
    ├── test_health.py
    └── test_errors.py           # if concrete exception/handler is implemented

docs/
└── backend/
    └── step-3.1-backend-skeleton.md
```

Package marker files are allowed because empty directories are not retained reliably and the Step requires recognizable logical boundaries. Do not put fake implementations inside them.

### 8.3 Modify

Only modify existing root-level files when strictly necessary for Step 3.1, for example:

- `.gitignore` only if the new Python/uv workflow produces local artifacts that should be ignored and no equivalent rule exists.

Do not make unrelated cleanup or repository-wide formatting changes.

### 8.4 Do not touch

Do not create or modify implementation for:

```text
frontend/
data/
migrations/
alembic.ini
Dockerfile
docker-compose*.yml
.github/workflows/
.env
.env.example
```

Do not modify later Step specifications.

## 9. Dependency/package instructions

Use `uv` as the backend package/environment workflow.

### Required runtime dependency

- `fastapi`

### Runtime server dependency

Step 3.1 does **not** require selecting or adding an ASGI server package as an acceptance condition. The application import plus FastAPI/TestClient verification is sufficient for the required Step checks.

If the execution environment already provides, or a minimal local manual smoke run genuinely requires, an ASGI server such as `uvicorn`, it may be used only when necessary. Do not add `uvicorn` (or another server package) merely for the optional smoke check.

### Required test dependencies

Use only what is needed for the Step 3.1 test foundation, normally:

- `pytest`
- `httpx` if required by FastAPI/Starlette `TestClient` in the resolved dependency set.

Keep test-only dependencies in the project's development dependency group/convention supported by `uv`.

### Explicitly forbidden dependencies in this Step

Do not add:

- `pydantic-settings`;
- `sqlalchemy`;
- `psycopg`;
- `alembic`;
- `pgvector`;
- JWT/auth/password libraries;
- LLM SDKs;
- `sentence-transformers` / model runtimes;
- document parsers;
- queue/broker libraries;
- frontend packages;
- Docker/deployment tooling.

Do not add formatter/linter/type-checker frameworks solely for this Step unless an already-existing repository convention requires them. PM-confirmed current state has no such convention.

## 10. Implementation instructions

### 10.1 Before editing

Return a concise implementation plan containing:

- actual files found;
- files to create/change;
- dependencies to add;
- API/error interfaces to implement;
- tests to add;
- any blocker found.

If a material blocker exists, stop and report `BLOCKED`. Otherwise proceed in the same Codex task.

### 10.2 Backend project

Create a valid `uv`-managed Python project under `backend/` with:

```text
requires-python = ">=3.12,<3.13"
```

Do not add package/config complexity unrelated to running/testing this Step.

### 10.3 FastAPI application

`backend/app/main.py` must create the main FastAPI application object.

The application must import/start with no:

- environment secrets;
- database connection;
- network request;
- LLM/provider setup;
- external service dependency.

Keep FastAPI's development OpenAPI/Swagger endpoints enabled.

### 10.4 Health endpoint

Implement `GET /health` directly as lightweight process liveness.

It must return exactly:

```json
{"status":"ok"}
```

with HTTP `200`.

Do not add readiness checks for PostgreSQL or other future dependencies.

### 10.5 Root endpoint

`GET /` is optional. If implemented, keep it to a small development API-identification response. Do not treat it as health/readiness monitoring.

### 10.6 Error foundation

Implement the smallest reusable foundation that can produce the required normalized application-error shape.

Preferred minimal responsibility split:

```text
app/core/errors.py
→ application exception representation
→ FastAPI exception handler and/or registration helper
```

Register it from application setup without creating a generic framework layer.

If a concrete handler is implemented, test its HTTP response shape without adding a production-only fake error endpoint. A test-local FastAPI route/app is acceptable for focused handler verification.

### 10.7 Package/domain boundaries

Create only package markers necessary to make the approved module boundaries recognizable/importable.

Do not populate future domain modules with fake routers, services, repositories, schemas, providers, database classes, or business rules.

### 10.8 Step documentation

Create:

```text
docs/backend/step-3.1-backend-skeleton.md
```

It must capture the Step Note required by the Step specification:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- Approach reusable in another project
- Common Mistakes
- Definition of Done

Keep it focused on knowledge actually used in Step 3.1.

## 11. Tests and verification commands

Run commands from `backend/` unless the repository environment requires an equivalent `uv` invocation.

### 11.1 Environment/dependency resolution

```bash
uv sync
```

Expected evidence:

- succeeds using Python 3.12-compatible project metadata;
- produces/updates `uv.lock`;
- does not introduce forbidden future-Step dependencies as direct project dependencies.

### 11.2 Application import/boot smoke check

```bash
uv run python -c "from app.main import app; assert app is not None"
```

Expected evidence: exit code `0` without DB/network/secrets.

### 11.3 Automated tests

```bash
uv run pytest -q
```

Tests must prove at minimum:

- the FastAPI app imports/boots;
- `GET /health` returns HTTP `200`;
- response JSON equals `{"status": "ok"}`;
- development OpenAPI is available (for example `/openapi.json` or `/docs` responds successfully);
- concrete application-error handler returns the required shape, if implemented.

Tests must require no:

- PostgreSQL;
- external network;
- LLM/provider credentials;
- file-storage service;
- production secrets.

### 11.4 Optional local server smoke check

Only if an ASGI server command is already available in the resolved environment, an optional manual server smoke check may be run, for example:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then verify:

```http
GET /health
→ 200
→ {"status":"ok"}
```

This check is optional and must **not** be the reason to add a new server dependency. Do not leave a background server process running after verification.

### 11.5 No speculative verification tooling

There is currently no established formatter/linter/type-checker convention. Do not add Ruff, mypy, Black, or another tool solely to create extra checks for Step 3.1.

## 12. Acceptance criteria

Codex must explicitly report each item as `PASS`, `FAIL`, or `NOT APPLICABLE` with evidence.

- [ ] PM-confirmed zero-implementation state was respected; no duplicate backend tree was created.
- [ ] Backend targets Python `>=3.12,<3.13`.
- [ ] Backend dependency/environment workflow uses `uv`.
- [ ] `pyproject.toml` contains only Step 3.1 runtime/test dependencies.
- [ ] FastAPI application object exists at `backend/app/main.py`.
- [ ] Application imports/boots without database or external services.
- [ ] Approved domain module boundaries are recognizable.
- [ ] Approved AI submodule boundaries are recognizable without AI behavior.
- [ ] Ingestion remains a module inside the backend modular monolith.
- [ ] No empty future layer files were created merely for symmetry.
- [ ] `Router → Service → Repository → Database` future dependency direction is documented/preserved.
- [ ] No domain business logic is placed in routers, `core`, or `shared` dumping areas.
- [ ] `GET /health` returns HTTP `200`.
- [ ] `GET /health` response is exactly `{"status":"ok"}` semantically.
- [ ] `/health` has no DB/provider/network dependency.
- [ ] Development OpenAPI/Swagger remains available.
- [ ] Standard application-error response foundation exists.
- [ ] Error foundation is minimal; no unnecessary exception hierarchy exists.
- [ ] Successful responses are not forced into a generic `data` wrapper.
- [ ] Minimal startup/health automated tests pass.
- [ ] Error response shape has a focused test if a concrete handler is implemented.
- [ ] Tests require no PostgreSQL/network/LLM credentials/external service.
- [ ] No Step 3.2+ implementation was introduced.
- [ ] No database/ORM/Alembic/auth/business/AI/ingestion-processing/queue/frontend/deployment implementation was introduced.
- [ ] Step Note exists at `docs/backend/step-3.1-backend-skeleton.md`.
- [ ] Concepts/tools actually used are identified for PM handoff; unused/future concepts/tools are not added.

## 13. Acceptance evidence to collect

The completion report must include concrete evidence, not only a claim of success:

1. Final relevant tree under `backend/` and `docs/backend/`.
2. Direct dependency declarations from `backend/pyproject.toml`.
3. Python version constraint from `pyproject.toml`.
4. `uv sync` result.
5. Application import/boot smoke result.
6. `uv run pytest -q` summary with passed/failed count.
7. `/health` response status/body evidence from test output or a local smoke request.
8. OpenAPI availability evidence from test or smoke request.
9. Error response test evidence if handler exists.
10. Explicit statement that no database/auth/AI/ingestion-processing/deployment dependency or implementation was added.
11. `git diff --stat` and concise `git diff` review summary if Git is available.

## 14. Architecture guardrails

- Do not redesign the Phase 1 architecture.
- Do not split the backend into services.
- Do not create a standalone AI/RAG service.
- Do not create a standalone ingestion service.
- Do not add Step 3.2 configuration early.
- Do not select/implement database, ORM, migration, auth, LLM, vector, storage, deployment, or worker technology in code in this Step.
- Do not create a generic service/repository/helper layer spanning unrelated domains.
- Do not use `shared/` as a dumping ground.
- Do not make `/health` a dependency-readiness endpoint.
- Do not add production secret/env requirements.
- Do not disable development OpenAPI docs.
- Do not implement future business endpoints under `/api/v1`.
- Do not add an application-wide catch-all that masks programming errors.
- Keep the skeleton small enough for a beginner to trace request flow and module ownership.

## 15. Required Codex completion report

Return exactly these sections after implementation:

```text
Step: 3.1 — Backend Skeleton
Status: DONE | PARTIAL | BLOCKED

Implementation plan executed:
- ...

What changed:
- ...

Files created:
- ...

Files modified:
- ...

Dependencies added:
- runtime: ...
- development/test: ...

Interfaces/API implemented:
- ...

Architecture checks:
- modular monolith: PASS/FAIL
- approved module boundaries: PASS/FAIL
- no future-Step implementation: PASS/FAIL

Tests / verification:
- command: ...
  result: ...
- command: ...
  result: ...

Acceptance criteria:
- [PASS|FAIL|N/A] ...

Step Note:
- path: ...

Concepts actually used:
- Concept | Category (DE/AI/BOTH/SYSTEM) | Role / why it mattered

Tools actually used:
- Tool | Category (DE/AI/BOTH/SYSTEM) | Role / why it was used

Deviations from specification:
- none | ...

Problems / risks:
- none | ...

Decisions needed:
- none | ...

Recommended next action:
- Return implementation to App Engineering Specialist for review. Do not begin Step 3.2.
```

## 16. Stop conditions

Stop and return `BLOCKED` instead of inventing a solution if, before or during implementation:

- the required source-of-truth files are not available to the Codex session/workspace;
- the actual repository unexpectedly contains a materially conflicting backend architecture;
- a higher-precedence PM decision conflicts with Step 3.1;
- completing the Step appears to require a public API/product/architecture decision not already frozen;
- a required behavior cannot be implemented without pulling Step 3.2+ into scope.

Otherwise implement the minimum coherent Step 3.1 only, run the required verification, and return the completion report to App Engineering Specialist.
