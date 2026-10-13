# Codex Execution Task — Step 3.3: Database Access

## Execution Gate

**Status:** PM review required before Codex execution.

This file is the **single current Codex execution task** for Step 3.3. It is not a replacement for the authoritative Step Specification.

Do not implement Step 3.4 or any later Step. If a real conflict exists between this task, the current Step Specification, Phase 2 schema, or a higher-precedence PM decision, stop and report `BLOCKED` rather than inventing a resolution.

---

## Step

**Step ID:** 3.3  
**Title:** Database Access  
**Owner:** App Engineering Specialist

---

## Objective

Implement the PostgreSQL persistence foundation for the accepted FastAPI backend using the approved Phase 2 schema.

The completed Step must provide only the database infrastructure required by Step 3.3:

- asynchronous PostgreSQL access;
- SQLAlchemy ORM/data mappings that faithfully represent the approved Phase 2 schema;
- psycopg 3 as the PostgreSQL driver;
- one application-level async engine/session factory;
- request-scoped `AsyncSession` lifecycle;
- explicit service/application transaction ownership;
- Alembic migration infrastructure and `0001_initial_schema`;
- reproducible PostgreSQL `vector` extension setup;
- idempotent required system seed;
- `GET /ready` database readiness behavior using the PM-frozen contract;
- database-focused automated tests and Step documentation.

Do not implement business APIs or future application behavior.

---

## Source of Truth

Read these before editing.

### Primary executable specification

- `Spec-CURRENT/Phase3/Step 3.3 — Database Access.md`

### Required project/control context

- `Spec-CURRENT/PROJECT_CONTEXT.md`
- `Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md`
- `Spec-CURRENT/PM-Control/05-Codex-Execution-Protocol.md`

### Direct schema/data dependencies

- `Spec-CURRENT/Phase2/Step 2.2 — Relational Data Model.md`
- `Spec-CURRENT/Phase2/Step 2.3 — PostgreSQL Schema.md`
- `Spec-CURRENT/Phase2/Step 2.4 — AI-RAG Data Model.md`
- `Spec-CURRENT/Phase2/Step 2.5 — Migration & Seed Strategy.md`

### Direct architecture dependencies

- `Spec-CURRENT/Phase1/Step 1.2 — High-Level Architecture Specification.md`
- `Spec-CURRENT/Phase1/Step 1.3 — Component Responsibilities.md`
- `Spec-CURRENT/Phase1/Step 1.5 — Repository - Module Structure.md`

### Accepted implementation dependencies

Inspect the actual repository state from accepted Steps 3.1 and 3.2, especially:

- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/.env.example`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/errors.py`
- `backend/app/database/__init__.py`
- `backend/tests/conftest.py`
- `backend/tests/test_config.py`
- existing Step 3.1/3.2 regression tests and docs.

### Precedence

Follow PM-control precedence. The current Step Specification and PM decisions beat generated plans/tasks. Preserve Phase 2 schema semantics exactly unless a higher-precedence document intentionally refines them.

---

## PM Decisions Affecting This Step

Frozen technology decisions:

- Python `>=3.12,<3.13`
- FastAPI
- `uv`
- `pydantic-settings`
- PostgreSQL
- async SQLAlchemy
- psycopg 3
- Alembic
- pgvector in PostgreSQL
- Modular Monolith; no separate database service/microservice.

Concrete hosting/managed PostgreSQL vendor selection remains deferred to Phase 8. Do not introduce vendor-specific production infrastructure.

### PM-frozen `/ready` public contract

Success:

```http
GET /ready
HTTP 200
```

```json
{
  "status": "ready"
}
```

Database unavailable / readiness probe failure:

```http
HTTP 503
```

```json
{
  "error": {
    "code": "DATABASE_NOT_READY",
    "message": "Database dependency is not ready",
    "details": null
  }
}
```

Rules:

