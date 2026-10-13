# Step 8.2 — Containerized Development and CI Step Note

## Objective

Make the accepted development and deterministic verification path reproducible from locked dependencies and a disposable local PostgreSQL+pgvector service.

## Architecture boundary

```text
Docker Compose: PostgreSQL 17 + pgvector 0.8.6 only
Host: FastAPI / uv, Vite / npm, Playwright / Chromium
GitHub Actions: migrations, backend/frontend gates, API contract, browser E2E
```

## Concepts Discovered

- Reproducible Environment | SYSTEM | MUST KNOW
- Container / Container Image | SYSTEM | MUST KNOW
- Docker Compose | SYSTEM | MUST KNOW
- CI Pipeline | SYSTEM | MUST KNOW
- Environment Variables / Secrets | SYSTEM | MUST KNOW
- Migration Validation | SYSTEM | MUST KNOW
- Deterministic Test Boundary | BOTH | MUST KNOW
- Health Check | SYSTEM | SHOULD KNOW
- Dependency Caching | SYSTEM | SHOULD KNOW

## Tools Used

- Docker | SYSTEM
- Docker Compose | SYSTEM
- GitHub Actions | SYSTEM
- PostgreSQL | SYSTEM
- pgvector | SYSTEM
- Alembic | SYSTEM
- uv | SYSTEM
- npm | SYSTEM
- pytest | SYSTEM
- Vitest / RTL | SYSTEM
- Playwright | SYSTEM
- Oxlint | SYSTEM

## Scope notes

- Compose starts only the database; app and browser processes remain native.
- Test DB reset continues to require explicit confirmation and validates dedicated database identity, loopback, pgvector, and the current migration graph before truncation.
- CI uses only deterministic test seams and local-only credentials. Official Phase 7 evaluation gates remain deferred.
- Step 8.1 B1/B4 product behavior is preserved; no product API, schema, dependency, or runtime behavior is added by this step.
