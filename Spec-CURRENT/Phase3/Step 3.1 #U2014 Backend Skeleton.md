# Step 3.1 — Backend Skeleton

## Context

Phases 0–2 define the MVP product boundaries, modular-monolith architecture, and data contracts. Step 3.1 is the first executable implementation Step. Its job is to create a runnable backend foundation without pulling database, authentication, AI, ingestion processing, or deployment complexity forward.

This Step establishes code ownership and dependency direction that later Steps must preserve.

## Objective

Create a minimal FastAPI backend that:

- boots successfully on Python 3.12;
- exposes a process-liveness health endpoint;
- establishes the approved domain/module boundaries;
- establishes the common application-error response foundation;
- provides a minimal automated test foundation;
- remains intentionally free of later-phase implementation.

## Current State

Treat the repository state at execution time as authoritative for existing files. Before changing anything, inspect the repository and preserve non-conflicting project files.

Expected architectural inputs are the approved reference specifications from Steps 1.2, 1.3, and 1.5 plus PM decision precedence. No database/auth/AI provider implementation is a prerequisite for this Step.

If an existing backend skeleton already implements part of this contract, reconcile it instead of creating a duplicate backend tree.

## In Scope

- `backend/` Python project managed by `uv`;
- FastAPI application entry point;
- approved backend domain package boundaries;
- `/health` process-liveness endpoint;
- optional minimal development root endpoint;
- development OpenAPI/Swagger support;
- reusable standard application-error response foundation;
- minimal tests that prove application boot and health behavior;
- Step documentation required by the project Definition of Done.

## Out of Scope

Do not implement:

- PostgreSQL connection;
- SQLAlchemy or another ORM;
- migrations;
- user authentication or authorization;
- password hashing;
- curriculum/business APIs;
- assessment/progress logic;
- LLM providers;
- embeddings, retrieval, reranking, RAG, or AI grading/generation;
- document parsing/ingestion execution;
- queue, worker, scheduler, or separate ingestion service;
- Docker, CI, or deployment;
- speculative abstractions for future providers.

## Functional Requirements

### FR-1 — Application boot

`app/main.py` must create the main FastAPI application and the application must start without database or external-service dependencies.

### FR-2 — Health endpoint

Implement:

```http
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

Expected status:

```text
200
```

`/health` verifies only that the backend process is alive. It must not depend on PostgreSQL or any future provider.

### FR-3 — Root endpoint

A minimal development endpoint may exist:

```http
GET /
```

It may return a small API-identification response. Monitoring must use `/health`, not `/`.

### FR-4 — Error response foundation

Establish a reusable application-error response shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": null
  }
}
```

Do not force successful responses into a generic `data` wrapper.

This Step needs only the reusable foundation and at least one focused test of it if a concrete application exception/handler is introduced. Do not build a large exception hierarchy.

### FR-5 — Development API documentation

FastAPI OpenAPI/Swagger documentation remains enabled for development. Final production exposure is deferred to Phase 8.

## Technical Requirements

### Runtime and dependency management

Use:

```text
Python >=3.12,<3.13
FastAPI
REST API
uv
```

`pyproject.toml` must contain only dependencies needed by Step 3.1 and its tests.

Do not add speculative dependencies for PostgreSQL/ORM, authentication, LLM providers, vector retrieval, or document processing.

### API versioning

Reserve:

```text
/api/v1
```

as the prefix for future business endpoints. Step 3.1 does not need to implement those business endpoints.

### Architectural style

Keep a modular monolith. Do not create separate AI or ingestion services.

Preserve dependency direction:

```text
Router
→ Service
→ Repository
→ Database
```

A service may later call another domain/application service when required. Reverse dependencies such as `Repository → Service` or `Database → Router` are prohibited.

Routers must remain HTTP transport adapters and must not own core business rules such as grading, score calculation, lesson unlocking, curriculum progression, or RAG orchestration.

## Repository / Files and Components

Create or reconcile the backend under:

```text
backend/
├── pyproject.toml
├── app/
│   ├── main.py
│   ├── core/
│   ├── database/
│   ├── auth/
│   ├── curriculum/
│   ├── exercise/
│   ├── progress/
│   ├── admin/
│   ├── ai/
│   ├── ingestion/
│   └── shared/
└── tests/
```

Exact package-marker files may be added where Python/import tooling requires them. Do not create empty layer files solely for visual symmetry.

### Approved domain modules

The following logical modules must remain recognizable:

```text
auth
curriculum
exercise
progress
admin
ai
ingestion
```

### Recommended domain pattern

Use only where a module actually needs the layer:

```text
module/
├── router.py
├── schemas.py
├── service.py
└── repository.py
```

Responsibilities:

```text
router.py      → HTTP transport
schemas.py     → request/response validation contracts
service.py     → business/application logic
repository.py  → persistence/data access
```

Do not create unused `router.py`, `service.py`, or `repository.py` files in every module during this Step.

### `app/core/`

Use only for application-wide infrastructure concerns such as future configuration, exceptions, security, and logging. Domain business logic must not live in `core`.

### `app/shared/`

Use only for functionality genuinely reused across multiple domains. Do not create a generic dumping ground such as unrelated `helpers`, `utils`, or `services`.

