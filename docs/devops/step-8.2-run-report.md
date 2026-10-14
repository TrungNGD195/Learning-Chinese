# Step 8.2 — Development and CI Run Report

## Status

- Gate A — LOCAL RUNTIME: **CLOSED**
- Gate B — HOSTED CI: **CLOSED**
- Implementation and verification criteria are satisfied; PM final Step acceptance is pending documentation review.

## Gate A — Local Runtime

Accepted local verification evidence:

| Area | Result |
|---|---|
| Runtime | PostgreSQL 17 with pgvector 0.8.6; one database-only Compose service |
| Fresh migrations | Development and test databases migrated from 0001 through 0012 |
| Current migration | `0012_vector_storage_readiness` (head) |
| Alembic check | PASS — no new upgrade operations |
| pgvector | Verified in both databases |
| Backend | 1,152 passed, 1 skipped, 0 failed |
| Frontend install | `npm ci` PASS |
| Frontend lint | PASS, 0 errors; warnings retained below |
| Vitest / RTL | 14 files, 326 tests PASS |
| Production build | PASS; existing Vite chunk-size warning retained below |
| API contract | Live `api:check` PASS |
| Browser | Deterministic, one-worker Playwright Chromium suite: 6/6 PASS |

## Gate B — Hosted CI

Accepted GitHub-hosted Actions evidence:

- `.github/workflows/ci.yml` quality job: **PASS**, approximately 3m05s.
- Hosted Vitest: 14/14 files and 326/326 tests passed.
- The Linux workflow runs locked installs, database migrations and identity checks, backend compile/full pytest, frontend lint/tests/build, live API contract validation, and deterministic Chromium Playwright.
- Required checks fail the workflow through normal command exit status.

Hosted-only issues resolved:

1. Invalid `setup-uv` action reference replaced with a valid setup-uv action reference.
2. Four backend scenarios now establish required system seed explicitly; no global CI seed command was added.
3. Step 7.7 manifest tests now use a deterministic `_code_commit()` seam; the production runner is unchanged.

## Non-blocking Observations

- SQLAlchemy reports an existing cyclic-FK/table-cycle `SAWarning` during migration checks.
- Frontend lint has warnings but zero errors.
- Vite reports a bundle chunk larger than 500 kB.
- `npm ci` reports one high-severity advisory in the existing lockfile. Its production-versus-development scope is currently unclassified and non-blocking for frozen Step 8.2. No `npm audit fix` was run.

## Secrets and Safety

- Compose binds PostgreSQL to loopback and uses local-development defaults from placeholder configuration.
- Workflow database/signing values are test-only and are not production credentials.
- `.env` files, database volumes, and provider credentials are not cached.
- Routine CI does not require LLM credentials or call paid providers or live external retrieval.

## Deferred Evaluation Gates

The following official gates remain deferred and were not run or marked PASS by Step 8.2 CI:

- Step 7.4 — official generation evaluation
- Step 7.5 — official end-to-end RAG evaluation
- Step 7.7 — official grading/generation evaluation
- Step 7.6 — official regression evaluation

## Scope

No product API, schema, production runtime, or deployment behavior is claimed by this report. Step 8.3 has not been started.