- `/ready` performs only a lightweight PostgreSQL readiness probe equivalent to `SELECT 1`.
- No business query.
- No mutation.
- No retry loop.
- Do not expose raw database/driver exception details.
- Reuse the existing normalized `ApplicationError` envelope.
- `/health` remains process liveness and MUST NOT query PostgreSQL.
- Database unavailable therefore means:
  - `/health` -> `200 {"status":"ok"}`
  - `/ready` -> `503 DATABASE_NOT_READY`
- Do not invent repository/service layers solely for readiness.

---

## Current Repository State

Treat the accepted Step 3.1 + 3.2 repository as the implementation baseline.

Current relevant state:

- FastAPI application exists in `backend/app/main.py`.
- `/health` exists and is database-independent.
- normalized `ApplicationError` foundation exists in `backend/app/core/errors.py`.
- centralized cached `Settings` exists in `backend/app/core/config.py`.
- accepted Settings currently represent `DATABASE_URL` and `TEST_DATABASE_URL` as configuration only; no database client exists yet.
- test mode already requires `TEST_DATABASE_URL` and rejects exact equality with `DATABASE_URL`.
- `backend/app/database/` currently has no engine/session/model implementation.
- no SQLAlchemy, psycopg, Alembic, pgvector Python integration, migration, ORM model, repository, seed, or readiness implementation exists.
- current regression suite contains 30 passing Step 3.1/3.2 tests in the accepted baseline.

Before editing, inspect the actual current repository again. Reconcile harmless differences instead of creating parallel structures.

---

## In Scope

1. Add only the minimal database dependencies required by Step 3.3.
2. Update Settings so runtime database selection is explicit and safe.
3. Implement async SQLAlchemy engine/session infrastructure.
4. Implement Phase 2 database mappings.
5. Implement Alembic configuration and the initial migration.
6. Configure the PostgreSQL `vector` extension through migration.
7. Implement the required idempotent seed.
8. Add `GET /ready` using the PM-frozen contract.
9. Add database infrastructure/integration tests.
10. Preserve all accepted Step 3.1/3.2 behavior.
11. Add `docs/backend/step-3.3-database-access.md` and record only concepts/tools actually used.

---

## Out of Scope

Do **not** implement:

- registration/login/change-password/reset;
- JWT, refresh tokens, password hashing or auth middleware;
- curriculum/dashboard/business APIs;
- exercise submission or grading behavior;
- progress mutation/unlock logic;
- conversation API behavior;
- AI grading, LLM, embedding generation, retrieval, reranking or RAG orchestration;
- document upload/ingestion workflows;
- frontend integration;
- Docker/CI/deployment;
- managed/cloud PostgreSQL provider selection;
- backup/restore;
- advanced pool tuning or database performance tuning;
- speculative repositories/services for future business logic;
- development content seed unless absolutely required for a focused database verification (prefer not to add it).

Do not add Step 3.4 routers/endpoints opportunistically.

---

## Dependencies

Add only database dependencies required by this Step, using bounded compatible versions consistent with the repository's existing dependency style:

- SQLAlchemy 2.x with async ORM support;
- psycopg 3 as the PostgreSQL driver (a standard psycopg installation variant appropriate for local development is acceptable);
- Alembic;
- Python pgvector integration needed to map PostgreSQL `vector` cleanly from SQLAlchemy/migrations.

Do not add:

- `asyncpg`;
- another ORM;
- another migration framework;
- a standalone vector database client/service;
- auth libraries;
- Redis/queue libraries;
- AI/provider libraries.

Update `backend/uv.lock` through `uv`.

---

## Configuration Contract to Preserve/Extend

Update the accepted Step 3.2 Settings contract only as required for database access.

### Runtime URL selection

```text
APP_ENV=development | production
→ use DATABASE_URL

APP_ENV=test
→ use TEST_DATABASE_URL
```

At Step 3.3:

