# Step 3.3 — Database Access

## Goal

Implement the PostgreSQL persistence foundation for the FastAPI backend using the database design approved in Phase 2.

The implementation must provide:

- asynchronous PostgreSQL access;
- SQLAlchemy ORM models;
- request-scoped sessions;
- explicit transaction ownership;
- Alembic migrations;
- required system seed;
- database readiness checking.

Do not implement product business APIs beyond what is required to verify database infrastructure.

---

# Technology Stack

Use:

```text
SQLAlchemy async ORM
psycopg 3
Alembic
PostgreSQL
PostgreSQL vector capability
```

FastAPI remains the HTTP framework.

---

# Database Runtime Structure

Target:

```text
backend/
├── alembic.ini
├── migrations/
│
└── app/
    └── database/
        ├── base.py
        ├── engine.py
        ├── session.py
        └── models/
            ├── user.py
            ├── curriculum.py
            ├── assessment.py
            ├── progress.py
            ├── conversation.py
            ├── document.py
            └── knowledge.py
```

Exact model-file grouping may be adjusted if necessary, but avoid a single oversized models file.

---

# Database Engine

Create an asynchronous SQLAlchemy engine using the configured:

```text
DATABASE_URL
```

Use psycopg 3 as the PostgreSQL driver.

Do not hard-code database credentials.

Connection configuration must come from Step 3.2 Settings.

---

# Session Factory

Create one application-level async session factory using:

```text
async_sessionmaker
```

Provide a request-scoped FastAPI dependency equivalent to:

```text
get_db_session()
```

Required lifecycle:

```text
Request
→ AsyncSession created
→ application uses session
→ session closed
→ Response
```

Never use one global mutable Session across concurrent requests.

---

# ORM Models

Implement SQLAlchemy models matching the approved Phase 2 schema.

Application data includes:

```text
users

hsk_levels
lessons
curriculum_units

pronunciation_sections
pronunciation_progress

vocabulary
lesson_vocabulary
grammar
lesson_grammar

assessments
assessment_lessons
assessment_vocabulary
assessment_grammar

questions
question_options

assessment_attempts
attempt_answers

learner_lesson_progress
learner_hsk_progress
learner_vocabulary_progress
learner_grammar_progress

conversations
messages
message_citations

documents
```

RAG data includes:

```text
knowledge_sources
knowledge_versions
chunks
embedding_profiles
embeddings
message_retrievals
```

Models must preserve the PK/FK, UNIQUE, CHECK and indexing requirements approved in Phase 2.

---

# UUID

Use UUID v4 for entity primary keys.

Application-side UUID generation is acceptable and preferred.

Do not use sequential integer IDs for main entities.

---

# Timestamp Convention

Persist UTC-aware timestamps.

Ensure `created_at`, `updated_at` and domain timestamps follow consistent UTC behavior.

---

# SQLAlchemy Model vs API Schema

Do not reuse ORM entities directly as unrestricted API response models.

Keep:

```text
SQLAlchemy model
→ persistence representation

Pydantic schema
→ API contract
```

Sensitive persistence fields such as:

```text
password_hash
```

must never become exposed automatically through API serialization.

---

# Repository Pattern

Domain repositories must operate using the provided AsyncSession.

Examples:

```text
auth/repository.py
curriculum/repository.py
exercise/repository.py
progress/repository.py
```

Repository responsibilities include:

```text
SELECT
INSERT
UPDATE
DELETE
FLUSH where necessary
```

Repositories must not own application transaction commits.

Do not create one generic repository containing all application queries.

---

# Transaction Ownership

Application/Service layer owns transaction boundaries.

Repository methods must not call `commit()` independently.

Example:

```text
ExerciseService.submit()

BEGIN

ExerciseRepository.save_attempt()
ExerciseRepository.save_answers()
ProgressRepository.update_progress()

COMMIT
```

If any operation fails:

```text
ROLLBACK
```

The operation must not leave partially persisted business state.

---

# External I/O and Transactions

Do not keep PostgreSQL transactions open while waiting on slow external services such as an LLM when avoidable.

Preferred pattern:

```text
1. Read required database state.
2. Complete/release current DB transaction.
3. Perform external AI/network call.
4. Start short DB transaction.
5. Persist validated result.
6. Commit.
```

