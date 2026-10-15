# Project status and study handoff

This document is a practical orientation note. The authoritative project state remains in `Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md` and each frozen task under `codex-tasks/`. Recheck those files before implementation; this summary does not accept or close a project Step.

## Product and architecture

- Product: a Chinese-learning platform for Vietnamese learners, with structured lessons and a lesson-aware AI assistant.
- Backend: FastAPI modular monolith, PostgreSQL/pgvector, SQLAlchemy, Alembic, and provider boundaries for AI capabilities.
- Frontend: React, TypeScript, Vite, TanStack Query, and Vitest; Playwright supports browser journeys.
- Main product areas in the repository: learner curriculum and assessments, admin content management, document/knowledge ingestion, lesson chat and citations, AI grading, and AI-assisted assessment drafting.
- Evaluation assets are versioned separately under `evaluation/`; evaluation expectations are not runtime ground truth.

## Repository orientation

Start with:

1. `Spec-CURRENT/PROJECT_CONTEXT.md` for product and architecture context.
2. `Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md` for frozen decisions and open gates.
3. `Spec-CURRENT/PM-Control/05-Codex-Execution-Protocol.md` for implementation workflow.
4. The exact step task under `codex-tasks/` before changing code.
5. The related `docs/` note and tests for the current implementation.

Current source layout:

```text
backend/       API, domain modules, migrations, tests, local config
frontend/      learner/admin UI, API client, component and browser tests
evaluation/    dataset schemas, fixtures, validators, and run tooling
docs/          step notes and handoffs by backend/data/AI/frontend/evaluation/QA
Spec-CURRENT/  product specifications and PM control documents
codex-tasks/   frozen and draft execution packets, grouped by phase
infra/         local PostgreSQL initialization
```

## Implementation history at a glance

The working tree contains implementations and documentation across backend foundation/auth/conversation, frontend learning/admin flows, knowledge ingestion, retrieval/RAG, grading and assessment generation, evaluation tooling, product QA, CI, and BGE runtime profiling. Individual code presence does not establish specialist approval or PM acceptance. Use the decision log and each step’s handoff for exact status.

## Current pause: Step 8.3 Stage B

- Stage B was authorized only within the included Modal compute allowance; payment method addition and paid overage are prohibited.
- Billing-before evidence was captured locally.
- The cache-population invocation stopped when Modal reported: `Please add a payment method to use T4 GPU functions.`
- Exact model cache population did not complete. No T4 parity or benchmark run occurred, and no billing-after evidence or final real-measurements artifact exists.
- No production Modal embedding profile was created or activated; production data was not re-embedded; `RAG_MIN_RERANK_SCORE` and D-005 were not changed.
- The user has paused deployment work to study. Do not resume Modal operations until the user decides to continue, and do not work around the payment-method stop by adding payment or changing GPU tier.

## Local setup notes

- Backend requires Python 3.12 and `uv`; dependency versions are locked in `backend/uv.lock`.
- Frontend requires Node.js 22.12+ and npm; use `npm ci` from `frontend/`.
- Local configuration belongs in ignored `.env` files copied from `.env.example`. Never put secrets in source control.
- PostgreSQL data, uploaded/raw content, derived storage, model caches, virtual environments, and generated test workspaces are machine-local and excluded from Git.
- The local Compose database is for development only. It does not replace the dedicated PostgreSQL test database required by DB-backed verification.

## Before resuming implementation

1. Read the latest PM Decision Log and relevant frozen task.
2. Check `git status` and preserve unrelated local changes.
3. Confirm database target and isolation before any migration or DB-backed tests.
4. Confirm provider credentials and cost authorization before real external/model calls.
5. Run only verification required by the selected task; report blockers without changing frozen architecture or thresholds.