- `DATABASE_URL` becomes required for non-test application database runtime.
- `TEST_DATABASE_URL` remains required for `APP_ENV=test`.
- if `DATABASE_URL` is also supplied in test mode, it must remain different from `TEST_DATABASE_URL`.
- database URLs used by this Step must target PostgreSQL through SQLAlchemy's psycopg 3 dialect, e.g. `postgresql+psycopg://...`.
- do not add database credentials to source control.
- `SECRET_KEY` remains unused/optional because authentication is still out of scope.

Prefer one clear Settings property/helper for the effective runtime database URL rather than scattering environment branching across database modules.

Update `backend/.env.example` with placeholder PostgreSQL+psycopg URLs only.

---

## Database / Session / Transaction Design

### Engine

Create one application-level async SQLAlchemy engine from the effective Settings database URL.

Requirements:

- use `create_async_engine` or the SQLAlchemy equivalent;
- psycopg 3 is the driver;
- do not open one raw network connection per query;
- use SQLAlchemy's normal connection pooling;
- do not tune pool sizes/speculative pool behavior in this Step;
- engine creation must not execute business queries.

### Session factory

Create one application-level `async_sessionmaker`.

Provide a FastAPI dependency equivalent to:

```python
async def get_db_session() -> AsyncIterator[AsyncSession]:
    ...
```

Required lifecycle:

```text
request
→ create AsyncSession
→ yield/use session
→ close session
→ response
```

Important:

- never share one mutable `AsyncSession` across requests;
- do **not** auto-commit every successful request inside the generic session dependency;
- repositories must not own `commit()`;
- service/application code owns transaction boundaries;
- no service/repository layer needs to be created in Step 3.3 merely to demonstrate this rule.

The infrastructure must allow future application/service code to use explicit commit/rollback/transaction contexts.

### External I/O rule

Document/preserve the Step 3.3 rule that slow external I/O must not intentionally be wrapped inside long-running database transactions. No AI/network workflow needs to be implemented now.

---

## Phase 2 Schema Fidelity

The initial models and migration must reflect the approved Phase 2 physical schema, not a simplified substitute.

### Required application tables

- `users`
- `hsk_levels`
- `lessons`
- `curriculum_units`
- `pronunciation_sections`
- `pronunciation_progress`
- `vocabulary`
- `lesson_vocabulary`
- `grammar`
- `lesson_grammar`
- `assessments`
- `assessment_lessons`
- `assessment_vocabulary`
- `assessment_grammar`
- `questions`
- `question_options`
- `assessment_attempts`
- `attempt_answers`
- `learner_lesson_progress`
- `learner_hsk_progress`
- `learner_vocabulary_progress`
- `learner_grammar_progress`
- `conversations`
- `messages`
- `message_citations`
- `documents`

### Required RAG/storage tables

- `knowledge_sources`
- `knowledge_versions`
- `chunks`
- `embedding_profiles`
- `embeddings`
- `message_retrievals`

### Global physical rules

- UUID v4 primary keys for main entities; application-side generation is preferred.
- snake_case identifiers.
- UTC-aware timestamps.
- use `TEXT`/`VARCHAR` + `CHECK` for lifecycle/type values rather than PostgreSQL native enums.
- preserve nullable/non-nullable fields exactly as Phase 2 specifies.
- preserve all Phase 2 PK/FK/UNIQUE/CHECK/basic index requirements.
- do not duplicate derived values that Phase 2 intentionally derives elsewhere.
- do not add speculative columns.

### Junction/association tables

Phase 2 specifies some pure junction tables as FK pairs with `UNIQUE(...)` but does not define a surrogate `id` column.

Do **not** invent surrogate IDs or change their physical schema simply to satisfy ORM-class identity requirements. If a mapped class would require an extra primary key not present in the approved physical schema, represent the table with a SQLAlchemy association/Core `Table` construct or another SQLAlchemy mapping approach that preserves the approved columns/constraints.

