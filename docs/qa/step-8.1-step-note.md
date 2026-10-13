# Step 8.1 — Product QA & End-to-End Verification

## Objective

Verify critical learner and Admin journeys across browser, React, FastAPI, PostgreSQL, persistence, and deterministic AI test seams.

## Why

Component tests alone do not verify cookies, route transitions, backend authorization, persisted progression, or the difference between semantic refusal and technical AI failure.

## Mental Model

```text
Browser → React → FastAPI → PostgreSQL / deterministic AI boundary
        ← asserted user-visible result and freshly-read business state
```

## Core Knowledge

- **End-to-End Testing | SYSTEM** — verifies a small set of complete user journeys.
- **Test Pyramid / Test Scope | SYSTEM** — browser checks journeys; API integration checks business invariants; unit tests retain focused logic coverage.
- **Deterministic Test Fixture | BOTH** — stable seeded rows and fake AI outputs produce reproducible evidence.
- **Test Environment Isolation | SYSTEM** — destructive reset requires test mode, a dedicated loopback PostgreSQL database, pgvector, and current Alembic head.
- **Authorization Boundary Testing | SYSTEM** — UI guards improve navigation; backend checks enforce access.
- **Failure-Semantics Verification | BOTH** — technical failure remains distinct from no evidence, UNCERTAIN, and ordinary grading results.
- **Release Checklist | SYSTEM** — evidence states remain PASS, FAIL, ENVIRONMENT_GATE, or DEFERRED_EVALUATION_GATE.

## Data Flow

Playwright starts a local Vite server and a test-only FastAPI entrypoint. The backend connects to `TEST_DATABASE_URL`. A guarded reset seeds required lookup rows and a minimal lesson/assessment fixture. Test-only chat, grading, and generation implementations replace paid/model boundaries. Browser actions call the real application APIs and assert fresh persisted state. Global teardown restores the dedicated DB to required lookup rows.

## Key Design Decisions

- D-111 selected exactly one browser framework: Playwright, because repository preflight found Vitest/RTL but no configured browser E2E framework.
- Vitest remains limited to `frontend/src/**/*.{test,spec}.{ts,tsx}`; Playwright owns `frontend/e2e/`.
- Windows test ASGI runner selects SelectorEventLoop for async psycopg; the production app is unchanged.
- Seed/reset require explicit flags and the reset helper rechecks database identity, environment, pgvector, and migration head before destructive work.
- Browser-level AI responses are deterministic and make no paid or external calls.
- B1 completion uses the existing pronunciation read/write contract and invalidates backend-owned progression reads. B4 membership uses published-candidate discovery and the existing full-replacement curriculum PUT; publish alone does not create membership.

## Reusable Testing Approach

- Frontend: `npm ci`, `npm run test -- --run`, `npm run build`, `npm run lint`, `npm run api:check`.
- Browser: from `frontend/`, `npm run test:e2e`; Playwright guarded global setup resets and seeds the dedicated DB, then guarded teardown resets it.
- API/regression: focused PostgreSQL pytest groups for auth, progression, conversations, documents, grading, generation, RAG, and offline regression.
- Backend syntax: from `backend/`, `python -m compileall -q app`.
- Use test-only fakes at existing dependency/provider seams. Never use SQLite, production data, paid AI, or live search.

## Common Mistakes

- Treating a working route as proof that the requested interaction can be completed.
- Marking a test PASS after reaching a screen while the required action is absent.
- Treating `NO_EVIDENCE` as a successful technical-failure outcome.
- Assuming frontend route guards replace backend authorization.
- Reusing test DB rows across browser runs without guarded reset/cleanup.
- Converting deferred Phase-7 evaluation gates into deterministic QA passes.

## Definition of Done

The deterministic QA implementation and focused B1/B4 product rework are reviewable. Passing these journeys does not close Step 8.1 or grant product-release approval. Official Phase-7 evaluation gates remain separate and were not run as part of this rework.

## Concepts Discovered

- End-to-End Testing | SYSTEM
- Test Pyramid / Test Scope | SYSTEM
- Deterministic Test Fixture | BOTH
- Test Environment Isolation | SYSTEM
- Authorization Boundary Testing | SYSTEM
- Failure-Semantics Verification | BOTH
- Release Checklist | SYSTEM

## Tools Used

- pytest | SYSTEM
- PostgreSQL | SYSTEM
- pgvector | SYSTEM
- Vitest | SYSTEM
- React Testing Library | SYSTEM
- Playwright | SYSTEM
- Chromium | SYSTEM
- FastAPI | SYSTEM
- Vite | SYSTEM
