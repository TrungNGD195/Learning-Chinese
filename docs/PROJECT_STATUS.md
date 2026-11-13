# Current project status

Last verified deployed application release: 2026-11-13, commit 501e157.
This is an orientation note, not PM acceptance of an implementation Step.
Authoritative specifications and decisions remain in Spec-CURRENT.

## Application

- Web: https://hanfolio-mcbo1.vercel.app
- Backend: https://backend-production-bc51b.up.railway.app
- Learners use the curriculum, pronunciation, lessons, practice and profile.
  The student AI assistant and journey-map prototypes have been removed.
- Administrators manage lesson theory, practice and publication in one editor.
- FastAPI, PostgreSQL/pgvector, SQLAlchemy and Alembic form the backend;
  React, TypeScript, Vite and TanStack Query form the frontend.
- Production uses the existing learning-only mode: KNOWLEDGE_AI_ENABLED=false.
  Document processing/retrieval AI is disabled. Source code for provider and
  evaluation tooling remains available for future work.
- The current pronunciation player and recording rights are documented in
  [Mandarin audio](mandarin-audio.md) and [third-party notices](third-party-notices.md).

## Modal work remains paused

Step 8.3 Stage B T4 validation stopped because Modal required a payment method.
No completed cache population, T4 parity/benchmark validation, production
embedding profile or production re-embedding is claimed. Paid overage,
adding a payment method and changing GPU tier are outside the authorized
boundary. Do not resume those operations without the user's instruction.
See the [PM Decision Log](../Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md).

## Development and operations

Use the [project README](../README.md) for setup and reproducible checks, and
[deployment instructions](deployment-railway-vercel.md) for release operations.
Database-backed tests must use the separate test database. Secrets belong in
ignored environment files; uploaded documents, databases and model data remain
local/runtime storage. Never overwrite production with local test data.
Versioned evaluation assets remain under evaluation/; they are not runtime
learning content. See the [documentation index](README.md) for maintained guides.