Do not silently convert a Phase 2 `UNIQUE(a,b)` requirement into a different physical model.

### Controlled values/checks

Preserve the controlled values/invariants stated in Phase 2, including at minimum:

- user roles: `LEARNER | ADMIN`;
- lesson status: `DRAFT | PUBLISHED | ARCHIVED`;
- curriculum unit type: `LESSON | PERIODIC_TEST` plus exactly-one-target invariant;
- assessment type/status and `pass_threshold BETWEEN 0 AND 100` plus lesson-exercise/periodic-test target invariant;
- supported question types from the approved schema;
- assessment attempt statuses;
- answer grading statuses;
- message roles/statuses and message content invariant;
- document processing/review statuses and approval invariant;
- knowledge source type and exactly-one-source-target invariant;
- knowledge version statuses;
- chunk content types;
- embedding profile statuses;
- message citation source kinds.

Do not replace these with Python-only validation when Phase 2 requires/permits database CHECK enforcement.

### Historical/delete behavior

Do not introduce broad cascading deletes.

Default to non-cascading/no-action or restrictive FK behavior unless Phase 2 explicitly requires another action.

Explicit citation behavior to preserve:

- `message_citations.message_id` → `ON DELETE CASCADE`;
- `message_citations.chunk_id` → nullable FK with `ON DELETE SET NULL`.

Historical attempts, answers and learner progress must not disappear because learning content is archived.

### Required basic indexes

Beyond PK/UNIQUE-created indexes, preserve the Phase 2 initial indexes for:

- `lessons(hsk_level_id)`
- `curriculum_units(hsk_level_id, order_index)`
- `assessment_attempts(user_id, assessment_id)`
- `conversations(user_id, updated_at)`
- `messages(conversation_id, created_at)`
- `documents(processing_status)`
- `documents(review_status)`

Do not add speculative performance indexes.

---

## RAG / pgvector Schema Requirements

Step 3.3 materializes the Phase 2 RAG storage model but does **not** implement retrieval behavior.

### `knowledge_sources`

Preserve real FKs to `documents` and `lessons` and the `DOCUMENT | LESSON` target invariant. Preserve the Phase 2 rule that one Lesson maps logically to one KnowledgeSource; do not create KnowledgeSource per vocabulary/grammar item.

### `knowledge_versions`

Preserve:

- `UNIQUE(knowledge_source_id, version_number)`;
- `PROCESSING | ACTIVE | SUPERSEDED | FAILED`;
- chunking configuration fields;
- only one ACTIVE version per KnowledgeSource.

Use a PostgreSQL-appropriate constraint/index mechanism for the one-ACTIVE-version invariant; do not leave it as documentation-only state.

### `chunks`

Preserve:

- `UNIQUE(knowledge_version_id, chunk_index)`;
- content type values;
- explicit relational metadata fields (`page_number`, `section`, `lesson_id`) plus auxiliary JSONB metadata.

### `embedding_profiles`

Preserve provider/model/version/dimensions/status fields. Do not hard-code one provider/model into persistence logic.

### `embeddings`

Preserve:

```text
UNIQUE(chunk_id, embedding_profile_id)
```

Use PostgreSQL pgvector storage.

Do not hard-code the vector database column to one model dimension unless the authoritative schema explicitly requires it. `EmbeddingProfile.dimensions` remains the profile dimension contract and multiple historical profiles must remain representable.

Do not add ANN indexes, semantic search SQL, retrieval filters or reranking in Step 3.3.

### `message_retrievals`

Persist only the approved trace shape (`message_id`, `chunk_id`, rank, nullable retrieval/rerank scores, timestamp). Do not implement retrieval execution.

---

## Alembic / Migration Plan

Create standard Alembic infrastructure under the repository convention, expected equivalent to:

