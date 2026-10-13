# Step 2.5 — Migration & Seed Strategy

## Goal

Define how the approved PostgreSQL application and RAG schemas are created, evolved and bootstrapped safely across development, testing and production.

Do not select a concrete migration framework until the backend technology stack is selected.

---

# Migration Policy

All persistent database schema changes must be represented through version-controlled migrations.

Required flow:

```text
Schema Change
→ Migration
→ Version Control
→ Apply to Environment
```

Do not rely on undocumented manual production database modifications.

---

# Migration History

Start with an initial baseline:

```text
0001_initial_schema
```

Future changes must use new migrations:

```text
0001_initial_schema
0002_add_xxx
0003_modify_yyy
```

Once a migration has been applied outside disposable local development, do not rewrite its historical meaning.

Create a new migration instead.

The selected migration framework must maintain a migration-history table indicating which migrations have been applied.

---

# Environment Consistency

Development, Test and Production must use the same migration chain.

```text
Migration Chain
├── Development
├── Test
└── Production
```

Environment differences belong in:

- configuration;
- credentials;
- data;
- infrastructure.

They must not depend on independently maintained schemas.

---

# Forward Migration Strategy

Prefer forward fixes over mandatory automatic rollback.

Do not require every migration to provide a destructive `down` operation when safe reversal cannot be guaranteed.

If a production migration needs correction:

```text
Migration N
→ Migration N+1 correction
```

is acceptable.

Rollback may be supported when the operation is genuinely reversible and safe.

---

# Destructive Changes

Avoid immediate destructive migrations such as:

```text
DROP COLUMN
DROP TABLE
destructive type conversion
```

when existing code/data may still depend on them.

Prefer:

```text
1. Add new representation
2. Backfill existing data
3. Deploy compatible application code
4. Switch reads/writes
5. Verify
6. Remove old representation later
```

Prefer backward-compatible migrations whenever practical.

---

# Migration and Application Deployment

Migration ordering must account for old and new application versions.

Do not deploy a schema migration that immediately removes a column still required by currently running backend code.

Use expand/migrate/switch/contract-style evolution when required.

---

# Seed Categories

Keep two separate seed categories:

```text
Required Seed
Development Seed
```

Do not mix them.

---

# Required Seed

Required system bootstrap data includes:

```text
HSK Levels:
- HSK1
- HSK2
- HSK3

Pronunciation Sections:
- TONES
- INITIALS
- FINALS
```

Required seed must be safe to run repeatedly.

Use stable business identifiers such as:

```text
hsk_levels.level_number
pronunciation_sections.code
```

to detect existing records.

Do not require hard-coded UUID values as seed identity.

---

# Development Seed

Development seed may contain:

- test Admin;
- test Learner;
- sample Lessons;
- sample Vocabulary;
- sample Grammar;
- sample Assessments.

Development seed must never be required for production startup.

---

# Production Admin Bootstrap

Do not commit a fixed production admin password to source control or seed files.

Production Admin creation should later use an explicit setup/bootstrap mechanism such as:

```text
environment-provided credentials
or
one-time setup command
```

Exact implementation is deferred to Backend Foundation.

---

# Curriculum Content

Do not store the full HSK curriculum inside schema migrations.

Keep these responsibilities distinct:

```text
Migration
→ Database structure

Required Seed
→ Required system records

Curriculum Import
→ Learning content

Knowledge Ingestion
→ RAG knowledge
```

Curriculum ingestion/import strategy will be implemented separately.

---

# Seed Idempotency

All reusable seed processes must be idempotent.

Repeated execution must not create duplicate HSK levels, pronunciation sections or equivalent system records.

Use find/upsert/update/skip behavior as appropriate.

---

# Automated Tests

Automated tests must create and isolate the data they require.

Tests must not assume that a developer previously ran development seed against a shared database.

Test fixtures/data lifecycle should be owned by the test environment.

---

# PostgreSQL Vector Setup

Required PostgreSQL vector capabilities/extensions must be reproducible through database setup/migration rather than undocumented manual installation.

Exact implementation depends on the selected PostgreSQL migration tool/environment.

---

# Embedding Model Changes

Changing embedding provider/model/profile is not automatically a database schema migration.

Use:

```text
Create EmbeddingProfile
→ Generate embeddings
→ Validate
→ Activate profile
```

Historical embedding representations should remain available according to the Step 2.4 model.

---

# Chunking Changes

Changing:

```text
chunking_strategy
chunk_size
chunk_overlap
```

is not a database schema migration.

Use:

```text
Create KnowledgeVersion
→ Reprocess source
→ Chunk
→ Embed
→ Validate
→ Activate version
```

---

# Data Backfills

Simple data transformations may execute inside a migration when the dataset and operation are small and safe.

For larger data volumes, separate:

```text
Schema Migration
from
Controlled Data Backfill Job
```

to reduce deployment risk.

---

# Production Database Policy

Local/Development/Test may use:

```text
drop
→ recreate
→ migrate
→ seed
```

when appropriate.

Production must not be upgraded by dropping and recreating the database.

Production evolution must use migrations against existing data.

---

# Migration Failure

When a migration fails:

- do not mark it successfully applied;
- use transactional migration where PostgreSQL supports the operation;
- restore/fix the database to a known state if necessary;
- rerun safely after correction.

Do not silently continue with a partially applied schema.

---

# Repository Structure

Logical target:

```text
backend/
└── database/
    ├── migrations/
    │   ├── 0001_initial_schema
    │   ├── 0002_...
    │   └── ...
    │
    └── seeds/
        ├── required/
        └── development/
```

Concrete filenames/layout may change according to the backend migration framework.

---

# Migration Tool

Do not select a migration framework in this step.

Select it after the backend stack is chosen in Phase 3.

The selected tool must support:

- ordered migrations;
- migration history;
- PostgreSQL;
- constraints/indexes;
- transactional behavior where possible;
- CI/test usage.

---

# Acceptance Criteria

- [ ] Schema changes are migration-driven.
- [ ] Migration files are version-controlled.
- [ ] Dev/Test/Production share one migration history.
- [ ] Applied migrations are not casually rewritten.
- [ ] Production evolution favors backward compatibility.
- [ ] Destructive changes use staged migration when needed.
- [ ] Required and development seeds are separate.
- [ ] Required seeds are idempotent.
- [ ] HSK1-3 and pronunciation sections can be bootstrapped.
- [ ] Production credentials are not hard-coded.
- [ ] Curriculum content is not embedded into schema migrations.
- [ ] Tests own their test data lifecycle.
- [ ] Vector database requirements are reproducible.
- [ ] Embedding-model changes use EmbeddingProfile rather than schema migration by default.
- [ ] Chunking changes use KnowledgeVersion rather than schema migration.
- [ ] Data backfill strategy supports future scale.
- [ ] Production database is never reset as a normal deployment procedure.
- [ ] Failed migrations cannot silently become accepted state.
- [ ] Concrete migration framework remains deferred until Backend Foundation.

# Expected Deliverable

```text
docs/data/
└── step-2.5-migration-seed-strategy.md
```

Next:

**Phase 3 — Backend Foundation**