Exact concurrency safeguards may be added when implementing AI grading.

---

# Connection Pool

Use SQLAlchemy's normal connection pooling.

Do not manually open a new PostgreSQL network connection for every query.

Do not prematurely tune pool sizes in this step unless required for the local environment.

---

# Relationship Loading

Avoid uncontrolled implicit relationship loading.

Load relationships explicitly according to the use case when possible.

Be conscious of N+1 query patterns.

Do not perform premature optimization, but preserve query visibility.

---

# Alembic

Use Alembic as the schema migration framework.

Production and normal development startup must not depend on:

```python
Base.metadata.create_all()
```

Schema creation/evolution must use migrations.

---

# Initial Migration

Create:

```text
0001_initial_schema
```

representing the approved Phase 2 schema.

It must include the required PostgreSQL vector capability/setup needed for the approved RAG architecture.

Review all generated migration code before use.

---

# Autogenerate Policy

Alembic autogenerate may be used to create migration drafts.

Generated migrations must be manually reviewed for:

- constraints;
- indexes;
- foreign keys;
- PostgreSQL-specific types;
- vector setup;
- destructive operations;
- unintended schema differences.

Do not assume autogenerate output is automatically correct.

---

# Required Seed

Implement an idempotent required seed for:

```text
HSK1
HSK2
HSK3
```

and:

```text
TONES
INITIALS
FINALS
```

Use stable business keys established in Phase 2:

```text
hsk_levels.level_number
pronunciation_sections.code
```

Do not hard-code production Admin credentials.

Development seed is out of scope unless required for verification.

---

# Health and Readiness

Preserve:

```http
GET /health
```

as a lightweight process-alive check.

Add:

```http
GET /ready
```

for dependency readiness.

At minimum `/ready` must verify PostgreSQL connectivity using a lightweight query such as:

```sql
SELECT 1;
```

Expected semantics:

```text
/health
→ application process is alive

/ready
→ required database dependency is reachable
```

Do not perform expensive application queries in readiness checks.

---

# Delete Policy

Do not introduce broad `ON DELETE CASCADE` behavior.

Historical records such as:

- assessment attempts;
- attempt answers;
- learner progress;

must not disappear when learning content is archived.

Use the Phase 2 lifecycle/archive strategy.

Cascade deletion may be used only where a child has no valid lifecycle independent of the parent, and should be reviewed explicitly.

---

# Verification

The following flow must succeed against an empty development/test PostgreSQL database:

```text
Create empty DB
→ enable required vector capability
→ alembic upgrade head
→ verify tables/constraints
→ execute required seed
→ start FastAPI
→ GET /health = 200
→ GET /ready = 200
```

Required seed must remain correct when executed repeatedly.

---

# Tests

Add infrastructure tests for at least:

```text
database connection
readiness endpoint
required seed idempotency
migration-created schema availability
```

Tests must use the dedicated Test database configuration from Step 3.2.

Never run destructive test setup against Production.

---

# Out of Scope

Do not implement yet:

- register/login;
- JWT or session authentication;
- curriculum business endpoints;
- exercise submission;
- progression logic;
- AI grading;
- RAG retrieval;
- conversation API;
- document ingestion flow;
- database performance tuning;
- advanced connection-pool tuning.

---

# Acceptance Criteria

- [ ] Async SQLAlchemy engine connects to PostgreSQL through psycopg 3.
- [ ] AsyncSession is request-scoped.
- [ ] ORM models represent the approved Phase 2 schema.
- [ ] API schemas remain separate from ORM models.
- [ ] Repositories do not independently commit transactions.
- [ ] Service layer can control commit/rollback.
- [ ] Long external calls are not intentionally wrapped in long DB transactions.
- [ ] Alembic manages schema evolution.
- [ ] `create_all()` is not the production schema mechanism.
- [ ] Initial migration can create a clean database.
- [ ] PostgreSQL vector capability is reproducibly configured.
- [ ] Required seed is idempotent.
- [ ] `/health` remains lightweight.
- [ ] `/ready` verifies database connectivity.
- [ ] UTC/UUID conventions are respected.
- [ ] Tests operate against a safe test database.

# Expected Deliverable

Runnable database-access foundation plus:

```text
docs/backend/
└── step-3.3-database-access.md
```

Next Step:

**Step 3.4 — Business APIs**