```text
backend/
├── alembic.ini
└── migrations/
    ├── env.py
    ├── script.py.mako
    └── versions/
        └── 0001_initial_schema.py
```

Requirements:

1. Alembic uses the same model metadata/schema definitions as the application.
2. Alembic obtains the effective database URL from the accepted Settings contract; no hard-coded credentials.
3. Dev/Test/Production share one migration chain.
4. Normal startup must not call `Base.metadata.create_all()`.
5. The initial revision is `0001_initial_schema` and represents the approved Phase 2 application + RAG schema.
6. Migration must reproducibly enable pgvector using the PostgreSQL extension named `vector`, equivalent to:

   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

7. Migration must create all required tables, FKs, UNIQUE constraints, CHECK constraints and initial indexes.
8. Review generated/autogenerated output manually. Do not accept autogenerate blindly.
9. Migration failure must not be silently treated as success.
10. Do not place full curriculum content or development users inside the migration.
11. Future migrations must be forward migrations; do not establish a convention of rewriting already-applied revisions.

If the PostgreSQL user/test environment cannot create/use the `vector` extension, report the verification blocker instead of replacing pgvector or removing the extension requirement.

---

## Required Seed Plan

Implement a reusable **required system seed**, separate from schema migration and separate from any development sample-data seed.

Expected repository boundary may be equivalent to:

```text
backend/app/database/seeds/
├── __init__.py
└── required.py
```

or another small database-owned layout consistent with the existing repository.

Provide a simple executable entry point, for example:

```bash
uv run python -m app.database.seeds.required
```

Required rows:

```text
HSK levels
- level_number = 1
- level_number = 2
- level_number = 3

Pronunciation sections, ordered
1. TONES
2. INITIALS
3. FINALS
```

Rules:

- use `hsk_levels.level_number` and `pronunciation_sections.code` as stable identity;
- repeated execution must not create duplicates;
- do not use fixed UUIDs as seed identity;
- populate required `order_index` deterministically;
- do not add curriculum lessons/vocabulary/grammar/content;
- do not create production Admin credentials;
- nullable display fields may remain null unless an already-approved required value exists; do not invent product content solely for the seed.

---

## `/health` and `/ready`

### `/health`

Preserve exactly:

```http
GET /health
200
{"status":"ok"}
```

`/health` must not obtain a database session, execute SQL, or fail because PostgreSQL is down.

### `/ready`

Implement the PM-frozen contract exactly.

Readiness flow:

```text
GET /ready
→ lightweight DB connection/probe
→ SELECT 1
→ success: 200 {"status":"ready"}
```

If the connection/probe raises a database/SQLAlchemy/driver readiness failure:

```text
→ raise/return existing ApplicationError contract
→ HTTP 503
→ code = DATABASE_NOT_READY
→ message = Database dependency is not ready
→ details = null
```

Do not expose exception strings, DSNs, credentials, hostnames or stack traces in the API response.

Do not catch unrelated programming errors with a broad application-wide `except Exception` simply to force a 503.

Do not create repository/service abstractions solely for readiness. A small database-infrastructure helper is acceptable.

---

## Expected Files / Components

### Create

Expected equivalent files/components:

```text
backend/alembic.ini
backend/migrations/env.py
backend/migrations/script.py.mako
backend/migrations/versions/0001_initial_schema.py

backend/app/database/base.py
backend/app/database/engine.py
backend/app/database/session.py
backend/app/database/models/__init__.py
backend/app/database/models/user.py
backend/app/database/models/curriculum.py
backend/app/database/models/assessment.py
backend/app/database/models/progress.py
backend/app/database/models/conversation.py
backend/app/database/models/document.py
backend/app/database/models/knowledge.py
backend/app/database/seeds/__init__.py
backend/app/database/seeds/required.py
```

A small `backend/app/database/readiness.py` may be created if it keeps `main.py` and `engine.py` clearer; do not add router/service/repository layers just for readiness.

Focused tests expected equivalent to:

