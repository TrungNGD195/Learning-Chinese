# Step 8.2 — Final Docs-Only Reconciliation

## Target

`READY_FOR_SPECIALIST_REVIEW — STEP 8.2 DOCS CLOSEOUT`

Do not mark Step 8.2 DONE.  
Do not start Step 8.3.

## Scope

Docs-only reconciliation. Do not modify application code, frontend code, tests, migrations, `compose.yaml`, or `.github/workflows/ci.yml`.

Mandatory files:

- `docs/devops/step-8.2-step-note.md`
- `docs/devops/step-8.2-run-report.md`
- `Spec-CURRENT/Phase8/Step-8.2-Containerized-Dev-and-CI.md`

Do not create duplicate documentation. Leave `docs/devops/step-8.2-container-ci.md` unchanged unless actual source contradicts it.

If an existing project Concepts/Tools master list exists in the current working tree, reconcile only its existing Step 8.2 entries. Do not create a new master-list file.

## Accepted Evidence

Gate A — local runtime is closed:

- PostgreSQL 17 + pgvector 0.8.6
- development and test DB fresh migrations `0001 → 0012`
- `alembic current = 0012_vector_storage_readiness`
- `alembic check` reports no new upgrade operations
- pgvector verified in both databases
- backend: `1152 passed, 1 skipped`
- frontend: 14 Vitest files / 326 tests
- lint PASS with 0 errors
- build PASS
- live `api:check` PASS
- Playwright Chromium: `6/6 PASS`

Gate B — hosted CI is closed:

- GitHub Actions `.github/workflows/ci.yml`
- real hosted `quality` job PASS
- duration approximately 3m05s
- GitHub summary: 14/14 Vitest files, 326/326 tests

Hosted-only regressions already fixed and accepted:

1. invalid setup-uv action reference → valid immutable reference;
2. four backend test scenarios now explicitly establish required seed prerequisites; no global CI seed workaround;
3. Step 7.7 manifest tests deterministically monkeypatch `_code_commit`; production runner unchanged.

Official Phase 7.4, 7.5, 7.7 and 7.6 evaluation gates remain deferred.

## Step Note

Rewrite concisely with:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- Reusable approach in another project
- Common Mistakes
- Definition of Done
- Concepts Discovered
- Tools Used

Mental model:

`Git change → reproducible dependency setup → PostgreSQL/pgvector → migrations → static checks → backend/frontend tests → build/API-contract/browser verification → CI result`

Preserve the principle that local and CI prove the same contracts without hiding test prerequisites through global setup.

Final Concepts:

- Reproducible Environment — SYSTEM — MUST KNOW
- Container / Container Image — SYSTEM — MUST KNOW
- CI Pipeline — SYSTEM — MUST KNOW
- Environment Variables / Secrets — SYSTEM — MUST KNOW
- Migration Validation — SYSTEM — MUST KNOW
- Deterministic Test Boundary — BOTH — MUST KNOW
- Health Check — SYSTEM — SHOULD KNOW
- Dependency Caching — SYSTEM — SHOULD KNOW

`Docker Compose` must not appear as a Concept.

Final Tools:

- Docker — SYSTEM
- Docker Compose — SYSTEM
- GitHub Actions — SYSTEM
- PostgreSQL — BOTH
- pgvector — AI
- Alembic — SYSTEM
- uv — SYSTEM
- npm — SYSTEM
- pytest — SYSTEM
- Vitest / RTL — SYSTEM
- Playwright — SYSTEM
- Oxlint — SYSTEM

## Run Report

Replace stale statements that Docker runtime or hosted GitHub Actions are blocked/not run.

Record Gate A and Gate B as PASS with the accepted evidence above.

Record the three hosted-only regressions as resolved.

Keep these as non-blocking observations only:

- SQLAlchemy cyclic-FK/table-cycle warning;
- frontend lint warnings with 0 errors;
- Vite >500 kB chunk warning;
- one high-severity npm advisory.

Do not run `npm audit fix`. Do not invent whether the advisory is a production or dev dependency if current evidence does not establish that classification.

Explicitly preserve all official Phase-7 evaluation gates as deferred.

## Step Specification

Reconcile Current State and verification sections with the implemented design:

- DB-only `compose.yaml`
- `pgvector/pgvector:0.8.6-pg17`
- one PostgreSQL container
- `chinese_learning` and `chinese_learning_test`
- init SQL creates only test DB
- Alembic owns application schema
- Python 3.12 + uv native backend
- Node 22 + npm native frontend
- one Linux GitHub Actions quality pipeline
- migrations/current/check + pgvector verification
- compile/full pytest
- lint/Vitest/build
- live API contract check
- deterministic Chromium Playwright
- no SQLite
- no live/paid AI or live external retrieval

Mark canonical AC1–AC5 satisfied.

Do not write that the overall Step is DONE. State PM final acceptance is pending.

Open Questions: `NONE`.

## Validation

Before handoff verify:

- no stale statement says Compose runtime remains blocked;
- no stale statement says hosted Actions was not run;
- no Concepts entry classifies Docker Compose as a concept;
- no Tool entry classifies pgvector as SYSTEM;
- PostgreSQL is BOTH;
- Phase-7 official gates remain explicitly deferred;
- no architecture/product decision was added;
- only documentation/master-list files were modified.

## Handoff

Return:

- files changed
- exact stale statements reconciled
- AC1–AC5 mapping
- final Concepts
- final Tools
- deferred gates preserved
- warnings retained
- production/code/config files changed: NO
- decisions needed: NONE

Successful status:

`READY_FOR_SPECIALIST_REVIEW — STEP 8.2 DOCS CLOSEOUT`