### `app/ai/`

Preserve the approved boundaries for future AI work:

```text
app/ai/
├── chat/
├── retrieval/
├── grading/
├── generation/
├── prompts/
└── providers/
```

Do not implement AI capabilities in Step 3.1. If empty directories would not be retained by the repository, minimal package markers are acceptable; do not add fake classes or provider abstractions merely to populate them.

### `app/ingestion/`

Keep ingestion inside the backend modular monolith. Do not introduce a queue, worker, scheduler, or independent ingestion deployment.

## Inputs / Outputs

### Inputs

- approved Phase 1 architecture/module boundaries;
- PM decision precedence;
- current repository state;
- Python 3.12 runtime.

### Outputs

- runnable backend project under `backend/`;
- FastAPI application object;
- `GET /health` contract;
- standard application-error response foundation;
- minimal automated tests;
- Step Note/documentation under `docs/backend/step-3.1-backend-skeleton.md` (or the repository's already-established equivalent documentation path).

## Data Flow

There is no persistent business-data flow yet.

Health request flow:

```text
Client
→ FastAPI application
→ GET /health route
→ static liveness result
→ HTTP 200 {"status":"ok"}
```

Future business flow boundary to preserve:

```text
HTTP request
→ Router
→ Service
→ Repository
→ Database
```

Step 3.1 implements only the application/HTTP foundation, not the persistence flow.

## Interfaces / API / Schema

### Implemented API

```http
GET /health
```

Response body:

```json
{
  "status": "ok"
}
```

A development `GET /` endpoint is optional.

### Reserved API prefix

```text
/api/v1
```

### Persistence schema

None is implemented in this Step. Phase 2 remains reference-only until the database Steps materialize it.

## Config / Environment

Step 3.1 must not require runtime secrets or external-service environment variables.

Python target:

```text
>=3.12,<3.13
```

Detailed environment/configuration loading belongs to Step 3.2.

## Error Handling

- use the standard application-error response shape defined above for application errors;
- do not leak Python stack traces as API payloads in deliberate application-error paths;
- `/health` must not fail because a later dependency such as database/LLM is absent;
- avoid broad `except Exception` handlers that hide programming errors merely to satisfy the response contract.

## Testing

Create the minimum test foundation, for example:

```text
tests/
├── conftest.py
└── test_health.py
```

Required verification:

```text
FastAPI application imports/boots
GET /health returns HTTP 200
response JSON status == "ok"
```

If the standard error handler is concretely implemented in this Step, add a focused test proving its response shape.

Tests must not require PostgreSQL, network access, LLM credentials, or any external service.

Run tests through the project-managed environment (`uv`).

## Step Documentation / Knowledge Capture

The completed Step Note must capture at minimum:

- Objective;
- Why;
- Mental Model;
- Core Knowledge;
- Data Flow;
- Key Design Decisions;
- reusable approach for another project;
- Common Mistakes;
- Definition of Done.

Concepts actually used in this Step should be classified in the project Concepts list. Expected likely concepts are architectural boundaries, API/HTTP endpoint, modular monolith, dependency direction, and health check; do not add concepts that were only mentioned but not used.

Tools actually used should be recorded in the Tools list. For this Step, only tools actually present in implementation (for example Python, FastAPI, uv, pytest if used) should be recorded.

## Acceptance Criteria

- [ ] Current repository state was inspected before changes and no duplicate backend project was created.
- [ ] Backend targets Python `>=3.12,<3.13`.
- [ ] Dependencies are managed through `uv`.
- [ ] FastAPI application boots successfully with no database/external service.
- [ ] Approved main domain module boundaries are recognizable.
- [ ] AI submodule boundaries reflect the approved modular-monolith architecture without actual AI implementation.
- [ ] Ingestion remains inside the modular monolith with no queue/worker/service added.
- [ ] Router → Service → Repository → Database dependency direction is documented/preserved.
- [ ] Domain business logic is not placed in routers or `core`/`shared` dumping areas.
- [ ] `GET /health` returns HTTP 200 and `{"status":"ok"}`.
- [ ] Minimal automated health/startup test passes.
- [ ] Development OpenAPI documentation is available.
- [ ] Standard application-error response foundation exists without unnecessary abstraction.
- [ ] No database/auth/business/AI/ingestion-processing/deployment implementation is prematurely introduced.
- [ ] Step Note and actually-used Concepts/Tools records are updated as required by the project Definition of Done.

## Constraints / Non-goals

- Do not redesign Phase 1 architecture.
- Do not choose database/auth/LLM/deployment implementation details early.
- Do not introduce framework layers with no current use.
- Do not split the modular monolith into services.
- Keep the skeleton small enough that a beginner can trace request flow and module ownership.

## Open Questions

None that blocks implementation.

If the existing repository materially conflicts with this specification, stop that conflict from being silently overwritten and report it to PM as `Decision Needed` before Codex chooses a new architecture.

## Definition of Done

Step 3.1 is Done only when implementation and tests pass, the acceptance criteria above are satisfied, the learner can explain the request flow/module boundaries, the Step Note plus Concepts/Tools updates are complete, and App Engineering sends the required specialist handoff to PM.

Next Step after PM acceptance: **Step 3.2 — Configuration & Environment**.