```text
backend/tests/test_database_session.py
backend/tests/test_migrations.py
backend/tests/test_required_seed.py
backend/tests/test_readiness.py
```

Documentation:

```text
docs/backend/step-3.3-database-access.md
```

Exact model/test filenames may follow current repository convention, but do not collapse the entire schema into one oversized model file.

### Modify

Expected existing files to modify only as required:

- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/.env.example`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/tests/conftest.py`
- existing Step 3.2 config tests if their accepted URL assumptions must change to psycopg 3 DSNs.

`backend/app/core/errors.py` should normally not require structural redesign; reuse `ApplicationError`. Modify only if a minimal, non-breaking change is genuinely necessary for the frozen readiness contract.

### Do Not Touch for Feature Implementation

Do not add business logic/routes under:

- `app/auth/`
- `app/curriculum/`
- `app/exercise/`
- `app/progress/`
- `app/admin/`
- `app/ai/`
- `app/ingestion/`
- `app/shared/`

Package imports may reference database models where necessary for Alembic metadata only; do not implement future domain behavior.

---

## Test Database Safety

All integration/database tests must use the accepted test configuration boundary.

Minimum safeguards:

- `APP_ENV=test`;
- use the effective `TEST_DATABASE_URL`, never `DATABASE_URL`;
- refuse destructive setup if the effective test URL equals the runtime/production URL;
- do not run destructive reset logic unless the target is clearly test-scoped;
- never use production credentials in tests;
- never silently fall back to SQLite.

If a test fixture performs schema drop/reset operations, fail closed unless the test target is clearly safe. Keep this safeguard in test infrastructure, not as a new production feature/config subsystem.

Tests own their required data lifecycle and must not depend on a developer having run a development seed.

---

## Required Tests

Use focused unit tests plus real PostgreSQL+pgvector integration tests where the behavior is database-specific.

### Configuration / engine

Verify:

- development/production select `DATABASE_URL`;
- test selects `TEST_DATABASE_URL`;
- missing required runtime DB URL fails early for the relevant environment;
- accepted URL format uses PostgreSQL + psycopg 3;
- engine/session factory are created from Settings, not hard-coded credentials.

### Session lifecycle / transaction ownership

Verify:

- separate requests/usages receive separate `AsyncSession` instances;
- sessions are closed after use;
- generic session dependency does not auto-commit;
- application/service caller can explicitly commit;
- rollback prevents partial persistence on failure.

Do not create fake business services solely to test this; test the infrastructure boundary directly.

### Migration/schema

Against an empty dedicated PostgreSQL test database with pgvector available:

- `alembic upgrade head` succeeds;
- Alembic revision/history exists;
- `vector` extension exists;
- every required Phase 2 table exists;
- critical FKs/UNIQUE/CHECK constraints exist;
- required initial indexes exist;
- vector column exists with pgvector type;
- no forbidden extra business tables are introduced.

Include focused checks for high-risk invariants such as:

- curriculum unit exactly-one target;
- assessment type/lesson target;
- message nullable-content state invariant;
- document approval invariant;
- knowledge-source exactly-one target;
- one ACTIVE knowledge version per source;
- message citation cascade/set-null rules.

### Required seed

Verify:

- first run creates HSK 1/2/3 and TONES/INITIALS/FINALS;
- second run succeeds without duplicates;
- business-key identity is used;
- no development users/content are inserted.

### Readiness

Verify:

- database available → `/ready` returns exactly `200 {"status":"ready"}`;
- database probe unavailable/fails → `/ready` returns exactly the PM-frozen 503 normalized error;
- raw database exception text is absent from response;
- `/health` stays `200 {"status":"ok"}` even when readiness is forced to fail;
- readiness performs no mutation/business query/retry loop.

### Regression

Run the full existing Step 3.1/3.2 test suite and preserve accepted behavior.

---

## Verification Commands

