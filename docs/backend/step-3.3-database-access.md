# Step 3.3 — Database Access

## Objective

Add the PostgreSQL persistence foundation used by the Modular Monolith: async SQLAlchemy, psycopg 3, Alembic, pgvector, the approved Phase 2 schema, required bootstrap rows, and the database readiness endpoint.

## Why

Database connectivity and schema evolution need one explicit boundary before business features depend on persistent state. A versioned schema and request-scoped session provide consistent development, test, and production behavior without adding domain repositories or business APIs prematurely.

## Mental Model

```text
APP_ENV / backend/.env
→ validated Settings chooses DATABASE_URL or TEST_DATABASE_URL
→ one async SQLAlchemy engine and session factory
→ request dependency yields and closes an AsyncSession
→ application/service code owns commit and rollback

Alembic migration → PostgreSQL schema + vector extension
Required seed → HSK levels and pronunciation section lookup rows
GET /ready → SELECT 1 → ready or normalized 503
```

`/health` remains process liveness and has no database dependency.

## Core Knowledge

- SQLAlchemy maps the approved relational schema, UUID keys, UTC-aware timestamps, JSONB fields, database constraints and indexes. Three assessment junction tables are plain association tables with no invented surrogate IDs.
- psycopg 3 is the PostgreSQL driver. The application owns one pooled async engine and one `async_sessionmaker`; each request gets its own session.
- A session dependency closes the session but does not commit. Application/service code decides when a transaction commits or rolls back. Slow external I/O should not be intentionally held inside a database transaction.
- Alembic is the versioned schema history. `0001_initial_schema` creates the Phase 2 tables and enables PostgreSQL's `vector` extension. Application startup does not call `create_all()`.
- `embeddings.vector` uses pgvector without a fixed dimension or ANN index. Embedding profile dimensions remain data, so multiple profiles can coexist.
- The required seed uses HSK `level_number` and pronunciation `code` as idempotent business keys. It adds no users or curriculum content.
- `/ready` issues only `SELECT 1`; it translates SQLAlchemy database errors into the frozen `DATABASE_NOT_READY` response and does not reveal driver details.
- Tests fail closed unless `APP_ENV=test` and the effective database is named `chinese_learning_test`, distinct from the runtime database. No SQLite fallback is used.
- Windows uses a selector event-loop policy before loop creation because psycopg 3 async connections are incompatible with the default Proactor loop.

## Data Flow

The Settings property selects `TEST_DATABASE_URL` only in test mode and `DATABASE_URL` otherwise. The async engine pools connections. FastAPI's session dependency creates a request-scoped session, yields it, and closes it when the request finishes; it does not infer transaction success from the HTTP response. Explicit transaction contexts own commit/rollback behavior.

Alembic loads the same model metadata used by the application, applies the initial revision transactionally, and records its revision. The separate required seed inserts three HSK levels and the ordered `TONES`, `INITIALS`, and `FINALS` rows. Readiness checks the database connection independently from liveness.

## Key Design Decisions

- Use PostgreSQL + async SQLAlchemy + psycopg 3 + Alembic + pgvector, with no second database, ORM, or vector service.
- Keep environment credentials out of source control and use PostgreSQL+psycopg DSNs.
- Keep `AsyncSession` request-scoped, and leave transaction ownership with future application/service code.
- Match Phase 2 FKs, unique/check constraints, indexes, and citation delete behavior. No broad cascades are added.
- Use a partial unique index for one `ACTIVE` knowledge version per source.
- Keep pgvector dimension-agnostic and avoid ANN/retrieval behavior at this step.
- Keep required seed separate from migration and development content.
- Keep readiness separate from liveness and catch only SQLAlchemy database failures.
- On Windows, select the event loop required by psycopg before the ASGI/migration runner creates it.

## Reusable Approach in Another Project

Establish one validated runtime/test DSN selector, one application-level async engine and session factory, and a request dependency that only manages session lifetime. Model persistent state with explicit relational constraints, version schema changes in Alembic, and keep bootstrap data idempotent by business keys. Verify destructive or integration tests target an unmistakably isolated database before running them.

## Common Mistakes

- Using a synchronous URL or the wrong PostgreSQL driver with an async engine.
- Reusing one mutable session across requests or committing automatically in generic request cleanup.
- Calling `create_all()` as production schema management instead of applying migrations.
- Adding primary keys to approved pure junction tables or using broad delete cascades.
- Hard-coding an embedding dimension or adding retrieval indexes before a measured requirement exists.
- Treating a successful database connection as proof that migrations or required seed data are present.
- Letting tests silently connect to `DATABASE_URL`, use SQLite, or reset a database without verifying its test scope.
- Holding transactions open around slow network or model calls.
- Returning raw SQLAlchemy/driver errors in health responses.

## Definition of Done

- The 32 Phase 2 tables, constraints and required indexes are represented in SQLAlchemy and the initial Alembic revision.
- PostgreSQL vector support and dimension-agnostic vector storage are verified.
- Runtime and test database selection is explicit and protected by a test target guard.
- Session lifecycle, explicit transaction ownership, and idempotent required seed are verified.
- `/health` stays database-independent and `/ready` follows the PM contract.
- Existing Step 3.1/3.2 tests and Step 3.3 PostgreSQL integration tests pass.
- No Step 3.4 business behavior is implemented.

## Concepts Actually Used

| Concept | Category | Role |
|---|---|---|
| Relational schema, keys and constraints | DE | Preserve Phase 2 entities and data integrity in PostgreSQL. |
| Schema migration history | DE | Apply the same versioned schema across environments. |
| Database session and connection pool | SYSTEM | Manage per-request database work over a shared application engine. |
| Transaction boundary / commit / rollback | SYSTEM | Supports application correctness and consistent persisted data. |
| Database readiness endpoint | SYSTEM | Expose dependency readiness without changing liveness behavior. |
| Test database isolation | SYSTEM | Prevent integration checks from targeting runtime data. |
| pgvector persistence | BOTH | Store vectors in PostgreSQL for future retrieval without implementing retrieval. |

## Tools Actually Used

| Tool | Category | Role |
|---|---|---|
| Python | SYSTEM | Backend implementation and seed execution. |
| uv | SYSTEM | Resolve and run the backend environment. |
| SQLAlchemy | SYSTEM | Async engine, request sessions and ORM mappings. |
| psycopg 3 | SYSTEM | PostgreSQL async driver. |
| Alembic | DE | Versioned migration and schema verification. |
| PostgreSQL | DE | Relational database and integration-test target. |
| pgvector | BOTH | PostgreSQL vector column support. |
| pytest | SYSTEM | Regression and database integration tests. |