Use the project-managed `uv` environment.

Minimum:

```bash
cd backend
uv sync
uv run python -c "from app.main import app; assert app is not None"
```

With a dedicated empty PostgreSQL+pgvector **test** database configured through `APP_ENV=test` / `TEST_DATABASE_URL`:

```bash
uv run alembic upgrade head
uv run python -m app.database.seeds.required
uv run python -m app.database.seeds.required
uv run pytest -q
```

Also verify migration/schema metadata programmatically or with focused tests as described above.

If the required PostgreSQL+pgvector test database is unavailable, do **not** substitute SQLite and do not claim full acceptance. Report the affected database verification as `BLOCKED`/`PARTIAL` with the exact missing prerequisite.

Do not add Docker solely to make Step 3.3 tests pass; containerized development belongs to a later Step.

---

## Acceptance Criteria

Codex may report `DONE` only when all applicable items below have evidence:

- [ ] Existing accepted Step 3.1/3.2 behavior is preserved.
- [ ] Python remains `>=3.12,<3.13` and dependency management remains `uv`.
- [ ] SQLAlchemy async ORM, psycopg 3, Alembic and pgvector support are the only necessary new persistence dependencies.
- [ ] No forbidden future-Step dependency is introduced.
- [ ] Runtime DB URL selection uses `DATABASE_URL` outside test and `TEST_DATABASE_URL` in test.
- [ ] No database credentials are hard-coded.
- [ ] Async SQLAlchemy engine uses psycopg 3.
- [ ] One application-level `async_sessionmaker` exists.
- [ ] `AsyncSession` is request-scoped and closed after use.
- [ ] Generic session infrastructure does not auto-commit successful requests.
- [ ] Future service/application callers retain explicit commit/rollback ownership.
- [ ] ORM/data mappings represent every approved Phase 2 application and RAG table.
- [ ] No surrogate columns/physical schema changes were invented for pure Phase 2 junction tables.
- [ ] UUID, UTC, nullability, FK, UNIQUE, CHECK and basic index contracts match Phase 2.
- [ ] Historical data is protected from broad cascade deletion.
- [ ] Citation-specific `CASCADE`/`SET NULL` behavior matches Phase 2.
- [ ] Alembic is configured and `0001_initial_schema` exists.
- [ ] Normal app startup does not use `Base.metadata.create_all()` as schema management.
- [ ] `alembic upgrade head` creates the clean approved schema.
- [ ] PostgreSQL `vector` extension is created/configured reproducibly by migration.
- [ ] Embedding vector persistence uses pgvector without implementing retrieval/ANN indexes.
- [ ] Required seed creates HSK1-3 and TONES/INITIALS/FINALS using stable business keys.
- [ ] Required seed is idempotent.
- [ ] No production Admin credentials or development curriculum content are seeded.
- [ ] `/health` remains exact process-liveness behavior and never queries the DB.
- [ ] `/ready` success returns exactly `200 {"status":"ready"}`.
- [ ] `/ready` DB failure returns exactly the PM-frozen `503 DATABASE_NOT_READY` envelope.
- [ ] `/ready` runs only a lightweight `SELECT 1`-equivalent probe with no mutation/retry/business query.
- [ ] Database errors do not leak raw driver/DSN details through `/ready`.
- [ ] Database tests use the dedicated safe test database and never silently use Production.
- [ ] Real PostgreSQL+pgvector integration verification passes; SQLite is not substituted.
- [ ] Existing regression suite plus Step 3.3 tests pass.
- [ ] No Step 3.4 business API/auth/AI/ingestion/deployment implementation was added.
- [ ] Step Note exists at `docs/backend/step-3.3-database-access.md` and reflects the actual implementation.
- [ ] Concepts/Tools records include only items actually used and use the project taxonomy correctly.

---

## Step Documentation / Knowledge Capture

Create/update:

```text
docs/backend/step-3.3-database-access.md
```

The Step Note must include at minimum:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- reusable approach for another project
- Common Mistakes
- Definition of Done

Likely concepts actually used in this Step include, only if implemented:

- relational database / PostgreSQL — **DE**
- relational schema, PK/FK/UNIQUE/CHECK/indexes — **DE**
- schema migration / migration history — **DE**
- transaction boundary / commit / rollback — **BOTH** only if documented as shared application/data correctness concern; otherwise classify by its actual role and explain it
- database session / connection pool — **SYSTEM** or **DE** according to actual project role; do not classify mechanically
- database readiness endpoint — **SYSTEM**
- test database isolation — **SYSTEM** / **DE** according to the implemented concern

Tools should be classified by actual role. Do not assume every Python/database development tool is automatically DE merely because the project targets Data Engineering.

---

## Architecture Guardrails

- Keep the backend a Modular Monolith.
- Do not split persistence into a separate service.
- Preserve `Router → Service → Repository → Database` direction for future business paths.
- Do not create repositories/services with no current Step use.
- Database infrastructure may live under `app/database/`; domain persistence access belongs in future domain repositories when those Steps require it.
- Do not put domain business rules in `app/database`, `core`, routers, migrations or seed scripts.
- Do not use ORM models directly as unrestricted public API response schemas.
- Do not introduce a generic repository abstraction for all domains.
- Do not introduce provider/vendor-specific production DB abstractions in this Step.
- Do not tune for scale without evidence.

---

## Error Handling

- Reuse the existing normalized application-error foundation.
- `/ready` database failure uses only the frozen `DATABASE_NOT_READY` contract.
- Do not expose SQL statements, credentials, DSNs or raw driver exception text to clients.
- Do not hide migration/seed/test failures behind success fallbacks.
- A migration that partially fails must not be reported as successfully applied.

---

## Before Editing

Return a concise implementation plan covering:

1. exact files to inspect/create/modify;
2. dependency additions;
3. effective Settings/DB URL changes;
4. ORM/schema grouping and high-risk constraints;
5. migration/vector-extension plan;
6. required-seed plan;
7. `/ready` implementation plan;
8. test DB prerequisite and safety checks;
9. verification commands;
10. any blocker/conflict found.

If an unresolved conflict would change schema semantics, public API, transaction ownership, migration strategy or database technology, stop with `BLOCKED` and report it before editing.

If no blocker exists, proceed in the same Codex task.

---

## Required Codex Completion Report

Return exactly enough evidence for specialist review:

```text
Step: 3.3 — Database Access
Status: DONE | PARTIAL | BLOCKED

Implementation plan executed:
- ...

Files created:
- ...

Files modified:
- ...

Dependencies added/removed:
- ...

Configuration changes:
- effective development/production DB URL behavior
- effective test DB URL behavior
- DSN/driver scheme

Database/session design:
- engine
- session factory
- request lifecycle
- commit/rollback ownership

Schema/migration changes:
- Alembic revision(s)
- tables created
- high-risk constraints/indexes verified
- pgvector extension/vector type evidence

Required seed:
- execution command
- rows/business keys
- first-run result
- repeated-run/idempotency result

API/interface:
- /health evidence
- /ready success evidence
- /ready DB-failure evidence

Tests / verification:
- command:
  result:
- command:
  result:
...

Test database safety:
- exact guard/evidence showing Production is not targeted

Acceptance criteria:
- [PASS/FAIL] ...

Step Note:
- path

Concepts actually used:
- Concept | Category | Role

Tools actually used:
- Tool | Category | Role

Deviations from specification:
- none | ...

Problems / risks:
- none | ...

Decisions needed:
- none | ...

Recommended next action:
- Return to App Engineering Specialist for independent review.
- Do not begin Step 3.4.
```

Do not claim `DONE` if the real PostgreSQL+pgvector migration/integration verification was not run successfully.
